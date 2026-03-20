import bpy
import logging
import traceback
from collections import namedtuple
from contextlib import contextmanager
from ..constants import (
    BAKE_CHANNEL_INFO, BSDF_COMPATIBILITY_MAP, 
    SOCKET_DEFAULT_TYPE, APPLY_RESULT_CHANNEL_MAP,
    SYSTEM_NAMES
)

logger = logging.getLogger(__name__)

ValidationResult = namedtuple('ValidationResult', ['success', 'message', 'job_name'])

def log_error(context, message, state_mgr=None, include_traceback=False):
    """
    统一错误日志记录：UI 信息简明，日志与追溯写入后台。
    """
    technical_msg = message
    if include_traceback:
        technical_msg = f"{message}\n{traceback.format_exc()}"
    
    # 1. Python Logging (Detailed)
    logger.error(technical_msg)
    
    # 2. Scene UI Log (Simplified for user)
    if context and hasattr(context, "scene"):
        context.scene.bake_error_log += f"{message}\n"
        
    # 3. Persistence Log (Full Traceback for crash recovery)
    if state_mgr:
        try: state_mgr.log_error(technical_msg)
        except Exception: pass

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
    defs.extend(BAKE_CHANNEL_INFO.get(key, []))
    
    if setting.use_light_map: defs.extend(BAKE_CHANNEL_INFO.get('LIGHT', []))
    if setting.use_mesh_map: defs.extend(BAKE_CHANNEL_INFO.get('MESH', []))
    if setting.use_extension_map: defs.extend(BAKE_CHANNEL_INFO.get('EXTENSION', []))
    
    target_ids = {d['id']: d for d in defs}
    
    # Non-destructive sync
    existing_map = {c.id: c for c in setting.channels}
    
    # 1. Update existing and mark validity
    for c in setting.channels:
        if c.id in target_ids:
            c.valid_for_mode = True
            c.name = target_ids[c.id]['name']
        else:
            c.valid_for_mode = False
            c.enabled = False
            # print(f"BT_DEBUG: Invalidating channel {c.id}")
            
    # 2. Add missing
    for d in defs:
        d_id = d['id']
        if d_id not in existing_map:
            new_chan = setting.channels.add()
            new_chan.id = d_id
            new_chan.name = d['name']
            new_chan.valid_for_mode = True
            defaults = d.get('defaults', {})
            for k, v in defaults.items():
                if hasattr(new_chan, k): setattr(new_chan, k, v)

def manage_objects_logic(s, action, sel, act):
    """Business logic for object list management."""
    def add(o):
        if not any(i.bakeobject == o for i in s.bake_objects):
            from .uv_manager import detect_object_udim_tile
            new = s.bake_objects.add()
            new.bakeobject = o
            new.udim_tile = detect_object_udim_tile(o)

    if action == 'SET':
        s.bake_objects.clear()
        targets = sel
        if s.bake_mode == 'SELECT_ACTIVE' and act and act in targets:
            s.active_object = act
            targets = [o for o in targets if o != act]
        for o in targets: add(o)
    elif action == 'ADD':
        for o in sel:
            if s.bake_mode == 'SELECT_ACTIVE' and o == s.active_object: continue
            add(o)
    elif action == 'REMOVE':
        rem = set(sel)
        for i in range(len(s.bake_objects)-1, -1, -1):
            if s.bake_objects[i].bakeobject in rem: s.bake_objects.remove(i)
    elif action == 'CLEAR': s.bake_objects.clear()
    elif action == 'SET_ACTIVE': 
        if act: s.active_object = act
    elif action == 'SMART_SET':
        if act: s.active_object = act
        s.bake_objects.clear()
        for o in sel:
            if o != act: add(o)

def manage_channels_logic(target, action_type, bj):
    """Business logic for generic collection item manipulation."""
    job = bj.jobs[bj.job_index] if bj.jobs else None
    
    dispatch = {
        "jobs_channel": (bj.jobs, 'job_index', bj),
        "job_custom_channel": (job.custom_bake_channels, 'custom_bake_channels_index', job) if job else None,
        "bake_objects": (job.setting.bake_objects, 'active_object_index', job.setting) if job else None
    }

    entry = dispatch.get(target)
    if not entry: return False, f"Invalid target: {target}"
        
    coll, attr, parent = entry
    if parent is None: return False, "Action unavailable: Parent data missing"
        
    idx = getattr(parent, attr)
    
    if action_type == 'ADD':
        item = manage_collection_item(coll, 'ADD', idx)
        if target == "jobs_channel":
            item.name = f"Job {len(coll)}"
            s = item.setting
            s.bake_type = 'BSDF'
            s.bake_mode = 'SINGLE_OBJECT'
            reset_channels_logic(s)
            for c in s.channels:
                if c.id in {'color', 'combine', 'normal'}:
                    c.enabled = True
    else:
        manage_collection_item(coll, action_type, idx, parent, attr)
    
    return True, ""

