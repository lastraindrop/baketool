import bpy
import logging
import traceback
import time
from collections import namedtuple
from typing import List, Dict, Any, Optional
from pathlib import Path

from .common import (
    get_safe_base_name, check_objects_uv, safe_context_override, 
    SceneSettingsContext, apply_baked_result, reset_channels_logic
)
from .image_manager import set_image, save_image
from .math_utils import process_pbr_numpy, setup_mesh_attribute, pack_channels_numpy
from .uv_manager import get_active_uv_udim_tiles, UDIMPacker, UVLayoutManager, detect_object_udim_tile
from .node_manager import NodeGraphHandler
from ..constants import (
    UI_MESSAGES, CHANNEL_BAKE_INFO, CHANNEL_MESH_TYPE_MAP, DATA_BAKE_FORCE_SINGLE_SAMPLE
)
from . import compat

logger = logging.getLogger(__name__)

# --- Data Structures ---
BakeStep = namedtuple('BakeStep', ['job', 'task', 'channels', 'frame_info'])
BakeTask = namedtuple('BakeTask', ['objects', 'materials', 'active_obj', 'base_name', 'folder_name'])

# --- Runtime Proxies (For Quick Bake) ---
class RuntimeBakeObject:
    def __init__(self, obj, tile=1001):
        self.bakeobject = obj
        self.udim_tile = tile
        self.override_size = False
        self.udim_width = 1024
        self.udim_height = 1024

class RuntimeJobSettingProxy:
    def __init__(self, original_setting, override_objects, override_active):
        self._orig = original_setting
        self.bake_objects = [RuntimeBakeObject(o, detect_object_udim_tile(o)) for o in override_objects]
        self.active_object = override_active

    def __getattr__(self, name):
        return getattr(self._orig, name)

class RuntimeJobProxy:
    def __init__(self, original_job, setting_proxy):
        self._orig = original_job
        self.setting = setting_proxy
        self.name = original_job.name + " (Quick)"
        self.custom_bake_channels = original_job.custom_bake_channels
    
    def __getattr__(self, name):
        return getattr(self._orig, name)

# --- Logic Classes ---

class BakePostProcessor:
    """封装烘焙后的图像后处理逻辑 (降噪等)"""
    @staticmethod
    def apply_denoise(image):
        """封装烘焙后的图像后处理逻辑 (降噪等)"""
        if not image: return
        
        # 1. 创建临时场景 // Create temporary scene
        tmp_scene = bpy.data.scenes.new(name="BT_Denoise_Temp")
        try:
            tmp_scene.render.engine = 'CYCLES' 
            # Use nodes and ensure tree exists
            # Use nodes and ensure tree exists
            tmp_scene.use_nodes = True
            try:
                if hasattr(tmp_scene, "node_tree_add"):
                    tmp_scene.node_tree_add()
            except Exception: pass
            
            # Support version-specific access or forceful creation
            tree = getattr(tmp_scene, "node_tree", None)
            if not tree and hasattr(tmp_scene, "compositing_node_group"):
                tree = tmp_scene.compositing_node_group
                
            if not tree:
                # Forceful fallback for some builds/versions
                try:
                    if hasattr(bpy.ops.node, "tree_path_parent"):
                        # This sometimes triggers internal tree creation
                        pass
                    tree = getattr(tmp_scene, "node_tree", None)
                except Exception: pass
            
            if not tree:
                logger.error("Could not find/create compositor node tree on temporary scene.")
                return

            nodes = tree.nodes
            links = tree.links
            nodes.clear()
            
            # 2. 构建合成树 // Setup nodes
            n_img = nodes.new('CompositorNodeImage')
            n_img.image = image
            
            n_denoise = nodes.new('CompositorNodeDenoise')
            n_comp = nodes.new('CompositorNodeComposite')
            
            links.new(n_img.outputs[0], n_denoise.inputs[0])
            links.new(n_denoise.outputs[0], n_comp.inputs[0])
            
            n_viewer = nodes.new('CompositorNodeViewer')
            links.new(n_denoise.outputs[0], n_viewer.inputs[0])
            
            # 3. 执行单帧“合成” // Execute "render" to process pixels
            with bpy.context.temp_override(scene=tmp_scene):
                bpy.ops.render.render() 
                
            # 4. 回写像素 // Retrieve processed pixels from Viewer
            viewer_img = bpy.data.images.get("Viewer Node")
            if viewer_img:
                if viewer_img.size[0] == image.size[0] and viewer_img.size[1] == image.size[1]:
                    try:
                        if not compat.is_blender_5() and hasattr(image, "gl_free"):
                            image.gl_free()
                        
                        image.pixels.foreach_set(viewer_img.pixels)
                        image.update()
                    except Exception as e:
                        logger.error(f"无法回写降噪像素 (Failed to write back denoised pixels): {e}")
            
            if viewer_img and not compat.is_blender_5() and hasattr(viewer_img, "gl_free"):
                viewer_img.gl_free()
                
        finally:
            # 重要：始终移除临时场景以防止内存泄漏 // Always remove temporary scene
            if tmp_scene:
                try: bpy.data.scenes.remove(tmp_scene)
                except Exception: pass


