"""
Blender Version Compatibility Layer
Centralizes all version-specific API differences to improve maintainability.
Supports Blender 3.6 - 5.0+
"""
import bpy
import logging

logger = logging.getLogger(__name__)

# Version Detection
def is_blender_5():
    return bpy.app.version >= (5, 0, 0)

def is_blender_4():
    return bpy.app.version >= (4, 0, 0) and bpy.app.version < (5, 0, 0)

def is_blender_3():
    return bpy.app.version >= (3, 0, 0) and bpy.app.version < (4, 0, 0)

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
    # Mapping for different versions
    BAKE_MAPPING = {
        'EMIT': 'EMISSION',
        'DIFFUSE': 'DIFFUSE',
        'NORMAL': 'NORMALS' if (not is_blender_3() or is_blender_3()) else 'NORMAL'
    }
    target_bake_type = BAKE_MAPPING.get(bake_type, bake_type)

    try:
        # PRIORITY: Cycles-specific bake type property (Exists in 3.6 - 5.0+)
        has_cycles = hasattr(scene, "cycles")
        if has_cycles:
            # Force Cycles engine temporarily if needed to avoid "property not found" errors in B3.x
            orig_engine = scene.render.engine
            if orig_engine != 'CYCLES':
                try: scene.render.engine = 'CYCLES'
                except Exception: pass
                
            if hasattr(scene.cycles, "bake_type"):
                try:
                    scene.cycles.bake_type = bake_type # Cycles usually takes standard names
                    if bake_type not in {'NORMALS', 'DISPLACEMENT', 'VECTOR_DISPLACEMENT'}:
                        return True
                except Exception:
                    try: 
                        scene.cycles.bake_type = target_bake_type
                        return True
                    except Exception: pass
            
            # Restore engine if we didn't return (meaning we move to fallback)
            # Actually, standard practice in BT is to stay in CYCLES while setting up.
            pass
            
        bake_settings = get_bake_settings(scene)
        if bake_settings is None: return False

        # Attempt to set on BakeSettings struct
        for attr in ["type", "bake_type"]: # Try both
            if hasattr(bake_settings, attr):
                try:
                    setattr(bake_settings, attr, bake_type)
                    return True
                except (TypeError, ValueError):
                    try:
                        setattr(bake_settings, attr, target_bake_type)
                        return True
                    except (TypeError, ValueError):
                        pass
            
        # Last resort fallback for B3.3 and others
        if hasattr(scene.render, "bake_type"):
            try:
                scene.render.bake_type = bake_type
                return True
            except Exception:
                try:
                    scene.render.bake_type = target_bake_type
                    return True
                except Exception: pass
            
        logger.warning(f"Could not conclusively set bake type to {bake_type} on {bake_settings}")
        return False
    except Exception as e:
        logger.warning(f"Could not set bake type to {bake_type}: {e}")
        return False


def get_version_string():
    """Get a human-readable version string."""
    v = bpy.app.version
    return f"{v[0]}.{v[1]}.{v[2]}"
