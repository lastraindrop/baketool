"""Operator definitions for BakeNexus.

This module contains all Blender Operators used by the BakeNexus add-on,
handling UI interactions, baking orchestration, and data management.
"""

import bpy
from bpy import props
import logging
import os
import subprocess
import tempfile
import traceback
import json
from pathlib import Path
from typing import Optional, List, Set, Any, Dict
from bpy_extras.io_utils import ExportHelper, ImportHelper

from .core.common import (
    apply_baked_result,
    safe_context_override,
    reset_channels_logic,
    check_objects_uv,
    log_error,
    manage_channels_logic,
    manage_objects_logic,
)
from .core.image_manager import set_image, save_image
from .core.uv_manager import UVLayoutManager, detect_object_udim_tile
from .core.math_utils import pack_channels_numpy
from .core.engine import (
    BakeStep,
    BakeTask,
    TaskBuilder,
    JobPreparer,
    BakeContextManager,
    BakePassExecutor,
    ModelExporter,
    BakeStepRunner,
)
from .core.execution import BakeModalOperator
from .core import compat
from . import preset_handler
from .constants import UI_MESSAGES
from .state_manager import BakeStateManager

logger = logging.getLogger(__name__)


class _DummyEvent:
    """Mock event object for script-based operator invocations.

    Attributes:
        event_type (str): Type of event.
        event_value (str): Value of event (e.g., 'PRESS').
        mouse_x (int): X coordinate of mouse.
        mouse_y (int): Y coordinate of mouse.
    """

    event_type: str = "NONE"
    event_value: str = "PRESS"
    mouse_x: int = 0
    mouse_y: int = 0
    shift: bool = False
    ctrl: bool = False
    alt: bool = False
    oskey: bool = False


# --- Operators ---