class BakeStepRunner:
    """
    Encapsulates the full execution logic for a single bake step.
    Handles context management, execution, result recording, and channel packing.
    """
    def __init__(self, context=None, scene=None):
        self.context = context
        self.scene = scene if scene else (context.scene if context else None)

    def run(self, step: BakeStep, state_mgr=None, queue_idx=0) -> List[Dict]:
        """
        Execute a single Step and return the generated results.
        Returns: List of dicts {'image': bpy.types.Image, 'type': str, 'path': str, 'obj': str}
        """
        job, task, channels, f_info = step.job, step.task, step.channels, step.frame_info
        scene = self.scene
        
        results = [] 
        baked_images = {}
        array_cache = {} 

        from contextlib import ExitStack
        with ExitStack() as stack:
            stack.enter_context(BakeContextManager(self.context, job.setting))
            stack.enter_context(safe_context_override(self.context, task.active_obj, task.objects))
            stack.enter_context(UVLayoutManager(task.objects, job.setting))
            
            udim_tiles = BakePassExecutor.get_udim_configuration(job.setting, task.objects)
            handler = stack.enter_context(NodeGraphHandler(task.materials))
            
            handler.setup_protection(task.objects, task.materials)
                        
            total_ch = len(channels)
            for i, c in enumerate(channels):
                # Update UI status with channel info
                scene.bake_status = f"[{i+1}/{total_ch}] Baking {c['name']} - {task.base_name}"
                
                start_time = time.time()
                
                if state_mgr: 
                    try:
                        state_mgr.update_step(i, task.active_obj.name, c['name'], queue_idx)
                    except Exception: pass

                
                img = BakePassExecutor.execute(job.setting, task, c, handler, baked_images, udim_tiles, array_cache)
                bake_duration = time.time() - start_time
                
                if img:
                    if job.setting.use_denoise:
                        scene.bake_status = f"[{i+1}/{total_ch}] Denoising {c['name']}..."
                        BakePostProcessor.apply_denoise(img)
                    
                    key = c['name'] if c['id'] == 'CUSTOM' else c['id']
                    baked_images[key] = img
                    
                    save_start = time.time()
                    path = self._handle_save(job.setting, task, img, f_info)
                    save_duration = time.time() - save_start
                    
                    total_duration = bake_duration + save_duration
                    
                    # Package metadata
                    results.append({
                        'image': img,
                        'type': c['name'],
                        'obj': task.active_obj.name,
                        'path': path,
                        'meta': {
                            'res_x': img.size[0],
                            'res_y': img.size[1],
                            'samples': int(job.setting.sample),
                            'duration': total_duration,
                            'bake_time': bake_duration,
                            'save_time': save_duration,
                            'bake_type': str(job.setting.bake_type),
                            'device': str(job.setting.device)
                        }
                    })

            if job.setting.use_packing:
                scene.bake_status = f"Packing Channels... - {task.base_name}"
                packed_res = self._handle_channel_packing(job.setting, task, baked_images, f_info, array_cache)
                if packed_res:
                    results.append(packed_res)

        # --- Post-Bake Logic: Apply & Export ---
        if not f_info: # Static bake
            res_obj = None
            if job.setting.apply_to_scene or job.setting.export_model:
                scene.bake_status = f"Preparing Material... - {task.base_name}"
                res_obj = apply_baked_result(task.active_obj, baked_images, job.setting, task.base_name)
                
            if res_obj and job.setting.export_model and job.setting.use_external_save:
                scene.bake_status = f"Exporting Model... - {task.base_name}"
                ModelExporter.export(self.context, res_obj, job.setting, folder_name=task.folder_name, file_name=task.base_name)
                
            if res_obj and not job.setting.apply_to_scene:
                # Cleanup the temporary proxy object since we only needed it for export
                try:
                    for mat_slot in res_obj.material_slots:
                        if mat_slot.material:
                            bpy.data.materials.remove(mat_slot.material)
                    bpy.data.objects.remove(res_obj, do_unlink=True)
                except Exception as e:
                    logger.error(f"Failed to cleanup temp export object: {e}")
                                
        return results

    def _handle_save(self, s, task, img, f_info):
        path = ""
        if s.use_external_save:
            path = save_image(
                img, s.external_save_path, 
                folder=s.create_new_folder, folder_name=task.folder_name, 
                file_format=s.external_save_format, 
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
        
        start_time = time.time()
        pack_name = f"{task.base_name}{s.pack_suffix}"
        pack_img = set_image(pack_name, s.res_x, s.res_y, alpha=True, space='Non-Color')
        
        if pack_channels_numpy(pack_img, pack_map, array_cache):
            bake_duration = time.time() - start_time
            
            save_start = time.time()
            path = self._handle_save(s, task, pack_img, f_info)
            save_duration = time.time() - save_start
            
            baked_images['PACKED'] = pack_img
            return {
                'image': pack_img,
                'type': "Packed",
                'obj': task.active_obj.name,
                'path': path,
                'meta': {
                    'res_x': pack_img.size[0],
                    'res_y': pack_img.size[1],
                    'samples': 0, # Packing doesn't use samples
                    'duration': bake_duration + save_duration,
                    'bake_time': bake_duration,
                    'save_time': save_duration,
                    'bake_type': "NUMPY_PACK",
                    'device': "CPU"
                }
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
            return sorted(list(mats), key=lambda m: m.name)

        if mode == 'SINGLE_OBJECT':
            is_batch = len(objects) > 1
            for obj in objects:
                mats = [ms.material for ms in obj.material_slots if ms.material]
                if not mats:
                    continue # Skip objects with no materials
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
                mats_in_obj = [ms.material for ms in obj.material_slots if ms.material]
                for mat in mats_in_obj:
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
            result = JobPreparer.validate_job(job, scene)
            if not result.success:
                logger.error(result.message)
                scene.bake_error_log += result.message + "\n"
                continue

            s = job.setting
            objs = [o.bakeobject for o in s.bake_objects if o.bakeobject]
            
            # HP-4: Protect against empty objs list
            if not objs:
                logger.warning(f"Job {job.name} has no valid objects. Skipping.")
                continue
                
            active = s.active_object if s.active_object else next((o for o in objs if o.type == 'MESH'), objs[0])

            tasks = TaskBuilder.build(context, s, objs, active)
            channels = JobPreparer._collect_channels(job)
            if not channels: continue

            frames = JobPreparer._build_frame_list(s, scene)

            for f_info in frames:
                for task in tasks:
                    queue.append(BakeStep(job, task, channels, f_info))
                    
        return queue

    @staticmethod
    def validate_job(job, scene) -> 'ValidationResult':
        """Standalone validation logic for CLI and UI usage."""
        from .common import ValidationResult
        s = job.setting
        objs = [o.bakeobject for o in s.bake_objects if o.bakeobject]
        
        if not objs:
            return ValidationResult(False, UI_MESSAGES['JOB_SKIPPED_NO_OBJS'].format(job.name), job.name)

        if s.bake_mode == 'SELECT_ACTIVE':
            if not s.active_object:
                return ValidationResult(False, UI_MESSAGES['JOB_SKIPPED_NO_TARGET'].format(job.name), job.name)
            if missing_uvs := check_objects_uv([s.active_object]):
                return ValidationResult(False, UI_MESSAGES['JOB_SKIPPED_MISSING_UV'].format(job.name, s.active_object.name), job.name)
        else:
            if missing_uvs := check_objects_uv(objs):
                return ValidationResult(False, UI_MESSAGES['JOB_SKIPPED_MISSING_UV'].format(job.name, ', '.join(missing_uvs)), job.name)

        active = s.active_object if s.active_object else objs[0]
        if active and active.type != 'MESH':
            mesh_objs = [o for o in objs if o.type == 'MESH']
            if not mesh_objs:
                return ValidationResult(False, UI_MESSAGES['JOB_SKIPPED_NO_MESH'].format(job.name), job.name)
        
        return ValidationResult(True, "", job.name)

    @staticmethod
    def prepare_quick_bake_queue(context: bpy.types.Context, reference_job: Any, selected_objects: List[bpy.types.Object], active_object: Optional[bpy.types.Object]) -> List[BakeStep]:
        """
        Dynamically construct a temporary execution queue based on current selection.
        Uses the provided reference_job as a template for settings, using Runtime Proxies
        to avoid modifying the actual scene data.
        """
        if not reference_job:
            return []
            
        # Create Runtime Proxies
        # Filter selected objects to remove active if mode is SELECT_ACTIVE (as it is the target)
        bake_objs = []
        for o in selected_objects:
            if reference_job.setting.bake_mode == 'SELECT_ACTIVE' and o == active_object:
                continue
            bake_objs.append(o)
            
        runtime_setting = RuntimeJobSettingProxy(reference_job.setting, bake_objs, active_object)
        runtime_job = RuntimeJobProxy(reference_job, runtime_setting)
        
        # Build Tasks
        tasks = TaskBuilder.build(context, runtime_setting, bake_objs, active_object)
        channels = JobPreparer._collect_channels(reference_job) # Channels are same as ref
        
        queue = []
        frames = JobPreparer._build_frame_list(runtime_setting, context.scene)
        
        for f_info in frames:
            for task in tasks:
                queue.append(BakeStep(runtime_job, task, channels, f_info))
                
        return queue

    @staticmethod
    def _build_frame_list(setting, scene) -> List[Optional[Dict]]:
        """Build animation frame info list. Returns [None] for static (non-animated) bakes."""
        if not (setting.bake_motion and setting.use_external_save):
            return [None]
        start = int(setting.bake_motion_start if setting.bake_motion_use_custom else scene.frame_start)
        dur = int(setting.bake_motion_last if setting.bake_motion_use_custom else (scene.frame_end - start + 1))
        
        # If startindex is exactly 0 and it's the default, we might want to follow the frame number
        # for better user experience, especially in multi-version tests.
        base_idx = setting.bake_motion_startindex
        if base_idx == 0 and setting.bake_motion_use_custom and start != 0:
             # Heuristic: If user sets start frame but doesn't touch startindex, match them
             base_idx = start

        return [{
            'frame': start + i,
            'save_idx': base_idx + i,
            'digits': setting.bake_motion_digit
        } for i in range(dur)]

    @staticmethod
    def _collect_channels(job) -> List[Dict]:
        s = job.setting
        chans = []
        for c in s.channels:
            if c.enabled and c.valid_for_mode:
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
        from contextlib import ExitStack
        self.stack = ExitStack()
        self.context = context
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
                'file_format': str(setting.external_save_format or 'PNG'), 
                'color_depth': str(setting.color_depth), 
                'color_mode': str(setting.color_mode), 
                'quality': int(setting.quality),
                'exr_codec': str(setting.exr_code)
            }),
            ('cm', {'view_transform': 'Standard'})
        ]

    def __enter__(self):
        scene = self.context.scene if self.context else bpy.context.scene
        for ctx_type, params in self.configs:
            ctx = SceneSettingsContext(ctx_type, params, scene=scene)
            self.stack.enter_context(ctx)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stack.__exit__(exc_type, exc_val, exc_tb)
        return False

