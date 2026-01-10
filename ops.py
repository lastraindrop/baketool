import bpy
from bpy import props
import traceback
from collections import namedtuple
from .utils import *
from .constants import *
from . import preset_handler
from .state_manager import BakeStateManager
import json
import os

# --- Data Structures ---
BakeStep = namedtuple('BakeStep', ['job', 'task', 'channels', 'frame_info'])
BakeTask = namedtuple('BakeTask', ['objects', 'materials', 'active_obj', 'base_name', 'folder_name'])

class TaskBuilder:
    @staticmethod
    def build(context, setting, objects, active_obj):
        mode = setting.bake_mode
        tasks = []
        
        def get_primary_mat(target_obj):
            if not target_obj: return None
            return target_obj.material_slots[0].material if target_obj.material_slots else None

        if mode == 'SINGLE_OBJECT':
            is_batch = len(objects) > 1
            for obj in objects:
                mats = [ms.material for ms in obj.material_slots if ms.material]
                primary_mat = mats[0] if mats else None
                name = get_safe_base_name(setting, obj, mat=primary_mat, is_batch=is_batch)
                tasks.append(BakeTask([obj], mats, obj, name, name))
                
        elif mode == 'COMBINE_OBJECT' or mode == 'UDIM':
            primary_mat = get_primary_mat(active_obj) if active_obj else (get_primary_mat(objects[0]) if objects else None)
            
            # For UDIM, we might want a specific default name if not custom
            if mode == 'UDIM' and setting.name_setting != 'CUSTOM':
                name = "UDIM_Bake"
            else:
                name = get_safe_base_name(setting, active_obj, mat=primary_mat) if active_obj else "Combined"
                
            all_mats = {ms.material for obj in objects for ms in obj.material_slots if ms.material}
            tasks.append(BakeTask(objects, list(all_mats), active_obj, name, name))
            
        elif mode == 'SELECT_ACTIVE':
            if active_obj:
                primary_mat = get_primary_mat(active_obj)
                name = get_safe_base_name(setting, active_obj, mat=primary_mat)
                # 关键修复：收集所有相关物体的材质（包含高模和低模）
                all_mats = {ms.material for obj in objects for ms in obj.material_slots if ms.material}
                all_mats.update({ms.material for ms in active_obj.material_slots if ms.material})
                tasks.append(BakeTask(objects, list(all_mats), active_obj, name, name))
                
        elif mode == 'SPLIT_MATERIAL':
            for obj in objects:
                valid_mats = [ms.material for ms in obj.material_slots if ms.material]
                for mat in valid_mats:
                    name = get_safe_base_name(setting, obj, mat, is_batch=True)
                    tasks.append(BakeTask([obj], [mat], obj, name, name))
                    
        return tasks

class BakeContextManager:
    """Manages scene render settings for baking."""
    def __init__(self, context, setting, override_color_mode=None):
        self.setting = setting
        self.override_color_mode = override_color_mode
        self.stack = []
        
    def __enter__(self):
        s = self.setting
        scene_args = {'res_x': s.res_x, 'res_y': s.res_y, 'res_pct': 100, 'engine': 'CYCLES'}
        cycles_args = {'samples': s.sample, 'device': s.device}
        
        c_mode = self.override_color_mode if self.override_color_mode else s.color_mode
        img_args = {
            'file_format': s.save_format if s.save_format else 'PNG', 
            'color_depth': s.color_depth, 
            'color_mode': c_mode, 
            'quality': s.quality,
            'exr_codec': s.exr_code
        }
        
        self.stack = [
            SceneSettingsContext('scene', scene_args),
            SceneSettingsContext('cycles', cycles_args),
            SceneSettingsContext('image', img_args),
            SceneSettingsContext('cm', {'view_transform': 'Standard'})
        ]
        for ctx in self.stack: ctx.__enter__()
        return self
        
    def __exit__(self, *args):
        for ctx in reversed(self.stack): ctx.__exit__(*args)

