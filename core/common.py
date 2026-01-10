import bpy
import logging
from contextlib import contextmanager
from ..constants import CHANNEL_DEFINITIONS, BSDF_COMPATIBILITY_MAP

logger = logging.getLogger(__name__)

def get_safe_base_name(setting, obj, mat=None, is_batch=False):
    """Naming convention logic."""
    mode = setting.bake_mode
    m = setting.name_setting
    base = "Bake"
    
    if m == 'CUSTOM':
        base = setting.custom_name
        if is_batch:
            suffix = f"_{obj.name}"
            if mode == 'SPLIT_MATERIAL' and mat:
                suffix += f"_{mat.name}"
            base += suffix
    elif m == 'OBJECT': 
        base = obj.name
    elif m == 'MAT': 
        base = mat.name if mat else "NoMat"
        if is_batch and mode == 'SPLIT_MATERIAL':
            base = f"{obj.name}_{base}"
    elif m == 'OBJ_MAT': 
        base = f"{obj.name}_{mat.name if mat else 'NoMat'}"
        
    return bpy.path.clean_name(base)

def check_objects_uv(objects):
    """Return objects missing UVs."""
    return [obj.name for obj in objects if obj.type == 'MESH' and not obj.data.uv_layers]

def reset_channels_logic(setting):
    """Sync channel collection with definitions."""
    defs = []
    b_type = setting.bake_type
    
    key = ('BSDF_4' if bpy.app.version >= (4, 0, 0) else 'BSDF_3') if b_type == 'BSDF' else b_type
    defs.extend(CHANNEL_DEFINITIONS.get(key, []))
    
    if setting.use_light_map: defs.extend(CHANNEL_DEFINITIONS.get('LIGHT', []))
    if setting.use_mesh_map: defs.extend(CHANNEL_DEFINITIONS.get('MESH', []))
    if setting.use_extension_map: defs.extend(CHANNEL_DEFINITIONS.get('EXTENSION', []))
    
    target_ids = {d['id']: d for d in defs}
    
    for i in range(len(setting.channels)-1, -1, -1):
        if setting.channels[i].id not in target_ids:
            setting.channels.remove(i)
            
    existing = {c.id: c for c in setting.channels}
    
    for d in defs:
        d_id = d['id']
        if d_id not in existing:
            new_chan = setting.channels.add()
            new_chan.id = d_id
            new_chan.name = d['name']
            defaults = d.get('defaults', {})
            for k, v in defaults.items():
                if hasattr(new_chan, k): setattr(new_chan, k, v)
        else:
            existing[d_id].name = d['name']

@contextmanager
def safe_context_override(context, active_object=None, selected_objects=None):
    """Safe temp_override."""
    kw = {}
    if active_object:
        kw['active_object'] = active_object
        kw['object'] = active_object
    if selected_objects:
        kw['selected_objects'] = selected_objects
        kw['selected_editable_objects'] = selected_objects
    
    with context.temp_override(**kw):
        yield

class SceneSettingsContext:
    """Safely apply and restore scene/render settings."""
    def __init__(self, category, settings):
        self.category = category
        self.settings = settings
        self.original = {}
        self.attr_map = {
            'scene': {'res_x': 'resolution_x', 'res_y': 'resolution_y', 'res_pct': 'resolution_percentage'}
        }

    def _get_target(self):
        scene = bpy.context.scene
        if self.category == 'scene': return scene.render
        if self.category == 'cycles': return scene.cycles
        if self.category == 'image': return scene.render.image_settings
        if self.category == 'cm': return scene.view_settings
        return None

    def __enter__(self):
        target = self._get_target()
        if not target or not self.settings: return self
        
        mapping = self.attr_map.get(self.category, {})
        for k, v in self.settings.items():
            real_key = mapping.get(k, k)
            if hasattr(target, real_key):
                self.original[real_key] = getattr(target, real_key)
                if v is not None:
                    try: setattr(target, real_key, v)
                    except Exception as e:
                        logger.warning(f"Failed to set {self.category}.{real_key}: {e}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        target = self._get_target()
        if not target: return
        for k, v in self.original.items():
            try: setattr(target, k, v)
            except: pass

def apply_baked_result(original_obj, task_images, setting, task_base_name):
    """Create a new object with baked textures applied."""
    if not task_images: return None
    col = bpy.data.collections.get("Baked_Results") or bpy.data.collections.new("Baked_Results")
    if col.name not in bpy.context.scene.collection.children:
        try: bpy.context.scene.collection.children.link(col)
        except: pass

    new_obj = original_obj.copy()
    new_obj.data = original_obj.data.copy()
    new_obj.name = f"{task_base_name}_Baked"
    for c in new_obj.users_collection: c.objects.unlink(new_obj)
    col.objects.link(new_obj)

    # Helper to create simple material
    def _create_simple_mat(name, texture_map):
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        tree = mat.node_tree
        tree.nodes.clear()
        bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
        out = tree.nodes.new('ShaderNodeOutputMaterial'); out.location = (300, 0)
        tree.links.new(bsdf.outputs[0], out.inputs[0])
        y_pos = 0
        
        channel_to_socket_keys = {
            'color': 'color', 'metal': 'metal', 'rough': 'rough', 
            'specular': 'specular', 'emi': 'emi', 'alpha': 'alpha', 
            'normal': 'normal', 'ao': 'color', 'combine': 'color'
        }

        for chan_id, image in texture_map.items():
            target_socket = None
            compat_key = channel_to_socket_keys.get(chan_id)
            if compat_key and compat_key in BSDF_COMPATIBILITY_MAP:
                possible_names = BSDF_COMPATIBILITY_MAP[compat_key]
                for name in possible_names:
                    if name in bsdf.inputs:
                        target_socket = bsdf.inputs[name]
                        break
            
            is_normal = (chan_id == 'normal')
            if not target_socket and not is_normal: continue

            tex = tree.nodes.new('ShaderNodeTexImage'); tex.image = image
            tex.location = (-600 if is_normal else -300, y_pos); y_pos -= 280
            
            if chan_id in {'metal', 'rough', 'normal', 'specular', 'ao'}:
                try: tex.image.colorspace_settings.name = 'Non-Color'
                except: pass
                
            if is_normal:
                nor = tree.nodes.new('ShaderNodeNormalMap'); nor.location = (-300, tex.location.y)
                tree.links.new(tex.outputs[0], nor.inputs['Color'])
                normal_socket = bsdf.inputs.get('Normal')
                if normal_socket: tree.links.new(nor.outputs['Normal'], normal_socket)
            elif target_socket:
                tree.links.new(tex.outputs[0], target_socket)
                
            if chan_id == 'alpha': mat.blend_method = 'BLEND'
        return mat

    first_val = next(iter(task_images.values()))
    if isinstance(first_val, dict):
        orig_mat_names = [s.material.name for s in original_obj.material_slots if s.material]
        while len(new_obj.material_slots) < len(orig_mat_names): new_obj.data.materials.append(None)
        for i, orig_name in enumerate(orig_mat_names):
            mat_textures = {}
            for chan_id, mat_dict in task_images.items():
                if orig_name in mat_dict: mat_textures[chan_id] = mat_dict[orig_name]
            mat = _create_simple_mat(f"{task_base_name}_{orig_name}_Baked", mat_textures)
            new_obj.material_slots[i].material = mat
    else:
        mat = _create_simple_mat(f"{task_base_name}_Mat", task_images)
        new_obj.data.materials.clear()
        new_obj.data.materials.append(mat)
    return new_obj
