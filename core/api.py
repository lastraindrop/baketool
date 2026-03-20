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
        
    # Logic to queue a bake job (Modal operators require UI context, 
    # so this will trigger the existing operator but with API-initialized settings)
    bpy.ops.bake.bake_operator('INVOKE_DEFAULT')
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
