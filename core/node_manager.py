import bpy
import logging
from ..constants import BSDF_COMPATIBILITY_MAP, SOCKET_DEFAULT_TYPE

logger = logging.getLogger(__name__)

class NodeGraphHandler:
    def __init__(self, materials):
        self.materials = [m for m in materials if m and m.use_nodes]
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
            self.session_nodes[mat] = {
                'tex': tree.nodes.new('ShaderNodeTexImage'),
                'emi': tree.nodes.new('ShaderNodeEmission')
            }
            self.session_nodes[mat]['tex'].location = (-800, 500)
            self.session_nodes[mat]['emi'].location = (600, 0)
            self.temp_logic_nodes[mat] = []

    def cleanup(self):
        # 1. Clean up all materials that had nodes added (including protected ones)
        for mat in list(self.temp_logic_nodes.keys()):
            if not mat or not mat.node_tree: continue
            tree = mat.node_tree
            
            # Remove session nodes if this material was one of the active ones
            if mat in self.session_nodes:
                for n in self.session_nodes[mat].values():
                    try: tree.nodes.remove(n)
                    except: pass
            
            # Remove all temp logic nodes
            if mat in self.temp_logic_nodes:
                for n in self.temp_logic_nodes[mat]:
                    try: tree.nodes.remove(n)
                    except: pass
        
        # 2. Restore original links
        for mat, link_info in self.original_links.items():
            if not mat or not mat.node_tree: continue
            try:
                out_n = self._find_output(mat.node_tree)
                if out_n and link_info:
                    from_node, from_socket = link_info
                    if from_node and from_node.name in mat.node_tree.nodes:
                        mat.node_tree.links.new(from_socket, out_n.inputs[0])
            except: pass
        
        # 3. Clean up temp attributes
        for obj, attr in self.temp_attributes:
            try: 
                if attr in obj.data.attributes:
                    obj.data.attributes.remove(obj.data.attributes[attr])
            except: pass

        # 4. Explicitly remove the protection dummy image if it has no users left
        d = bpy.data.images.get("BT_Protection_Dummy")
        if d and d.users == 0:
            try: bpy.data.images.remove(d)
            except: pass

    def setup_protection(self, objects, active_materials):
        """
        Ensure non-active materials on objects have an active texture node 
        to prevent Blender's baker from potentially using wrong nodes.
        Uses a temporary dummy image that shouldn't be saved.
        """
        active_set = set(active_materials)
        d = bpy.data.images.get("BT_Protection_Dummy") or bpy.data.images.new("BT_Protection_Dummy", 32, 32, alpha=True)
        # Ensure it doesn't persist after nodes are gone
        d.use_fake_user = False 
        
        for obj in objects:
            if obj.type != 'MESH': continue
            for s in obj.material_slots:
                m = s.material
                # Skip linked (read-only) materials
                if m and m.use_nodes and m not in active_set and not m.library:
                    # We add a node to the material's tree. 
                    # The NodeGraphHandler will track this in temp_logic_nodes[m]
                    self._add_node(m, 'ShaderNodeTexImage', image=d)

    def setup_for_pass(self, bake_pass, socket_name, image, mesh_type=None, attr_name=None, channel_settings=None):
        for mat in self.materials:
            tree = mat.node_tree
            out_n = self._find_output(tree)
            if not out_n or mat not in self.session_nodes: continue
            
            for n in self.temp_logic_nodes[mat]:
                try: tree.nodes.remove(n)
                except: pass
            self.temp_logic_nodes[mat] = []

            if mat not in self.original_links:
                socket = out_n.inputs[0]
                self.original_links[mat] = (socket.links[0].from_node, socket.links[0].from_socket) if socket.is_linked else None

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
        if not s or not s.node_group: return None
        ng_data = bpy.data.node_groups.get(s.node_group)
        if not ng_data: return None
        grp = self._add_node(mat, 'ShaderNodeGroup')
        grp.node_tree = ng_data
        return grp.outputs.get(s.node_group_output) if s.node_group_output else (grp.outputs[0] if grp.outputs else None)

    def _add_node(self, mat, type, **kwargs):
        n = mat.node_tree.nodes.new(type)
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
        if settings and socket_name == 'rough' and getattr(settings, 'rough_inv', False):
            inv = self._add_node(mat, 'ShaderNodeInvert'); inv.inputs[0].default_value=1.0
            tree.links.new(src, inv.inputs[1]); src = inv.outputs[0]
        return src

    def _create_mesh_map_logic(self, mat, mtype, attr, s):
        if mtype == 'ID': return self._add_node(mat, 'ShaderNodeAttribute', attribute_name=attr).outputs['Color']
        elif mtype == 'AO':
            n = self._add_node(mat, 'ShaderNodeAmbientOcclusion')
            n.samples = getattr(s, 'ao_sample', 16); n.inputs['Distance'].default_value = getattr(s, 'ao_dis', 1.0)
            n.inside = getattr(s, 'ao_inside', False); return n.outputs['Color']
        elif mtype == 'POS': return self._add_node(mat, 'ShaderNodeNewGeometry').outputs['Position']
        elif mtype == 'UV': return self._add_node(mat, 'ShaderNodeUVMap').outputs['UV']
        elif mtype == 'WF':
            n = self._add_node(mat, 'ShaderNodeWireframe'); n.use_pixel_size = getattr(s, 'wireframe_use_pix', False)
            n.inputs[0].default_value = getattr(s, 'wireframe_dis', 0.01); return n.outputs[0]
        elif mtype == 'BEVEL':
            n = self._add_node(mat, 'ShaderNodeBevel'); n.samples = getattr(s, 'bevel_sample', 8)
            n.inputs['Radius'].default_value = getattr(s, 'bevel_rad', 0.05); return n.outputs[0]
        return None

    def _create_extension_logic(self, mat, socket_name, settings):
        threshold = getattr(settings, 'pbr_conv_threshold', 0.04) if settings else 0.04
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
            mix = self._add_node(mat, 'ShaderNodeMix', data_type='RGBA')
            tree.links.new(metallic_out, mix.inputs[0])
            tree.links.new(diff_src, mix.inputs[6]); tree.links.new(spec_src, mix.inputs[7])
            return mix.outputs[2]
        return None
