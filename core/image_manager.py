"""Image creation, manipulation, and storage management for BakeNexus.

Handles the lifecycle of images used during baking, including creation of
standard and UDIM textures, memory-efficient clearing, and safe disk storage.
"""

import bpy
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, List, Dict, Tuple, Any
from ..constants import FORMAT_SETTINGS

logger = logging.getLogger(__name__)


def _resolve_color_space_name(
    image: bpy.types.Image, space: str
) -> str:
    """Map addon enum keys to Blender color-space identifiers."""
    if not space:
        return "sRGB"

    fallback_map = {
        "NONCOL": ("Non-Color",),
        "SRGB": ("sRGB",),
        "LINEAR": ("Linear Rec.709", "Linear"),
    }
    candidates = list(fallback_map.get(space, (space,)))
    if space not in candidates:
        candidates.append(space)

    try:
        enum_items = image.colorspace_settings.bl_rna.properties["name"].enum_items
        valid_names = {item.identifier for item in enum_items}
    except Exception:
        valid_names = set()

    for candidate in candidates:
        if not valid_names or candidate in valid_names:
            return candidate

    if space == "LINEAR":
        for name in valid_names:
            if name.startswith("Linear") and "CIE" not in name:
                return name

    return "sRGB"


@contextmanager
def robust_image_editor_context(context: bpy.types.Context, image: bpy.types.Image):
    """Safely finds or hijacks an area to function as an IMAGE_EDITOR context.

    Necessary for certain Blender operators (like UDIM tile management) that
    require an active Image Editor space.

    Args:
        context: Blender context.
        image: Image to display in the editor.

    Yields:
        bool: True if context switch was successful.
    """
    window = context.window
    if not window and context.window_manager.windows:
        window = context.window_manager.windows[0]

    if not window:
        yield False
        return

    screen = window.screen

    area = None
    if context.area and context.area.type != "EMPTY":
        area = context.area

    if not area:
        for a in screen.areas:
            if a.type == "IMAGE_EDITOR":
                area = a
                break
        if not area:
            for a in screen.areas:
                if a.type == "VIEW_3D":
                    area = a
                    break
        if not area and screen.areas:
            area = screen.areas[0]

    if not area:
        yield False
    else:
        old_type = area.type
        try:
            if old_type != "IMAGE_EDITOR":
                area.type = "IMAGE_EDITOR"
            area.spaces.active.image = image
            region = next((r for r in area.regions if r.type == "WINDOW"), None)

            with context.temp_override(
                window=window,
                area=area,
                region=region,
                screen=screen,
                space_data=area.spaces.active,
            ):
                yield True
        except (AttributeError, RuntimeError) as e:
            logger.error(f"Context switch failed: {e}")
            yield False
        finally:
            if area.type != old_type:
                area.type = old_type


def _needs_persistent_reference(setting: Any = None) -> bool:
    """Determine if image needs persistent reference (fake user).

    Temporary images should not use fake user to allow automatic cleanup.

    Args:
        setting: Configuration object.

    Returns:
        bool: True if image should persist.
    """
    if setting is None:
        return False
    if hasattr(setting, "apply_to_scene"):
        return setting.apply_to_scene
    if hasattr(setting, "use_external_save"):
        return setting.use_external_save and hasattr(setting, "external_save_path")
    return False


def set_image(
    name: str,
    x: int,
    y: int,
    alpha: bool = True,
    full: bool = False,
    space: str = "sRGB",
    basiccolor: Tuple[float, float, float, float] = (0, 0, 0, 0),
    clear: bool = True,
    use_udim: bool = False,
    udim_tiles: Optional[List[int]] = None,
    tile_resolutions: Optional[Dict[int, Tuple[int, int]]] = None,
    context: Optional[bpy.types.Context] = None,
    setting: Optional[Any] = None,
) -> bpy.types.Image:
    """Get or create an image with specified settings.

    Args:
        name: Image name.
        x: Width in pixels.
        y: Height in pixels.
        alpha: Use alpha channel.
        full: Use 32-bit float buffer.
        space: Color space name.
        basiccolor: Clear color as (r, g, b, a) tuple.
        clear: Whether to physically clear pixel data.
        use_udim: Use UDIM tiled images.
        udim_tiles: List of UDIM tile numbers.
        tile_resolutions: Dict mapping tile number to (width, height).
        context: Optional Blender context.
        setting: Optional settings object.

    Returns:
        bpy.types.Image: The created or retrieved image.
    """
    if context is None:
        context = bpy.context
    image = _get_or_create_image_base(
        name, x, y, alpha, full, use_udim, tile_resolutions
    )

    image.file_format = "PNG"

    if _needs_persistent_reference(setting):
        image.use_fake_user = True
    else:
        image.use_fake_user = False

    if not full:
        try:
            image.colorspace_settings.name = _resolve_color_space_name(image, space)
        except (AttributeError, RuntimeError):
            pass

    if alpha:
        image.alpha_mode = "STRAIGHT"

    if clear:
        _physical_clear_pixels(image, basiccolor)

    if use_udim and image.source == "TILED":
        _handle_udim_tiles(
            image,
            x,
            y,
            udim_tiles,
            tile_resolutions,
            full,
            alpha,
            basiccolor,
            context=context,
        )

    try:
        image.update()
    except RuntimeError:
        pass

    from . import compat

    if use_udim and compat.is_blender_3():
        _touch_udim_buffer_v3(image)

    return image