class BakePassExecutor:
    """封装单一烘焙通道的执行逻辑 (Refactored for KISS/Decoupling)"""
    
    @classmethod
    def execute(cls, setting, task, c_config, handler, current_results, udim_tiles=None, array_cache=None):
        """主入口：编排单通道烘焙流"""
        chan_id = c_config['id']
        prop = c_config['prop']
        
        # 1. Prepare Target Image
        img = cls._create_target_image(setting, task, c_config, udim_tiles)
        
        # 2. Path A: Numpy-based PBR Conversion (Bypass Blender Bake)
        if cls._try_numpy_pbr(chan_id, prop, img, current_results, array_cache):
            return img
            
        # 3. Path B: Standard Blender Bake Pipeline
        return cls._run_blender_bake_pipeline(setting, task, c_config, handler, img)

    @classmethod
    def _create_target_image(cls, setting, task, c_config, udim_tiles):
        prop = c_config['prop']
        target_cs, is_float = cls._get_color_settings(setting, prop, c_config)
        img_name = f"{c_config['prefix']}{task.base_name}{c_config['suffix']}"
        
        tile_resolutions = {}
        if setting.bake_mode == 'UDIM':
            tile_resolutions = {bo.udim_tile: (bo.udim_width, bo.udim_height) 
                               for bo in setting.bake_objects if bo.bakeobject and bo.override_size}
        
        return set_image(
            img_name, setting.res_x, setting.res_y, 
            alpha=setting.use_alpha, full=is_float, space=target_cs, 
            clear=setting.use_clear_image, basiccolor=setting.color_base,
            use_udim=(setting.bake_mode == 'UDIM'),
            udim_tiles=udim_tiles, tile_resolutions=tile_resolutions
        )

    @classmethod
    def _run_blender_bake_pipeline(cls, setting, task, c_config, handler, img):
        chan_id = c_config['id']
        prop = c_config['prop']
        mesh_type = cls._get_mesh_type(chan_id)
        attr_name = cls._ensure_attributes(task, setting, handler, chan_id)
        
        is_data_pass = chan_id in DATA_BAKE_FORCE_SINGLE_SAMPLE
        orig_samples = bpy.context.scene.cycles.samples
        
        try:
            if is_data_pass: bpy.context.scene.cycles.samples = 1
            handler.setup_for_pass(
                c_config['bake_pass'], chan_id, img, 
                mesh_type=mesh_type, attr_name=attr_name, channel_settings=prop
            )
            success = cls._execute_blender_bake_op(setting, task, prop, c_config['bake_pass'], mesh_type, chan_id)
            return img if success else None
        finally:
            if is_data_pass: bpy.context.scene.cycles.samples = orig_samples

    @staticmethod
    def _execute_blender_bake_op(setting, task, prop, bake_pass, mesh_type, chan_id):
        scene = bpy.context.scene
        try:
            # 1. Resolve Bake Type
            is_special = (mesh_type is not None) or (chan_id == 'CUSTOM')
            bake_type = 'EMIT' if is_special else bake_pass
            # NOTE: compat.set_bake_type syncs Cycles internal state (scene.cycles.bake_type)
            # This is separate from the operator kwarg 'type' which tells bpy.ops.object.bake what pass to run
            compat.set_bake_type(scene, bake_type)

            # 2. Build Parameters
            params = {
                'type': bake_type, 
                'margin': setting.margin, 
                'use_clear': setting.use_clear_image, 
                'target': 'IMAGE_TEXTURES'
            }
            
            if bake_type == 'NORMAL': 
                params['normal_space'] = 'OBJECT' if prop.normal_settings.object_space else 'TANGENT'
            
            if setting.bake_mode == 'SELECT_ACTIVE':
                params.update({
                    'use_selected_to_active': True, 
                    'cage_object': setting.cage_object.name if setting.cage_object else "", 
                    'cage_extrusion': BakePassExecutor._resolve_cage_extrusion(task, setting)
                })
            
            # NOTE: engine 已由 BakeContextManager 设置为 CYCLES
            bpy.ops.object.bake(**params)
            return True
        except Exception as e:
            from .common import log_error
            log_error(bpy.context, f"Bake Error {chan_id}: {e}", include_traceback=True)
            return False

    @staticmethod
    def _resolve_cage_extrusion(task, setting):
        """根据 Auto-Cage 模式解析挤出距离"""
        if setting.auto_cage_mode == 'PROXIMITY' and not setting.cage_object:
            from .math_utils import calculate_cage_proximity
            exts = calculate_cage_proximity(task.active_obj, task.objects, setting.auto_cage_margin)
            if exts is not None:
                return float(sum(exts) / len(exts))
        return setting.extrusion

    @staticmethod
    def _get_color_settings(setting, prop, c):
        chan_id = c['id']
        if chan_id == 'CUSTOM': return prop.color_space, setting.use_float32
        target_cs = prop.custom_cs if prop.override_defaults else c['info'].get('def_cs', 'sRGB')
        is_float = setting.use_float32 or chan_id in {'position', 'normal', 'displacement'}
        return target_cs, is_float

    @staticmethod
    def _try_numpy_pbr(chan_id, prop, img, current_results, array_cache):
        if not chan_id.startswith('pbr_conv_') or not current_results: return False
        spec, diff = current_results.get('specular'), current_results.get('color')
        threshold = prop.extension_settings.threshold if prop else 0.04
        if spec and process_pbr_numpy(img, spec, diff, chan_id, threshold, array_cache):
            return True
        return False

    @staticmethod
    def _get_mesh_type(chan_id):
        if chan_id in CHANNEL_MESH_TYPE_MAP: return CHANNEL_MESH_TYPE_MAP[chan_id]
        return 'ID' if chan_id.startswith('ID_') else None

    @staticmethod
    def _ensure_attributes(task, setting, handler, chan_id):
        if not chan_id.startswith('ID_'): return None
        type_key = {'ID_mat':'MAT','ID_ele':'ELEMENT','ID_UVI':'UVI','ID_seam':'SEAM'}.get(chan_id, 'ELEMENT')
        attr_name = setup_mesh_attribute(task.active_obj, type_key, setting.id_start_color, setting.id_iterations, setting.id_manual_start_color, setting.id_seed)
        if attr_name: handler.temp_attributes.append((task.active_obj, attr_name))
        return attr_name

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
    def export(context, obj, setting, folder_name="", file_name=""):
        if not obj or not setting.external_save_path: return
        
        base_path = Path(bpy.path.abspath(setting.external_save_path))
        target_dir = base_path
        if folder_name and setting.create_new_folder:
            target_dir = base_path / bpy.path.clean_name(folder_name)
            
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create export directory {target_dir}: {e}")
            return

        final_file_name = bpy.path.clean_name(file_name if file_name else obj.name)
        file_path_base = target_dir / final_file_name
        
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
            
            # C-07: 导出副本材质清理安全性 // Material clearing safety for export copies
            use_tex = getattr(setting, 'export_textures_with_model', True)
            if not use_tex:
                # 仅对副本的材质槽进行清理，不影响共享的材质数据块 // Only clear slots of the instance
                for slot in obj.material_slots:
                    slot.material = None
            
            if fmt == 'FBX':
                # HP-8: Check for io_scene_fbx addon
                if not hasattr(bpy.ops.export_scene, "fbx"):
                    logger.error("FBX Export failed: Addon 'io_scene_fbx' not enabled.")
                    return
                # Force packing textures into FBX if requested
                path_mode = 'COPY' if use_tex else 'AUTO'
                bpy.ops.export_scene.fbx(
                    filepath=f"{abs_filepath}.fbx", 
                    use_selection=True, 
                    path_mode=path_mode, 
                    embed_textures=use_tex,
                    mesh_smooth_type='FACE'
                )
            elif fmt == 'GLB':
                # HP-8: Check for io_scene_gltf2 addon
                if not hasattr(bpy.ops.export_scene, "gltf"):
                    logger.error("GLB/glTF Export failed: Addon 'io_scene_gltf2' not enabled.")
                    return
                # GLB standardly embeds all active Principled BSDF images automatically
                bpy.ops.export_scene.gltf(
                    filepath=f"{abs_filepath}.glb", 
                    use_selection=True, 
                    export_format='GLB'
                )
            elif fmt == 'USD':
                # HP-8: Check for USD support (ops.wm.usd_export)
                if not hasattr(bpy.ops.wm, "usd_export"):
                    logger.error("USD Export failed: USD not supported in this Blender build.")
                    return
                bpy.ops.wm.usd_export(
                    filepath=f"{abs_filepath}.usd", 
                    selected_objects_only=True,
                    export_materials=use_tex,
                    export_textures=use_tex
                )
            logger.info(f"Exported: {fmt} -> {abs_filepath}")
        except Exception as e:
            logger.exception(f"Export Error: {e}")
        finally:
            try:
                # Restore original selection state with safety checks
                bpy.ops.object.select_all(action='DESELECT')
                for o in prev_sel:
                    try:
                        if o and o.name in bpy.data.objects:
                            o.select_set(True)
                    except Exception: pass
                
                # Restore active object only if it still exists and is in the current context
                if prev_act and prev_act.name in bpy.data.objects:
                    try:
                        context.view_layer.objects.active = prev_act
                    except (AttributeError, RuntimeError): pass
            except Exception: pass