# --- New Logic Class: Decoupled from Operator ---

class BakePassExecutor:
    """
    Encapsulates the logic for executing a single bake pass.
    Stateless logic that handles image creation, node setup, and bake API calls.
    """
    
    @classmethod
    def execute(cls, setting, task, channel_config, handler, current_results, udim_tiles=None, array_cache=None):
        """
        Main entry point for baking a single channel.
        Returns the generated image object or None if failed.
        """
        prop = channel_config['prop']
        chan_id = channel_config['id']
        
        # 1. Image Setup
        target_cs, is_float = cls._get_color_settings(setting, prop, channel_config)
        img_name = f"{channel_config['prefix']}{task.base_name}{channel_config['suffix']}"
        
        # Collect per-tile resolutions
        tile_resolutions = {}
        if setting.bake_mode == 'UDIM':
            for bo in setting.bake_objects:
                if bo.bakeobject and bo.override_size:
                    tile_resolutions[bo.udim_tile] = (bo.udim_width, bo.udim_height)
        
        img = set_image(
            img_name, setting.res_x, setting.res_y, 
            alpha=setting.use_alpha, 
            full=is_float, 
            space=target_cs, 
            clear=setting.clearimage, 
            basiccolor=setting.colorbase,
            use_udim=(setting.bake_mode == 'UDIM'),
            udim_tiles=udim_tiles,
            tile_resolutions=tile_resolutions
        )
        
        # 2. Optimization: NumPy PBR Conversion (Early Return)
        if cls._try_numpy_pbr(chan_id, prop, img, current_results, array_cache):
            return img
            
        # 3. Scene & Node Preparation
        mesh_type = cls._get_mesh_type(chan_id)
        attr_name = cls._ensure_attributes(task, setting, handler, chan_id)
        
        # [Efficiency] Throttling Samples for Data Passes
        is_data_pass = chan_id in {'normal', 'position', 'UV', 'height', 'wireframe', 'ID_mat', 'ID_ele'}
        orig_samples = bpy.context.scene.cycles.samples
        
        try:
            if is_data_pass:
                bpy.context.scene.cycles.samples = 1
            
            # Setup the graph in the handler
            handler.setup_for_pass(
                channel_config['bake_pass'], chan_id, img, 
                mesh_type=mesh_type, 
                attr_name=attr_name, 
                channel_settings=prop
            )
            
            # 4. Execution
            success = cls._run_blender_bake(setting, prop, channel_config['bake_pass'], mesh_type, chan_id)
        finally:
            if is_data_pass:
                bpy.context.scene.cycles.samples = orig_samples
        
        return img if success else None

    @staticmethod
    def _get_color_settings(setting, prop, c):
        chan_id = c['id']
        is_custom = chan_id == 'CUSTOM'
        
        if is_custom:
            target_cs = prop.color_space
        elif prop.override_defaults:
            target_cs = prop.custom_cs
        else:
            target_cs = c['info'].get('def_cs', 'sRGB')
            
        is_float = setting.float32 or chan_id in {'position', 'normal', 'displacement'}
        return target_cs, is_float

    @staticmethod
    def _try_numpy_pbr(chan_id, prop, img, current_results, array_cache):
        if not chan_id.startswith('pbr_conv_') or not current_results:
            return False
        spec = current_results.get('specular')
        diff = current_results.get('color')
        if spec and process_pbr_numpy(img, spec, diff, chan_id, prop.pbr_conv_threshold, array_cache):
            return True
        return False

    @staticmethod
    def _get_mesh_type(chan_id):
        mesh_type = {
            'position': 'POS', 'UV': 'UV', 'wireframe': 'WF', 'ao': 'AO',
            'bevel': 'BEVEL', 'bevnor': 'BEVEL', 'slope': 'SLOPE'
        }.get(chan_id)
        if not mesh_type and chan_id.startswith('ID_'):
            return 'ID'
        return mesh_type

    @staticmethod
    def _ensure_attributes(task, setting, handler, chan_id):
        if not chan_id.startswith('ID_'):
            return None
            
        type_key = {'ID_mat':'MAT','ID_ele':'ELEMENT','ID_UVI':'UVI','ID_seam':'SEAM'}.get(chan_id, 'ELEMENT')
        attr_name = setup_mesh_attribute(
            task.active_obj, type_key, 
            setting.id_start_color, 
            setting.id_iterations, 
            setting.id_manual_start_color,
            setting.id_seed
        )
        if attr_name: 
            handler.temp_attributes.append((task.active_obj, attr_name))
        return attr_name

    @staticmethod
    def _run_blender_bake(setting, prop, bake_pass, mesh_type, chan_id):
        is_custom = chan_id == 'CUSTOM'
        try:
            params = {
                'type': bake_pass if not mesh_type and not is_custom else 'EMIT', 
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
            # logger.error is called by the operator's catch block usually, but good to print here
            logger.warning(f"Bake Fail {chan_id}: {e}")
            return False
            
    @staticmethod
    def get_udim_configuration(setting, objects):
        if setting.bake_mode != 'UDIM':
            return None
            
        if setting.udim_mode == 'DETECT':
            return get_active_uv_udim_tiles(objects)
            
        elif setting.udim_mode == 'CUSTOM':
            tiles = set()
            for bo in setting.bake_objects:
                if bo.bakeobject: 
                     tiles.add(bo.udim_tile)
            return sorted(list(tiles)) if tiles else [1001]
            
        elif setting.udim_mode == 'REPACK':
            # Pre-calculate what the packing will look like to create necessary tiles
            assignments = UDIMPacker.calculate_repack(objects)
            tiles = set(assignments.values())
            return sorted(list(tiles)) if tiles else [1001]
            
        return None


class ModelExporter:
    """Handles the safe export of baked models to external files."""
    
    @staticmethod
    def export(context, obj, setting, folder_name=""):
        if not obj or not setting.save_path:
            logger.warning("Export skipped: Invalid object or missing save path.")
            return

        # Prepare Path
        base_path = Path(bpy.path.abspath(setting.save_path))
        if setting.create_new_folder and folder_name:
            base_path = base_path / folder_name
        
        try:
            base_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Export Error: Cannot create directory {base_path}. {e}")
            return

        file_path = base_path / f"{obj.name}" # Extension added by Blender exporter usually
        f_path_str = str(file_path)

        # Context Isolation: Ensure ONLY the target object is selected
        # We use safe_context_override logic conceptually here but specifically for Selection state
        
        # Save previous selection state
        prev_selected = context.selected_objects
        prev_active = context.active_object
        
        try:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj
            
            fmt = setting.export_format
            
            if fmt == 'FBX':
                bpy.ops.export_scene.fbx(
                    filepath=f_path_str + ".fbx",
                    check_existing=False,
                    use_selection=True,
                    path_mode='COPY' if setting.save_out else 'AUTO',
                    embed_textures=True,
                    mesh_smooth_type='FACE'
                )
            elif fmt == 'GLB':
                bpy.ops.export_scene.gltf(
                    filepath=f_path_str + ".glb",
                    check_existing=False,
                    use_selection=True,
                    export_format='GLB',
                    export_image_format='AUTO'
                )
            elif fmt == 'USD':
                # USD Export usually requires '.usdc' or '.usda' or '.usd'
                bpy.ops.wm.usd_export(
                    filepath=f_path_str + ".usd",
                    check_existing=False,
                    selected_objects_only=True,
                    export_materials=True,
                    export_textures=True,
                    relative_paths=True
                )
                
            logger.info(f"Model Exported: {fmt} -> {f_path_str}")
            
        except Exception as e:
            logger.error(f"Failed to export model: {e}")
            context.scene.bake_error_log += f"Export Fail: {e}\n"
            
        finally:
            # Restore selection
            if prev_active:
                try:
                    bpy.ops.object.select_all(action='DESELECT')
                    for o in prev_selected: o.select_set(True)
                    context.view_layer.objects.active = prev_active
                except: pass


class BAKETOOL_OT_BakeOperator(bpy.types.Operator):
    bl_label = "Bake"
    bl_idname = "bake.bake_operator"

    _timer = None
    state_mgr = None
    
    def invoke(self, context, event):
        self.bake_queue = []
        self.total_steps = 0
        self.current_step_idx = 0
        self.sequence_tracking = {}
        
        self.state_mgr = BakeStateManager()
        
        if context.object and context.object.mode != 'OBJECT': 
            bpy.ops.object.mode_set(mode='OBJECT')

        scene = context.scene
        jobs = [j for j in scene.BakeJobs.jobs if j.enabled]

        if not jobs: 
            self.report({'WARNING'}, "No enabled jobs.")
            return {'CANCELLED'}

        for job in jobs:
            if not self._prepare_job(context, job): 
                return {'CANCELLED'}

        if not self.bake_queue: 
            self.report({'WARNING'}, "Nothing to bake.")
            return {'CANCELLED'}

        scene.is_baking = True
        scene.bake_progress = 0.0
        scene.bake_status = "Initializing..."
        scene.bake_error_log = ""
        self.total_steps = len(self.bake_queue)

        job_names = ",".join([j.name for j in jobs])
        self.state_mgr.start_session(self.total_steps, job_names)

        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            if self.current_step_idx >= self.total_steps: 
                self.finish(context)
                return {'FINISHED'}
            
            # Update UI
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
            
            try: 
                step = self.bake_queue[self.current_step_idx]
                # Execute Step (Logging is now handled inside _process_step per channel)
                self._process_step(context, step)
                
            except InterruptedError:
                self.cancel(context)
                return {'CANCELLED'}
                
            except Exception as e:
                obj_name = step.task.active_obj.name if (step and step.task) else "Unknown"
                err_msg = f"[Error] Object: '{obj_name}' | Step {self.current_step_idx+1}: {str(e)}"
                
                context.scene.bake_error_log += err_msg + "\n"
                logger.error(f"{err_msg}\n{traceback.format_exc()}")
                
                if self.state_mgr:
                    self.state_mgr.log_error(err_msg)
            
            self.current_step_idx += 1
            context.scene.bake_progress = (self.current_step_idx / self.total_steps) * 100.0
            
        elif event.type == 'ESC': 
            self.cancel(context)
            return {'CANCELLED'}
            
        return {'RUNNING_MODAL'}

    def _prepare_job(self, context, job):
        s = job.setting
        objs = [o.bakeobject for o in s.bake_objects if o.bakeobject]
        
        if not objs: 
            self.report({'WARNING'}, f"Job '{job.name}' is skipped: No objects assigned.")
            return False

        no_uv = check_objects_uv(objs)
        if no_uv: 
            self.report({'ERROR'}, f"Missing UVs: {', '.join(no_uv)}")
            return False

        active = s.active_object if s.active_object else objs[0]
        if s.bake_mode == 'SELECT_ACTIVE' and active not in objs:
             active = objs[0]

        tasks = TaskBuilder.build(context, s, objs, active)
        chans = self._collect_channels(job)
        if not chans: return True

        frames = [None]
        if s.bake_motion and s.save_out:
            start = s.bake_motion_start if s.bake_motion_use_custom else context.scene.frame_start
            dur = s.bake_motion_last if s.bake_motion_use_custom else (context.scene.frame_end - start + 1)
            frames = [{'frame': start+i, 'save_idx': s.bake_motion_startindex+i, 'digits': s.bake_motion_digit} for i in range(dur)]

        for f_info in frames:
            for task in tasks: 
                self.bake_queue.append(BakeStep(job, task, chans, f_info))
        return True

    def _collect_channels(self, job):
        s = job.setting
        chans = []
        
        for c in s.channels:
            if not c.enabled: continue
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
        
        chans.sort(key=lambda x: 0 if x['id'].startswith('ID') else (2 if x['info'].get('cat') == 'EXTENSION' else 1))
        return chans

    def _process_step(self, context, step):
        job, task, channels, f_info = step.job, step.task, step.channels, step.frame_info
        s = job.setting
        
        info = f"Frame {f_info['frame']}" if f_info else "Static"
        context.scene.bake_status = f"[{self.current_step_idx+1}/{self.total_steps}] {task.base_name} ({info})"
        
        if f_info: context.scene.frame_set(f_info['frame'])
        
        baked_images = {}
        array_cache = {} # NumPy Cache for PBR Conversions
        
        with BakeContextManager(context, s):
            with safe_context_override(context, task.active_obj, task.objects):
                with UVLayoutManager(task.objects, s):
                    # Get UDIM config once per task
                    udim_tiles = BakePassExecutor.get_udim_configuration(s, task.objects)
                    
                    with NodeGraphHandler(task.materials) as handler:
                        handler.setup_protection(task.objects, task.materials)
                        
                        for c in channels:
                            # 1. Immediate Cancellation Check
                            if not context.scene.is_baking: 
                                raise InterruptedError("User cancelled baking")
                            
                            # 2. Granular Logging
                            if self.state_mgr:
                                self.state_mgr.update_step(
                                    self.current_step_idx + 1,
                                    task.active_obj.name,
                                    f"Channel: {c['name']}"
                                )
                            
                            # Execute Bake
                            img = BakePassExecutor.execute(s, task, c, handler, baked_images, udim_tiles, array_cache)
                            
                            if img:
                                key = c['name'] if c['id'] == 'CUSTOM' else c['id']
                                baked_images[key] = img
                                self._handle_save(context, s, task, c, img, f_info)

        # --- Post-Bake Logic: Apply & Export ---
        
        # We need a result object if user wants to Apply OR Export
        need_result_obj = (s.bake_texture_apply or s.export_model) and not f_info
        
        if need_result_obj:
            # Create the object with baked materials applied
            result_obj = apply_baked_result(task.active_obj, baked_images, s, task.base_name)
            
            if result_obj:
                # 1. Export if requested
                if s.export_model:
                    ModelExporter.export(context, result_obj, s, task.folder_name)
                
                # 2. Cleanup if not keeping it
                if not s.bake_texture_apply:
                    bpy.data.objects.remove(result_obj, do_unlink=True)
                else:
                    # Select the new object to give feedback to user
                    result_obj.select_set(True)

    def _handle_save(self, context, setting, task, c, img, f_info):
        path = ""
        if setting.save_out:
            path = save_image(
                img, setting.save_path, 
                folder=setting.create_new_folder,
                folder_name=task.folder_name,
                file_format=setting.save_format,
                motion=bool(f_info),
                frame=f_info['save_idx'] if f_info else 0,
                fillnum=f_info['digits'] if f_info else 4,
                separator=setting.bake_motion_separator,
                save=True
            )
            
            if f_info and path:
                self._track_sequence(img, path, f_info['save_idx'])
        else:
            img.pack()
            
        self._add_result_entry(context, img, c['name'], task.active_obj.name, path)

    def _track_sequence(self, img, path, frame_idx):
        if img not in self.sequence_tracking:
            self.sequence_tracking[img] = {'count': 0, 'first_path': path, 'min_frame': frame_idx}
        
        track = self.sequence_tracking[img]
        track['count'] += 1
        if frame_idx < track['min_frame']:
            track['min_frame'] = frame_idx
            track['first_path'] = path

    def _add_result_entry(self, context, img, type_name, obj_name, path):
        results = context.scene.baked_image_results
        for r in results:
            if r.image == img: return
        item = results.add()
        item.image = img
        item.channel_type = type_name
        item.object_name = obj_name
        item.filepath = path or ""

    def finish(self, context):
        context.scene.is_baking = False
        context.scene.bake_status = "Finished"
        
        if self.state_mgr: self.state_mgr.finish_session()
        
        if self.sequence_tracking:
            for img, info in self.sequence_tracking.items():
                try:
                    img.source = 'SEQUENCE'
                    img.filepath = info['first_path']
                    img.frame_duration = info['count']
                    img.reload() 
                except: pass
            self.sequence_tracking.clear()
        
        if self._timer: 
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
            
        if self.bake_queue and self.bake_queue[0].job.setting.save_and_quit: 
            bpy.ops.wm.save_mainfile(exit=True)

    def cancel(self, context):
        context.scene.is_baking = False
        context.scene.bake_status = "Cancelled"
        if self.state_mgr: self.state_mgr.finish_session()
        if self._timer: 
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

# --- Other Operators ---

class BAKETOOL_OT_ResetChannels(bpy.types.Operator):
    bl_idname = "bake.reset_channels"; bl_label = "Reset"
    def execute(self, context):
        if not context.scene.BakeJobs.jobs: return {'CANCELLED'}
        s = context.scene.BakeJobs.jobs[context.scene.BakeJobs.job_index].setting
        reset_channels_logic(s)
        return {'FINISHED'}

class BAKETOOL_OT_GenericChannelOperator(bpy.types.Operator):
    bl_idname = "bake.generic_channel_op"; bl_label = "Op"
    action_type: props.EnumProperty(items=[('ADD','',''),('DELETE','',''),('UP','',''),('DOWN','',''),('CLEAR','','')])
    target: props.StringProperty()
    def execute(self, context):
        bj = context.scene.BakeJobs
        job = bj.jobs[bj.job_index] if bj.jobs else None
        
        if self.target=="jobs_channel": coll=bj.jobs; idx=bj.job_index
        elif self.target=="job_custom_channel": coll=job.custom_bake_channels; idx=job.custom_bake_channels_index
        elif self.target=="bake_objects": coll=job.setting.bake_objects; idx=job.setting.active_object_index
        else: return {'CANCELLED'}
        
        if self.action_type=='ADD':
            coll.add()
            if self.target=="jobs_channel": bpy.ops.bake.reset_channels()
        elif self.action_type=='DELETE': coll.remove(idx)
        elif self.action_type=='CLEAR': coll.clear()
        elif self.action_type=='UP' and idx > 0:
            coll.move(idx, idx-1); 
            if self.target=="jobs_channel": bj.job_index -= 1
        elif self.action_type=='DOWN' and idx < len(coll)-1:
            coll.move(idx, idx+1)
            if self.target=="jobs_channel": bj.job_index += 1
        return {'FINISHED'}

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
    """
    Recalculate UDIM tile locations based on current mode (Detect/Repack).
    Updates the UI properties to reflect actual UV locations or new packing results.
    """
    bl_idname = "bake.refresh_udim_locations"
    bl_label = "Refresh / Repack UDIMs"
    
    def execute(self, context):
        if not context.scene.BakeJobs.jobs: return {'CANCELLED'}
        job = context.scene.BakeJobs.jobs[context.scene.BakeJobs.job_index]
        s = job.setting
        
        objects = [o.bakeobject for o in s.bake_objects if o.bakeobject]
        if not objects: return {'CANCELLED'}
        
        assignments = {}
        
        if s.udim_mode == 'REPACK':
            # Run the packing algorithm
            assignments = UDIMPacker.calculate_repack(objects)
            self.report({'INFO'}, f"Repacked {len(objects)} objects.")
        else:
            # Just detect current locations (DETECT or CUSTOM fallback)
            for obj in objects:
                assignments[obj] = detect_object_udim_tile(obj)
            self.report({'INFO'}, "Refreshed UDIM locations.")
            
        # Update the UI properties
        for bo in s.bake_objects:
            if bo.bakeobject in assignments:
                bo.udim_tile = assignments[bo.bakeobject]
                
        return {'FINISHED'}

class BAKETOOL_OT_ManageObjects(bpy.types.Operator):
    bl_idname = "bake.manage_objects"; bl_label = "Manage Objects"; bl_options = {'REGISTER', 'UNDO'}
    action: props.EnumProperty(items=[('SET','',''),('ADD','',''),('REMOVE','',''),('CLEAR','',''),('SET_ACTIVE','',''),('SMART_SET','','')])

    def execute(self, context):
        if not context.scene.BakeJobs.jobs: return {'CANCELLED'}
        s = context.scene.BakeJobs.jobs[context.scene.BakeJobs.job_index].setting
        sel_meshes = [o for o in context.selected_objects if o.type == 'MESH']
        act_obj = context.active_object if (context.active_object and context.active_object.type == 'MESH') else None

        def add_obj(obj):
            for item in s.bake_objects:
                if item.bakeobject == obj: return
            new = s.bake_objects.add()
            new.bakeobject = obj
            # Auto-detect current UDIM tile
            new.udim_tile = detect_object_udim_tile(obj)

        if self.action == 'SET':
            s.bake_objects.clear()
            targets = sel_meshes
            if s.bake_mode == 'SELECT_ACTIVE' and act_obj and act_obj in targets:
                s.active_object = act_obj
                targets = [o for o in targets if o != act_obj]
            for o in targets: add_obj(o)
        elif self.action == 'ADD':
            for o in sel_meshes:
                if s.bake_mode == 'SELECT_ACTIVE' and o == s.active_object: continue
                add_obj(o)
        elif self.action == 'REMOVE':
            to_remove = set(sel_meshes)
            for i in range(len(s.bake_objects)-1, -1, -1):
                if s.bake_objects[i].bakeobject in to_remove: s.bake_objects.remove(i)
        elif self.action == 'CLEAR': s.bake_objects.clear()
        elif self.action == 'SET_ACTIVE': 
            if act_obj: s.active_object = act_obj
        elif self.action == 'SMART_SET':
            if act_obj: s.active_object = act_obj
            s.bake_objects.clear()
            for o in sel_meshes:
                if o != act_obj: add_obj(o)    
        return {'FINISHED'}

class BAKETOOL_OT_SaveSetting(bpy.types.Operator):
    bl_idname = "bake.save_setting"; bl_label = "Save Preset"; filepath: props.StringProperty(subtype="FILE_PATH")
    def invoke(self, context, event): context.window_manager.fileselect_add(self); return {'RUNNING_MODAL'}
    def execute(self, context):
        serializer = preset_handler.PropertyIO(exclude_props={'active_channel_index'})
        data = serializer.to_dict(context.scene.BakeJobs)
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
        mat = context.active_object.active_material
        node = context.active_node
        if not (mat and node): return {'CANCELLED'}
        
        img_name = f"{mat.name}_{node.name}"
        img = set_image(img_name, nbs.res_x, nbs.res_y)
        
        try:
            with safe_context_override(context, context.active_object):
                with NodeGraphHandler([mat]) as h:
                    tree = mat.node_tree
                    out_n = next((n for n in tree.nodes if n.bl_idname=='ShaderNodeOutputMaterial' and n.is_active_output), None)
                    if out_n:
                        emi = h._add_node(mat, 'ShaderNodeEmission', location=(out_n.location.x-200, out_n.location.y))
                        tree.links.new(node.outputs[0], emi.inputs[0])
                        tree.links.new(emi.outputs[0], out_n.inputs[0])
                        
                        bpy.ops.object.bake(type='EMIT', margin=nbs.margin)
                        
                        if nbs.save_outside: 
                            save_image(img, nbs.save_path, file_format=nbs.image_settings.save_format)
                        else: 
                            img.pack()
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        return {'FINISHED'}

class BAKETOOL_OT_DeleteResult(bpy.types.Operator):
    bl_idname = "baketool.delete_result"; bl_label = "Delete"
    def execute(self, context):
        idx = context.scene.baked_image_results_index
        if idx >= 0:
            context.scene.baked_image_results.remove(idx)
            context.scene.baked_image_results_index = max(0, idx-1)
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
