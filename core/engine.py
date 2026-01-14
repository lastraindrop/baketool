import bpy
import logging
import traceback
from collections import namedtuple
from typing import List, Dict, Optional, Any
from pathlib import Path

from .common import (
    get_safe_base_name, check_objects_uv, safe_context_override, 
    SceneSettingsContext, apply_baked_result, reset_channels_logic
)
from .image_manager import set_image, save_image
from .math_utils import process_pbr_numpy, setup_mesh_attribute, pack_channels_numpy
from .uv_manager import get_active_uv_udim_tiles, UDIMPacker
from .node_manager import NodeGraphHandler
from ..constants import CHANNEL_BAKE_INFO

logger = logging.getLogger(__name__)

# --- Data Structures ---
BakeStep = namedtuple('BakeStep', ['job', 'task', 'channels', 'frame_info'])
BakeTask = namedtuple('BakeTask', ['objects', 'materials', 'active_obj', 'base_name', 'folder_name'])

# --- Logic Classes ---

class BakeStepRunner:
    """
    Encapsulates the full execution logic for a single bake step.
    Handles context management, execution, result recording, and channel packing.
    """
    def __init__(self, context):
        self.context = context

    def run(self, step: BakeStep, state_mgr=None) -> List[Dict]:
        """
        Execute a single Step and return the generated results.
        Returns: List of dicts {'image': bpy.types.Image, 'type': str, 'path': str, 'obj': str}
        """
        job, task, channels, f_info = step.job, step.task, step.channels, step.frame_info
        
        results = [] 
        baked_images = {}
        array_cache = {} 

        with BakeContextManager(self.context, job.setting):
            with safe_context_override(self.context, task.active_obj, task.objects):
                with UVLayoutManager(task.objects, job.setting):
                    udim_tiles = BakePassExecutor.get_udim_configuration(job.setting, task.objects)
                    
                    with NodeGraphHandler(task.materials) as handler:
                        handler.setup_protection(task.objects, task.materials)
                        
                        for c in channels:
                            if state_mgr: 
                                # Safely try to read current step from log, strictly optional
                                try:
                                    cur = state_mgr.read_log().get('current_step', 0)
                                    state_mgr.update_step(cur, task.active_obj.name, c['name'])
                                except: pass
                            
                            img = BakePassExecutor.execute(job.setting, task, c, handler, baked_images, udim_tiles, array_cache)
                            
                            if img:
                                key = c['name'] if c['id'] == 'CUSTOM' else c['id']
                                baked_images[key] = img
                                
                                path = self._handle_save(job.setting, task, img, f_info)
                                results.append({
                                    'image': img,
                                    'type': c['name'],
                                    'obj': task.active_obj.name,
                                    'path': path
                                })

                        if job.setting.use_packing:
                            packed_res = self._handle_channel_packing(job.setting, task, baked_images, f_info, array_cache)
                            if packed_res:
                                results.append(packed_res)

        # --- Post-Bake Logic: Apply & Export ---
        if not f_info: # Only run on static bakes or last frame
            if job.setting.bake_texture_apply:
                res_obj = apply_baked_result(task.active_obj, baked_images, job.setting, task.base_name)
                if res_obj and job.setting.export_model:
                    ModelExporter.export(self.context, res_obj, job.setting, folder_name=task.folder_name)
                elif job.setting.export_model:
                    ModelExporter.export(self.context, task.active_obj, job.setting, folder_name=task.folder_name)
                                
        return results

    def _handle_save(self, s, task, img, f_info):
        path = ""
        if s.save_out:
            path = save_image(
                img, s.save_path, 
                folder=s.create_new_folder, folder_name=task.folder_name, 
                file_format=s.save_format, 
                motion=bool(f_info), 
                frame=f_info['save_idx'] if f_info else 0, 
                fillnum=f_info['digits'] if f_info else 4, 
                separator=s.bake_motion_separator, 
                save=True
            )
        else:
            img.pack()
        return path

    def _handle_channel_packing(self, s, task, baked_images, f_info, array_cache):
        pack_map = {}
        for idx, attr in enumerate(['pack_r', 'pack_g', 'pack_b', 'pack_a']):
            src_id = getattr(s, attr)
            if src_id != 'NONE' and src_id in baked_images:
                pack_map[idx] = baked_images[src_id]
        
        if not pack_map: return None
        
        pack_name = f"{task.base_name}{s.pack_suffix}"
        pack_img = set_image(pack_name, s.res_x, s.res_y, alpha=True, space='Non-Color')
        
        if pack_channels_numpy(pack_img, pack_map, array_cache):
            path = self._handle_save(s, task, pack_img, f_info)
            baked_images['PACKED'] = pack_img
            return {
                'image': pack_img,
                'type': "Packed",
                'obj': task.active_obj.name,
                'path': path
            }
        return None

