"""
Bake Execution Logic
Contains the modal operator mixin and execution flow management.
Extracted from ops.py for better separation of concerns.
"""
import os
import bpy
import logging
import time
from typing import Any, Dict, List, Optional, Set
from ..state_manager import BakeStateManager
from .engine import BakeStepRunner
from .common import log_error
from . import compat

logger = logging.getLogger(__name__)


def add_bake_result_to_ui(
    context: bpy.types.Context,
    img: bpy.types.Image,
    type_name: str,
    obj_name: str,
    path: str,
    meta: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:
    """
    Standardized utility to add a bake result to the scene's UI collection
    and populate metadata (resolution, time, file size).
    """
    results = context.scene.baked_image_results
    # Prevent duplicates
    if any(r.image == img for r in results):
        return None

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
        item.bake_time = meta.get('bake_time', 0.0)
        item.save_time = meta.get('save_time', 0.0)
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
    return item

class BakeModalOperator:
    """
    Mixin class providing robust modal execution logic, progress tracking,
    and crash recovery for any bake operation.
    Subclasses must populate `self.bake_queue` in `invoke`.
    """

    def __init__(self):
        """Initialize core state attributes for early-exit protection."""
        self._timer: Optional[Any] = None
        self.state_mgr: Optional[BakeStateManager] = None
        self.bake_queue: List[Any] = []
        self.current_step_idx: int = 0
        self.total_steps: int = 0
        self.sequence_tracking: Dict[Any, Any] = {}
        self.waiting_confirmation: bool = False

    def init_modal(self, context: bpy.types.Context, start_idx: int = 0) -> Set[str]:
        """Initialize state and start modal timer."""
        # Initialize instance variables defensively
        self._timer = None
        self.state_mgr = BakeStateManager()
        self._original_frame = context.scene.frame_current

        if not hasattr(self, "bake_queue") or self.bake_queue is None:
            self.bake_queue = []

        self.total_steps = len(self.bake_queue)
        self.current_step_idx = start_idx
        self.sequence_tracking = {}

        context.scene.is_baking = True
        context.scene.bake_progress = (self.current_step_idx / max(1, self.total_steps)) * 100.0
        context.scene.bake_status = "Initializing..."

        # HI-04: Append session separator instead of clearing history
        timestamp = time.strftime('%H:%M:%S')
        context.scene.bake_error_log += f"\n--- New bake session {timestamp} ---\n"

        # Extract job names for logging
        job_names = list(set(step.job.name for step in self.bake_queue))
        if start_idx == 0:
            self.state_mgr.start_session(self.total_steps, ",".join(job_names))

        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> Set[str]:
        # C-03: Cancel Confirmation Logic
        if hasattr(self, "waiting_confirmation") and self.waiting_confirmation:
            if event.type in {'RET', 'NUMPAD_ENTER', 'Y'}:
                self.cancel(context)
                return {'CANCELLED'}
            elif event.type in {'ESC', 'N', 'BACK_SPACE'}:
                self.waiting_confirmation = False
                context.scene.bake_status = getattr(self, "_last_status", "Resuming...")
                return {'RUNNING_MODAL'}
            return {'RUNNING_MODAL'}

        if event.type == 'TIMER':
            if self.current_step_idx >= self.total_steps:
                self.finish(context)
                return {'FINISHED'}

            try:
                # Check cancellation flag (from UI button)
                if not context.scene.is_baking:
                    self.cancel(context)
                    return {'CANCELLED'}

                step = self.bake_queue[self.current_step_idx]
                self._process_single_step(context, step)

            except (AttributeError, RuntimeError, TypeError, ValueError) as e:
                self._handle_step_error(context, e)

            self.current_step_idx += 1
            context.scene.bake_progress = (self.current_step_idx / max(1, self.total_steps)) * 100.0

        elif event.type == 'ESC':
            self.waiting_confirmation = True
            self._last_status = context.scene.bake_status
            context.scene.bake_status = bpy.app.translations.pgettext("!! STOP BAKING? Press Y/Enter to Stop, N/Esc to Resume !!")
            return {'RUNNING_MODAL'}

        return {'RUNNING_MODAL'}

    def _process_single_step(self, context, step):
        job, task, f_info = step.job, step.task, step.frame_info
        context.scene.bake_status = f"[{self.current_step_idx+1}/{self.total_steps}] {task.base_name}"

        if f_info:
            context.scene.frame_set(f_info['frame'])

        runner = BakeStepRunner(context)
        results = runner.run(step, self.state_mgr, self.current_step_idx)

        for res in results:
            add_bake_result_to_ui(context, res['image'], res['type'], res['obj'], res['path'], res.get('meta'))

            # Deep GC Pipeline: Free GPU/VRAM buffers immediately after step completion and save.
            img = res['image']
            if img:
                try:
                    # CB-4: gl_free() is removed in Blender 5.0+
                    if not compat.is_blender_5() and hasattr(img, 'gl_free'):
                        img.gl_free()

                    if hasattr(img, 'buffers_free'):
                        img.buffers_free()
                except (AttributeError, RuntimeError) as e:
                    logger.debug(f"GC Guard Free Error on {img.name}: {e}")

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

    def _handle_step_error(self, context, e):
        err_msg = f"[Error] Step {self.current_step_idx+1}: {str(e)}"
        log_error(context, err_msg, self.state_mgr, include_traceback=True)

    def _cleanup_state(self, context, status="Finished"):
        if self.state_mgr:
            self.state_mgr.finish_session(context, status)
        self._remove_timer(context)
        if hasattr(self, "_original_frame"):
            try:
                context.scene.frame_set(self._original_frame)
            except (RuntimeError, AttributeError):
                pass

    def finish(self, context: bpy.types.Context) -> None:
        """Complete the bake session, save sequence data, and optionally save-and-quit."""
        self._cleanup_state(context, "Finished")
        # Reload sequences if any
        for img, info in self.sequence_tracking.items():
            try:
                img.source, img.filepath, img.frame_duration = 'SEQUENCE', info['first_path'], info['count']
                img.reload()
            except RuntimeError as e:
                logger.error(f"Failed to reload sequence: {e}")
        self.sequence_tracking.clear()

        if self.bake_queue and hasattr(self.bake_queue[0].job, 'setting'):
            s = self.bake_queue[0].job.setting
            if getattr(s, 'save_and_quit', False):
                logger.warning(
                    "BakeNexus: save_and_quit enabled - "
                    "saving all changes and exiting Blender. "
                    "Any unsaved changes in other areas will also be saved."
                )
                if not bpy.data.filepath:
                    logger.error(
                        "BakeNexus: save_and_quit cancelled - blend file not saved on disk."
                    )
                else:
                    try:
                        bpy.ops.wm.save_mainfile()
                    except (RuntimeError, AttributeError) as e:
                        logger.error(f"BakeNexus: save_mainfile failed before quit: {e}")
                bpy.ops.wm.quit_blender()

    def cancel(self, context: bpy.types.Context) -> None:
        """Cancel the bake session and clean up state."""
        self._cleanup_state(context, "Cancelled")

    def _remove_timer(self, context: bpy.types.Context) -> None:
        if self._timer:
            try:
                context.window_manager.event_timer_remove(self._timer)
            except (AttributeError, RuntimeError):
                pass
            self._timer = None
