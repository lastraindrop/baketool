"""Blender Version Compatibility Layer.

Centralizes all version-specific API differences to improve maintainability
and ensure robust operation across Blender 3.6 to 5.0+.
"""

import bpy
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

BAKE_MAPPING = {
    "EMIT": "EMISSION",
    "DIFFUSE": "DIFFUSE",
    "NORMAL": "NORMALS",  # Version-aware logic handled in set_bake_type
}


def get_bake_operator_type(bake_type: str) -> str:
    """Return the bake type enum expected by bpy.ops.object.bake."""
    return bake_type


def is_blender_5() -> bool:
    """Check if the current Blender version is 5.0 or newer.

    Returns:
        bool: True if Blender version >= 5.0.0.
    """
    return bpy.app.version >= (5, 0, 0)


def is_blender_4() -> bool:
    """Check if the current Blender version is in the 4.x series.

    Returns:
        bool: True if 4.0.0 <= Blender version < 5.0.0.
    """
    return (4, 0, 0) <= bpy.app.version < (5, 0, 0)


def is_blender_3() -> bool:
    """Check if the current Blender version is in the 3.x series.

    Returns:
        bool: True if 3.0.0 <= Blender version < 4.0.0.
    """
    return (3, 0, 0) <= bpy.app.version < (4, 0, 0)


def is_extension() -> bool:
    """Check if the addon is running as a Blender Extension.

    Extensions typically have a package name prefixed with 'bl_ext'.

    Returns:
        bool: True if running as an extension.
    """
    pkg = __package__.split(".")[0] if "." in __package__ else __package__
    return pkg.startswith("bl_ext")


def get_bake_settings(scene: bpy.types.Scene) -> Optional[Any]:
    """Get the bake settings object in a version-safe way.

    Blender 4.0+ moved/added bake settings into scene.render.bake.

    Args:
        scene: The target Blender scene.

    Returns:
        The bake settings object or None if not available.
    """
    if hasattr(scene.render, "bake"):
        return scene.render.bake
    return scene.render


def get_compositor_tree(scene: bpy.types.Scene) -> Optional[bpy.types.NodeTree]:
    """Retrieve the compositor node tree for a scene in a version-safe way.

    Blender 5.0 introduced compositing_node_group and use_nodes for the
    main compositor tree.

    Args:
        scene: The Blender scene to query.

    Returns:
        The compositor node tree if found or created, else None.
    """
    # 1. Blender 5.0+ Renamed Property
    if hasattr(scene, "compositing_node_group"):
        try:
            if hasattr(scene, "use_nodes") and not scene.use_nodes:
                scene.use_nodes = True

            tree = getattr(scene, "compositing_node_group", None)

            # Background Initialization Fix for B5.0
            if not tree and is_blender_5():
                try:
                    # C-01: Check for existing group first to prevent leaks/duplicates
                    tree_name = "BT_Compositor_Tree"
                    tree = bpy.data.node_groups.get(tree_name)
                    if not tree:
                        tree = bpy.data.node_groups.new(
                            tree_name, "CompositorNodeTree"
                        )
                    scene.compositing_node_group = tree
                except (AttributeError, RuntimeError, TypeError) as e:
                    logger.debug(f"B5.0: Failed to create CompositorNodeTree: {e}")

            if tree:
                return tree
        except (AttributeError, RuntimeError):
            pass

    # 2. Legacy / Common Fallback (3.x - 4.x)
    try:
        if hasattr(scene, "use_nodes"):
            if not scene.use_nodes:
                scene.use_nodes = True

            tree = getattr(scene, "node_tree", None)
            # Safe type check
            if tree and hasattr(tree, "type") and tree.type in {"COMPOSITING", "CompositorNodeTree"}:
                return tree

            if hasattr(scene, "node_tree") and scene.node_tree:
                return scene.node_tree
    except (AttributeError, RuntimeError) as e:
        logger.debug(f"Error accessing compositor tree: {e}")

    return None


def set_bake_type(scene: bpy.types.Scene, bake_type: str) -> bool:
    """Set the active bake pass type for the Cycles engine.

    Handles differences in naming and attribute location across versions.

    Args:
        scene: Blender scene.
        bake_type: Internal pass type string (e.g., 'EMIT', 'NORMAL').

    Returns:
        bool: True if the bake type was successfully applied.
    """
    # V1.0.0-p3: Unified 'NORMAL' for B4.2+ and B5.0. 
    # Only use 'NORMALS' as fallback if 'NORMAL' fails.
    target_bake_type = BAKE_MAPPING.get(bake_type, bake_type)
    
    try:
        # PRIORITY: Cycles-specific bake type property (Exists in 3.6 - 5.0+)
        if hasattr(scene, "cycles") and hasattr(scene.cycles, "bake_type"):
            try:
                # Try the direct bake_type first (e.g. 'NORMAL')
                scene.cycles.bake_type = bake_type
                return True
            except (AttributeError, TypeError, ValueError):
                try:
                    # Try the mapped target_bake_type (e.g. 'NORMALS')
                    scene.cycles.bake_type = target_bake_type
                    return True
                except (AttributeError, TypeError, ValueError):
                    pass

        bake_settings = get_bake_settings(scene)
        if bake_settings is None:
            return False

        # Attempt to set on BakeSettings struct
        for attr in ["type", "bake_type"]:
            if hasattr(bake_settings, attr):
                try:
                    setattr(bake_settings, attr, bake_type)
                    return True
                except (AttributeError, TypeError, ValueError):
                    try:
                        setattr(bake_settings, attr, target_bake_type)
                        return True
                    except (AttributeError, TypeError, ValueError):
                        pass
    except (AttributeError, RuntimeError) as e:
        logger.warning(f"Unexpected error setting bake type: {e}")
    return False



def get_version_string() -> str:
    """Get a human-readable Blender version string.

    Returns:
        str: Formatted version (e.g., '4.2.1').
    """
    v = bpy.app.version
    return f"{v[0]}.{v[1]}.{v[2]}"