class TaskBuilder:
    """负责将设置和对象列表转换为具体的烘焙任务列表 (BakeTask)"""
    @staticmethod
    def build(context: bpy.types.Context, setting: Any, objects: List[bpy.types.Object], active_obj: bpy.types.Object) -> List[BakeTask]:
        mode = setting.bake_mode
        tasks = []
        
        def get_primary_mat(target_obj):
            return target_obj.material_slots[0].material if target_obj and target_obj.material_slots else None

        def get_all_materials(obj_list) -> List[bpy.types.Material]:
            mats = set()
            for obj in obj_list:
                mats.update(ms.material for ms in obj.material_slots if ms.material)
            return list(mats)

        if mode == 'SINGLE_OBJECT':
            is_batch = len(objects) > 1
            for obj in objects:
                mats = [ms.material for ms in obj.material_slots if ms.material]
                name = get_safe_base_name(setting, obj, mat=(mats[0] if mats else None), is_batch=is_batch)
                tasks.append(BakeTask([obj], mats, obj, name, name))
                
        elif mode in {'COMBINE_OBJECT', 'UDIM'}:
            primary = get_primary_mat(active_obj) if active_obj else (get_primary_mat(objects[0]) if objects else None)
            base_name = "UDIM_Bake" if (mode == 'UDIM' and setting.name_setting != 'CUSTOM') else \
                       (get_safe_base_name(setting, active_obj, mat=primary) if active_obj else "Combined")
            tasks.append(BakeTask(objects, get_all_materials(objects), active_obj, base_name, base_name))
            
        elif mode == 'SELECT_ACTIVE':
            if active_obj:
                primary = get_primary_mat(active_obj)
                name = get_safe_base_name(setting, active_obj, mat=primary)
                all_mats = list(set(get_all_materials(objects) + get_all_materials([active_obj])))
                tasks.append(BakeTask(objects, all_mats, active_obj, name, name))
                
        elif mode == 'SPLIT_MATERIAL':
            for obj in objects:
                for mat in [ms.material for ms in obj.material_slots if ms.material]:
                    name = get_safe_base_name(setting, obj, mat, is_batch=True)
                    tasks.append(BakeTask([obj], [mat], obj, name, name))
                    
        return tasks

class JobPreparer:
    """负责 Operator 运行前的校验与执行队列生成"""
    @staticmethod
    def prepare_execution_queue(context: bpy.types.Context, jobs: List[Any]) -> List[BakeStep]:
        queue = []
        scene = context.scene
        
        for job in jobs:
            s = job.setting
            objs = [o.bakeobject for o in s.bake_objects if o.bakeobject]
            if not objs:
                logger.warning(f"Job '{job.name}' skipped: No objects assigned.")
                continue

            if missing_uvs := check_objects_uv(objs):
                err = f"Job '{job.name}' skipped: Missing UVs on {', '.join(missing_uvs)}"
                logger.error(err)
                # 将错误记录到场景状态中，以便 UI 显示 // Log error to scene for UI feedback
                scene.bake_error_log += err + "\n"
                continue

            active = s.active_object if s.active_object else objs[0]
            if s.bake_mode == 'SELECT_ACTIVE' and active not in objs:
                 active = objs[0]

            tasks = TaskBuilder.build(context, s, objs, active)
            channels = JobPreparer._collect_channels(job)
            if not channels: continue

            frames = [None]
            if s.bake_motion and s.save_out:
                start = s.bake_motion_start if s.bake_motion_use_custom else scene.frame_start
                dur = s.bake_motion_last if s.bake_motion_use_custom else (scene.frame_end - start + 1)
                frames = [{
                    'frame': start + i, 
                    'save_idx': s.bake_motion_startindex + i, 
                    'digits': s.bake_motion_digit
                } for i in range(dur)]

            for f_info in frames:
                for task in tasks:
                    queue.append(BakeStep(job, task, channels, f_info))
                    
        return queue

    @staticmethod
    def _collect_channels(job) -> List[Dict]:
        s = job.setting
        chans = []
        for c in s.channels:
            if c.enabled:
                info = CHANNEL_BAKE_INFO.get(c.id, {})
                chans.append({
                    'id': c.id, 'name': c.name, 'prop': c, 
                    'bake_pass': info.get('bake_pass', 'EMIT'),
                    'info': info, 'prefix': c.prefix, 'suffix': c.suffix
                })
        
        if s.use_custom_map:
            for c in job.custom_bake_channels:
                chans.append({
                    'id': 'CUSTOM', 'name': c.name, 'prop': c, 
                    'bake_pass': 'EMIT', 
                    'info': {'cat': 'DATA', 'def_cs': c.color_space},
                    'prefix': c.prefix, 'suffix': c.suffix
                })
        
        def sort_key(x):
            if x['id'].startswith('ID'): return 0
            if x['info'].get('cat') == 'EXTENSION': return 2
            return 1
            
        chans.sort(key=sort_key)
        return chans

