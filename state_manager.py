"""Manages bake session state and crash recovery.

Provides a robust mechanism to persist the current state of a bake process
to a temporary file, enabling recovery and reporting after unexpected exits.
"""

import json
import os
import time
import bpy
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class BakeStateManager:
    """Manages bake session state for crash recovery.

    Writes session data to a JSON file in the system temp directory,
    allowing recovery from crashes or unexpected exits.

    Attributes:
        log_dir (Path): Directory where state logs are stored.
        log_file (Path): Path to the current session log file.
    """

    def __init__(self):
        """Initialize state manager with system temp paths."""
        self.log_dir = Path(bpy.app.tempdir)
        self.log_file = self.log_dir / "sbt_last_session.json"

    def start_session(self, total_steps: int, job_name: str) -> None:
        """Initialize a new bake session record.

        Args:
            total_steps: Total number of steps in the bake queue.
            job_name: Name of the job being processed.
        """
        data = {
            "status": "STARTED",
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "job_name": job_name,
            "total_steps": total_steps,
            "current_step": 0,
            "current_queue_idx": 0,
            "current_object": "",
            "current_channel": "",
            "last_error": "",
        }
        self._write(data)

    def update_step(
        self, step_idx: int, obj_name: str, channel_name: str, queue_idx: int = 0
    ) -> None:
        """Update the persistent record with current progress.

        Args:
            step_idx: Index of the current channel/pass.
            obj_name: Name of the object being baked.
            channel_name: Name of the active channel.
            queue_idx: Absolute index in the full execution queue.
        """
        data = self.read_log() or {}
        data.update(
            {
                "status": "RUNNING",
                "current_step": step_idx,
                "current_queue_idx": queue_idx,
                "current_object": obj_name,
                "current_channel": channel_name,
                "update_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        self._write(data)

    def reset_ui_state(self, context: bpy.types.Context, status: str = "Idle") -> None:
        """Reset scene progress and status properties to default values.

        Args:
            context: Blender context.
            status: Status string to display in the UI.
        """
        if not context or not hasattr(context, "scene"):
            return

        scene = context.scene
        scene.is_baking = False
        scene.bake_status = status
        scene.bake_progress = 0.0

    def finish_session(
        self, context: Optional[bpy.types.Context] = None, status: str = "Idle"
    ) -> None:
        """End the session and remove the crash record file.

        Args:
            context: Optional Blender context to trigger UI reset.
            status: Final status message for the UI.
        """
        if self.log_file.exists():
            try:
                os.remove(self.log_file)
            except (OSError, FileNotFoundError, PermissionError) as e:
                logger.debug(f"Could not remove log file {self.log_file}: {e}")

        if context:
            self.reset_ui_state(context, status)

    def clear_state(self) -> None:
        """Delete crash record file without touching scene UI state."""
        if self.log_file.exists():
            try:
                os.remove(self.log_file)
            except (OSError, FileNotFoundError, PermissionError) as e:
                logger.debug(f"Could not clear state file {self.log_file}: {e}")

    def log_error(self, error_msg: str) -> None:
        """Record an error state without removing the crash file.

        Args:
            error_msg: The error message to persist.
        """
        data = self.read_log()
        if data:
            data["status"] = "ERROR"
            data["last_error"] = str(error_msg)
            self._write(data)

    def _write(self, data: Dict[str, Any]) -> None:
        """Physically write data to disk with sync.

        Args:
            data: Dictionary of session state data.
        """
        try:
            if not self.log_dir.exists():
                self.log_dir.mkdir(parents=True, exist_ok=True)

            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except (OSError, AttributeError, NotImplementedError):
                    pass
        except (OSError, IOError) as e:
            logger.error(f"BakeNexus Log Error: {e}")

    def read_log(self) -> Optional[Dict[str, Any]]:
        """Read and parse the session log file.

        Returns:
            Dictionary of session data, or None if file missing or invalid.
        """
        if not self.log_file.exists():
            return None
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError, IOError):
            return None

    def has_crash_record(self) -> bool:
        """Check if an unfinished session record exists on disk.

        Returns:
            bool: True if log file exists.
        """
        return self.log_file.exists()
