import bpy
from bpy import props
import traceback
from collections import namedtuple
from typing import List, Dict, Optional, Any, Set
import json
import os
from pathlib import Path

# 本地模块引用
from .utils import (
    logger, get_safe_base_name, set_image, process_pbr_numpy, 
    setup_mesh_attribute, check_objects_uv, get_active_uv_udim_tiles,
    detect_object_udim_tile, save_image, apply_baked_result,
    safe_context_override, UVLayoutManager, NodeGraphHandler, UDIMPacker,
    SceneSettingsContext, reset_channels_logic
)
from .constants import CHANNEL_BAKE_INFO
from . import preset_handler
from .state_manager import BakeStateManager

# --- Data Structures ---
BakeStep = namedtuple('BakeStep', ['job', 'task', 'channels', 'frame_info'])
BakeTask = namedtuple('BakeTask', ['objects', 'materials', 'active_obj', 'base_name', 'folder_name'])

# --- Logic Classes ---

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

            # UV 校验
            if missing_uvs := check_objects_uv(objs):
                raise ValueError(f"Missing UVs: {', '.join(missing_uvs)}")

            # 确定 Active Object
            active = s.active_object if s.active_object else objs[0]
            if s.bake_mode == 'SELECT_ACTIVE' and active not in objs:
                 active = objs[0]

            tasks = TaskBuilder.build(context, s, objs, active)
            channels = JobPreparer._collect_channels(job)
            if not channels: continue

            # 动画帧逻辑
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
        s = setting
        self.configs = [
            ('scene', {'res_x': s.res_x, 'res_y': s.res_y, 'res_pct': 100, 'engine': 'CYCLES'}),
            ('cycles', {'samples': s.sample, 'device': s.device}),
            ('image', {
                'file_format': s.save_format or 'PNG', 
                'color_depth': s.color_depth, 
                'color_mode': s.color_mode, 
                'quality': s.quality,
                'exr_codec': s.exr_code
            }),
            ('cm', {'view_transform': 'Standard'})
        ]

    def __enter__(self):
        for ctx_type, params in self.configs:
            ctx = SceneSettingsContext(ctx_type, params)
            ctx.__enter__()
            self.stack.append(ctx)
        return self
        
    def __exit__(self, *args):
        for ctx in reversed(self.stack):
            ctx.__exit__(*args)