class BakeContextManager:
    """管理烘焙时的场景与渲染临时设置"""
    def __init__(self, context, setting):
        self.stack = []
        self.configs = [
            ('scene', {
                'res_x': int(setting.res_x), 
                'res_y': int(setting.res_y), 
                'res_pct': 100, 
                'engine': 'CYCLES'
            }),
            ('cycles', {
                'samples': int(setting.sample), 
                'device': str(setting.device)
            }),
            ('image', {
                'file_format': str(setting.save_format or 'PNG'), 
                'color_depth': str(setting.color_depth), 
                'color_mode': str(setting.color_mode), 
                'quality': int(setting.quality),
                'exr_codec': str(setting.exr_code)
            }),
            ('cm', {'view_transform': 'Standard'})
        ]

    def __enter__(self):
        for ctx_type, params in self.configs:
            ctx = SceneSettingsContext(ctx_type, params)
            ctx.__enter__()
            self.stack.append(ctx)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        for ctx in reversed(self.stack):
            ctx.__exit__(exc_type, exc_val, exc_tb)

class BakePassExecutor:
    """封装单一烘焙通道的执行逻辑"""
    @classmethod
    def execute(cls, setting, task, channel_config, handler, current_results, udim_tiles=None, array_cache=None):
        prop = channel_config['prop']
        chan_id = channel_config['id']
        
        target_cs, is_float = cls._get_color_settings(setting, prop, channel_config)
        img_name = f"{channel_config['prefix']}{task.base_name}{channel_config['suffix']}"
        
        tile_resolutions = {}
        if setting.bake_mode == 'UDIM':
            for bo in setting.bake_objects:
                if bo.bakeobject and bo.override_size:
                    tile_resolutions[bo.udim_tile] = (bo.udim_width, bo.udim_height)
        
        img = set_image(
            img_name, setting.res_x, setting.res_y, 
            alpha=setting.use_alpha, full=is_float, space=target_cs, 
            clear=setting.clearimage, basiccolor=setting.colorbase,
            use_udim=(setting.bake_mode == 'UDIM'),
            udim_tiles=udim_tiles, tile_resolutions=tile_resolutions
        )
        
        if cls._try_numpy_pbr(chan_id, prop, img, current_results, array_cache):
            return img
            
        mesh_type = cls._get_mesh_type(chan_id)
        attr_name = cls._ensure_attributes(task, setting, handler, chan_id)
        
        is_data_pass = chan_id in {'normal', 'position', 'UV', 'height', 'wireframe', 'ID_mat', 'ID_ele'}
        orig_samples = bpy.context.scene.cycles.samples
        
        try:
            if is_data_pass: bpy.context.scene.cycles.samples = 1
            handler.setup_for_pass(
                channel_config['bake_pass'], chan_id, img, 
                mesh_type=mesh_type, attr_name=attr_name, channel_settings=prop
            )
            success = cls._run_blender_bake(setting, prop, channel_config['bake_pass'], mesh_type, chan_id)
        finally:
            if is_data_pass: bpy.context.scene.cycles.samples = orig_samples
        
        return img if success else None

    @staticmethod
    def _get_color_settings(setting, prop, c):
        chan_id = c['id']
        if chan_id == 'CUSTOM': return prop.color_space, setting.float32
        target_cs = prop.custom_cs if prop.override_defaults else c['info'].get('def_cs', 'sRGB')
        is_float = setting.float32 or chan_id in {'position', 'normal', 'displacement'}
        return target_cs, is_float

    @staticmethod
    def _try_numpy_pbr(chan_id, prop, img, current_results, array_cache):
        if not chan_id.startswith('pbr_conv_') or not current_results: return False
        spec, diff = current_results.get('specular'), current_results.get('color')
        if spec and process_pbr_numpy(img, spec, diff, chan_id, prop.pbr_conv_threshold, array_cache):
            return True
        return False

    @staticmethod
    def _get_mesh_type(chan_id):
        m_map = {'position': 'POS', 'UV': 'UV', 'wireframe': 'WF', 'ao': 'AO', 'bevel': 'BEVEL', 'bevnor': 'BEVEL', 'slope': 'SLOPE'}
        if chan_id in m_map: return m_map[chan_id]
        return 'ID' if chan_id.startswith('ID_') else None

    @staticmethod
    def _ensure_attributes(task, setting, handler, chan_id):
        if not chan_id.startswith('ID_'): return None
        type_key = {'ID_mat':'MAT','ID_ele':'ELEMENT','ID_UVI':'UVI','ID_seam':'SEAM'}.get(chan_id, 'ELEMENT')
        attr_name = setup_mesh_attribute(task.active_obj, type_key, setting.id_start_color, setting.id_iterations, setting.id_manual_start_color, setting.id_seed)
        if attr_name: handler.temp_attributes.append((task.active_obj, attr_name))
        return attr_name

    @staticmethod
    def _run_blender_bake(setting, prop, bake_pass, mesh_type, chan_id):
        scene = bpy.context.scene
        try:
            is_special = (mesh_type is not None) or (chan_id == 'CUSTOM')
            bake_type = 'EMIT' if is_special else bake_pass
            
            # --- Version Specific Bake Settings ---
            if bpy.app.version >= (5, 0, 0):
                # Blender 5.0+ path
                if hasattr(scene.render, "bake"):
                    bset = scene.render.bake
                    if hasattr(bset, "use_multires"): bset.use_multires = False
                    try: bset.type = bake_type
                    except: logger.debug(f"5.0: Could not set bake.type to {bake_type}")
                    bset.margin = setting.margin
                    bset.use_clear = setting.clearimage
                    bset.target = 'IMAGE_TEXTURES'
            else:
                # Legacy path (Pre-5.0)
                if hasattr(scene.render, "use_bake_multires"):
                    scene.render.use_bake_multires = False
                
                if hasattr(scene.render, "bake_type"):
                    try: scene.render.bake_type = bake_type
                    except: logger.debug(f"Legacy: Could not set bake_type to {bake_type}")
                    scene.render.bake_margin = setting.margin
                    scene.render.use_bake_clear = setting.clearimage
            
            params = {
                'type': bake_type, 
                'margin': setting.margin, 
                'use_clear': setting.clearimage, 
                'target': 'IMAGE_TEXTURES'
            }
            if params['type'] == 'NORMAL': 
                params['normal_space'] = 'OBJECT' if prop.normal_obj else 'TANGENT'
            
            if setting.bake_mode == 'SELECT_ACTIVE':
                params.update({
                    'use_selected_to_active': True, 
                    'cage_object': setting.cage_object.name if setting.cage_object else "", 
                    'cage_extrusion': setting.extrusion
                })
            
            # Ensure we are in the right engine
            scene.render.engine = 'CYCLES'
            
            bpy.ops.object.bake(**params)
            return True
        except Exception as e:
            logger.warning(f"Bake Fail {chan_id}: {e}")
            return False

    @staticmethod
    def get_udim_configuration(setting, objects):
        if setting.bake_mode != 'UDIM': return None
        if setting.udim_mode == 'DETECT': return get_active_uv_udim_tiles(objects)
        if setting.udim_mode == 'REPACK':
            assignments = UDIMPacker.calculate_repack(objects)
            tiles = set(assignments.values())
        else:
            tiles = {bo.udim_tile for bo in setting.bake_objects if bo.bakeobject}
        return sorted(list(tiles)) if tiles else [1001]

