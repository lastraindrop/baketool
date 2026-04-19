"""
BakeTool Public API
Exposes simplified entry points for external scripts and pipeline integration.
"""
import bpy
import logging
from .engine import JobPreparer, BakeStepRunner
from .common import ValidationResult
from .uv_manager import detect_object_udim_tile

logger = logging.getLogger(__name__)

def bake(objects, use_selection=True):
    """
    Main entry point for programmatic baking.
    
    Args:
        objects: List of objects to bake (if use_selection=False)
        use_selection: If True, uses current viewport selection instead of 'objects' arg
    
    Returns:
        bool: True if bake started successfully (modal)
    """
    if use_selection:
        objects = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    
    if not objects:
        logger.error("API Error: No objects provided for baking.")
        return False
        
    # CB-2: Rewrite to use engine logic directly instead of UI Operator
    # We use the currently active job setup in the scene as the template
    if not hasattr(bpy.context.scene, "BakeJobs"):
        logger.error("API Error: BakeTool properties not registered.")
        return False
        
    jobs_manager = bpy.context.scene.BakeJobs
    if not jobs_manager.jobs:
        # Create a default job for the API call
        jobs_manager.jobs.add()
        jobs_manager.jobs[0].name = "API_Auto_Job"
        # Reset channels to default for new job
        from .common import reset_channels_logic
        reset_channels_logic(jobs_manager.jobs[0].setting)
        
    job = jobs_manager.jobs[0]
    active_obj = bpy.context.active_object if (bpy.context.active_object and bpy.context.active_object.type == 'MESH') else None
    
    # Generate the execution queue
    queue = JobPreparer.prepare_quick_bake_queue(bpy.context, job, objects, active_obj)

    if not queue:
        logger.warning("API Warning: No bake steps generated for the given objects.")
        return False

    # Run the bake steps synchronously
    # Note: In UI this will block Blender, but for API usage (especially CLI/background)
    # this is often the expected behavior for programmatic control.
    runner = BakeStepRunner(bpy.context)
    for step in queue:
        success = runner.run(step)
        if not success:
            logger.error(f"API Error: Bake step failed for {step.channel_id}")
            return False

    return True

def get_udim_tiles(objects):
    """Returns a list of unique UDIM tiles used by the given objects."""
    tiles = set()
    for obj in objects:
        tiles.add(detect_object_udim_tile(obj))
    return sorted(list(tiles))

def validate_settings(job):
    """Programmatically validate a BakeJob's settings."""
    return JobPreparer.validate_job(job, bpy.context.scene)