def manage_collection_item(collection, action, index, parent_obj=None, index_prop=""):
    """
    Generic helper to manage items in a Blender CollectionProperty.
    Supports: ADD, DELETE, CLEAR, UP, DOWN.
    """
    if action == 'ADD':
        return collection.add()
    elif action == 'DELETE':
        if len(collection) > 0 and 0 <= index < len(collection):
            collection.remove(index)
            if parent_obj and index_prop:
                setattr(parent_obj, index_prop, max(0, index - 1))
            return True
    elif action == 'CLEAR':
        collection.clear()
        if parent_obj and index_prop:
            setattr(parent_obj, index_prop, 0)
        return True
    elif action in {'UP', 'DOWN'}:
        if action == 'UP' and index > 0:
            target_idx = index - 1
        elif action == 'DOWN' and index < len(collection) - 1:
            target_idx = index + 1
        else:
            return False
        collection.move(index, target_idx)
        if parent_obj and index_prop:
            setattr(parent_obj, index_prop, target_idx)
        return True
    return None

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
            'scene': {'res_x': 'resolution_x', 'res_y': 'resolution_y', 'res_pct': 'resolution_percentage'},
            # NOTE: 'bake' category currently unused (params passed via bpy.ops), kept for reference
            'bake': {'margin': 'bake_margin', 'type': 'bake_type', 'use_clear': 'bake_clear'} if bpy.app.version < (5, 0, 0) else {},
        }

    def _get_target(self):
        scene = bpy.context.scene
        if self.category == 'scene': return scene.render
        if self.category == 'cycles': return scene.cycles
        if self.category == 'image': return scene.render.image_settings
        if self.category == 'cm': return scene.view_settings
        if self.category == 'bake': return scene.render.bake if bpy.app.version >= (5, 0, 0) and hasattr(scene.render, "bake") else scene.render
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
            except Exception: pass

def apply_baked_result(original_obj, task_images, setting, task_base_name):
    """Create a new object or update existing one with baked textures applied."""
    if not task_images: return None
    col = bpy.data.collections.get(SYSTEM_NAMES['RESULT_COLLECTION']) or bpy.data.collections.new(SYSTEM_NAMES['RESULT_COLLECTION'])
    if col.name not in bpy.context.scene.collection.children:
        try: bpy.context.scene.collection.children.link(col)
        except Exception: pass

    # 1. Reuse existing baked object if possible to save memory
    target_name = f"{task_base_name}_Baked"
    new_obj = bpy.data.objects.get(target_name)
    
    if new_obj:
        # If it exists, ensure it uses the same mesh data type or refresh it
        # Note: We still refresh the mesh data to match current source state
        new_obj.data = original_obj.data.copy()
    else:
        new_obj = original_obj.copy()
        new_obj.data = original_obj.data.copy()
        new_obj.name = target_name
        for c in new_obj.users_collection: c.objects.unlink(new_obj)
        col.objects.link(new_obj)

    # Helper to create simple material
    def _create_simple_mat(name, texture_map):
        # reuse material if exists
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
        mat.use_nodes = True
        tree = mat.node_tree
        tree.nodes.clear()
        bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
        out = tree.nodes.new('ShaderNodeOutputMaterial'); out.location = (300, 0)
        tree.links.new(bsdf.outputs[0], out.inputs[0])
        y_pos = 0
        
        # 扩展映射表：支持标准模式与 BSDF 模式的互补 // Extended mapping
        for chan_id, image in texture_map.items():
            target_socket = None
            compat_key = APPLY_RESULT_CHANNEL_MAP.get(chan_id)
            if compat_key:
                for p_name in BSDF_COMPATIBILITY_MAP.get(compat_key, []):
                    if p_name in bsdf.inputs:
                        target_socket = bsdf.inputs[p_name]
                        break
            
            if not target_socket and not (chan_id == 'normal'): continue

            tex = tree.nodes.new('ShaderNodeTexImage'); tex.image = image
            tex.location = (-600 if chan_id == 'normal' else -300, y_pos); y_pos -= 280
            
            # 自动设置色彩空间 // Auto ColorSpace
            non_color_channels = {'metal', 'rough', 'normal', 'specular', 'ao', 'height', 'gloss', 'bevnor'}
            if chan_id in non_color_channels:
                try: tex.image.colorspace_settings.name = 'Non-Color'
                except Exception: pass
                
            if chan_id == 'normal':
                nor = tree.nodes.new('ShaderNodeNormalMap'); nor.location = (-300, tex.location.y)
                tree.links.new(tex.outputs[0], nor.inputs['Color'])
                if 'Normal' in bsdf.inputs: tree.links.new(nor.outputs['Normal'], bsdf.inputs['Normal'])
            elif chan_id == 'gloss':
                # Gloss 到 Roughness 的反转逻辑 // Invert Gloss to Roughness
                inv = tree.nodes.new('ShaderNodeInvert')
                inv.location = (-150, tex.location.y)
                tree.links.new(tex.outputs[0], inv.inputs[1])
                if target_socket: tree.links.new(inv.outputs[0], target_socket)
            elif target_socket:
                tree.links.new(tex.outputs[0], target_socket)
                
            if chan_id == 'alpha' and hasattr(mat, 'blend_method'):  # blend_method removed in Blender 4.0+ EEVEE Next
                mat.blend_method = 'BLEND'
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
