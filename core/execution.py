"""
Bake Execution Logic
Contains the modal operator mixin and execution flow management.
Extracted from ops.py for better separation of concerns.
"""
import bpy
import logging
from ..state_manager import BakeStateManager
from .engine import BakeStepRunner
from .common import log_error

logger = logging.getLogger(__name__)


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

    def _process_single_step(self, context, step):
        job, task, f_info = step.job, step.task, step.frame_info
        context.scene.bake_status = f"[{self.current_step_idx+1}/{self.total_steps}] {task.base_name}"
        
        if f_info: 
            context.scene.frame_set(f_info['frame'])
        
        runner = BakeStepRunner(context)
        results = runner.run(step, self.state_mgr)
        
        for res in results:
            self._add_ui_result(context, res['image'], res['type'], res['obj'], res['path'], res.get('meta'))
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

    def _add_ui_result(self, context, img, type_name, obj_name, path, meta=None):
        import os
        results = context.scene.baked_image_results
        if any(r.image == img for r in results): return
        item = results.add()
        item.image = img
        item.channel_type = type_name 
        item.object_name = obj_name
        item.filepath = path or ""
        
        # Apply metadata if available
        if meta:
            item.res_x = meta.get('res_x', 0)
            item.res_y = meta.get('res_y', 0)
            item.samples = meta.get('samples', 0)
            item.duration = meta.get('duration', 0.0)
            item.bake_type = meta.get('bake_type', 'UNKNOWN')
            item.device = meta.get('device', 'UNKNOWN')
            
            # Calculate file size if path exists
            if path and os.path.exists(path):
                size_bytes = os.path.getsize(path)
                if size_bytes < 1024:
                    item.file_size = f"{size_bytes} B"
                elif size_bytes < 1048576:
                    item.file_size = f"{size_bytes/1024:.1f} KB"
                else:
                    item.file_size = f"{size_bytes/1048576:.1f} MB"
            else:
                item.file_size = "N/A (Memory)"

    def _handle_step_error(self, context, e):
        err_msg = f"[Error] Step {self.current_step_idx+1}: {str(e)}"
        log_error(context, err_msg, self.state_mgr, include_traceback=True)

    def _cleanup_state(self, context, status="Finished"):
        if self.state_mgr: 
            self.state_mgr.finish_session(context, status)
        self._remove_timer(context)

    def finish(self, context):
        self._cleanup_state(context, "Finished")
        # Reload sequences if any
        for img, info in self.sequence_tracking.items():
            try:
                img.source, img.filepath, img.frame_duration = 'SEQUENCE', info['first_path'], info['count']
                img.reload()
            except Exception: pass
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
            except Exception: pass
            self._timer = None
