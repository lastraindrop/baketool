"""
Blender Version Compatibility Layer
Centralizes all version-specific API differences to improve maintainability.
Supports Blender 3.6 - 5.0+
"""
import bpy
import logging

logger = logging.getLogger(__name__)

# Version Detection
IS_BLENDER_5 = bpy.app.version >= (5, 0, 0)
IS_BLENDER_4 = bpy.app.version >= (4, 0, 0) and bpy.app.version < (5, 0, 0)
IS_BLENDER_3 = bpy.app.version >= (3, 0, 0) and bpy.app.version < (4, 0, 0)

def get_bake_settings(scene):
    """
    Get bake settings object in a version-safe way.
    
    Blender 4.0+ moved/added bake settings in scene.render.bake
    Returns: The bake settings object or None if not available
    """
    if hasattr(scene.render, "bake"):
        return scene.render.bake
    # Legacy: settings are directly on scene.render
    return scene.render


def set_bake_type(scene, bake_type):
    """
    Set bake type in a version-safe way.
    
    Args:
        scene: Blender scene
        bake_type: String like 'EMIT', 'COMBINED', 'NORMAL', etc.
    """
    try:
        # PRIORITY: Cycles-specific bake type property (Exists in 3.6 - 5.0+)
        # This is the most reliable path for Cycles bake passes.
        if scene.render.engine == 'CYCLES' and hasattr(scene, "cycles"):
            if hasattr(scene.cycles, "bake_type"):
                scene.cycles.bake_type = bake_type
                return True
            
        bake_settings = get_bake_settings(scene)
        if bake_settings is None:
            return False

        # Attempt to set on BakeSettings struct
        # B5.0: .type, Others: .bake_type
        # Note: We check .type FIRST because in B5.0, .bake_type might exist but be legacy
        if IS_BLENDER_5 and hasattr(bake_settings, "type"):
            bake_settings.type = bake_type
        elif hasattr(bake_settings, "bake_type"):
            bake_settings.bake_type = bake_type
        elif hasattr(bake_settings, "type"): # Fallback for non-B5 that still uses .type
            bake_settings.type = bake_type
        else:
            logger.warning(f"No bake type property found on {bake_settings}")
            return False
            
        return True
    except Exception as e:
        logger.warning(f"Could not set bake type to {bake_type}: {e}")
        return False


def get_version_string():
    """Get a human-readable version string."""
    v = bpy.app.version
    return f"{v[0]}.{v[1]}.{v[2]}"