class BakePassExecutor:
    """封装单一烘焙通道的执行逻辑"""
    @classmethod
    def execute(cls, setting, task, channel_config, handler, current_results, udim_tiles=None, array_cache=None):
        prop = channel_config['prop']
        chan_id = channel_config['id']
        
        # 1. 图像设置
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
        
        # 2. 优化：NumPy PBR 快速路径
        if cls._try_numpy_pbr(chan_id, prop, img, current_results, array_cache):
            return img
            
        # 3. 场景与节点准备
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
            # 4. 执行烘焙
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
        try:
            # 只有 mesh_type 或自定义通道需要强制使用 EMIT 模式，其余遵循配置
            is_special = (mesh_type is not None) or (chan_id == 'CUSTOM')
            params = {
                'type': 'EMIT' if is_special else bake_pass, 
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
            bpy.ops.object.bake(**params)
            return True
        except RuntimeError as e:
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
        path = Path(bpy.path.abspath(setting.save_path))
        if setting.create_new_folder and folder_name: path = path / folder_name
        path.mkdir(parents=True, exist_ok=True)
        file_base = str(path / obj.name)
        
        prev_sel, prev_act = context.selected_objects, context.active_object
        try:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj
            fmt = setting.export_format
            if fmt == 'FBX':
                bpy.ops.export_scene.fbx(filepath=f"{file_base}.fbx", use_selection=True, path_mode='COPY' if setting.save_out else 'AUTO', embed_textures=True, mesh_smooth_type='FACE')
            elif fmt == 'GLB':
                bpy.ops.export_scene.gltf(filepath=f"{file_base}.glb", use_selection=True, export_format='GLB')
            elif fmt == 'USD':
                bpy.ops.wm.usd_export(filepath=f"{file_base}.usd", selected_objects_only=True, export_textures=True, relative_paths=True)
            logger.info(f"Exported: {fmt} -> {file_base}")
        except Exception as e: logger.error(f"Export Error: {e}")
        finally:
            if prev_act:
                try:
                    bpy.ops.object.select_all(action='DESELECT')
                    for o in prev_sel: o.select_set(True)
                    context.view_layer.objects.active = prev_act
                except: pass

# --- Operators ---

class BAKETOOL_OT_BakeOperator(bpy.types.Operator):
    bl_label = "Bake"
    bl_idname = "bake.bake_operator"
    _timer = None
    state_mgr = None
    bake_queue: List[BakeStep] = []
    
    def invoke(self, context, event):
        self.state_mgr = BakeStateManager()
        if context.object and context.object.mode != 'OBJECT': 
            bpy.ops.object.mode_set(mode='OBJECT')
        try:
            enabled_jobs = [j for j in context.scene.BakeJobs.jobs if j.enabled]
            if not enabled_jobs:
                self.report({'WARNING'}, "No enabled jobs.")
                return {'CANCELLED'}
            self.bake_queue = JobPreparer.prepare_execution_queue(context, enabled_jobs)
            if not self.bake_queue:
                self.report({'WARNING'}, "Nothing to bake.")
                return {'CANCELLED'}
        except Exception as e: self.report({'ERROR'}, str(e)); traceback.print_exc()

        self.total_steps = len(self.bake_queue)
        self.current_step_idx = 0
        self.sequence_tracking = {}
        context.scene.is_baking = True
        context.scene.bake_progress = 0.0
        context.scene.bake_status = "Initializing..."
        context.scene.bake_error_log = ""
        
        self.state_mgr.start_session(self.total_steps, ",".join([s.job.name for s in self.bake_queue]))
        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            if self.current_step_idx >= self.total_steps: 
                self.finish(context); return {'FINISHED'}
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
            try: 
                step = self.bake_queue[self.current_step_idx]
                if not context.scene.is_baking: self.cancel(context); return {'CANCELLED'}
                self._process_single_step(context, step)
            except Exception as e:
                self._handle_step_error(context, e)
            self.current_step_idx += 1
            context.scene.bake_progress = (self.current_step_idx / self.total_steps) * 100.0
        elif event.type == 'ESC': 
            self.cancel(context); return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def _process_single_step(self, context, step: BakeStep):
        job, task, channels, f_info = step.job, step.task, step.channels, step.frame_info
        context.scene.bake_status = f"[{self.current_step_idx+1}/{self.total_steps}] {task.base_name}"
        if f_info: context.scene.frame_set(f_info['frame'])
        
        baked_images = {}
        array_cache = {}
        with BakeContextManager(context, job.setting):
            with safe_context_override(context, task.active_obj, task.objects):
                with UVLayoutManager(task.objects, job.setting):
                    udim_tiles = BakePassExecutor.get_udim_configuration(job.setting, task.objects)
                    with NodeGraphHandler(task.materials) as handler:
                        handler.setup_protection(task.objects, task.materials)
                        for c in channels:
                            if self.state_mgr: self.state_mgr.update_step(self.current_step_idx+1, task.active_obj.name, c['name'])
                            img = BakePassExecutor.execute(job.setting, task, c, handler, baked_images, udim_tiles, array_cache)
                            if img:
                                key = c['name'] if c['id'] == 'CUSTOM' else c['id']
                                baked_images[key] = img
                                self._save_and_record(context, job.setting, task, c, img, f_info)

        if (job.setting.bake_texture_apply or job.setting.export_model) and not f_info:
            res = apply_baked_result(task.active_obj, baked_images, job.setting, task.base_name)
            if res:
                if job.setting.export_model: ModelExporter.export(context, res, job.setting, task.folder_name)
                if not job.setting.bake_texture_apply: bpy.data.objects.remove(res, do_unlink=True)
                else: res.select_set(True)

    def _save_and_record(self, context, s, task, c, img, f_info):
        path = ""
        if s.save_out:
            path = save_image(img, s.save_path, folder=s.create_new_folder, folder_name=task.folder_name, file_format=s.save_format, motion=bool(f_info), frame=f_info['save_idx'] if f_info else 0, fillnum=f_info['digits'] if f_info else 4, separator=s.bake_motion_separator, save=True)
            if f_info and path: self._track_sequence(img, path, f_info['save_idx'])
        else: img.pack()
        self._add_ui_result(context, img, c['name'], task.active_obj.name, path)

    def _track_sequence(self, img, path, idx):
        if img not in self.sequence_tracking: self.sequence_tracking[img] = {'count': 0, 'first_path': path, 'min_frame': idx}
        t = self.sequence_tracking[img]
        t['count'] += 1
        if idx < t['min_frame']: t['min_frame'] = idx; t['first_path'] = path

    def _add_ui_result(self, context, img, type_name, obj_name, path):
        results = context.scene.baked_image_results
        if any(r.image == img for r in results): return
        item = results.add()
        item.image, item.channel_type, item.object_name, item.filepath = img, type_name, obj_name, path or ""

    def _handle_step_error(self, context, e):
        err_msg = f"[Error] Step {self.current_step_idx+1}: {str(e)}"
        context.scene.bake_error_log += err_msg + "\n"
        logger.error(f"{err_msg}\n{traceback.format_exc()}")
        if self.state_mgr: self.state_mgr.log_error(err_msg)

    def finish(self, context):
        context.scene.is_baking = False
        context.scene.bake_status = "Finished"
        if self.state_mgr: self.state_mgr.finish_session()
        for img, info in self.sequence_tracking.items():
            try:
                img.source, img.filepath, img.frame_duration = 'SEQUENCE', info['first_path'], info['count']
                img.reload()
            except: pass
        self.sequence_tracking.clear(); self._remove_timer(context)
        if self.bake_queue and self.bake_queue[0].job.setting.save_and_quit: bpy.ops.wm.save_mainfile(exit=True)

    def cancel(self, context):
        context.scene.is_baking = False; context.scene.bake_status = "Cancelled"
        if self.state_mgr: self.state_mgr.finish_session()
        self._remove_timer(context)

    def _remove_timer(self, context):
        if self._timer: context.window_manager.event_timer_remove(self._timer); self._timer = None

class BAKETOOL_OT_ResetChannels(bpy.types.Operator):
    bl_idname = "bake.reset_channels"; bl_label = "Reset"
    def execute(self, context):
        if context.scene.BakeJobs.jobs: reset_channels_logic(context.scene.BakeJobs.jobs[context.scene.BakeJobs.job_index].setting)
        return {'FINISHED'}

class BAKETOOL_OT_GenericChannelOperator(bpy.types.Operator):
    bl_idname = "bake.generic_channel_op"; bl_label = "Op"
    action_type: props.EnumProperty(items=[('ADD','',''),('DELETE','',''),('UP','',''),('DOWN','',''),('CLEAR','','')])
    target: props.StringProperty()
    def execute(self, context):
        bj = context.scene.BakeJobs
        job = bj.jobs[bj.job_index] if bj.jobs else None
        c_map = {"jobs_channel": (bj.jobs, 'job_index', bj), "job_custom_channel": (job.custom_bake_channels, 'custom_bake_channels_index', job) if job else None, "bake_objects": (job.setting.bake_objects, 'active_object_index', job.setting) if job else None}
        if self.target not in c_map or not c_map[self.target]: return {'CANCELLED'}
        coll, attr, parent = c_map[self.target]; idx = getattr(parent, attr)
        
        if self.action_type == 'ADD':
            new_item = coll.add()
            if self.target == "jobs_channel": 
                new_item.name = f"Job {len(coll)}"
                
                # Initialize critical Enums to prevent empty state on creation
                new_item.setting.bake_type = 'BSDF'
                new_item.setting.bake_mode = 'SINGLE_OBJECT'
                
                reset_channels_logic(new_item.setting)
                # Auto-enable default channels
                for c in new_item.setting.channels:
                    if c.id in {'color', 'combine', 'normal'}: c.enabled = True
        elif self.action_type == 'DELETE': coll.remove(idx); setattr(parent, attr, max(0, idx-1))
        elif self.action_type == 'CLEAR': coll.clear(); setattr(parent, attr, 0)
        elif self.action_type == 'UP' and idx > 0:
            coll.move(idx, idx-1); setattr(parent, attr, idx-1)
            if self.target=="jobs_channel": bj.job_index = idx-1
        elif self.action_type == 'DOWN' and idx < len(coll)-1:
            coll.move(idx, idx+1); setattr(parent, attr, idx+1)
            if self.target=="jobs_channel": bj.job_index = idx+1
        return {'FINISHED'}

class BAKETOOL_OT_QuickBake(bpy.types.Operator):
    """Bake current selection using active job settings immediately"""
    bl_idname = "bake.quick_bake"
    bl_label = "Quick Bake Selected"
    
    def execute(self, context):
        if not context.scene.BakeJobs.jobs:
            self.report({'WARNING'}, "No Job settings available to use as template.")
            return {'CANCELLED'}
            
        # 1. Use current active job as template
        job = context.scene.BakeJobs.jobs[context.scene.BakeJobs.job_index]
        s = job.setting
        
        # 2. Get ephemeral target objects
        sel_objs = [o for o in context.selected_objects if o.type == 'MESH']
        act_obj = context.active_object if (context.active_object and context.active_object.type == 'MESH') else None
        
        if not sel_objs:
            self.report({'WARNING'}, "Select mesh objects to bake.")
            return {'CANCELLED'}
            
        if s.bake_mode == 'SELECT_ACTIVE' and not act_obj:
            self.report({'WARNING'}, "Active object required for Selected to Active.")
            return {'CANCELLED'}

        # 3. Build ephemeral Task (Manual construction to bypass JobPreparer object list check)
        # Note: We use TaskBuilder but pass our selection directly
        try:
            tasks = TaskBuilder.build(context, s, sel_objs, act_obj)
            channels = JobPreparer._collect_channels(job)
            if not channels: 
                self.report({'WARNING'}, "No enabled channels in active job.")
                return {'CANCELLED'}
                
            baked_images = {}
            task = tasks[0] # Quick bake typically implies one logical group
            
            self.report({'INFO'}, f"Quick Baking: {task.base_name}...")
            
            with BakeContextManager(context, s):
                with safe_context_override(context, task.active_obj, task.objects):
                    with UVLayoutManager(task.objects, s):
                        udim_tiles = BakePassExecutor.get_udim_configuration(s, task.objects)
                        with NodeGraphHandler(task.materials) as handler:
                            handler.setup_protection(task.objects, task.materials)
                            for c in channels:
                                img = BakePassExecutor.execute(s, task, c, handler, baked_images, udim_tiles)
                                if img:
                                    img.pack() # Always pack for Quick Bake result visibility
                                    # Add to result list
                                    key = c['name'] if c['id'] == 'CUSTOM' else c['id']
                                    baked_images[key] = img
                                    
                                    # Add to UI list
                                    results = context.scene.baked_image_results
                                    if not any(r.image == img for r in results):
                                        item = results.add()
                                        item.image, item.channel_type, item.object_name = img, c['name'], task.active_obj.name

            self.report({'INFO'}, "Quick Bake Finished.")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Quick Bake Failed: {e}")
            traceback.print_exc()
            return {'CANCELLED'}

class BAKETOOL_OT_SetSaveLocal(bpy.types.Operator):
    bl_idname="bake.set_save_local"; bl_label="Local"; save_location: props.IntProperty(default=0)
    def execute(self,context):
        if not bpy.data.filepath: return {'CANCELLED'}
        path = str(Path(bpy.data.filepath).parent) + os.sep
        bj = context.scene.BakeJobs
        if self.save_location==0: bj.jobs[bj.job_index].setting.save_path=path
        elif self.save_location==2: bj.node_bake_settings.save_path=path
        return{'FINISHED'}

class BAKETOOL_OT_RefreshUDIM(bpy.types.Operator):
    bl_idname = "bake.refresh_udim_locations"; bl_label = "Refresh / Repack UDIMs"
    def execute(self, context):
        if not context.scene.BakeJobs.jobs: return {'CANCELLED'}
        s = context.scene.BakeJobs.jobs[context.scene.BakeJobs.job_index].setting
        objs = [o.bakeobject for o in s.bake_objects if o.bakeobject]
        if not objs: return {'CANCELLED'}
        if s.udim_mode == 'REPACK': assignments = UDIMPacker.calculate_repack(objs)
        else: assignments = {o: detect_object_udim_tile(o) for o in objs}
        for bo in s.bake_objects:
            if bo.bakeobject in assignments: bo.udim_tile = assignments[bo.bakeobject]
        return {'FINISHED'}

class BAKETOOL_OT_ManageObjects(bpy.types.Operator):
    bl_idname = "bake.manage_objects"; bl_label = "Manage Objects"; bl_options = {'REGISTER', 'UNDO'}
    action: props.EnumProperty(items=[('SET','',''),('ADD','',''),('REMOVE','',''),('CLEAR','',''),('SET_ACTIVE','',''),('SMART_SET','','')])
    def execute(self, context):
        if not context.scene.BakeJobs.jobs: return {'CANCELLED'}
        s = context.scene.BakeJobs.jobs[context.scene.BakeJobs.job_index].setting
        sel = [o for o in context.selected_objects if o.type == 'MESH']
        act = context.active_object if (context.active_object and context.active_object.type == 'MESH') else None
        def add(o):
            if not any(i.bakeobject == o for i in s.bake_objects):
                new = s.bake_objects.add(); new.bakeobject, new.udim_tile = o, detect_object_udim_tile(o)
        if self.action == 'SET':
            s.bake_objects.clear(); targets = sel
            if s.bake_mode == 'SELECT_ACTIVE' and act and act in targets:
                s.active_object = act; targets = [o for o in targets if o != act]
            for o in targets: add(o)
        elif self.action == 'ADD':
            for o in sel:
                if s.bake_mode == 'SELECT_ACTIVE' and o == s.active_object: continue
                add(o)
        elif self.action == 'REMOVE':
            rem = set(sel)
            for i in range(len(s.bake_objects)-1, -1, -1):
                if s.bake_objects[i].bakeobject in rem: s.bake_objects.remove(i)
        elif self.action == 'CLEAR': s.bake_objects.clear()
        elif self.action == 'SET_ACTIVE': 
            if act: s.active_object = act
        elif self.action == 'SMART_SET':
            if act: s.active_object = act
            s.bake_objects.clear()
            for o in sel:
                if o != act: add(o)    
        return {'FINISHED'}

class BAKETOOL_OT_SaveSetting(bpy.types.Operator):
    bl_idname = "bake.save_setting"; bl_label = "Save Preset"; filepath: props.StringProperty(subtype="FILE_PATH")
    def invoke(self, context, event): context.window_manager.fileselect_add(self); return {'RUNNING_MODAL'}
    def execute(self, context):
        data = preset_handler.PropertyIO(exclude_props={'active_channel_index'}).to_dict(context.scene.BakeJobs)
        path = self.filepath if self.filepath.endswith(".json") else self.filepath+".json"
        with open(path, 'w') as f: json.dump(data, f, indent=4)
        return {'FINISHED'}

class BAKETOOL_OT_LoadSetting(bpy.types.Operator):
    bl_idname = "bake.load_setting"; bl_label = "Load Preset"; filepath: props.StringProperty(subtype="FILE_PATH")
    def invoke(self, context, event): context.window_manager.fileselect_add(self); return {'RUNNING_MODAL'}
    def execute(self, context):
        with open(self.filepath, 'r') as f: data = json.load(f)
        preset_handler.PropertyIO().from_dict(context.scene.BakeJobs, data)
        return {'FINISHED'}

class BAKETOOL_OT_BakeSelectedNode(bpy.types.Operator):
    bl_label = "Bake Node"; bl_idname = "bake.selected_node_bake"
    def execute(self, context):
        nbs = context.scene.BakeJobs.node_bake_settings
        mat, node = context.active_object.active_material, context.active_node
        if not (mat and node): return {'CANCELLED'}
        img = set_image(f"{mat.name}_{node.name}", nbs.res_x, nbs.res_y)
        try:
            with safe_context_override(context, context.active_object):
                with NodeGraphHandler([mat]) as h:
                    tree = mat.node_tree
                    out = next((n for n in tree.nodes if n.bl_idname=='ShaderNodeOutputMaterial' and n.is_active_output), None)
                    if out:
                        emi = h._add_node(mat, 'ShaderNodeEmission', location=(out.location.x-200, out.location.y))
                        tree.links.new(node.outputs[0], emi.inputs[0]); tree.links.new(emi.outputs[0], out.inputs[0])
                        bpy.ops.object.bake(type='EMIT', margin=nbs.margin)
                        if nbs.save_outside: save_image(img, nbs.save_path, file_format=nbs.image_settings.save_format)
                        else: img.pack()
        except Exception as e: self.report({'ERROR'}, str(e)); return {'CANCELLED'}
        return {'FINISHED'}

class BAKETOOL_OT_DeleteResult(bpy.types.Operator):
    bl_idname = "baketool.delete_result"; bl_label = "Delete"
    def execute(self, context):
        idx = context.scene.baked_image_results_index
        if idx >= 0: context.scene.baked_image_results.remove(idx); context.scene.baked_image_results_index = max(0, idx-1)
        return {'FINISHED'}

class BAKETOOL_OT_DeleteAllResults(bpy.types.Operator):
    bl_idname = "baketool.delete_all_results"; bl_label = "Delete All"
    def execute(self, context): context.scene.baked_image_results.clear(); return {'FINISHED'}

class BAKETOOL_OT_ExportResult(bpy.types.Operator):
    bl_idname = "baketool.export_result"; bl_label = "Export"; filepath: props.StringProperty(subtype="FILE_PATH")
    def invoke(self, context, event): context.window_manager.fileselect_add(self); return {'RUNNING_MODAL'}
    def execute(self, context):
        r = context.scene.baked_image_results[context.scene.baked_image_results_index]
        if r.image: save_image(r.image, os.path.dirname(self.filepath)) 
        return {'FINISHED'}

class BAKETOOL_OT_ExportAllResults(bpy.types.Operator):
    bl_idname = "baketool.export_all_results"; bl_label = "Export All"; directory: props.StringProperty(subtype="DIR_PATH")
    def invoke(self, context, event): context.window_manager.fileselect_add(self); return {'RUNNING_MODAL'}
    def execute(self, context):
        for r in context.scene.baked_image_results:
             if r.image: save_image(r.image, self.directory)
        return {'FINISHED'}

class BAKETOOL_OT_ClearCrashLog(bpy.types.Operator):
    bl_idname = "bake.clear_crash_log"
    bl_label = "Dismiss Warning"
    def execute(self, context):
        try: BakeStateManager().finish_session()
        except: pass
        return {'FINISHED'}