import bpy
import logging
from ..constants import BSDF_COMPATIBILITY_MAP, SOCKET_DEFAULT_TYPE, SYSTEM_NAMES
from . import compat

logger = logging.getLogger(__name__)

def bake_node_to_image(context, material, node, settings):
    """
    Bake a specific node output to an image.
    
    Args:
        context: Blender context
        material: Material containing the node
        node: Node to bake
        settings: BakeNodeSettings with resolution, margin, etc.
    
    Returns:
        bpy.types.Image: The baked image, or None on failure
    """
    from .image_manager import set_image, save_image
    from .common import safe_context_override
    
    if not (material and node):
        logger.warning("bake_node_to_image: Invalid material or node")
        return None
        
    img = set_image(f"{material.name}_{node.name}", settings.res_x, settings.res_y)
    
    # Store original engine
    orig_engine = context.scene.render.engine
    context.scene.render.engine = 'CYCLES'
    
    try:
        with safe_context_override(context, context.active_object):
            with NodeGraphHandler([material]) as h:
                tree = material.node_tree
                out = next((n for n in tree.nodes if n.bl_idname=='ShaderNodeOutputMaterial' and n.is_active_output), None)
                if out:
                    emi = h._add_node(material, 'ShaderNodeEmission', location=(out.location.x-200, out.location.y))
                    tree.links.new(node.outputs[0], emi.inputs[0])
                    tree.links.new(emi.outputs[0], out.inputs[0])
                    
                    # Use compatibility layer for bake settings
                    compat.set_bake_type(context.scene, 'EMIT')
                    
                    bpy.ops.object.bake(
                        type='EMIT',
                        margin=settings.margin,
                        use_clear=True,
                        target='IMAGE_TEXTURES'
                    )
                    
                    if settings.use_external_save:
                        save_image(img, settings.external_save_path, file_format=settings.image_settings.external_save_format)
                    else:
                        img.pack()
                        
        return img
    except Exception as e:
        logger.exception(f"Node baking failed: {e}")
        return None
    finally:
        context.scene.render.engine = orig_engine