class ModelExporter:
    """模型安全导出逻辑"""
    @staticmethod
    def export(context, obj, setting, folder_name=""):
        if not obj or not setting.save_path: return
        
        base_path = Path(bpy.path.abspath(setting.save_path))
        target_dir = base_path
        if folder_name:
            target_dir = base_path / bpy.path.clean_name(folder_name)
            
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create export directory {target_dir}: {e}")
            return

        file_name = bpy.path.clean_name(obj.name)
        file_path_base = target_dir / file_name
        
        prev_sel = context.selected_objects[:]
        prev_act = context.active_object
        
        try:
            if context.object and context.object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj
            
            fmt = setting.export_format
            abs_filepath = str(file_path_base.resolve())
            
            if fmt == 'FBX':
                bpy.ops.export_scene.fbx(
                    filepath=f"{abs_filepath}.fbx", 
                    use_selection=True, 
                    path_mode='AUTO', 
                    mesh_smooth_type='FACE'
                )
            elif fmt == 'GLB':
                bpy.ops.export_scene.gltf(
                    filepath=f"{abs_filepath}.glb", 
                    use_selection=True, 
                    export_format='GLB'
                )
            elif fmt == 'USD':
                bpy.ops.wm.usd_export(
                    filepath=f"{abs_filepath}.usd", 
                    selected_objects_only=True
                )
            logger.info(f"Exported: {fmt} -> {abs_filepath}")
        except Exception as e:
            logger.error(f"Export Error: {e}")
            traceback.print_exc()
        finally:
            try:
                bpy.ops.object.select_all(action='DESELECT')
                for o in prev_sel:
                    try: o.select_set(True)
                    except: pass
                context.view_layer.objects.active = prev_act
            except: pass