def _get_or_create_image_base(
    name: str,
    x: int,
    y: int,
    alpha: bool,
    full: bool,
    use_udim: bool,
    tile_resolutions: Optional[Dict[int, Tuple[int, int]]],
) -> bpy.types.Image:
    """Get or create base image datablock."""
    image = bpy.data.images.get(name)

    if image:
        if (image.source == "TILED") != use_udim:
            bpy.data.images.remove(image)
            image = None

    if not image:
        init_x, init_y = x, y
        if use_udim and tile_resolutions and 1001 in tile_resolutions:
            init_x, init_y = tile_resolutions[1001]

        image = bpy.data.images.new(
            name,
            width=init_x,
            height=init_y,
            alpha=alpha,
            float_buffer=full,
            tiled=use_udim,
        )
        if use_udim and hasattr(image, "tiles") and len(image.tiles) == 0:
            image.tiles.new(1001)
            image.update()
    else:
        target_w, target_h = x, y
        if use_udim and tile_resolutions and 1001 in tile_resolutions:
            target_w, target_h = tile_resolutions[1001]

        try:
            if image.size[0] != target_w or image.size[1] != target_h:
                image.scale(target_w, target_h)
                if image.source == "GENERATED":
                    image.generated_width = target_w
                    image.generated_height = target_h
        except (RuntimeError, AttributeError):
            pass
    return image


def _physical_clear_pixels(
    image: bpy.types.Image, basiccolor: Tuple[float, float, float, float]
) -> None:
    """Clear image pixels with minimal memory usage.

    Uses NumPy broadcast assignment to avoid creating large temporary arrays.
    """
    image.generated_color = basiccolor
    if image.source != "TILED":
        import numpy as np

        try:
            num_pixels = image.size[0] * image.size[1]
            arr = np.empty((num_pixels, 4), dtype=np.float32)
            arr[:] = basiccolor
            image.pixels.foreach_set(arr.ravel())
        except (AttributeError, ValueError, MemoryError):
            pass


def _handle_udim_tiles(
    image: bpy.types.Image,
    x: int,
    y: int,
    udim_tiles: Optional[List[int]],
    tile_resolutions: Optional[Dict[int, Tuple[int, int]]],
    full: bool,
    alpha: bool,
    basiccolor: Tuple[float, float, float, float],
    context: Optional[bpy.types.Context] = None,
) -> None:
    """Manage UDIM tile creation and layout."""
    target_tiles = set(udim_tiles) if udim_tiles else {1001}
    existing_tiles = {t.number for t in image.tiles}

    if 1001 in existing_tiles and 1001 in target_tiles:
        t_w, t_h = x, y
        if tile_resolutions and 1001 in tile_resolutions:
            t_w, t_h = tile_resolutions[1001]
        try:
            if image.size[0] != t_w or image.size[1] != t_h:
                image.scale(t_w, t_h)
        except (RuntimeError, AttributeError):
            pass

    missing_tiles = target_tiles - existing_tiles
    if missing_tiles:
        if context is None:
            context = bpy.context
        with robust_image_editor_context(context, image) as valid:
            for t_idx in missing_tiles:
                t_w, t_h = x, y
                if tile_resolutions and t_idx in tile_resolutions:
                    t_w, t_h = tile_resolutions[t_idx]

                op_success = False
                if valid:
                    try:
                        bpy.ops.image.tile_add(
                            number=t_idx,
                            count=1,
                            label=str(t_idx),
                            fill=True,
                            width=t_w,
                            height=t_h,
                            float=full,
                            alpha=alpha,
                            generated_type="BLANK",
                            color=basiccolor,
                        )
                        op_success = True
                    except (RuntimeError, AttributeError):
                        pass

                if not op_success:
                    try:
                        image.tiles.new(tile_number=t_idx)
                        image.generated_color = basiccolor
                        image.update()
                    except (RuntimeError, AttributeError) as e:
                        logger.error(f"Failed to add UDIM tile {t_idx}: {e}")

    extra_tiles = existing_tiles - target_tiles
    for t_idx in extra_tiles:
        tile_to_remove = next((t for t in image.tiles if t.number == t_idx), None)
        if tile_to_remove:
            try:
                image.tiles.remove(tile_to_remove)
            except (KeyError, AttributeError):
                pass