class NodeGraphHandler:
    def __init__(self, materials):
        self.materials = [m for m in materials if m and hasattr(m, 'use_nodes') and m.use_nodes]
        self.session_nodes = {}
        self.temp_logic_nodes = {}
        self.temp_attributes = []
        self.original_links = {}

    def __enter__(self): 
        self._prepare_session_nodes()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb): 
        self.cleanup()
        return False

    def _prepare_session_nodes(self):
        for mat in self.materials:
            tree = mat.node_tree
            tex_n = tree.nodes.new('ShaderNodeTexImage')
            emi_n = tree.nodes.new('ShaderNodeEmission')
            tex_n["is_bt_temp"] = True
            emi_n["is_bt_temp"] = True
            
            self.session_nodes[mat] = {
                'tex': tex_n,
                'emi': emi_n
            }
            self.session_nodes[mat]['tex'].location = (-800, 500)
            self.session_nodes[mat]['emi'].location = (600, 0)
            self.temp_logic_nodes[mat] = []

    def cleanup(self):
        # 1. Clean up all materials that had nodes added (including protected ones)
        for mat in list(self.temp_logic_nodes.keys()):
            if not mat or not hasattr(mat, "node_tree") or not mat.node_tree: continue
            tree = mat.node_tree
            
            # Remove session nodes if this material was one of the active ones
            if mat in self.session_nodes:
                for n in self.session_nodes[mat].values():
                    try: tree.nodes.remove(n)
                    except Exception: pass
            
            # Remove all temp logic nodes securely
            if mat in self.temp_logic_nodes:
                # Iterate backwards to avoid index shift issues
                nodes = self.temp_logic_nodes[mat]
                for n in reversed(nodes):
                    try:
                        if n in tree.nodes.values():
                            tree.nodes.remove(n)
                    except Exception: pass
                self.temp_logic_nodes[mat] = []
        
        # 2. Restore original links
        for mat, link_info in self.original_links.items():
            if not mat or not mat.node_tree: continue
            try:
                out_n = self._find_output(mat.node_tree)
                if out_n and link_info:
                    from_socket, to_socket_idx = link_info
                    # Ensure the from_socket belongs to a node that still exists
                    if from_socket and from_socket.node and from_socket.node.name in mat.node_tree.nodes:
                        mat.node_tree.links.new(from_socket, out_n.inputs[to_socket_idx])
            except Exception: pass
        
        # 3. Clean up temp attributes
        for obj, attr in self.temp_attributes:
            try: 
                if attr in obj.data.attributes:
                    obj.data.attributes.remove(obj.data.attributes[attr])
            except Exception: pass

        # 4. Explicitly remove the protection dummy image if it has no users left
        d = bpy.data.images.get(SYSTEM_NAMES['DUMMY_IMG'])
        if d and d.users == 0:
            try: bpy.data.images.remove(d)
            except Exception: pass

    def setup_protection(self, objects=None, active_materials=None):
        """
        Ensure non-active materials on objects have an active texture node 
        to prevent Blender's baker from potentially using wrong nodes.
        Uses a temporary dummy image that shouldn't be saved.
        """
        # Fallback to instance materials if not provided
        if not objects:
            # Heuristic: We don't have objects, so we can't find 'other' materials to protect.
            return
        if active_materials is None:
            active_materials = self.materials
            
        active_set = set(active_materials)
        d = bpy.data.images.get(SYSTEM_NAMES['DUMMY_IMG']) or bpy.data.images.new(SYSTEM_NAMES['DUMMY_IMG'], 32, 32, alpha=True)
        # Ensure it doesn't persist after nodes are gone
        d.use_fake_user = False 
        
        for obj in objects:
            if obj.type != 'MESH': continue
            for s in obj.material_slots:
                m = s.material
                # Skip linked (read-only) materials OR materials already in our active bake set
                if m and m.use_nodes and m not in active_set:
                    if m.library:
                        logger.debug(f"Skipping protection for library material: {m.name}")
                        continue
                    # 将节点添加到材质的树中 // Add node to material's tree
                    # NodeGraphHandler 将在 temp_logic_nodes[m] 中跟踪该节点
                    self._add_node(m, 'ShaderNodeTexImage', image=d, name=SYSTEM_NAMES['PROTECTION_NODE'], label=SYSTEM_NAMES['PROTECTION_LABEL'])

    def setup_for_pass(self, bake_pass, socket_name, image, mesh_type=None, attr_name=None, channel_settings=None):
        for mat in self.materials:
            tree = mat.node_tree
            out_n = self._find_output(tree)
            if not out_n or mat not in self.session_nodes: continue
            
            for n in self.temp_logic_nodes[mat]:
                try: tree.nodes.remove(n)
                except Exception: pass
            self.temp_logic_nodes[mat] = []

            if mat not in self.original_links:
                # Find which input was linked (usually 0, but safety first)
                socket = out_n.inputs[0]
                self.original_links[mat] = (socket.links[0].from_socket, 0) if socket.is_linked else None

            s_nodes = self.session_nodes[mat]
            tex_n, emi_n = s_nodes['tex'], s_nodes['emi']
            
            tex_n.image = image
            tree.nodes.active = tex_n
            
            needs_emit = (bake_pass == 'EMIT' or mesh_type or socket_name.startswith('pbr_conv') or socket_name == 'node_group')
            
            if needs_emit:
                tree.links.new(emi_n.outputs[0], out_n.inputs[0])
                src = None
                if mesh_type: src = self._create_mesh_map_logic(mat, mesh_type, attr_name, channel_settings)
                elif socket_name.startswith('pbr_conv'): src = self._create_extension_logic(mat, socket_name, channel_settings)
                elif socket_name == 'node_group': src = self._create_node_group_logic(mat, channel_settings)
                else: src = self._find_socket_source(mat, socket_name, channel_settings)
                
                if src: tree.links.new(src, emi_n.inputs[0])

    def _create_node_group_logic(self, mat, s):
        es = getattr(s, "extension_settings", None)
        if not es or not es.node_group: return None
        ng_data = bpy.data.node_groups.get(es.node_group)
        if not ng_data: return None
        grp = self._add_node(mat, 'ShaderNodeGroup')
        grp.node_tree = ng_data
        return grp.outputs.get(es.output_name) if es.output_name else (grp.outputs[0] if grp.outputs else None)

    def _add_node(self, mat, node_type, **kwargs):
        """通用节点添加辅助函数，自动管理生命周期"""
        n = mat.node_tree.nodes.new(node_type)
        n["is_bt_temp"] = True
        for k, v in kwargs.items():
            if hasattr(n, k): setattr(n, k, v)
        if mat not in self.temp_logic_nodes: self.temp_logic_nodes[mat] = []
        self.temp_logic_nodes[mat].append(n)
        return n

    def _find_output(self, tree):
        for n in tree.nodes:
            if n.bl_idname == 'ShaderNodeOutputMaterial' and n.is_active_output: return n
        return next((n for n in tree.nodes if n.bl_idname == 'ShaderNodeOutputMaterial'), None)

    def _find_socket_source(self, mat, socket_name, settings):
        tree = mat.node_tree
        # 1. Try to find Principled BSDF
        bsdf = next((n for n in tree.nodes if n.bl_idname=='ShaderNodeBsdfPrincipled'), None)
        found = None
        if bsdf:
            for cand in BSDF_COMPATIBILITY_MAP.get(socket_name, [socket_name]):
                if cand in bsdf.inputs: found = bsdf.inputs[cand]; break
        
        # 2. Fallback: If no BSDF but baking Color/Emit, look for Emission node
        if not found and socket_name in {'color', 'emi'}:
            emi = next((n for n in tree.nodes if n.bl_idname=='ShaderNodeEmission'), None)
            if emi: found = emi.inputs['Color']
            
        src = None
        if found and found.is_linked: src = found.links[0].from_socket
        else:
            val = found.default_value if found else SOCKET_DEFAULT_TYPE.get(socket_name, (0,0,0,1))
            rgb = self._add_node(mat, 'ShaderNodeRGB')
            v = (val[0],val[1],val[2],1) if hasattr(val,"__len__") and len(val)>=3 else (val,val,val,1)
            rgb.outputs[0].default_value = v
            src = rgb.outputs[0]
        
        # Roughness inversion logic
        if settings and socket_name == 'rough' and settings.rough_inv:
            inv = self._add_node(mat, 'ShaderNodeInvert'); inv.inputs[0].default_value=1.0
            tree.links.new(src, inv.inputs[1]); src = inv.outputs[0]
        return src

    def _create_mesh_map_logic(self, mat, mtype, attr, s):
        ms = getattr(s, "mesh_settings", None)
        if mtype == 'ID': return self._add_node(mat, 'ShaderNodeAttribute', attribute_name=attr).outputs['Color']
        elif mtype == 'AO':
            n = self._add_node(mat, 'ShaderNodeAmbientOcclusion')
            n.samples = ms.samples if ms else 16; n.inputs['Distance'].default_value = ms.distance if ms else 1.0
            n.inside = ms.inside if ms else False; return n.outputs['Color']
        elif mtype == 'POS': return self._add_node(mat, 'ShaderNodeNewGeometry').outputs['Position']
        elif mtype == 'UV': return self._add_node(mat, 'ShaderNodeUVMap').outputs['UV']
        elif mtype == 'WF':
            n = self._add_node(mat, 'ShaderNodeWireframe'); n.use_pixel_size = ms.use_pixel_size if ms else False
            n.inputs[0].default_value = ms.distance if ms else 0.01; return n.outputs[0]
        elif mtype == 'BEVEL':
            n = self._add_node(mat, 'ShaderNodeBevel'); n.samples = ms.samples if ms else 8
            n.inputs['Radius'].default_value = ms.radius if ms else 0.05; return n.outputs[0]
        return None

    def _create_extension_logic(self, mat, socket_name, settings):
        es = getattr(settings, "extension_settings", None)
        threshold = es.threshold if es else 0.04
        tree = mat.node_tree
        spec_src = self._find_socket_source(mat, 'specular', None)
        sep = self._add_node(mat, 'ShaderNodeSeparateColor'); tree.links.new(spec_src, sep.inputs[0])
        math1 = self._add_node(mat, 'ShaderNodeMath', operation='MAXIMUM')
        tree.links.new(sep.outputs[0], math1.inputs[0]); tree.links.new(sep.outputs[1], math1.inputs[1])
        math2 = self._add_node(mat, 'ShaderNodeMath', operation='MAXIMUM')
        tree.links.new(math1.outputs[0], math2.inputs[0]); tree.links.new(sep.outputs[2], math2.inputs[1])
        sub = self._add_node(mat, 'ShaderNodeMath', operation='SUBTRACT')
        tree.links.new(math2.outputs[0], sub.inputs[0]); sub.inputs[1].default_value = threshold
        div = self._add_node(mat, 'ShaderNodeMath', operation='DIVIDE')
        tree.links.new(sub.outputs[0], div.inputs[0]); div.inputs[1].default_value = max(1e-5, 1.0 - threshold)
        clamp = self._add_node(mat, 'ShaderNodeClamp'); tree.links.new(div.outputs[0], clamp.inputs[0])
        metallic_out = clamp.outputs[0]
        if socket_name == 'pbr_conv_metal': return metallic_out
        elif socket_name == 'pbr_conv_base':
            diff_src = self._find_socket_source(mat, 'color', None)
            
            # 创建 Mix 节点 (B3.4+ ShaderNodeMix / Legacy ShaderNodeMixRGB)
            from . import compat
            if compat.is_blender_4() or compat.is_blender_5():
                mix = self._add_node(mat, 'ShaderNodeMix')
                mix.data_type = 'RGBA'
                tree.links.new(metallic_out, mix.inputs[0])  # Factor
                # B4+ Mix node: inputs索引: 0=Factor, 6=A(RGBA), 7=B(RGBA)
                sock_a = mix.inputs[6] if len(mix.inputs) > 6 else None
                sock_b = mix.inputs[7] if len(mix.inputs) > 7 else None
            else:
                mix = self._add_node(mat, 'ShaderNodeMixRGB')
                tree.links.new(metallic_out, mix.inputs[0])  # Fac
                sock_a = mix.inputs.get('Color1', mix.inputs[1] if len(mix.inputs) > 1 else None)
                sock_b = mix.inputs.get('Color2', mix.inputs[2] if len(mix.inputs) > 2 else None)
            
            if sock_a is None or sock_b is None:
                logger.warning("PBR Conv: Mix node socket not found, skipping.")
                return None
            
            tree.links.new(diff_src, sock_a)
            tree.links.new(spec_src, sock_b)
            # 输出: B4+ ShaderNodeMix outputs[2]=Result(RGBA); Legacy MixRGB outputs[0]=Color
            result_output = mix.outputs[2] if (compat.is_blender_4() or compat.is_blender_5()) else mix.outputs[0]
            return result_output
        return None
