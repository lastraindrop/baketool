import bpy
import logging
from pathlib import Path
from contextlib import contextmanager
from ..constants import FORMAT_SETTINGS

logger = logging.getLogger(__name__)

@contextmanager
def robust_image_editor_context(context, image):
    """
    Safely finds or hijacks an area to function as an IMAGE_EDITOR context.
    """
    window = context.window
    if not window and context.window_manager.windows:
        window = context.window_manager.windows[0]
    screen = window.screen
    
    area = None
    if context.area and context.area.type != 'EMPTY': area = context.area
    
    if not area:
        for a in screen.areas:
            if a.type == 'IMAGE_EDITOR': area = a; break
        if not area:
            for a in screen.areas:
                if a.type == 'VIEW_3D': area = a; break
        if not area and screen.areas: area = screen.areas[0]
            
    if not area:
        yield False
        return

    old_type = area.type
    try:
        if old_type != 'IMAGE_EDITOR': area.type = 'IMAGE_EDITOR'
        area.spaces.active.image = image
        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
        
        with context.temp_override(window=window, area=area, region=region, screen=screen):
            yield True
            
    except Exception as e:
        logger.error(f"Context hijack failed: {e}")
        yield False
    finally:
        if area.type != old_type: area.type = old_type

def set_image(name, x, y, alpha=True, full=False, space='sRGB', ncol=False, basiccolor=(0,0,0,0), clear=True, 
              use_udim=False, udim_tiles=None, tile_resolutions=None):
    """Get or create an image with specified settings."""
    image = bpy.data.images.get(name)
    
    if image:
        is_tiled = (image.source == 'TILED')
        if is_tiled != use_udim:
            bpy.data.images.remove(image)
            image = None
    
    if not image:
        init_x, init_y = x, y
        if use_udim and tile_resolutions and 1001 in tile_resolutions:
            init_x, init_y = tile_resolutions[1001]
            
        image = bpy.data.images.new(name, width=init_x, height=init_y, alpha=alpha, float_buffer=full, tiled=use_udim)
    else:
        target_w, target_h = x, y
        if use_udim and tile_resolutions and 1001 in tile_resolutions:
            target_w, target_h = tile_resolutions[1001]
            
        if image.size[0] != target_w or image.size[1] != target_h: 
            image.scale(target_w, target_h)
            if image.source == 'GENERATED':
                image.generated_width = target_w; image.generated_height = target_h

    image.file_format = 'PNG' 
    image.use_fake_user = True
    
    if not full:
        try: image.colorspace_settings.name = space
        except: pass 
    
    if alpha: image.alpha_mode = 'STRAIGHT'
    
    if use_udim and image.source == 'TILED':
        target_tiles = set(udim_tiles) if udim_tiles else {1001}
        existing_tiles = {t.number for t in image.tiles}
        
        if 1001 in existing_tiles and 1001 in target_tiles:
            t_w, t_h = x, y
            if tile_resolutions and 1001 in tile_resolutions: t_w, t_h = tile_resolutions[1001]
            if image.size[0] != t_w or image.size[1] != t_h: image.scale(t_w, t_h)

        missing_tiles = target_tiles - existing_tiles
        if missing_tiles:
            with robust_image_editor_context(bpy.context, image) as valid:
                if valid:
                    for t_idx in missing_tiles:
                        t_w, t_h = x, y
                        if tile_resolutions and t_idx in tile_resolutions: t_w, t_h = tile_resolutions[t_idx]
                        try: 
                            bpy.ops.image.tile_add(
                                number=t_idx, count=1, label=str(t_idx), fill=True, 
                                width=t_w, height=t_h, float=full, alpha=alpha,
                                generated_type='BLANK', color=basiccolor
                            )
                        except Exception: pass
                else:
                    for t_idx in missing_tiles: image.tiles.new(tile_number=t_idx)

        extra_tiles = existing_tiles - target_tiles
        for t_idx in extra_tiles:
            tile_to_remove = next((t for t in image.tiles if t.number == t_idx), None)
            if tile_to_remove:
                try: image.tiles.remove(tile_to_remove)
                except: pass

    if clear: image.generated_color = basiccolor
    return image

def save_image(image, path='//', folder=False, folder_name='folder', file_format='PNG', motion=False, frame=0, reload=False, fillnum=4, save=True, separator="_", **kwargs):
    """Safe image saving wrapper."""
    if not save or not image: return None
    
    base = Path(bpy.path.abspath(path))
    if str(base) == '.': base = Path(bpy.data.filepath).parent 
    directory = base / folder_name if folder else base
    try: directory.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create directory '{directory}': {e}")
        return None
    
    info = FORMAT_SETTINGS.get(file_format, {})
    ext = info.get("extensions", ["." + file_format.lower()])[0]
    fname = f"{image.name}{separator}{str(frame).zfill(fillnum)}{ext}" if motion else f"{image.name}{ext}"
    
    if image.source == 'TILED' and "<UDIM>" not in fname:
        stem = Path(fname).stem
        fname = f"{stem}.<UDIM>{ext}"

    filepath = directory / fname
    abs_path = str(filepath.resolve())
    old_path = image.filepath_raw
    old_fmt = image.file_format
    
    try:
        image.filepath_raw = abs_path
        image.file_format = file_format
        image.save()
    except Exception as e:
        logger.error(f"Save failed: {e}")
        image.filepath_raw = old_path
        image.file_format = old_fmt
        return None
        
    if not motion and reload:
        try: 
            image.source = 'FILE'; image.reload()
        except: pass
        
    return abs_path