def _touch_udim_buffer_v3(image: bpy.types.Image) -> bpy.types.Image:
    """Initialize UDIM buffer for Blender 3.x compatibility."""
    try:
        import os, tempfile

        if not image.filepath:
            tmp_dir = tempfile.gettempdir()
            image.filepath_raw = os.path.join(tmp_dir, f"{image.name}.<UDIM>.png")
        
        is_packed = getattr(image, "is_packed", False)
        if hasattr(image, "packed_files") and not is_packed:
            is_packed = len(image.packed_files) > 0

        if not is_packed:
            try:
                image.pack()
            except (RuntimeError, AttributeError):
                pass
        image.update()
    except (IOError, OSError, RuntimeError) as e:
        logger.debug(f"3.3 UDIM buffer touch failed: {e}")

    return image


def save_image(
    image: bpy.types.Image,
    path: str = "//",
    folder: bool = False,
    folder_name: str = "folder",
    file_format: str = "PNG",
    motion: bool = False,
    frame: int = 0,
    reload: bool = False,
    fillnum: int = 4,
    save: bool = True,
    separator: str = "_",
    color_depth: str = "8",
    color_mode: str = "RGBA",
    quality: int = 90,
    exr_code: str = "ZIP",
    tiff_codec: str = "DEFLATE",
) -> Optional[str]:
    """Save image to disk with automatic directory creation.

    Args:
        image: Blender image to save.
        path: Base directory path.
        folder: Whether to create a subfolder.
        folder_name: Subfolder name.
        file_format: Output format.
        motion: If animation frame.
        frame: Frame index.
        reload: Reload image after save.
        fillnum: Frame padding digits.
        save: Actually perform save.
        separator: Animation separator string.
        color_depth: Bit depth ('8', '10', '12', '16', '32').
        color_mode: Color mode ('BW', 'RGB', 'RGBA').
        quality: Compression quality (0-100).
        exr_code: OpenEXR compression codec.
        tiff_codec: TIFF compression codec.

    Returns:
        Optional[str]: Absolute path to saved file or None if failed.
    """
    if not image or not save:
        return None

    directory = Path(bpy.path.abspath(path))
    if folder:
        directory = directory / folder_name

    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Could not create directory {directory}: {e}")
        return None

    ext = ".png"
    from ..constants import FORMAT_SETTINGS
    if file_format in FORMAT_SETTINGS:
        ext = FORMAT_SETTINGS[file_format]["extensions"][0]

    fname = (
        f"{image.name}{separator}{str(frame).zfill(fillnum)}{ext}"
        if motion
        else f"{image.name}{ext}"
    )

    if image.source == "TILED" and "<UDIM>" not in fname:
        stem = Path(fname).stem
        fname = f"{stem}.<UDIM>{ext}"

    filepath = directory / fname
    abs_path = str(filepath.resolve())
    
    # H-05: Set format settings via scene render settings
    render = bpy.context.scene.render
    s = render.image_settings
    
    old_fmt = s.file_format
    old_depth = s.color_depth
    old_mode = s.color_mode
    old_quality = s.quality
    old_exr = s.exr_codec
    old_tiff = s.tiff_codec
    
    try:
        s.file_format = file_format
        s.color_depth = color_depth
        s.color_mode = color_mode
        s.quality = quality
        s.exr_codec = exr_code
        s.tiff_codec = tiff_codec
        
        # We also set it on image for consistency, though image.save() 
        # is heavily dependent on scene settings for the details.
        image.filepath_raw = abs_path
        image.file_format = file_format
        image.save()
    except (OSError, RuntimeError, AttributeError) as e:
        logger.error(f"Save failed: {e}")
        return None
    finally:
        # Restore original scene settings
        s.file_format = old_fmt
        s.color_depth = old_depth
        s.color_mode = old_mode
        s.quality = old_quality
        s.exr_codec = old_exr
        s.tiff_codec = old_tiff


    if not motion and reload:
        try:
            image.source = "FILE"
            image.reload()
        except (RuntimeError, AttributeError):
            pass

    return abs_path
