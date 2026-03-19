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
    check_objects_uv,
    log_error
)
from .core.image_manager import set_image, save_image
from .core.uv_manager import UVLayoutManager, detect_object_udim_tile
from .core.node_manager import NodeGraphHandler
from .core.math_utils import pack_channels_numpy
from .core.engine import (
    BakeStep, BakeTask, TaskBuilder, JobPreparer,
    BakeContextManager, BakePassExecutor, ModelExporter, BakeStepRunner
)
from .core.execution import BakeModalOperator
from .core import compat
from . import preset_handler
from .constants import UI_MESSAGES
from .state_manager import BakeStateManager

import logging
logger = logging.getLogger(__name__)

# --- Operators ---

class BAKETOOL_OT_BakeOperator(bpy.types.Operator, BakeModalOperator):
    bl_label = "Bake"
    bl_idname = "bake.bake_operator"
    
    is_resume: props.BoolProperty(default=False)
    
    @classmethod
    def poll(cls, context):
        return not context.scene.is_baking
    
    def invoke(self, context, event):
        if context.object and context.object.mode != 'OBJECT': 
            bpy.ops.object.mode_set(mode='OBJECT')
        try:
            enabled_jobs = [j for j in context.scene.BakeJobs.jobs if j.enabled]
            if not enabled_jobs:
                self.report({'WARNING'}, UI_MESSAGES['NO_JOBS'])
                return {'CANCELLED'}
                
            self.bake_queue = JobPreparer.prepare_execution_queue(context, enabled_jobs)
            
            if not self.bake_queue:
                self.report({'WARNING'}, "Nothing to bake (Check logs/setup).")
                return {'CANCELLED'}
                
            start_idx = 0
            if self.is_resume:
                mgr = BakeStateManager()
                if mgr.has_crash_record():
                    data = mgr.read_log()
                    if data:
                        start_idx = data.get('current_queue_idx', 0)
                        
        except Exception as e: 
            err_msg = UI_MESSAGES['PREP_FAILED'].format(str(e))
            self.report({'ERROR'}, err_msg)
            log_error(context, err_msg, include_traceback=True)
            return {'CANCELLED'}

        return self.init_modal(context, start_idx=start_idx)

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
                self.report({'WARNING'}, UI_MESSAGES['QUICK_PREP_FAILED'])
                return {'CANCELLED'}
            
        except Exception as e:
            err_msg = f"Quick Bake preparation failed: {str(e)}"
            self.report({'ERROR'}, err_msg)
            log_error(context, err_msg, include_traceback=True)
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
        from .core.common import manage_channels_logic
        success, err = manage_channels_logic(self.target, self.action_type, context.scene.BakeJobs)
        if not success:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        return {'FINISHED'}

class BAKETOOL_OT_SetSaveLocal(bpy.types.Operator):
    bl_idname="bake.set_save_local"; bl_label="Local"; save_location: props.IntProperty(default=0)
    def execute(self,context):
        if not bpy.data.filepath: return {'CANCELLED'}
        path = str(Path(bpy.data.filepath).parent) + os.sep
        bj = context.scene.BakeJobs
        if self.save_location==0: bj.jobs[bj.job_index].setting.external_save_path=path
        elif self.save_location==2: bj.node_bake_settings.external_save_path=path
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
        
        from .core.common import manage_objects_logic
        manage_objects_logic(s, self.action, sel, act)
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
        from .core.node_manager import bake_node_to_image
        
        nbs = context.scene.BakeJobs.node_bake_settings
        mat, node = context.active_object.active_material, context.active_node
        
        if not (mat and node):
            self.report({'WARNING'}, "No active material or node selected")
            return {'CANCELLED'}
        
        img = bake_node_to_image(context, mat, node, nbs)
        
        if img:
            self.report({'INFO'}, f"Baked node to {img.name}")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Node baking failed")
            return {'CANCELLED'}

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
        try: 
            BakeStateManager().finish_session(context)
        except Exception as e:
            logger.error(f"Failed to clear crash log: {e}")
        return {'FINISHED'}

class BAKETOOL_OT_TogglePreview(bpy.types.Operator):
    """Toggle interactive packing preview in the viewport"""
    bl_idname = "bake.toggle_preview"
    bl_label = "Toggle Preview"
    
    def execute(self, context):
        bj = context.scene.BakeJobs
        if not bj.jobs: return {'CANCELLED'}
        job = bj.jobs[bj.job_index]
        s = job.setting
        
        from .core import shading
        # Toggle state
        s.use_preview = not s.use_preview
        
        # Apply to all objects in the job
        objs = [o.bakeobject for o in s.bake_objects if o.bakeobject]
        
        if not objs:
            self.report({'WARNING'}, UI_MESSAGES['JOB_SKIPPED_NO_OBJS'].format(job.name))
            s.use_preview = False
            return {'CANCELLED'}
            
        for obj in objs:
            if s.use_preview:
                shading.apply_preview(obj, s)
            else:
                shading.remove_preview(obj)
                
        # Force redraw to see changes
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
                
        return {'FINISHED'}