class BAKETOOL_OT_RunDevTests(bpy.types.Operator):
    """Run all internal test suites and report results to UI.

    Iterates through all registered test suites and executes them using
    unittest, providing feedback to the user via the sidebar.
    """

    bl_idname = "baketool.run_dev_tests"
    bl_label = "Run Development Tests"

    _SUBPROCESS_TIMEOUT_SECONDS = 1800

    @staticmethod
    def _summarize_subprocess_report(report: Dict[str, Any]) -> str:
        """Build a concise UI summary from the CLI JSON report."""
        summary = report.get("summary", {})
        total = int(summary.get("total", 0))
        passed = int(summary.get("passed", 0))
        failures = int(summary.get("failures", 0))
        errors = int(summary.get("errors", 0))
        skipped = int(summary.get("skipped", 0))
        return (
            f"Isolated audit: {passed}/{total} passed, "
            f"{failures} fails, {errors} errors, {skipped} skipped."
        )

    @classmethod
    def _run_isolated_test_suite(cls) -> tuple[bool, str]:
        """Run the full suite in a separate Blender process.

        Running tests inside the current interactive session is unsafe because
        they mutate scene RNA that the UI may still reference, which can lead
        to hard crashes during redraw/path resolution.
        """
        addon_root = Path(__file__).resolve().parent
        cli_runner = addon_root / "automation" / "cli_runner.py"
        blender_binary = Path(bpy.app.binary_path) if bpy.app.binary_path else None

        if not blender_binary or not blender_binary.exists():
            return False, "Safety audit unavailable: Blender executable not found."
        if not cli_runner.exists():
            return False, "Safety audit unavailable: automation runner not packaged."

        report_path: Optional[Path] = None
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

        try:
            with tempfile.NamedTemporaryFile(
                prefix="bakenexus_devtests_",
                suffix=".json",
                delete=False,
            ) as handle:
                report_path = Path(handle.name)

            cmd = [
                str(blender_binary),
                "-b",
                "--factory-startup",
                "--python",
                str(cli_runner),
                "--",
                "--discover",
                "--json",
                str(report_path),
            ]
            completed = subprocess.run(
                cmd,
                cwd=str(addon_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=cls._SUBPROCESS_TIMEOUT_SECONDS,
                creationflags=creationflags,
                check=False,
            )

            report = {}
            if report_path.exists() and report_path.stat().st_size > 0:
                with open(report_path, "r", encoding="utf-8") as handle:
                    report = json.load(handle)

            if report:
                summary = report.get("summary", {})
                info = cls._summarize_subprocess_report(report)
                success = (
                    completed.returncode == 0
                    and not summary.get("errors")
                    and not summary.get("failures")
                )
                return success, info

            output_lines = [
                line.strip()
                for line in (completed.stdout + "\n" + completed.stderr).splitlines()
                if line.strip()
            ]
            tail = (
                " | ".join(output_lines[-3:])
                if output_lines
                else f"exit code {completed.returncode}"
            )
            return completed.returncode == 0, f"Isolated audit finished without report: {tail}"
        except subprocess.TimeoutExpired:
            return False, f"Safety audit timed out after {cls._SUBPROCESS_TIMEOUT_SECONDS}s."
        except Exception as exc:
            logger.exception("Failed to launch isolated BakeNexus safety audit")
            return False, f"Safety audit launch failed: {exc}"
        finally:
            if report_path and report_path.exists():
                try:
                    report_path.unlink()
                except OSError:
                    pass

    def execute(self, context: bpy.types.Context) -> Set[str]:
        """Execute the full test suite in an isolated Blender process.

        Args:
            context: Blender context.

        Returns:
            Set[str]: {'FINISHED'}.
        """
        passed, info = self._run_isolated_test_suite()
        try:
            context.scene.last_test_info = info
            context.scene.test_pass = passed
        except (AttributeError, RuntimeError):
            pass

        if passed:
            self.report({"INFO"}, info)
        else:
            self.report({"ERROR"}, info)

        return {"FINISHED"}


class BAKETOOL_OT_BakeOperator(bpy.types.Operator, BakeModalOperator):
    """Executes the texture baking process for selected objects.

    This operator handles the complete baking pipeline including
    validation, UV preparation, task building, and result saving.
    Uses modal execution for progress tracking and crash recovery.
    """

    bl_label = "Bake"
    bl_idname = "baketool.execute"

    is_resume: props.BoolProperty(default=False)

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Ensure no other bake process is running.

        Returns:
            bool: True if baking can start.
        """
        return not context.scene.is_baking

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> Set[str]:
        """Initialize the bake queue and start modal execution.

        Args:
            context: Blender context.
            event: Event that triggered the invocation.

        Returns:
            Set[str]: {'RUNNING_MODAL'} or {'CANCELLED'}.
        """
        if context.object and context.object.mode != "OBJECT":
            try:
                bpy.ops.object.mode_set(mode="OBJECT")
            except (RuntimeError, AttributeError):
                pass
        try:
            enabled_jobs = [j for j in context.scene.BakeJobs.jobs if j.enabled]
            if not enabled_jobs:
                self.report({"WARNING"}, UI_MESSAGES["NO_JOBS"])
                return {"CANCELLED"}

            self.bake_queue = JobPreparer.prepare_execution_queue(context, enabled_jobs)

            if not self.bake_queue:
                self.report({"WARNING"}, "Nothing to bake (Check logs/setup).")
                return {"CANCELLED"}

            start_idx = 0
            if self.is_resume:
                mgr = BakeStateManager()
                if mgr.has_crash_record():
                    data = mgr.read_log()
                    if data:
                        start_idx = data.get("current_queue_idx", 0)

        except (RuntimeError, ValueError) as e:
            err_msg = UI_MESSAGES.get(
                "PREP_FAILED", "Bake preparation failed: {0}"
            ).format(str(e))
            self.report({"ERROR"}, err_msg)
            log_error(context, err_msg, include_traceback=True)
            return {"CANCELLED"}

        return self.init_modal(context, start_idx=start_idx)


class BAKETOOL_OT_QuickBake(bpy.types.Operator, BakeModalOperator):
    """Bake current selection using active job settings immediately.

    This operator provides quick baking for the current object selection
    using the active job as a template, without requiring full job setup.
    """

    bl_idname = "baketool.quick_bake"
    bl_label = "Quick Bake Selected"

    def execute(self, context: bpy.types.Context) -> Set[str]:
        """Support non-interactive execution.

        Args:
            context: Blender context.

        Returns:
            Set[str]: Result of invocation.
        """
        return self.invoke(context, _DummyEvent())

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> Set[str]:
        """Prepare quick bake queue and start modal.

        Args:
            context: Blender context.
            event: Triggering event.

        Returns:
            Set[str]: Modal result.
        """
        if not hasattr(context.scene, "BakeJobs"):
            self.report({"ERROR"}, "BakeNexus properties not initialized.")
            return {"CANCELLED"}

        bj = context.scene.BakeJobs
        if not bj.jobs:
            return {"CANCELLED"}
        job_index = bj.job_index
        if job_index < 0 or job_index >= len(bj.jobs):
            job_index = 0
        job = bj.jobs[job_index]

        sel_objs = [o for o in context.selected_objects if o.type == "MESH"]
        act_obj = (
            context.active_object
            if (context.active_object and context.active_object.type == "MESH")
            else None
        )

        if not sel_objs:
            self.report({"WARNING"}, "Select mesh objects to bake.")
            return {"CANCELLED"}

        try:
            self.bake_queue = JobPreparer.prepare_quick_bake_queue(
                context, job, sel_objs, act_obj
            )

            if not self.bake_queue:
                self.report({"WARNING"}, UI_MESSAGES["QUICK_PREP_FAILED"])
                return {"CANCELLED"}

        except (RuntimeError, ValueError) as e:
            err_msg = f"Quick Bake preparation failed: {str(e)}"
            self.report({"ERROR"}, err_msg)
            log_error(context, err_msg, include_traceback=True)
            return {"CANCELLED"}

        return self.init_modal(context)


class BAKETOOL_OT_ResetChannels(bpy.types.Operator):
    """Reset bake channels to default configuration based on bake type."""

    bl_idname = "baketool.reset_channels"
    bl_label = "Reset"

    def execute(self, context: bpy.types.Context) -> Set[str]:
        bj = context.scene.BakeJobs
        if bj.job_index < 0 or job_index >= len(bj.jobs):
            return {"CANCELLED"}
        job = bj.jobs[bj.job_index]
        reset_channels_logic(job.setting)
        self.report({"INFO"}, "Channels reset to default for current bake type.")
        return {"FINISHED"}


class BAKETOOL_OT_SetSaveLocal(bpy.types.Operator):
    """Point save paths to the current blend directory or a safe temp fallback."""

    bl_idname = "baketool.set_save_local"
    bl_label = "Use Local Path"

    save_location: props.IntProperty(default=0)

    @staticmethod
    def _resolve_local_dir() -> str:
        if bpy.data.filepath:
            return str(Path(bpy.data.filepath).resolve().parent)
        return str(Path(bpy.app.tempdir or os.getcwd()).resolve())

    def execute(self, context: bpy.types.Context) -> Set[str]:
        if not hasattr(context.scene, "BakeJobs"):
            return {"CANCELLED"}

        bj = context.scene.BakeJobs
        local_dir = self._resolve_local_dir()
        target = None

        if self.save_location == 2:
            target = bj.node_bake_settings
        elif self.save_location == 1:
            target = bj.bake_result_settings
        elif bj.jobs:
            job_index = bj.job_index if 0 <= bj.job_index < len(bj.jobs) else 0
            target = bj.jobs[job_index].setting

        if target is None:
            self.report({"WARNING"}, "No save target is available.")
            return {"CANCELLED"}

        target.external_save_path = local_dir
        self.report({"INFO"}, f"Save path set to {local_dir}")
        return {"FINISHED"}


class BAKETOOL_OT_SelectedNodeBake(bpy.types.Operator):
    """Bake the active shader node to an image using node-bake settings."""

    bl_idname = "baketool.selected_node_bake"
    bl_label = "Bake Selected Node"

    def execute(self, context: bpy.types.Context) -> Set[str]:
        if not hasattr(context.scene, "BakeJobs"):
            self.report({"ERROR"}, "BakeNexus properties not initialized.")
            return {"CANCELLED"}

        obj = context.active_object
        if not obj or obj.type != "MESH":
            self.report({"WARNING"}, "Active mesh object required.")
            return {"CANCELLED"}

        mat = obj.active_material
        if not mat or not mat.use_nodes or not mat.node_tree:
            self.report({"WARNING"}, "Active material with nodes required.")
            return {"CANCELLED"}

        node = mat.node_tree.nodes.active
        if not node:
            self.report({"WARNING"}, "Select an active shader node to bake.")
            return {"CANCELLED"}
        if not node.outputs:
            self.report({"WARNING"}, "Selected node has no output sockets.")
            return {"CANCELLED"}

        settings = context.scene.BakeJobs.node_bake_settings
        from .core.node_manager import bake_node_to_image
        from .core.execution import add_bake_result_to_ui

        image = bake_node_to_image(context, mat, node, settings)
        if not image:
            self.report({"ERROR"}, f"Failed to bake node '{node.name}'.")
            return {"CANCELLED"}

        path = image.filepath_raw if settings.use_external_save else ""
        add_bake_result_to_ui(
            context,
            image,
            node.name,
            obj.name,
            path,
            {
                "res_x": image.size[0],
                "res_y": image.size[1],
                "samples": int(getattr(settings, "sample", 1)),
                "duration": 0.0,
                "bake_time": 0.0,
                "save_time": 0.0,
                "bake_type": "NODE_BAKE",
                "device": getattr(context.scene.cycles, "device", "UNKNOWN"),
            },
        )
        self.report({"INFO"}, f"Baked node '{node.name}'.")
        return {"FINISHED"}


class BAKETOOL_OT_RefreshUDIMLocations(bpy.types.Operator):
    """Rescan assigned bake objects and sync their detected UDIM tiles."""

    bl_idname = "baketool.refresh_udim_locations"
    bl_label = "Refresh UDIM Tiles"

    def execute(self, context: bpy.types.Context) -> Set[str]:
        if not os.path.exists(self.filepath):
            return {"CANCELLED"}

        bj = context.scene.BakeJobs
        if not bj.jobs:
            bj.jobs.add()
            bj.job_index = 0
        job = bj.jobs[job_index]
        synced = 0

        for bake_obj in job.setting.bake_objects:
            obj = bake_obj.bakeobject
            if not obj or obj.type != "MESH":
                continue
            bake_obj.udim_tile = detect_object_udim_tile(obj)
            synced += 1

        self.report({"INFO"}, f"Synchronized UDIM tiles for {synced} objects.")
        return {"FINISHED"}


class BAKETOOL_OT_TogglePreview(bpy.types.Operator):
    """Toggle real-time viewport preview for the active bake job."""

    bl_idname = "baketool.toggle_preview"
    bl_label = "Toggle Preview"

    def execute(self, context: bpy.types.Context) -> Set[str]:
        bj = context.scene.BakeJobs
        if not bj.jobs:
            return {"CANCELLED"}
        job_index = bj.job_index
        if job_index < 0 or job_index >= len(bj.jobs):
            job_index = 0
        job = bj.jobs[job_index]
        s = job.setting

        from .core import shading

        s.use_preview = not s.use_preview
        objs = [o.bakeobject for o in s.bake_objects if o.bakeobject]

        if not objs:
            self.report({"WARNING"}, "No objects to preview")
            s.use_preview = False
            return {"CANCELLED"}

        for obj in objs:
            if s.use_preview:
                shading.apply_preview(obj, s)
            else:
                shading.remove_preview(obj)

        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()

        return {"FINISHED"}


class BAKETOOL_OT_AnalyzeCage(bpy.types.Operator):
    """Analyze cage overlap by raycasting high-poly onto low-poly."""

    bl_idname = "baketool.analyze_cage"
    bl_label = "Analyze Cage Overlap"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Ensure active object is a mesh.

        Returns:
            bool: True if analysis is possible.
        """
        if not context.active_object:
            return False
        return context.active_object.type == "MESH"

    def execute(self, context: bpy.types.Context) -> Set[str]:
        """Execute BVH-based raycast analysis.

        Args:
            context: Blender context.

        Returns:
            Set[str]: {'FINISHED'} or {'CANCELLED'}.
        """
        if not hasattr(context.scene, "BakeJobs"):
            return {"CANCELLED"}
        bj = context.scene.BakeJobs
        if not bj.jobs:
            return {"CANCELLED"}
        job_index = bj.job_index
        if job_index < 0 or job_index >= len(bj.jobs):
            job_index = 0
        job = bj.jobs[job_index]
        s = job.setting
        act_obj = (
            context.active_object
            if (context.active_object and context.active_object.type == "MESH")
            else None
        )
        sel_objs = [o for o in context.selected_objects if o.type == "MESH"]

        if s.bake_mode == "SELECT_ACTIVE":
            low = act_obj
            highs = [o for o in sel_objs if o != low]
        else:
            self.report({"WARNING"}, "Requires 'Selected to Active' mode.")
            return {"CANCELLED"}

        if not highs:
            self.report({"WARNING"}, "Select high poly objects first.")
            return {"CANCELLED"}

        from .core.cage_analyzer import CageAnalyzer

        success, msg = CageAnalyzer.run_raycast_analysis(
            context,
            low,
            highs,
            extrusion=s.extrusion,
            auto_switch_vp=s.auto_switch_vertex_paint,
        )
        self.report({"INFO"}, msg)
        return {"FINISHED"}


class BAKETOOL_OT_OneClickPBR(bpy.types.Operator):
    """Setup standard PBR channels (Color, Roughness, Normal) for the job."""

    bl_idname = "baketool.one_click_pbr"
    bl_label = "One-Click PBR Setup"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Ensure a job exists.

        Returns:
            bool: True if job is available.
        """
        if not hasattr(context.scene, "BakeJobs"):
            return False
        bj = context.scene.BakeJobs
        return len(bj.jobs) > 0

    def execute(self, context: bpy.types.Context) -> Set[str]:
        """Enable standard PBR channels.

        Args:
            context: Blender context.

        Returns:
            Set[str]: {'FINISHED'} or {'CANCELLED'}.
        """
        bj = context.scene.BakeJobs
        if bj.job_index < 0 or bj.job_index >= len(bj.jobs):
            return {"CANCELLED"}
        job = bj.jobs[bj.job_index]
        s = job.setting

        standards = {"color", "rough", "normal"}
        for c in s.channels:
            if c.id in standards:
                c.enabled = True

        self.report({"INFO"}, "Standard PBR channels enabled.")
        return {"FINISHED"}


class BAKETOOL_OT_OpenAddonPrefs(bpy.types.Operator):
    """Open Blender addon preferences for configuring dependencies."""

    bl_idname = "baketool.open_addon_prefs"
    bl_label = "Addon Prefs"

    def execute(self, context: bpy.types.Context) -> Set[str]:
        """Open user preferences.

        Args:
            context: Blender context.

        Returns:
            Set[str]: {'FINISHED'}.
        """
        bpy.ops.screen.userpref_show("INVOKE_DEFAULT")
        return {"FINISHED"}


class BAKETOOL_OT_DeleteResult(bpy.types.Operator):
    """Delete the currently selected baked result."""

    bl_idname = "baketool.delete_result"
    bl_label = "Delete"

    def execute(self, context: bpy.types.Context) -> Set[str]:
        results = context.scene.baked_image_results
        idx = context.scene.baked_image_results_index

        if 0 <= idx < len(results):
            r = results[idx]
            img = r.image

            r.image = None
            results.remove(idx)
            context.scene.baked_image_results_index = max(0, idx - 1)

            context.view_layer.depsgraph.update()

            if img and img.users == 0:
                try:
                    bpy.data.images.remove(img, do_unlink=True)
                except (ReferenceError, RuntimeError) as e:
                    logger.debug(f"Failed to remove image: {e}")
        return {"FINISHED"}


class BAKETOOL_OT_DeleteAllResults(bpy.types.Operator):
    """Delete all baked results and their associated images."""

    bl_idname = "baketool.delete_all_results"
    bl_label = "Delete All"

    def execute(self, context: bpy.types.Context) -> Set[str]:
        results = context.scene.baked_image_results
        images = [r.image for r in results if r.image]

        results.clear()

        for img in images:
            if img.users == 0:
                try:
                    bpy.data.images.remove(img, do_unlink=True)
                except (ReferenceError, RuntimeError):
                    pass
            else:
                img.use_fake_user = False

        return {"FINISHED"}


class BAKETOOL_OT_ExportResult(bpy.types.Operator):
    """Export the selected baked result to disk."""

    bl_idname = "baketool.export_result"
    bl_label = "Export"
    filepath: props.StringProperty(subtype="FILE_PATH")

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> Set[str]:
        results = context.scene.baked_image_results
        idx = context.scene.baked_image_results_index
        if not (0 <= idx < len(results)):
            return {"CANCELLED"}

        res = results[idx]
        if not res.image:
            return {"CANCELLED"}

        img = res.image
        default_path = bpy.data.filepath
        if not default_path:
            default_path = "untitled"

        name = os.path.splitext(os.path.basename(default_path))[0]
        self.filepath = f"{name}_{img.name}.png"

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context: bpy.types.Context) -> Set[str]:
        results = context.scene.baked_image_results
        idx = context.scene.baked_image_results_index
        if not (0 <= idx < len(results)):
            self.report({"ERROR"}, "No result selected")
            return {"CANCELLED"}

        res = results[idx]
        if not res.image:
            self.report({"ERROR"}, "No image to export")
            return {"CANCELLED"}

        img = res.image
        # H-06: Save original state to restore later
        old_path = img.filepath_raw
        old_fmt = img.file_format
        
        try:
            # Save the image to the selected filepath
            img.filepath_raw = self.filepath
            img.file_format = self._get_format_from_path(self.filepath)
            img.save()
            self.report({"INFO"}, f"Exported {img.name} to {self.filepath}")
        except Exception as e:
            self.report({"ERROR"}, f"Export failed: {e}")
            return {"CANCELLED"}
        finally:
            # Restore original metadata
            img.filepath_raw = old_path
            img.file_format = old_fmt

        return {"FINISHED"}

    def _get_format_from_path(self, path: str) -> str:
        import os
        ext = os.path.splitext(path)[1].lower()
        format_map = {
            ".png": "PNG",
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".exr": "OPEN_EXR",
            ".tif": "TIFF",
            ".tiff": "TIFF",
            ".bmp": "BMP",
            ".tga": "TARGA",
            ".hdr": "HDR",
        }
        return format_map.get(ext, "PNG")


class BAKETOOL_OT_ExportAllResults(bpy.types.Operator):
    """Export all baked results to disk."""

    bl_idname = "baketool.export_all_results"
    bl_label = "Export All"
    directory: props.StringProperty(subtype="DIR_PATH")

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> Set[str]:
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context: bpy.types.Context) -> Set[str]:
        results = context.scene.baked_image_results
        if not results:
            self.report({"WARNING"}, "No results to export")
            return {"CANCELLED"}

        export_dir = self.directory
        if not export_dir:
            # Fallback to scene path or temp
            export_dir = bpy.data.filepath
            if export_dir:
                export_dir = os.path.dirname(export_dir)
            else:
                import tempfile
                export_dir = tempfile.gettempdir()

        success_count = 0
        error_count = 0

        # C-01: Use Job result settings instead of hardcoded PNG
        from .constants import FORMAT_SETTINGS
        bj = context.scene.BakeJobs
        res_settings = bj.bake_result_settings.image_settings
        target_fmt = res_settings.external_save_format
        ext = FORMAT_SETTINGS.get(target_fmt, {}).get("extensions", [".png"])[0]

        for i, res in enumerate(results):
            if not res.image:
                continue
            img = res.image
            filename = f"{img.name}{ext}"
            filepath = os.path.join(export_dir, filename)
            
            # H-06: Save original state
            old_path = img.filepath_raw
            old_fmt = img.file_format
            
            try:
                img.filepath_raw = filepath
                img.file_format = target_fmt
                img.save()
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to export {img.name}: {e}")
                error_count += 1
            finally:
                # Restore original metadata
                img.filepath_raw = old_path
                img.file_format = old_fmt

        if success_count > 0:
            self.report({"INFO"}, f"Exported {success_count} images to {export_dir}")
        if error_count > 0:
            self.report({"WARNING"}, f"Failed to export {error_count} images")

        return {"FINISHED"} if success_count > 0 else {"CANCELLED"}


class BAKETOOL_OT_ManageObjects(bpy.types.Operator):
    """Manage objects in the bake list (add, remove, clear)."""

    bl_idname = "baketool.manage_objects"
    bl_label = "Manage Objects"

    action: props.StringProperty()

    def execute(self, context: bpy.types.Context) -> Set[str]:
        bj = context.scene.BakeJobs
        if not bj.jobs:
            return {"CANCELLED"}
        job = bj.jobs[bj.job_index]

        sel = [o for o in context.selected_objects if o.type == "MESH"]
        act = (
            context.active_object
            if (context.active_object and context.active_object.type == "MESH")
            else None
        )

        manage_objects_logic(job.setting, self.action, sel, act)
        return {"FINISHED"}


class BAKETOOL_OT_SaveSetting(bpy.types.Operator, ExportHelper):
    """Export current bake job settings to a JSON file."""

    bl_idname = "baketool.save_setting"
    bl_label = "Export Bake Nexus Settings"
    filename_ext = ".json"
    filter_glob: props.StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context: bpy.types.Context) -> Set[str]:
        bj = context.scene.BakeJobs
        if not bj.jobs:
            return {"CANCELLED"}
        job = bj.jobs[bj.job_index]

        data = preset_handler.PropertyIO().to_dict(job)
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            self.report({"INFO"}, f"Settings exported to {self.filepath}")
        except IOError as e:
            self.report({"ERROR"}, f"Export failed: {e}")
            return {"CANCELLED"}

        return {"FINISHED"}


class BAKETOOL_OT_LoadSetting(bpy.types.Operator, ImportHelper):
    """Import bake job settings from a JSON file."""

    bl_idname = "baketool.load_setting"
    bl_label = "Import Bake Nexus Settings"
    filename_ext = ".json"
    filter_glob: props.StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context: bpy.types.Context) -> Set[str]:
        if not hasattr(context.scene, "BakeJobs"):
            return {"CANCELLED"}

        bj = context.scene.BakeJobs
        if not bj.jobs:
            bj.jobs.add()
            bj.job_index = 0
        job = bj.jobs[bj.job_index]

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            preset_handler.PropertyIO().from_dict(job, data)
            self.report({"INFO"}, f"Settings imported from {self.filepath}")
        except (IOError, json.JSONDecodeError) as e:
            self.report({"ERROR"}, f"Import failed: {e}")
            return {"CANCELLED"}

        return {"FINISHED"}


class BAKETOOL_OT_GenericChannelOperator(bpy.types.Operator):
    """Generic operator for list operations (add, delete, move, clear)."""

    bl_idname = "baketool.generic_channel_op"
    bl_label = "Channel Op"

    action_type: props.EnumProperty(
        name="Action",
        items=[
            ("ADD", "Add", "Add a new item"),
            ("DELETE", "Delete", "Remove the selected item"),
            ("UP", "Up", "Move current item up"),
            ("DOWN", "Down", "Move current item down"),
            ("CLEAR", "Clear", "Remove all items"),
        ],
    )
    target: props.StringProperty()

    def execute(self, context: bpy.types.Context) -> Set[str]:
        success, msg = manage_channels_logic(
            self.target, self.action_type, context.scene.BakeJobs
        )
        if not success:
            self.report({"ERROR"}, msg)
            return {"CANCELLED"}
        return {"FINISHED"}


class BAKETOOL_OT_RefreshPresets(bpy.types.Operator):
    """Refresh the visual preset library list."""

    bl_idname = "baketool.refresh_presets"
    bl_label = "Refresh Presets"

    def execute(self, context: bpy.types.Context) -> Set[str]:
        # Reset the thumbnail manager and trigger redraw
        from .core import thumbnail_manager

        thumbnail_manager.clear_all_previews()
        for area in context.screen.areas:
            area.tag_redraw()
        return {"FINISHED"}


class BAKETOOL_OT_ClearCrashLog(bpy.types.Operator):
    """Clear the cached crash record from the current scene."""

    bl_idname = "baketool.clear_crash_log"
    bl_label = "Clear Crash Log"

    def execute(self, context: bpy.types.Context) -> Set[str]:
        scene = context.scene
        scene.baketool_has_crash_record = False
        scene.baketool_crash_data_cache = ""
        # Also delete state file if exists
        from .state_manager import BakeStateManager

        BakeStateManager().clear_state()
        return {"FINISHED"}
