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

# Session files carry the PID so concurrent Blender instances do not
# overwrite each other's crash records. Detection globs the shared prefix.
SESSION_FILE_GLOB = "sbt_last_session*.json"


class BakeStateManager:
    """Manages bake session state for crash recovery.

    Writes session data to a JSON file in the system temp directory,
    allowing recovery from crashes or unexpected exits.

    Attributes:
        log_dir (Path): Directory where state logs are stored.
        log_file (Path): Path to this instance's session log file.
    """

    def __init__(self):
        """Initialize state manager with system temp paths."""
        import os
        temp_dir = bpy.app.tempdir or os.environ.get("TEMP", "/tmp")
        self.log_dir = Path(temp_dir)
        self.log_file = self.log_dir / f"sbt_last_session_{os.getpid()}.json"
        self._cached_data: Optional[Dict[str, Any]] = None

    def _all_session_files(self):
        """Return all session files in the temp dir, newest first.

        Includes files written by other (possibly crashed) Blender
        instances so crash detection works across processes.
        """
        try:
            files = list(self.log_dir.glob(SESSION_FILE_GLOB))
        except OSError:
            return []
        def safe_mtime(path):
            try:
                return path.stat().st_mtime
            except OSError:
                return 0.0
        return sorted(files, key=safe_mtime, reverse=True)

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
        """End the session and remove this instance's crash record file.

        Other instances' files are intentionally preserved so a parallel
        session that crashes later can still be recovered.

        Args:
            context: Optional Blender context to trigger UI reset.
            status: Final status message for the UI.
        """
        self._cached_data = None
        self._remove_file(self.log_file)

        if context:
            self.reset_ui_state(context, status)

    def clear_state(self) -> None:
        """Delete all crash record files without touching scene UI state.

        Removes records from every Blender instance (including stale files
        left by crashed sessions) so the UI does not re-report old crashes.
        """
        self._cached_data = None
        for path in self._all_session_files():
            self._remove_file(path)

    @staticmethod
    def _remove_file(path: Path) -> None:
        """Best-effort removal of a single state file."""
        try:
            if path.exists():
                os.remove(path)
        except (OSError, FileNotFoundError, PermissionError) as e:
            logger.debug(f"Could not remove log file {path}: {e}")

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
        self._cached_data = data
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
        """Read and parse the most recent session log file.

        Falls back through files written by other instances so a fresh
        Blender process can recover a crashed session's record.

        Returns:
            Dictionary of session data, or None if no valid file exists.
        """
        if self._cached_data is not None:
            return self._cached_data

        for candidate in self._all_session_files():
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    self._cached_data = json.load(f)
                    return self._cached_data
            except (json.JSONDecodeError, OSError, IOError):
                continue
        return None

    def has_crash_record(self) -> bool:
        """Check if any unfinished session record exists on disk.

        Returns:
            bool: True if a session file (from any instance) exists.
        """
        return bool(self._all_session_files())
