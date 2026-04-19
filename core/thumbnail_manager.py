import bpy
import bpy.utils.previews
import os
from pathlib import Path

preview_collections = {}


def get_preview_collection(name="main"):
    """Get or create a preview collection."""
    global preview_collections
    if name not in preview_collections:
        pcoll = bpy.utils.previews.new()
        preview_collections[name] = pcoll
    return preview_collections[name]


def clear_preview_collection(name="main"):
    """Clear a specific preview collection."""
    global preview_collections
    if name in preview_collections:
        bpy.utils.previews.remove(preview_collections[name])
        del preview_collections[name]


def load_preset_thumbnails(directory):
    """Load preset thumbnails from a directory."""
    import logging

    logger = logging.getLogger(__name__)
    directory = Path(directory)

    if not directory.exists() or not directory.is_dir():
        logger.warning(f"Preset directory does not exist: {directory}")
        return

    pcoll = get_preview_collection("presets")

    for f in directory.glob("*.png"):
        try:
            pcoll.load(f.stem, str(f.resolve()), "IMAGE")
        except Exception as e:
            logger.warning(f"Failed to load preset icon {f.name}: {e}")


def get_icon_id(name):
    """Get preview icon ID for a preset name."""
    pcoll = get_preview_collection("presets")
    return pcoll.get(name).icon_id if pcoll.get(name) else 0


def clear_all_previews():
    """Clear all preview collections."""
    global preview_collections
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()