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
        
        def clean(n): return bpy.path.clean_name(n)
        
        def get_base_name(obj, mat=None, is_batch=False):
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
            
            return clean(base)

        def get_primary_mat(target_obj):
            if not target_obj: return None
            return target_obj.material_slots[0].material if target_obj.material_slots else None

        if mode == 'SINGLE_OBJECT':
            is_batch = len(objects) > 1
            for obj in objects:
                mats = [ms.material for ms in obj.material_slots if ms.material]
                primary_mat = mats[0] if mats else None
                name = get_base_name(obj, mat=primary_mat, is_batch=is_batch)
                tasks.append(BakeTask([obj], mats, obj, name, name))
                
        elif mode == 'COMBINE_OBJECT':
            primary_mat = get_primary_mat(active_obj) if active_obj else (get_primary_mat(objects[0]) if objects else None)
            name = get_base_name(active_obj, mat=primary_mat) if active_obj else "Combined"
            all_mats = {ms.material for obj in objects for ms in obj.material_slots if ms.material}
            tasks.append(BakeTask(objects, list(all_mats), active_obj, name, name))
            
        elif mode == 'SELECT_ACTIVE':
            if active_obj:
                primary_mat = get_primary_mat(active_obj)
                name = get_base_name(active_obj, mat=primary_mat)
                mats = [ms.material for ms in active_obj.material_slots if ms.material]
                tasks.append(BakeTask(objects, mats, active_obj, name, name))
                
        elif mode == 'SPLIT_MATERIAL':
            for obj in objects:
                valid_mats = [ms.material for ms in obj.material_slots if ms.material]
                for mat in valid_mats:
                    name = get_base_name(obj, mat, is_batch=True)
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
        scene_args = {'res_x': s.res_x, 'res_y': s.res_y, 'engine': 'CYCLES'}
        cycles_args = {'samples': s.sample, 'device': s.device}
        
        c_mode = self.override_color_mode if self.override_color_mode else s.color_mode
        img_args = {
            'file_format': format_map.get(s.save_format, 'PNG'), 
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
                
                # Update Log
                if self.state_mgr:
                    self.state_mgr.update_step(
                        self.current_step_idx + 1,
                        step.task.active_obj.name,
                        "Processing"
                    )
                
                # Execute Step
                self._process_step(context, step)
                
            except Exception as e:
                err_msg = f"Step {self.current_step_idx+1} Error: {e}"
                context.scene.bake_error_log += err_msg + "\n"
                logger.error(traceback.format_exc())
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
        if not objs and context.selected_objects: 
            objs = [o for o in context.selected_objects if o.type=='MESH']
        if not objs: return True 
        
        # Check UVs
        no_uv = check_objects_uv(objs)
        if no_uv: 
            self.report({'ERROR'}, f"Missing UVs: {', '.join(no_uv)}")
            return False

        active = s.active_object or (context.active_object if context.active_object in objs else objs[0])
        tasks = TaskBuilder.build(context, s, objs, active)
        chans = self._collect_channels(job)
        if not chans: return True

        # Frame Range
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
        
        # Standard Channels
        for c in s.channels:
            if not c.enabled: continue
            info = CHANNEL_BAKE_INFO.get(c.id, {})
            chans.append({
                'id': c.id, 'name': c.name, 'prop': c, 
                'bake_pass': info.get('bake_pass', 'EMIT'),
                'info': info, 'prefix': c.prefix, 'suffix': c.suffix
            })
            
        # Custom Channels
        if s.use_custom_map:
            for c in job.Custombakechannels:
                chans.append({
                    'id': 'CUSTOM', 'name': c.name, 'prop': c, 
                    'bake_pass': 'EMIT', 
                    'info': {'cat': 'DATA', 'def_cs': c.color_space},
                    'prefix': c.prefix, 'suffix': c.suffix
                })
        
        # Sort execution order (ID maps first, Extensions last)
        chans.sort(key=lambda x: 0 if x['id'].startswith('ID') else (2 if x['info'].get('cat') == 'EXTENSION' else 1))
        return chans

    def _process_step(self, context, step):
        job, task, channels, f_info = step.job, step.task, step.channels, step.frame_info
        s = job.setting
        
        info = f"Frame {f_info['frame']}" if f_info else "Static"
        context.scene.bake_status = f"[{self.current_step_idx+1}/{self.total_steps}] {task.base_name} ({info})"
        
        if f_info: context.scene.frame_set(f_info['frame'])
        
        baked_images = {}
        
        with BakeContextManager(context, s):
            with safe_context_override(context, task.active_obj, task.objects):
                # Smart UV Handling
                with SmartUVHandler(task.objects, s):
                    with NodeGraphHandler(task.materials) as handler:
                        # Protect other materials
                        handler.setup_protection(task.objects, task.materials)
                        
                        for c in channels:
                            if not context.scene.is_baking: raise InterruptedError("Cancelled")
                            
                            img = self._bake_single_channel(context, s, task, c, handler, baked_images)
                            
                            if img:
                                key = c['name'] if c['id'] == 'CUSTOM' else c['id']
                                baked_images[key] = img
                                
                                # Save
                                self._handle_save(context, s, task, c, img, f_info)

        if s.bake_texture_apply and not f_info:
            apply_baked_result(task.active_obj, baked_images, s, task.base_name)

    def _bake_single_channel(self, context, setting, task, c, handler, current_results):
        prop = c['prop']
        chan_id = c['id']
        is_custom = chan_id == 'CUSTOM'
        
        # Determine Color Space
        if is_custom:
            target_cs = prop.color_space
        elif prop.override_defaults:
            target_cs = prop.custom_cs
        else:
            target_cs = c['info'].get('def_cs', 'sRGB')
            
        is_float = setting.float32 or chan_id in {'position', 'normal', 'displacement'}
        
        # --- UDIM Logic ---
        udim_tiles = None
        if setting.use_udim:
            if setting.udim_mode == 'AUTO':
                udim_tiles = get_active_uv_udim_tiles(task.objects)
            elif setting.udim_mode == 'MANUAL':
                start = setting.udim_start_tile
                u, v = setting.udim_grid_u, setting.udim_grid_v
                udim_tiles = []
                for i in range(u):
                    for j in range(v):
                        udim_tiles.append(start + i + (j * 10))
            elif setting.udim_mode == 'LIST':
                start = setting.udim_start_tile
                count = setting.udim_count
                udim_tiles = [start + i for i in range(count)]
        
        # Setup Image
        img_name = f"{c['prefix']}{task.base_name}{c['suffix']}"
        img = set_image(
            img_name, setting.res_x, setting.res_y, 
            alpha=setting.use_alpha, 
            full=is_float, 
            space=target_cs, 
            clear=setting.clearimage, 
            basiccolor=setting.colorbase,
            use_udim=setting.use_udim,
            udim_tiles=udim_tiles
        )
        
        # NumPy Optimization Check
        if chan_id.startswith('pbr_conv_') and current_results:
            spec = current_results.get('specular')
            diff = current_results.get('color')
            if spec and process_pbr_numpy(img, spec, diff, chan_id, prop.pbr_conv_threshold):
                return img

        # ID Map Generation
        attr_name = None
        if chan_id.startswith('ID_'):
            type_key = {'ID_mat':'MAT','ID_ele':'ELEMENT','ID_UVI':'UVI','ID_seam':'SEAM'}.get(chan_id, 'ELEMENT')
            attr_name = setup_mesh_attribute(
                task.active_obj, type_key, 
                setting.id_start_color, 
                setting.id_iterations, 
                setting.id_manual_start_color,
                setting.id_seed
            )
            if attr_name: handler.temp_attributes.append((task.active_obj, attr_name))

        # Helper ID for node logic
        mesh_type = {
            'position':'POS','UV':'UV','wireframe':'WF','ao':'AO',
            'bevel':'BEVEL','bevnor':'BEVEL','slope':'SLOPE'
        }.get(chan_id)
        if not mesh_type and chan_id.startswith('ID_'): mesh_type = 'ID'

        # Configure Nodes
        handler.setup_for_pass(
            c['bake_pass'], chan_id, img, 
            mesh_type=mesh_type, 
            attr_name=attr_name, 
            channel_settings=prop
        )
        
        # Execute Blender Bake
        try:
            params = {
                'type': c['bake_pass'] if not mesh_type and not is_custom else 'EMIT', 
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
            return img
            
        except RuntimeError as e:
            logger.error(f"Bake Fail {chan_id}: {e}")
            return None

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
        # Check duplicate
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
        
        # Setup Sequence References
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

# --- Other Operators (Kept mostly same but cleaned) ---

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
        elif self.target=="job_custom_channel": coll=job.Custombakechannels; idx=job.Custombakechannels_index
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
            # Simplified node bake using handler
            with safe_context_override(context, context.active_object):
                with NodeGraphHandler([mat]) as h:
                    tree = mat.node_tree
                    # Manually add emission for selected node
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
        try: BakeStateManager().finish_session() # Use finish logic to delete file
        except: pass
        return {'FINISHED'}