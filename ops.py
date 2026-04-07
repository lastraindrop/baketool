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

# --- Helpers ---
class _DummyEvent:
    type = 'NONE'

# --- Operators ---

class BAKETOOL_OT_RunDevTests(bpy.types.Operator):
    """Run all internal test suites and report results to UI"""
    bl_idname = "bake.run_dev_tests"
    bl_label = "Run Development Tests"
    
    def execute(self, context):
        import unittest
        import io
        from .test_cases import suite_unit, suite_shading, suite_negative
        
        # 1. 组装测试集 / Assemble Suites
        loader = unittest.TestLoader()
        suites = [
            loader.loadTestsFromTestCase(suite_unit.SuiteUnit),
            loader.loadTestsFromTestCase(suite_shading.SuiteShading),
            loader.loadTestsFromTestCase(suite_negative.SuiteNegative)
        ]
        consolidated = unittest.TestSuite(suites)
        
        # 2. 静默运行并捕获输出 / Run silently and capture output
        stream = io.StringIO()
        runner = unittest.TextTestRunner(stream=stream, verbosity=1)
        result = runner.run(consolidated)
        
        # 3. 更新场景反馈属性 / Update scene attributes
        info = f"Ran {result.testsRun} tests. {len(result.errors)} Errors, {len(result.failures)} Fails."
        context.scene.last_test_info = info
        context.scene.test_pass = result.wasSuccessful()
        
        if result.wasSuccessful():
            self.report({'INFO'}, f"All {result.testsRun} tests passed!")
        else:
            self.report({'ERROR'}, f"Tests Failed: {info}")
            
        return {'FINISHED'}

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
        # 支持脚本调用，需创建虚拟 event // Support script calls via dummy event
        return self.invoke(context, _DummyEvent())

    def invoke(self, context, event):
        if not hasattr(context.scene, "BakeJobs"):
            self.report({'ERROR'}, "BakeTool properties not initialized in this scene.")
            return {'CANCELLED'}
            
        bj = context.scene.BakeJobs
        if not bj.jobs:
            self.report({'WARNING'}, "No Job settings available to use as template.")
            return {'CANCELLED'}
        
        # Ensure job_index is within bounds
        if bj.job_index < 0 or bj.job_index >= len(bj.jobs):
            bj.job_index = 0
            
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
    bl_idname = "bake.reset_channels"
    bl_label = "Reset"
    def execute(self, context):
        bj = context.scene.BakeJobs
        if not bj.jobs: 
            return {'CANCELLED'}
        if bj.job_index >= 0 and bj.job_index < len(bj.jobs):
             reset_channels_logic(bj.jobs[bj.job_index].setting)
        else:
             bj.job_index = 0
             if bj.jobs: reset_channels_logic(bj.jobs[0].setting)
        return {'FINISHED'}

class BAKETOOL_OT_GenericChannelOperator(bpy.types.Operator):
    bl_idname = "bake.generic_channel_op"
    bl_label = "Op"
    action_type: props.EnumProperty(
        name="Action",
        items=[
            ('ADD', 'Add', 'Add a new custom channel to the list'),
            ('DELETE', 'Delete', 'Remove the currently selected custom channel'),
            ('UP', 'Up', 'Move current channel up in execution order'),
            ('DOWN', 'Down', 'Move current channel down in execution order'),
            ('CLEAR', 'Clear', 'Remove all custom channels')
        ]
    )
    target: props.StringProperty()
    def execute(self, context):
        from .core.common import manage_channels_logic
        success, err = manage_channels_logic(self.target, self.action_type, context.scene.BakeJobs)
        if not success:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        return {'FINISHED'}

class BAKETOOL_OT_SetSaveLocal(bpy.types.Operator):
    bl_idname = "bake.set_save_local"
    bl_label = "Local"
    save_location: props.IntProperty(default=0)
    
    def execute(self, context):
        if not bpy.data.filepath: 
            self.report({'WARNING'}, "Save your file first to use relative paths.")
            return {'CANCELLED'}
            
        path = str(Path(bpy.data.filepath).parent) + os.sep
        bj = context.scene.BakeJobs
        
        # C-04: Bounds Check & Handle all locations
        if self.save_location == 0:
            if bj.job_index >= 0 and bj.job_index < len(bj.jobs):
                bj.jobs[bj.job_index].setting.external_save_path = path
            else:
                self.report({'WARNING'}, "Select a job first to set its path.")
                return {'CANCELLED'}
        elif self.save_location == 2:
            bj.node_bake_settings.external_save_path = path
        else:
            self.report({'WARNING'}, "Invalid save location target.")
            return {'CANCELLED'}
            
        return {'FINISHED'}

