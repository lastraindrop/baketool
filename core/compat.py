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
        if hasattr(bake_settings, "type"):
            bake_settings.type = bake_type
        elif hasattr(bake_settings, "bake_type"):
            bake_settings.bake_type = bake_type
        else:
            logger.warning(f"No bake type property found on {bake_settings}")
            return False
            
        return True
    except Exception as e:
        logger.warning(f"Could not set bake type to {bake_type}: {e}")
        return False


def set_bake_margin(scene, margin):
    """
    DEPRECATED: Not directly called; margin is passed via bpy.ops.object.bake(margin=...)
    Set bake margin in a version-safe way.
    """
    bake_settings = get_bake_settings(scene)
    if bake_settings is None:
        return False
        
    try:
        bake_settings.margin = margin
        return True
    except Exception as e:
        logger.debug(f"Could not set margin: {e}")
        return False


def set_bake_clear(scene, clear):
    """
    DEPRECATED: Not directly called; clear is passed via bpy.ops.object.bake(use_clear=...)
    Set bake clear flag in a version-safe way.
    """
    bake_settings = get_bake_settings(scene)
    if bake_settings is None:
        return False
        
    try:
        if IS_BLENDER_5:
            bake_settings.use_clear = clear
        else:
            bake_settings.use_bake_clear = clear
        return True
    except Exception as e:
        logger.debug(f"Could not set clear: {e}")
        return False


def set_bake_target(scene, target='IMAGE_TEXTURES'):
    """
    DEPRECATED: Not directly called; target is passed via bpy.ops.object.bake(target=...)
    Set bake target in a version-safe way.
    """
    bake_settings = get_bake_settings(scene)
    if bake_settings is None:
        return False
        
    try:
        bake_settings.target = target
        return True
    except Exception as e:
        logger.debug(f"Could not set target: {e}")
        return False


def disable_multires_bake(scene):
    """
    DEPRECATED: Not directly called
    Disable multires baking in a version-safe way.
    """
    bake_settings = get_bake_settings(scene)
    if bake_settings is None:
        return False
        
    try:
        if hasattr(bake_settings, "use_multires"):
            bake_settings.use_multires = False
        elif hasattr(scene.render, "use_bake_multires"):
            scene.render.use_bake_multires = False
        return True
    except Exception as e:
        logger.debug(f"Could not disable multires: {e}")
        return False


def configure_bake_settings(scene, bake_type, margin, use_clear, target='IMAGE_TEXTURES'):
    """
    Configure all bake settings at once in a version-safe way.
    
    Args:
        scene: Blender scene
        bake_type: Bake pass type
        margin: Margin in pixels
        use_clear: Whether to clear image before baking
        target: Bake target (usually 'IMAGE_TEXTURES')
    
    Returns:
        bool: True if all settings were applied successfully
    """
    success = True
    success &= disable_multires_bake(scene)
    success &= set_bake_type(scene, bake_type)
    success &= set_bake_margin(scene, margin)
    success &= set_bake_clear(scene, use_clear)
    success &= set_bake_target(scene, target)
    return success


def get_version_string():
    """Get a human-readable version string."""
    v = bpy.app.version
    return f"{v[0]}.{v[1]}.{v[2]}"
