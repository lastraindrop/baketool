import bpy
from bpy import props
import traceback
import os
from pathlib import Path
import json

# Local Modules
from .core.common import (
    apply_baked_result,
    safe_context_override,
    reset_channels_logic,
    check_objects_uv
)
from .core.image_manager import set_image, save_image
from .core.uv_manager import UVLayoutManager, detect_object_udim_tile
from .core.node_manager import NodeGraphHandler
from .core.math_utils import pack_channels_numpy
from .core.engine import (
    BakeStep, BakeTask, TaskBuilder, JobPreparer,
    BakeContextManager, BakePassExecutor, ModelExporter, BakeStepRunner
)
from . import preset_handler
from .state_manager import BakeStateManager

import logging
logger = logging.getLogger(__name__)

# --- Base Modal Operator ---

class BakeModalOperator:
    """
    Mixin class providing robust modal execution logic, progress tracking,
    and crash recovery for any bake operation.
    Subclasses must populate `self.bake_queue` in `invoke`.
    """
    _timer = None
    state_mgr = None
    bake_queue = []
    
    def init_modal(self, context):
        """Initialize state and start modal timer."""
        self.state_mgr = BakeStateManager()
        self.total_steps = len(self.bake_queue)
        self.current_step_idx = 0
        self.sequence_tracking = {}
        
        context.scene.is_baking = True
        context.scene.bake_progress = 0.0
        context.scene.bake_status = "Initializing..."
        context.scene.bake_error_log = ""
        
        # Extract job names for logging
        job_names = list(set(step.job.name for step in self.bake_queue))
        self.state_mgr.start_session(self.total_steps, ",".join(job_names))
        
        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            if self.current_step_idx >= self.total_steps: 
                self.finish(context)
                return {'FINISHED'}
            
            # Force UI update
            # bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1) # Can cause flicker, optional
            
            try: 
                # Check cancellation flag
                if not context.scene.is_baking: 
                    self.cancel(context)
                    return {'CANCELLED'}
                
                step = self.bake_queue[self.current_step_idx]
                self._process_single_step(context, step)
                
            except Exception as e:
                self._handle_step_error(context, e)
            
            self.current_step_idx += 1
            context.scene.bake_progress = (self.current_step_idx / self.total_steps) * 100.0
            
        elif event.type == 'ESC': 
            self.cancel(context)
            return {'CANCELLED'}
            
        return {'RUNNING_MODAL'}

    def _process_single_step(self, context, step: BakeStep):
        job, task, f_info = step.job, step.task, step.frame_info
        context.scene.bake_status = f"[{self.current_step_idx+1}/{self.total_steps}] {task.base_name}"
        
        if f_info: 
            context.scene.frame_set(f_info['frame'])
        
        runner = BakeStepRunner(context)
        results = runner.run(step, self.state_mgr)
        
        for res in results:
            self._add_ui_result(context, res['image'], res['type'], res['obj'], res['path'])
            if f_info and res['path']:
                self._track_sequence(res['image'], res['path'], f_info['save_idx'])

    def _track_sequence(self, img, path, idx):
        if img not in self.sequence_tracking: 
            self.sequence_tracking[img] = {'count': 0, 'first_path': path, 'min_frame': idx}
        t = self.sequence_tracking[img]
        t['count'] += 1
        if idx < t['min_frame']: 
            t['min_frame'] = idx
            t['first_path'] = path

    def _add_ui_result(self, context, img, type_name, obj_name, path):
        results = context.scene.baked_image_results
        if any(r.image == img for r in results): return
        item = results.add()
        item.image = img
        item.channel_type = type_name 
        item.object_name = obj_name
        item.filepath = path or ""

    def _handle_step_error(self, context, e):
        err_msg = f"[Error] Step {self.current_step_idx+1}: {str(e)}"
        context.scene.bake_error_log += err_msg + "\n"
        logger.error(f"{err_msg}\n{traceback.format_exc()}")
        if self.state_mgr: 
            self.state_mgr.log_error(err_msg)

    def _cleanup_state(self, context, status="Finished"):
        context.scene.is_baking = False
        context.scene.bake_status = status
        if self.state_mgr: 
            self.state_mgr.finish_session()
        self._remove_timer(context)

    def finish(self, context):
        self._cleanup_state(context, "Finished")
        # Reload sequences if any
        for img, info in self.sequence_tracking.items():
            try:
                img.source, img.filepath, img.frame_duration = 'SEQUENCE', info['first_path'], info['count']
                img.reload()
            except: pass
        self.sequence_tracking.clear()
        
        # Auto-Save logic (Only for standard jobs, checked via first step)
        if self.bake_queue and hasattr(self.bake_queue[0].job, 'setting'):
             if getattr(self.bake_queue[0].job.setting, 'save_and_quit', False): 
                bpy.ops.wm.save_mainfile(exit=True)

    def cancel(self, context):
        self._cleanup_state(context, "Cancelled")

    def _remove_timer(self, context):
        if self._timer: 
            try: context.window_manager.event_timer_remove(self._timer)
            except: pass
            self._timer = None

# --- Operators ---