class BAKETOOL_OT_RefreshUDIM(bpy.types.Operator):
    bl_idname = "bake.refresh_udim_locations"
    bl_label = "Refresh / Repack UDIMs"
    def execute(self, context):
        bj = context.scene.BakeJobs
        if not (bj.jobs and bj.job_index >= 0 and bj.job_index < len(bj.jobs)):
             self.report({'WARNING'}, "No active job selected for UDIM refresh.")
             return {'CANCELLED'}
             
        s = bj.jobs[bj.job_index].setting
        objs = [o.bakeobject for o in s.bake_objects if o.bakeobject]
        if not objs: 
            self.report({'WARNING'}, "No objects assigned to this job.")
            return {'CANCELLED'}
        from .core.engine import UDIMPacker
        if s.udim_mode == 'REPACK': assignments = UDIMPacker.calculate_repack(objs)
        else: assignments = {o: detect_object_udim_tile(o) for o in objs}
        for bo in s.bake_objects:
            if bo.bakeobject in assignments: bo.udim_tile = assignments[bo.bakeobject]
        return {'FINISHED'}

class BAKETOOL_OT_ManageObjects(bpy.types.Operator):
    bl_idname = "bake.manage_objects"
    bl_label = "Manage Objects"
    bl_options = {'REGISTER', 'UNDO'}
    action: props.EnumProperty(
        name="Action",
        items=[
            ('SET', 'Set', 'Replace entire object list with current selection'),
            ('ADD', 'Add', 'Add selected objects to the job'),
            ('REMOVE', 'Remove', 'Remove selected objects from the job'),
            ('CLEAR', 'Clear', 'Remove all objects from this job'),
            ('SET_ACTIVE', 'Set Active', 'Set the active object as the bake target'),
            ('SMART_SET', 'Smart Set', 'Auto-assign objects based on naming conventions (_high/_low)')
        ]
    )
    def execute(self, context):
        bj = context.scene.BakeJobs
        if not bj.jobs: 
            self.report({'WARNING'}, "No jobs available.")
            return {'CANCELLED'}
        if bj.job_index < 0 or bj.job_index >= len(bj.jobs):
            bj.job_index = 0
            
        s = bj.jobs[bj.job_index].setting
        sel = [o for o in context.selected_objects if o.type == 'MESH']
        act = context.active_object if (context.active_object and context.active_object.type == 'MESH') else None
        
        from .core.common import manage_objects_logic
        manage_objects_logic(s, self.action, sel, act)
        return {'FINISHED'}

class BAKETOOL_OT_SaveSetting(bpy.types.Operator):
    bl_idname = "bake.save_setting"
    bl_label = "Save Preset"
    filepath: props.StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event): 
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
        
    def execute(self, context):
        bj = context.scene.BakeJobs
        if not (bj.jobs and bj.job_index >= 0 and bj.job_index < len(bj.jobs)):
             self.report({'WARNING'}, "No active job to save")
             return {'CANCELLED'}
             
        data = preset_handler.PropertyIO(exclude_props={'active_channel_index'}).to_dict(bj)
        path = self.filepath if self.filepath.endswith(".json") else self.filepath+".json"
        with open(path, 'w') as f: json.dump(data, f, indent=4)
        return {'FINISHED'}

class BAKETOOL_OT_LoadSetting(bpy.types.Operator):
    bl_idname = "bake.load_setting"
    bl_label = "Load Preset"
    filepath: props.StringProperty(subtype="FILE_PATH")
    
    def invoke(self, context, event): 
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
        
    def execute(self, context):
        with open(self.filepath, 'r') as f: data = json.load(f)
        preset_handler.PropertyIO().from_dict(context.scene.BakeJobs, data)
        return {'FINISHED'}

class BAKETOOL_OT_RefreshPresets(bpy.types.Operator):
    """Scan library path and load thumbnails"""
    bl_idname = "bake.refresh_presets"
    bl_label = "Refresh Preset Library"
    
    def execute(self, context):
        from .core import thumbnail_manager
        prefs = context.preferences.addons[__package__].preferences
        if prefs.library_path:
            thumbnail_manager.load_preset_thumbnails(prefs.library_path)
            self.report({'INFO'}, f"Library refreshed from: {prefs.library_path}")
        else:
            self.report({'WARNING'}, "Library path not set in Addon Preferences.")
        return {'FINISHED'}

