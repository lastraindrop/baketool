"""
BakeNexus Public API

This module provides a stable, minimal public interface for external
scripts and other add-ons to interact with BakeNexus programmatically.
"""
import bpy
import logging
from typing import Any, Optional, List
from .engine import JobPreparer, BakeStepRunner
from .uv_manager import detect_object_udim_tile

logger = logging.getLogger(__name__)

def bake(
    objects: Optional[List[bpy.types.Object]] = None,
    use_selection: bool = True,
    context: Optional[bpy.types.Context] = None,
) -> bool:
    """
    Main entry point for programmatic baking.

    Args:
        objects: List of objects to bake (if use_selection=False).
        use_selection: If True, uses current viewport selection.
        context: Optional Blender context (uses bpy.context if None).

    Returns:
        bool: True if bake started successfully.
    """
    ctx = context if context is not None else bpy.context
    if use_selection:
        objects = [o for o in ctx.selected_objects if o.type == 'MESH']

    if not objects:
        logger.error("API Error: No objects provided for baking.")
        return False

    if not hasattr(ctx.scene, "BakeJobs"):
        logger.error("API Error: BakeNexus properties not registered.")
        return False

    jobs_manager = ctx.scene.BakeJobs
    if not jobs_manager.jobs:
        jobs_manager.jobs.add()
        jobs_manager.jobs[0].name = "API_Auto_Job"
        from .common import reset_channels_logic
        reset_channels_logic(jobs_manager.jobs[0].setting)

    job = jobs_manager.jobs[0]
    active_obj = (
        ctx.active_object
        if (ctx.active_object and ctx.active_object.type == 'MESH')
        else None
    )

    queue = JobPreparer.prepare_quick_bake_queue(ctx, job, objects, active_obj)
    if not queue:
        logger.warning("API Warning: No bake steps generated for the given objects.")
        return False

    runner = BakeStepRunner(ctx)
    for step in queue:
        results = runner.run(step)
        if not results:
            channel_name = step.channels[0] if step.channels else "unknown"
            logger.error(f"API Error: Bake step failed for {channel_name}")
            return False

    return True


def get_udim_tiles(objects: List[bpy.types.Object]) -> List[int]:
    """Returns a list of unique UDIM tiles used by the given objects."""
    tiles = set()
    for obj in objects:
        tiles.add(detect_object_udim_tile(obj))
    return sorted(list(tiles))

def validate_settings(
    job: Any, context: Optional[bpy.types.Context] = None
) -> Any:
    """Programmatically validate a BakeJob's settings."""
    from .common import ValidationResult
    ctx = context if context is not None else bpy.context
    return JobPreparer.validate_job(job, ctx.scene, ctx.view_layer)