class BAKETOOL_OT_BakeOperator(bpy.types.Operator, BakeModalOperator):
    bl_label = "Bake"
    bl_idname = "bake.bake_operator"
    
    @classmethod
    def poll(cls, context):
        return not context.scene.is_baking
    
    def invoke(self, context, event):
        if context.object and context.object.mode != 'OBJECT': 
            bpy.ops.object.mode_set(mode='OBJECT')
        try:
            enabled_jobs = [j for j in context.scene.BakeJobs.jobs if j.enabled]
            if not enabled_jobs:
                self.report({'WARNING'}, "No enabled jobs.")
                return {'CANCELLED'}
                
            self.bake_queue = JobPreparer.prepare_execution_queue(context, enabled_jobs)
            
            if not self.bake_queue:
                self.report({'WARNING'}, "Nothing to bake (Check logs/setup).")
                return {'CANCELLED'}
                
        except Exception as e: 
            self.report({'ERROR'}, str(e))
            traceback.print_exc()
            return {'CANCELLED'}

        return self.init_modal(context)

class BAKETOOL_OT_QuickBake(bpy.types.Operator, BakeModalOperator):
    """Bake current selection using active job settings immediately"""
    bl_idname = "bake.quick_bake"
    bl_label = "Quick Bake Selected"
    
    def execute(self, context):
        # We redirect execute to invoke for script usage, though usually not recommended for modal
        return self.invoke(context, None)

    def invoke(self, context, event):
        bj = context.scene.BakeJobs
        if not bj.jobs:
            self.report({'WARNING'}, "No Job settings available to use as template.")
            return {'CANCELLED'}
            
        job = bj.jobs[bj.job_index]
        sel_objs = [o for o in context.selected_objects if o.type == 'MESH']
        act_obj = context.active_object if (context.active_object and context.active_object.type == 'MESH') else None
        
        if not sel_objs:
            self.report({'WARNING'}, "Select mesh objects to bake.")
            return {'CANCELLED'}
        
        try:
            self.bake_queue = JobPreparer.prepare_quick_bake_queue(context, job, sel_objs, act_obj)
            
            if not self.bake_queue:
                self.report({'WARNING'}, "Quick Bake preparation failed (check logs).")
                return {'CANCELLED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Quick Bake Prep Failed: {e}")
            traceback.print_exc()
            return {'CANCELLED'}
            
        return self.init_modal(context)

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
        
        dispatch = {
            "jobs_channel": (bj.jobs, 'job_index', bj),
            "job_custom_channel": (job.custom_bake_channels, 'custom_bake_channels_index', job) if job else None,
            "bake_objects": (job.setting.bake_objects, 'active_object_index', job.setting) if job else None
        }

        entry = dispatch.get(self.target)
        if not entry: return {'CANCELLED'}
            
        coll, attr, parent = entry
        idx = getattr(parent, attr)
        
        if self.action_type == 'ADD':
            self._handle_add(coll, bj)
        elif self.action_type == 'DELETE':
            if len(coll) > 0:
                coll.remove(idx)
                setattr(parent, attr, max(0, idx - 1))
        elif self.action_type == 'CLEAR':
            coll.clear()
            setattr(parent, attr, 0)
        elif self.action_type in {'UP', 'DOWN'}:
            self._handle_move(coll, parent, attr, idx)
            
        return {'FINISHED'}

    def _handle_add(self, coll, bj):
        new_item = coll.add()
        if self.target == "jobs_channel": 
            new_item.name = f"Job {len(coll)}"
            s = new_item.setting
            s.bake_type = 'BSDF'
            s.bake_mode = 'SINGLE_OBJECT'
            reset_channels_logic(s)
            for c in s.channels:
                if c.id in {'color', 'combine', 'normal'}:
                    c.enabled = True

    def _handle_move(self, coll, parent, attr, idx):
        if self.action_type == 'UP' and idx > 0:
            target_idx = idx - 1
        elif self.action_type == 'DOWN' and idx < len(coll) - 1:
            target_idx = idx + 1
        else:
            return
        coll.move(idx, target_idx)
        setattr(parent, attr, target_idx)

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
        from .core.engine import UDIMPacker
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
        
        # Store original engine
        orig_engine = context.scene.render.engine
        context.scene.render.engine = 'CYCLES'
        
        try:
            with safe_context_override(context, context.active_object):
                with NodeGraphHandler([mat]) as h:
                    tree = mat.node_tree
                    out = next((n for n in tree.nodes if n.bl_idname=='ShaderNodeOutputMaterial' and n.is_active_output), None)
                    if out:
                        emi = h._add_node(mat, 'ShaderNodeEmission', location=(out.location.x-200, out.location.y))
                        tree.links.new(node.outputs[0], emi.inputs[0]); tree.links.new(emi.outputs[0], out.inputs[0])
                        
                        # Version safe bake call
                        if bpy.app.version >= (5, 0, 0):
                            if hasattr(context.scene.render, "bake"):
                                b = context.scene.render.bake
                                b.type = 'EMIT'
                                b.margin = nbs.margin
                                b.use_clear = True
                                b.target = 'IMAGE_TEXTURES'
                            bpy.ops.object.bake(type='EMIT')
                        else:
                            bpy.ops.object.bake(type='EMIT', margin=nbs.margin)
                            
                        if nbs.save_outside: save_image(img, nbs.save_path, file_format=nbs.image_settings.save_format)
                        else: img.pack()
        except Exception as e: 
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        finally:
            context.scene.render.engine = orig_engine
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