"""Preview collection management for the visual preset library."""
import bpy
import logging
from pathlib import Path

preview_collections = {}

_HAS_PREVIEWS = hasattr(bpy.utils, "previews")


def get_preview_collection(name="main"):
    """Get or create a preview collection."""
    global preview_collections
    if name not in preview_collections:
        if _HAS_PREVIEWS:
            pcoll = bpy.utils.previews.new()
        else:
            pcoll = _PreviewCollectionPlaceholder(name)
        preview_collections[name] = pcoll
    return preview_collections[name]


def clear_preview_collection(name="main"):
    """Clear a specific preview collection."""
    global preview_collections
    if name in preview_collections:
        if _HAS_PREVIEWS:
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

    if not _HAS_PREVIEWS:
        return

    for f in directory.glob("*.png"):
        try:
            pcoll.load(f.stem, str(f.resolve()), "IMAGE")
        except Exception as e:
            logger.warning(f"Failed to load preset icon {f.name}: {e}")


def get_icon_id(name):
    """Get preview icon ID for a preset name."""
    if not _HAS_PREVIEWS:
        return 0
    pcoll = get_preview_collection("presets")
    icon = pcoll.get(name)
    return icon.icon_id if icon else 0


def clear_all_previews():
    """Clear all preview collections."""
    global preview_collections
    if _HAS_PREVIEWS:
        for pcoll in preview_collections.values():
            bpy.utils.previews.remove(pcoll)
    preview_collections.clear()


class _PreviewCollectionPlaceholder:
    """Placeholder for Blender 4.2+ where bpy.utils.previews was removed."""

    def __init__(self, name):
        self.name = name

    def get(self, key, default=None):
        return default

    def load(self, *args, **kwargs):
        pass