class BAKETOOL_OT_BakeSelectedNode(bpy.types.Operator):
    bl_label = "Bake Node"; bl_idname = "bake.selected_node_bake"
    def execute(self, context):
        from .core.node_manager import bake_node_to_image
        
        nbs = context.scene.BakeJobs.node_bake_settings
        if not context.active_object:
             self.report({'WARNING'}, "No active object")
             return {'CANCELLED'}
             
        mat = context.active_object.active_material
        node = getattr(context, 'active_node', None)
        
        if not mat:
            self.report({'WARNING'}, "Active object has no material")
            return {'CANCELLED'}
        if not node:
            self.report({'WARNING'}, "No node selected in the Shader Editor")
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
        results = context.scene.baked_image_results
        idx = context.scene.baked_image_results_index
        if idx >= 0 and idx < len(results):
             results.remove(idx)
             context.scene.baked_image_results_index = max(0, idx - 1)
        return {'FINISHED'}

class BAKETOOL_OT_DeleteAllResults(bpy.types.Operator):
    bl_idname = "baketool.delete_all_results"; bl_label = "Delete All"
    def execute(self, context): context.scene.baked_image_results.clear(); return {'FINISHED'}

class BAKETOOL_OT_ExportResult(bpy.types.Operator):
    bl_idname = "baketool.export_result"; bl_label = "Export"; filepath: props.StringProperty(subtype="FILE_PATH")
    def invoke(self, context, event): context.window_manager.fileselect_add(self); return {'RUNNING_MODAL'}
    def execute(self, context):
        results = context.scene.baked_image_results
        idx = context.scene.baked_image_results_index
        # C-06: Bounds check
        if 0 <= idx < len(results):
            r = results[idx]
            if r.image: 
                # Ensure directory exists or use default
                export_dir = os.path.dirname(self.filepath)
                if not os.path.exists(export_dir):
                    try: os.makedirs(export_dir)
                    except Exception: pass
                save_image(r.image, export_dir) 
                self.report({'INFO'}, f"Exported {r.image.name} to {export_dir}")
            else:
                self.report({'WARNING'}, "Selected result has no valid image data.")
                return {'CANCELLED'}
        else:
            self.report({'WARNING'}, "Select a valid result from the list to export.")
            return {'CANCELLED'}
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

class BAKETOOL_OT_AnalyzeCage(bpy.types.Operator):
    """Run raycast analysis to find cage intersections"""
    bl_idname = "bake.analyze_cage"
    bl_label = "Analyze Cage Overlap"
    
    @classmethod
    def poll(cls, context):
        if not context.active_object: return False
        return context.active_object.type == 'MESH'

    def execute(self, context):
        if not hasattr(context.scene, "BakeJobs"): return {'CANCELLED'}
        bj = context.scene.BakeJobs
        if not bj.jobs: return {'CANCELLED'}
        job = bj.jobs[bj.job_index]
        s = job.setting

        sel_objs = [o for o in context.selected_objects if o.type == 'MESH']
        act_obj = context.active_object if (context.active_object and context.active_object.type == 'MESH') else None
        
        if s.bake_mode == 'SELECT_ACTIVE':
            low = act_obj
            highs = [o for o in sel_objs if o != low]
        else:
            self.report({'WARNING'}, "Cage analysis requires 'Selected to Active' mode.")
            return {'CANCELLED'}

        if not highs:
            self.report({'WARNING'}, "Select high poly objects first, then shift-select the low poly.")
            return {'CANCELLED'}

        from .core.cage_analyzer import CageAnalyzer
        success, msg = CageAnalyzer.run_raycast_analysis(context, low, highs, extrusion=s.extrusion, auto_switch_vp=s.auto_switch_vertex_paint)
        
        return {'FINISHED'}

class BAKETOOL_OT_OneClickPBR(bpy.types.Operator):
    """Setup standard PBR channels (Color, Roughness, Normal) for the current job"""
    bl_idname = "bake.one_click_pbr"
    bl_label = "One-Click PBR Setup"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        if not hasattr(context.scene, "BakeJobs"): return False
        bj = context.scene.BakeJobs
        return len(bj.jobs) > 0
        
    def execute(self, context):
        bj = context.scene.BakeJobs
        if bj.job_index < 0 or bj.job_index >= len(bj.jobs):
            return {'CANCELLED'}
        job = bj.jobs[bj.job_index]
        s = job.setting
        
        # Enable specific standard ones
        standards = {'color', 'rough', 'normal'}
        for c in s.channels:
            if c.id in standards:
                c.enabled = True
        
        self.report({'INFO'}, "Standard PBR channels (Color, Roughness, Normal) enabled.")
        return {'FINISHED'}

class BAKETOOL_OT_OpenAddonPrefs(bpy.types.Operator):
    """Open Addon Preferences to fix dependencies"""
    bl_idname = "bake.open_addon_prefs"
    bl_label = "Addon Prefs"
    
    def execute(self, context):
        bpy.ops.screen.userpref_show('INVOKE_DEFAULT')
        # Use simple search instead of complex section mapping for better reliability
        return {'FINISHED'}