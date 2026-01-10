import bpy
import bmesh
import logging
import random
import colorsys
import numpy as np
from pathlib import Path
from contextlib import contextmanager
from math import floor, ceil
from .constants import FORMAT_SETTINGS, BSDF_COMPATIBILITY_MAP, SOCKET_DEFAULT_TYPE, CHANNEL_DEFINITIONS

logger = logging.getLogger(__name__)

# --- General Helpers ---

def get_safe_base_name(setting, obj, mat=None, is_batch=False):
    """Centralized naming logic for baking and exporting."""
    mode = setting.bake_mode
    m = setting.name_setting
    base = "Bake"
    
    if m == 'CUSTOM':
        base = setting.custom_name
        if is_batch:
            suffix = f"_{obj.name}"
            if mode == 'SPLIT_MATERIAL' and mat:
                suffix += f"_{mat.name}"
            base += suffix
    elif m == 'OBJECT': 
        base = obj.name
    elif m == 'MAT': 
        base = mat.name if mat else "NoMat"
        if is_batch and mode == 'SPLIT_MATERIAL':
            base = f"{obj.name}_{base}"
    elif m == 'OBJ_MAT': 
        base = f"{obj.name}_{mat.name if mat else 'NoMat'}"
        
    return bpy.path.clean_name(base)

def check_objects_uv(objects):
    """Return a list of object names that are missing UV layers."""
    return [obj.name for obj in objects if obj.type == 'MESH' and not obj.data.uv_layers]

def reset_channels_logic(setting):
    """
    Reset and repopulate channels based on the current bake_type and enabled map toggles.
    Directly modifies the collection property. Preserves existing user settings where possible.
    """
    defs = []
    b_type = setting.bake_type
    
    # 1. Collect target definitions
    key = ('BSDF_4' if bpy.app.version >= (4, 0, 0) else 'BSDF_3') if b_type == 'BSDF' else b_type
    defs.extend(CHANNEL_DEFINITIONS.get(key, []))
    
    if setting.use_light_map: defs.extend(CHANNEL_DEFINITIONS.get('LIGHT', []))
    if setting.use_mesh_map: defs.extend(CHANNEL_DEFINITIONS.get('MESH', []))
    if setting.use_extension_map: defs.extend(CHANNEL_DEFINITIONS.get('EXTENSION', []))
    
    target_ids = {d['id']: d for d in defs}
    
    # 2. Sync existing channels
    # Remove channels no longer in the definitions
    for i in range(len(setting.channels)-1, -1, -1):
        if setting.channels[i].id not in target_ids:
            setting.channels.remove(i)
            
    # 3. Add or update channels
    existing = {c.id: c for c in setting.channels}
    
    for d in defs:
        d_id = d['id']
        if d_id not in existing:
            new_chan = setting.channels.add()
            new_chan.id = d_id
            new_chan.name = d['name']
            # Apply defaults only for new channels
            defaults = d.get('defaults', {})
            for k, v in defaults.items():
                if hasattr(new_chan, k): setattr(new_chan, k, v)
        else:
            # Optionally update name if definition changed
            existing[d_id].name = d['name']

@contextmanager
def safe_context_override(context, active_object=None, selected_objects=None):
    """
    Safe context override using context.temp_override (Blender 3.2+).
    Directly overrides context members without modifying scene selection state.
    """
    kw = {}
    if active_object:
        kw['active_object'] = active_object
        # Explicitly set 'object' as well, as some operators rely on context.object
        kw['object'] = active_object
    if selected_objects:
        kw['selected_objects'] = selected_objects
        kw['selected_editable_objects'] = selected_objects
    
    with context.temp_override(**kw):
        yield

class SceneSettingsContext:
    """
    Context manager to temporarily modify scene/render settings and restore them afterwards.
    """
    def __init__(self, category, settings):
        self.category = category
        self.settings = settings
        self.original = {}
        
        # Mapping for properties that have different names in UI vs API
        self.attr_map = {
            'scene': {
                'res_x': 'resolution_x', 
                'res_y': 'resolution_y',
                'res_pct': 'resolution_percentage'
            }
        }

    def _get_target(self):
        scene = bpy.context.scene
        if self.category == 'scene': return scene.render
        if self.category == 'cycles': return scene.cycles
        if self.category == 'image': return scene.render.image_settings
        if self.category == 'cm': return scene.view_settings
        return None

    def __enter__(self):
        target = self._get_target()
        if not target or not self.settings: return self
        
        # Save original values and apply new ones
        mapping = self.attr_map.get(self.category, {})
        
        for k, v in self.settings.items():
            real_key = mapping.get(k, k)
            if hasattr(target, real_key):
                # Save original
                self.original[real_key] = getattr(target, real_key)
                # Apply new
                if v is not None:
                    try: setattr(target, real_key, v)
                    except Exception as e:
                        logger.warning(f"Failed to set {self.category}.{real_key}: {e}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        target = self._get_target()
        if not target: return
        
        # Restore original values
        for k, v in self.original.items():
            try: setattr(target, k, v)
            except: pass

# --- UV & UDIM Layout Manager ---

def detect_object_udim_tile(obj):
    """
    Analyzes the object's active UV layer using NumPy to find its dominant UDIM tile.
    Returns: (int) Tile Index (e.g., 1001, 1002). Defaults to 1001 if empty or error.
    """
    if obj.type != 'MESH' or not obj.data.uv_layers: return 1001
    
    try:
        uv_layer = obj.data.uv_layers.active
        n_loops = len(obj.data.loops)
        if n_loops == 0: return 1001
        
        # Fast extraction
        uvs = np.zeros(n_loops * 2, dtype=np.float32)
        uv_layer.data.foreach_get("uv", uvs)
        uvs = uvs.reshape(-1, 2)
        
        # Determine tile for each vertex
        u_indices = np.floor(uvs[:, 0]).astype(int)
        v_indices = np.floor(uvs[:, 1]).astype(int)
        
        # Clamp and filter valid UDIM range (1001-1099, usually 10x10)
        valid = (u_indices >= 0) & (u_indices < 10) & (v_indices >= 0) & (v_indices < 10)
        if not np.any(valid): return 1001
        
        tiles = 1001 + u_indices[valid] + (v_indices[valid] * 10)
        
        # Majority vote: which tile appears most often
        counts = np.bincount(tiles)
        return int(np.argmax(counts))
    except Exception as e:
        logger.warning(f"UV Detect Failed for {obj.name}: {e}")
        return 1001

class UDIMPacker:
    """Helper to calculate new UDIM layouts."""
    @staticmethod
    def calculate_repack(objects):
        """
        Returns a mapping {obj: target_tile_index}
        Logic:
        1. Keep objects that are already in valid non-1001 tiles.
        2. Move objects that are in 1001 (or overlapping) to new free tiles.
        """
        assignments = {}
        used_tiles = set()
        pending_objects = []
        
        # 1. Analysis Phase
        for obj in objects:
            current_tile = detect_object_udim_tile(obj)
            
            # If strictly 1001, we treat it as "Pending Assignment" (standard 0-1 UVs)
            # If > 1001, we treat it as "Intentionally Placed"
            if current_tile > 1001:
                if current_tile in used_tiles:
                    # Conflict! Two objects manually placed in the same high tile.
                    # Strategy: Keep one, move other? Or Keep both (assuming user knows)?
                    # For safety, we keep both in Custom/Detect, but in Repack we might warn.
                    # Here we assume user intention -> Keep.
                    pass
                assignments[obj] = current_tile
                used_tiles.add(current_tile)
            else:
                pending_objects.append(obj)
        
        # 2. Allocation Phase
        # Sort pending objects by name to ensure deterministic result
        pending_objects.sort(key=lambda o: o.name)
        
        next_tile = 1001
        for obj in pending_objects:
            # Find next free tile
            while next_tile in used_tiles:
                next_tile += 1
            
            assignments[obj] = next_tile
            used_tiles.add(next_tile)
            
        return assignments

class UVLayoutManager:
    """
    Manages UV layers for baking, including:
    1. Creating temporary UV layers to protect original data.
    2. Generating Smart UVs.
    3. Repacking/Distributing UVs into UDIM tiles (0-1 -> 1001, 1002...)
    """
    def __init__(self, objects, settings):
        self.objects = [o for o in objects if o.type == 'MESH']
        self.settings = settings
        self.original_states = {} # {obj_name: {active_idx, render_idx}}
        self.temp_layer_name = "BT_Bake_Temp_UV"
        self.created_layers = []

    def __enter__(self):
        self._record_and_setup_layers()
        self._process_layout()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._restore_state()

    def _record_and_setup_layers(self):
        """Record current state and create temporary baking UV layer."""
        for obj in self.objects:
            # Record state
            self.original_states[obj.name] = {
                'active': obj.data.uv_layers.active_index,
                'render': next((i for i, l in enumerate(obj.data.uv_layers) if l.active_render), 0)
            }
            
            # Create Temp Layer (Copy from Active or New)
            # If using Auto Smart UV, we might start fresh, otherwise copy active.
            src_uv = obj.data.uv_layers.active
            if src_uv:
                new_uv = obj.data.uv_layers.new(name=self.temp_layer_name)
                # Copy data from source
                if new_uv: # Blender automatically copies data from active when creating new
                    new_uv.active = True
                    new_uv.active_render = True
                    self.created_layers.append((obj, new_uv))
            else:
                # No UV, create one
                new_uv = obj.data.uv_layers.new(name=self.temp_layer_name)
                new_uv.active = True
                new_uv.active_render = True
                self.created_layers.append((obj, new_uv))

    def _process_layout(self):
        """
        Execute UV Layout Logic.
        Pipeline: [Smart UV Gen (Optional)] -> [UDIM Offset (Optional)]
        """
        s = self.settings
        
        # Step 1: UV Generation (Smart UV)
        # If enabled, this resets all UVs to the 0-1 (1001) space.
        if s.use_auto_uv:
            self._apply_smart_uv()
        
        # Step 2: UDIM Distribution
        if s.bake_mode == 'UDIM':
            if s.udim_mode == 'CUSTOM':
                self._distribute_udim_custom()
            elif s.udim_mode == 'REPACK':
                self._distribute_udim_repack()
            # If DETECT: Do nothing. Trust existing layout.

    def _distribute_udim_repack(self):
        """Auto-assign 1001 objects to new tiles."""
        assignments = UDIMPacker.calculate_repack(self.objects)
        self._apply_assignments(assignments)

    def _distribute_udim_custom(self):
        """Moves UVs based on the per-object 'udim_tile' setting in BakeObject list."""
        s = self.settings
        assignments = {}
        for bo in s.bake_objects:
            if bo.bakeobject and bo.bakeobject in self.objects:
                assignments[bo.bakeobject] = bo.udim_tile
        
        self._apply_assignments(assignments)

    def _apply_assignments(self, assignments):
        """
        Optimized UV mover using NumPy/foreach_set.
        assignments: dict {obj: target_tile_int}
        """
        for obj, target_tile in assignments.items():
            current_tile = detect_object_udim_tile(obj)
            if current_tile == target_tile: continue
            
            # Calculate integer offset
            # Target (e.g. 1012) -> u=1, v=1
            # Current (e.g. 1001) -> u=0, v=0
            # Offset = (1, 1)
            
            t_u = (target_tile - 1001) % 10
            t_v = (target_tile - 1001) // 10
            
            c_u = (current_tile - 1001) % 10
            c_v = (current_tile - 1001) // 10
            
            off_u = t_u - c_u
            off_v = t_v - c_v
            
            if off_u == 0 and off_v == 0: continue
            
            # Apply offset
            uv_layer = obj.data.uv_layers.active
            if not uv_layer: continue
            
            count = len(uv_layer.data)
            uvs = np.zeros(count * 2, dtype=np.float32)
            uv_layer.data.foreach_get("uv", uvs)
            
            # Reshape for easy addition: [ [u,v], [u,v] ... ]
            uvs_2d = uvs.reshape(-1, 2)
            uvs_2d[:, 0] += off_u
            uvs_2d[:, 1] += off_v
            
            uv_layer.data.foreach_set("uv", uvs_2d.flatten())

    def _apply_smart_uv(self):
        # Select all objects
        ctx_override = self._get_context_override()
        with ctx_override:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            
            bpy.ops.uv.smart_project(
                angle_limit=self.settings.auto_uv_angle,
                island_margin=self.settings.auto_uv_margin,
                area_weight=0.0
            )
            bpy.ops.object.mode_set(mode='OBJECT')

    def _get_context_override(self):
        """Helper to create context override for operators."""
        # Ensure we are in object mode first
        if bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
            
        bpy.ops.object.select_all(action='DESELECT')
        for o in self.objects: o.select_set(True)
        bpy.context.view_layer.objects.active = self.objects[0]
        
        return safe_context_override(bpy.context, self.objects[0], self.objects)
    
    def _restore_state(self):
        """Restore original UV indices and remove temporary layers."""
        # 1. Remove the temporary layers we created
        # We iterate in reverse to avoid index shifting issues if we were removing by index,
        # but here we remove by reference/name, which is safer.
        for obj, layer in self.created_layers:
            try:
                # Validate object still exists and layer is still attached
                if obj and layer and layer.name in obj.data.uv_layers:
                    obj.data.uv_layers.remove(layer)
            except Exception as e:
                logger.warning(f"Failed to remove temp UV for {obj.name}: {e}")

        # 2. Restore original active/render indices
        for obj_name, state in self.original_states.items():
            obj = bpy.data.objects.get(obj_name)
            if not obj or obj.type != 'MESH': continue
            
            try:
                if state['active'] < len(obj.data.uv_layers):
                    obj.data.uv_layers.active_index = state['active']
                
                # Restore render active state
                render_idx = state['render']
                if render_idx < len(obj.data.uv_layers):
                    obj.data.uv_layers[render_idx].active_render = True
            except Exception as e:
                logger.warning(f"Failed to restore UV state for {obj_name}: {e}")

# --- UDIM System Utilities ---

def get_active_uv_udim_tiles(objects):
    """
    Scans the active UV layers of given objects and returns a set of used UDIM indices.
    """
    tiles = set()
    for obj in objects:
        tile = detect_object_udim_tile(obj)
        tiles.add(tile)
    
    if not tiles: tiles.add(1001)
    return sorted(list(tiles))

# --- Image & IO Helpers ---

@contextmanager
def robust_image_editor_context(context, image):
    """
    Safely finds or hijacks an area to function as an IMAGE_EDITOR context.
    Crucial for running `bpy.ops.image` operators inside a Modal Timer where `context.area` might be None.
    """
    # 1. Find a valid Window and Screen
    window = context.window
    if not window and context.window_manager.windows:
        window = context.window_manager.windows[0]
    screen = window.screen
    
    # 2. Find a valid Area
    # Priority: Existing Image Editor -> View 3D -> Any valid area
    area = None
    
    # Check if current context area is valid
    if context.area and context.area.type != 'EMPTY':
        area = context.area
    
    # If not, search the screen
    if not area:
        for a in screen.areas:
            if a.type == 'IMAGE_EDITOR':
                area = a
                break
        if not area:
            for a in screen.areas:
                if a.type == 'VIEW_3D':
                    area = a
                    break
        if not area and screen.areas:
            area = screen.areas[0]
            
    if not area:
        logger.error("Could not find any valid area for Image Editor context.")
        yield False
        return

    # 3. Hijack the area
    old_type = area.type
    try:
        if old_type != 'IMAGE_EDITOR':
            area.type = 'IMAGE_EDITOR'
        
        # Essential: Set the active image so the operator knows what to modify
        area.spaces.active.image = image
        
        # Find the region (needed for some ops)
        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
        
        # 4. Yield the override context
        with context.temp_override(window=window, area=area, region=region, screen=screen):
            yield True
            
    except Exception as e:
        logger.error(f"Context hijack failed: {e}")
        yield False
    finally:
        # 5. Restore
        if area.type != old_type:
            area.type = old_type

def set_image(name, x, y, alpha=True, full=False, space='sRGB', ncol=False, basiccolor=(0,0,0,0), clear=True, 
              use_udim=False, udim_tiles=None, tile_resolutions=None):
    """Get or create an image with specified settings (Supports UDIM with per-tile resolution)."""
    image = bpy.data.images.get(name)
    
    # Conflict check: If existing image has different tiled state, remove it
    if image:
        is_tiled = (image.source == 'TILED')
        if is_tiled != use_udim:
            bpy.data.images.remove(image)
            image = None
    
    if not image:
        # Determine 1001 size for creation (Global X/Y or Custom 1001)
        init_x, init_y = x, y
        if use_udim and tile_resolutions and 1001 in tile_resolutions:
            init_x, init_y = tile_resolutions[1001]
            
        image = bpy.data.images.new(name, width=init_x, height=init_y, alpha=alpha, float_buffer=full, tiled=use_udim)
    else:
        # Scale if size mismatches (Handles both Single and UDIM 1001 base size)
        target_w, target_h = x, y
        if use_udim and tile_resolutions and 1001 in tile_resolutions:
            target_w, target_h = tile_resolutions[1001]
            
        if image.size[0] != target_w or image.size[1] != target_h: 
            image.scale(target_w, target_h)
            if image.source == 'GENERATED':
                image.generated_width = target_w
                image.generated_height = target_h

    image.file_format = 'PNG' 
    image.use_fake_user = True
    
    if not full:
        try: image.colorspace_settings.name = space
        except: pass 
    
    if alpha: image.alpha_mode = 'STRAIGHT'
    
    if use_udim and image.source == 'TILED':
        target_tiles = set(udim_tiles) if udim_tiles else {1001}
        existing_tiles = {t.number for t in image.tiles}
        
        # [Fix] Ensure 1001 (Main Tile) respects custom resolution if specified
        if 1001 in existing_tiles and 1001 in target_tiles:
            t_w, t_h = x, y
            if tile_resolutions and 1001 in tile_resolutions:
                t_w, t_h = tile_resolutions[1001]
            
            if image.size[0] != t_w or image.size[1] != t_h:
                image.scale(t_w, t_h)

        # 1. Add Missing Tiles
        missing_tiles = target_tiles - existing_tiles
        if missing_tiles:
            # Use the robust context manager to create filled tiles via Operator
            with robust_image_editor_context(bpy.context, image) as valid:
                if valid:
                    for t_idx in missing_tiles:
                        # Determine resolution for this specific tile
                        t_w, t_h = x, y
                        if tile_resolutions and t_idx in tile_resolutions:
                            t_w, t_h = tile_resolutions[t_idx]
                        
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
                                generated_type='BLANK',
                                color=basiccolor
                            )
                        except Exception as e:
                            logger.warning(f"Failed to add UDIM tile {t_idx}: {e}")
                else:
                    # Fallback (Cannot set resolution easily via API without ops)
                    for t_idx in missing_tiles:
                        image.tiles.new(tile_number=t_idx)

        # 2. Remove Extra Tiles (Cleanup)
        extra_tiles = existing_tiles - target_tiles
        if extra_tiles:
            # Note: Removing tiles shifts indices, so we iterate carefully or by reference
            # image.tiles collection behaves like a list, removal by pointer is safest if possible, 
            # or finding by number.
            for t_idx in extra_tiles:
                tile_ptr = image.tiles.get(t_idx) # Access by tile index (1001), not list index? No, get() uses index/key
                # image.tiles.get(1001) returns None usually, keys are not tile numbers.
                # We must find the tile object.
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
    
    # [Fix] UDIM Handling: Blender requires a token (e.g. <UDIM>) in the filepath for tiled images.
    # We replace the numeric suffix or just append the token if missing.
    if image.source == 'TILED':
        # Simple heuristic: If saving a tiled image, force the <UDIM> token pattern.
        # usually "Name.<UDIM>.ext"
        if "<UDIM>" not in fname:
            # Strip extension, append .<UDIM>, re-append extension
            stem = Path(fname).stem
            # If motion is involved, it might be Name_0001.<UDIM>.ext - complicated but supported
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
            image.source = 'FILE'
            image.reload()
        except: pass
        
    return abs_path

# --- Optimized ID Map Generation ---

def generate_optimized_colors(count, start_color=(1,0,0,1), iterations=0, manual_start=True, seed=0):
    if count <= 0: return np.zeros((0, 4), dtype=np.float32)
    indices = np.arange(count, dtype=np.float64)
    golden_ratio = 0.618033988749895
    
    if manual_start:
        h_start, _, _ = colorsys.rgb_to_hsv(start_color[0], start_color[1], start_color[2])
        hues = (h_start + indices * golden_ratio) % 1.0
    else:
        rng = np.random.default_rng(seed)
        hues = (rng.random() + indices * golden_ratio) % 1.0

    rng = np.random.default_rng(seed)
    sats = 0.5 + rng.random(count) * 0.3
    vals = 0.8 + rng.random(count) * 0.2
    
    rgb = np.array([colorsys.hsv_to_rgb(h, s, v) for h, s, v in zip(hues, sats, vals)], dtype=np.float32)
    colors = np.column_stack((rgb, np.ones(count, dtype=np.float32)))
    if manual_start: colors[0] = list(start_color)
    return colors

def setup_mesh_attribute(obj, id_type='ELEMENT', start_color=(1,0,0,1), iterations=0, manual_start=True, seed=0):
    if obj.type != 'MESH': return None
    if id_type == 'ELE': id_type = 'ELEMENT'
    attr_name = f"BT_ATTR_{id_type}"
    if attr_name in obj.data.attributes: return attr_name

    current_mode = obj.mode
    if current_mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    
    # --- Fast Path: Material ID (NumPy) ---
    if id_type == 'MAT':
        poly_count = len(obj.data.polygons)
        if poly_count == 0: return None
        
        mat_indices = np.zeros(poly_count, dtype=np.int32)
        obj.data.polygons.foreach_get("material_index", mat_indices)
        
        unique_mats = np.unique(mat_indices)
        palette = generate_optimized_colors(len(unique_mats), start_color, iterations, manual_start, seed)
        
        # Ensure we don't crash on empty/invalid indices
        max_idx = np.max(mat_indices) if len(mat_indices) > 0 else 0
        full_palette = np.zeros((max_idx + 1, 4), dtype=np.float32)
        full_palette[unique_mats] = palette
        
        loop_totals = np.zeros(poly_count, dtype=np.int32)
        obj.data.polygons.foreach_get("loop_total", loop_totals)
        loop_colors = np.repeat(full_palette[mat_indices], loop_totals, axis=0)
        
        obj.data.attributes.new(name=attr_name, type='BYTE_COLOR', domain='CORNER')
        obj.data.attributes[attr_name].data.foreach_set("color", loop_colors.flatten())
        
        if current_mode != 'OBJECT': bpy.ops.object.mode_set(mode=current_mode)
        return attr_name

    # --- Optimized: Islands (BMesh C-Extension) ---
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        
        if len(bm.faces) == 0:
            bm.free()
            return None
        
        if id_type in {'ELEMENT', 'SEAM', 'UVI'}:
            # Reset tags for all faces before starting
            for f in bm.faces: f.tag = 0
            visited_tag = 1
            islands = [] # Must be a list of lists of faces

            if id_type == 'ELEMENT':
                # Try to use fast C-extension for island finding
                try:
                    res = bmesh.ops.find_adjacent_mesh_islands(bm, faces=bm.faces[:])
                    islands = res.get('faces', res.get('regions', []))
                except Exception as e:
                    logger.warning(f"BMesh island op failed, falling back to manual: {e}")
                    islands = []
            
            # If ELEMENT op failed to return results, or we are doing SEAM/UVI, use manual traversal
            if not islands:
                uv_lay = bm.loops.layers.uv.active if id_type == 'UVI' else None
                for f in bm.faces:
                    if f.tag == visited_tag: continue
                    island_faces = []
                    stack = [f]
                    f.tag = visited_tag
                    while stack:
                        curr = stack.pop()
                        island_faces.append(curr)
                        for edge in curr.edges:
                            # Seam check for SEAM mode
                            if id_type == 'SEAM' and edge.seam: continue
                            for other_f in edge.link_faces:
                                if other_f.tag == visited_tag: continue
                                
                                # UV check for UVI mode
                                if id_type == 'UVI' and uv_lay:
                                    is_continuous = True
                                    for v in edge.verts:
                                        l1 = next((l for l in curr.loops if l.vert == v), None)
                                        l2 = next((l for l in other_f.loops if l.vert == v), None)
                                        if l1 and l2 and (l1[uv_lay].uv - l2[uv_lay].uv).length_squared > 1e-5:
                                            is_continuous = False; break
                                    if not is_continuous: continue
                                    
                                other_f.tag = visited_tag
                                stack.append(other_f)
                    islands.append(island_faces)
            
            island_count = len(islands)
            palette = generate_optimized_colors(max(1, island_count), start_color, iterations, manual_start, seed)
            
            # Ensure indices are valid
            bm.faces.ensure_lookup_table()
            
            # Map faces back to color
            face_to_color_idx = np.zeros(len(bm.faces), dtype=np.int32)
            for idx, island_faces in enumerate(islands):
                for f in island_faces:
                    face_to_color_idx[f.index] = idx
            
            loop_totals = np.zeros(len(obj.data.polygons), dtype=np.int32)
            obj.data.polygons.foreach_get("loop_total", loop_totals)
            loop_colors = np.repeat(palette[face_to_color_idx], loop_totals, axis=0)
            
            obj.data.attributes.new(name=attr_name, type='BYTE_COLOR', domain='CORNER')
            obj.data.attributes[attr_name].data.foreach_set("color", loop_colors.flatten())
    except Exception as e:
        logger.exception("ID Map Gen Failed")
        attr_name = None
    finally:
        bm.free()
    
    if current_mode != 'OBJECT': 
        try: bpy.ops.object.mode_set(mode=current_mode)
        except: pass
        
    return attr_name

def process_pbr_numpy(target_img, spec_img, diff_img, map_id, threshold=0.04, array_cache=None):
    """
    Optimized PBR conversion using NumPy and optional array caching.
    array_cache: dict {image_ptr: numpy_array}
    """
    try:
        def get_pixels(img):
            if array_cache is not None and img in array_cache:
                return array_cache[img]
            
            count = len(img.pixels)
            arr = np.empty(count, dtype=np.float32)
            img.pixels.foreach_get(arr)
            arr = arr.reshape(-1, 4)
            
            if array_cache is not None:
                array_cache[img] = arr
            return arr

        spec_arr = get_pixels(spec_img)
        
        # Specular Max (Luminance check for metallic separation)
        spec_max = np.max(spec_arr[:, :3], axis=1)
        denom = max(1e-5, 1.0 - threshold)
        metal_arr = np.clip((spec_max - threshold) / denom, 0.0, 1.0)
        
        result = np.zeros_like(spec_arr)
        result[:, 3] = 1.0
        
        if map_id == 'pbr_conv_metal':
            result[:, 0] = metal_arr
            result[:, 1] = metal_arr
            result[:, 2] = metal_arr
        elif map_id == 'pbr_conv_base' and diff_img:
            diff_arr = get_pixels(diff_img)
            m = metal_arr[:, np.newaxis]
            # BaseColor = Diffuse * (1-Metal) + Specular * Metal
            result[:, :3] = diff_arr[:, :3] * (1.0 - m) + spec_arr[:, :3] * m
            result[:, 3] = diff_arr[:, 3]
        
        target_img.pixels.foreach_set(result.flatten())
        return True
    except Exception as e:
        logger.error(f"PBR Conv Failed: {e}")
        return False

def apply_baked_result(original_obj, task_images, setting, task_base_name):
    if not task_images: return None
    col = bpy.data.collections.get("Baked_Results") or bpy.data.collections.new("Baked_Results")
    if col.name not in bpy.context.scene.collection.children:
        try: bpy.context.scene.collection.children.link(col)
        except: pass

    new_obj = original_obj.copy()
    new_obj.data = original_obj.data.copy()
    new_obj.name = f"{task_base_name}_Baked"
    for c in new_obj.users_collection: c.objects.unlink(new_obj)
    col.objects.link(new_obj)

    first_val = next(iter(task_images.values()))
    if isinstance(first_val, dict):
        orig_mat_names = [s.material.name for s in original_obj.material_slots if s.material]
        while len(new_obj.material_slots) < len(orig_mat_names): new_obj.data.materials.append(None)
        for i, orig_name in enumerate(orig_mat_names):
            mat_textures = {}
            for chan_id, mat_dict in task_images.items():
                if orig_name in mat_dict: mat_textures[chan_id] = mat_dict[orig_name]
            mat = _create_simple_mat(f"{task_base_name}_{orig_name}_Baked", mat_textures)
            new_obj.material_slots[i].material = mat
    else:
        mat = _create_simple_mat(f"{task_base_name}_Mat", task_images)
        new_obj.data.materials.clear()
        new_obj.data.materials.append(mat)
    return new_obj

def _create_simple_mat(name, texture_map):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    out = tree.nodes.new('ShaderNodeOutputMaterial'); out.location = (300, 0)
    tree.links.new(bsdf.outputs[0], out.inputs[0])
    y_pos = 0
    
    # Use global compatibility map directly
    # Map internal channel IDs to BSDF socket names (Key: internal_id, Value: List of possible socket names)
    channel_to_socket_keys = {
        'color': 'color', 'metal': 'metal', 'rough': 'rough', 
        'specular': 'specular', 'emi': 'emi', 'alpha': 'alpha', 
        'normal': 'normal', 'ao': 'color', 'combine': 'color' # AO and Combine act as Color
    }

    for chan_id, image in texture_map.items():
        # Determine target socket on BSDF
        target_socket = None
        
        # 1. Resolve socket name via compatibility map
        compat_key = channel_to_socket_keys.get(chan_id)
        if compat_key and compat_key in BSDF_COMPATIBILITY_MAP:
            possible_names = BSDF_COMPATIBILITY_MAP[compat_key]
            for name in possible_names:
                if name in bsdf.inputs:
                    target_socket = bsdf.inputs[name]
                    break
        
        # Special handling if not found via map (or special logic)
        is_normal = (chan_id == 'normal')
        
        if not target_socket and not is_normal:
            continue

        tex = tree.nodes.new('ShaderNodeTexImage'); tex.image = image
        tex.location = (-600 if is_normal else -300, y_pos); y_pos -= 280
        
        # Set Color Space
        if chan_id in {'metal', 'rough', 'normal', 'specular', 'ao'}:
            try: tex.image.colorspace_settings.name = 'Non-Color'
            except: pass
            
        # Link
        if is_normal:
            nor = tree.nodes.new('ShaderNodeNormalMap'); nor.location = (-300, tex.location.y)
            tree.links.new(tex.outputs[0], nor.inputs['Color'])
            # Find Normal socket specifically
            normal_socket = bsdf.inputs.get('Normal')
            if normal_socket:
                tree.links.new(nor.outputs['Normal'], normal_socket)
        elif target_socket:
            tree.links.new(tex.outputs[0], target_socket)
            
        if chan_id == 'alpha': mat.blend_method = 'BLEND'
            
    return mat

# --- Node Graph Handler ---

class NodeGraphHandler:
    def __init__(self, materials):
        self.materials = [m for m in materials if m and m.use_nodes]
        # {mat: {'tex': node, 'emi': node}}
        self.session_nodes = {}
        # {mat: [nodes]} per-pass nodes
        self.temp_logic_nodes = {}
        self.temp_attributes = []
        self.original_links = {} # {mat: (from_node, from_socket)}

    def __enter__(self): 
        self._prepare_session_nodes()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb): 
        self.cleanup()
        return False

    def _prepare_session_nodes(self):
        """Pre-create essential bake nodes once per session."""
        for mat in self.materials:
            tree = mat.node_tree
            self.session_nodes[mat] = {
                'tex': tree.nodes.new('ShaderNodeTexImage'),
                'emi': tree.nodes.new('ShaderNodeEmission')
            }
            # Position away from user nodes
            self.session_nodes[mat]['tex'].location = (-800, 500)
            self.session_nodes[mat]['emi'].location = (600, 0)
            self.temp_logic_nodes[mat] = []

    def cleanup(self):
        # 1. Remove All Session and Logic Nodes
        for mat in self.materials:
            if not mat.node_tree: continue
            tree = mat.node_tree
            if mat in self.session_nodes:
                for n in self.session_nodes[mat].values():
                    try: tree.nodes.remove(n)
                    except: pass
            if mat in self.temp_logic_nodes:
                for n in self.temp_logic_nodes[mat]:
                    try: tree.nodes.remove(n)
                    except: pass
        
        # 2. Restore Original Links
        for mat, link_info in self.original_links.items():
            if not mat.node_tree: continue
            try:
                out_n = self._find_output(mat.node_tree)
                if out_n and link_info:
                    from_node, from_socket = link_info
                    if from_node and from_node.name in mat.node_tree.nodes:
                        mat.node_tree.links.new(from_socket, out_n.inputs[0])
            except: pass
        
        # 3. Attributes cleanup
        for obj, attr in self.temp_attributes:
            try: 
                if attr in obj.data.attributes:
                    obj.data.attributes.remove(obj.data.attributes[attr])
            except: pass

    def setup_protection(self, objects, active_materials):
        active_set = set(active_materials)
        d = bpy.data.images.get("BT_Protection_Dummy") or bpy.data.images.new("BT_Protection_Dummy", 32, 32, alpha=True)
        d.use_fake_user=True
        for obj in objects:
            if obj.type!='MESH': continue
            for s in obj.material_slots:
                m = s.material
                if m and m.use_nodes and m not in active_set:
                    # Use tracked logic node for protection images too
                    self._add_node(m, 'ShaderNodeTexImage', image=d)

    def setup_for_pass(self, bake_pass, socket_name, image, mesh_type=None, attr_name=None, channel_settings=None):
        for mat in self.materials:
            tree = mat.node_tree
            out_n = self._find_output(tree)
            if not out_n or mat not in self.session_nodes: continue
            
            # Clear previous pass logic nodes
            for n in self.temp_logic_nodes[mat]:
                try: tree.nodes.remove(n)
                except: pass
            self.temp_logic_nodes[mat] = []

            # Store Original Link (Only once per material)
            if mat not in self.original_links:
                socket = out_n.inputs[0]
                self.original_links[mat] = (socket.links[0].from_node, socket.links[0].from_socket) if socket.is_linked else None

            # Setup Persistent Nodes
            s_nodes = self.session_nodes[mat]
            tex_n, emi_n = s_nodes['tex'], s_nodes['emi']
            
            tex_n.image = image
            tree.nodes.active = tex_n
            
            # Needs wrapper?
            needs_emit = (bake_pass == 'EMIT' or mesh_type or socket_name.startswith('pbr_conv') or socket_name == 'node_group')
            
            if needs_emit:
                tree.links.new(emi_n.outputs[0], out_n.inputs[0])
                src = None
                if mesh_type: src = self._create_mesh_map_logic(mat, mesh_type, attr_name, channel_settings)
                elif socket_name.startswith('pbr_conv'): src = self._create_extension_logic(mat, socket_name, channel_settings)
                elif socket_name == 'node_group': src = self._create_node_group_logic(mat, channel_settings)
                else: src = self._find_socket_source(mat, socket_name, channel_settings)
                
                if src: tree.links.new(src, emi_n.inputs[0])

    def _create_node_group_logic(self, mat, s):
        if not s or not s.node_group: return None
        ng_data = bpy.data.node_groups.get(s.node_group)
        if not ng_data: return None
        grp = self._add_node(mat, 'ShaderNodeGroup')
        grp.node_tree = ng_data
        out_socket = grp.outputs.get(s.node_group_output) if s.node_group_output else (grp.outputs[0] if grp.outputs else None)
        return out_socket

    def _add_node(self, mat, type, **kwargs):
        n = mat.node_tree.nodes.new(type)
        for k, v in kwargs.items():
            if hasattr(n, k): setattr(n, k, v)
        if mat not in self.temp_logic_nodes: self.temp_logic_nodes[mat] = []
        self.temp_logic_nodes[mat].append(n)
        return n

    def _find_output(self, tree):
        for n in tree.nodes:
            if n.bl_idname == 'ShaderNodeOutputMaterial' and n.is_active_output: return n
        return next((n for n in tree.nodes if n.bl_idname == 'ShaderNodeOutputMaterial'), None)

    def _find_socket_source(self, mat, socket_name, settings):
        tree = mat.node_tree
        bsdf = next((n for n in tree.nodes if n.bl_idname=='ShaderNodeBsdfPrincipled'), None)
        found = None
        if bsdf:
            for cand in BSDF_COMPATIBILITY_MAP.get(socket_name, [socket_name]):
                if cand in bsdf.inputs: found = bsdf.inputs[cand]; break
        src = None
        if found and found.is_linked: src = found.links[0].from_socket
        else:
            val = found.default_value if found else SOCKET_DEFAULT_TYPE.get(socket_name, (0,0,0,1))
            rgb = self._add_node(mat, 'ShaderNodeRGB')
            v = (val[0],val[1],val[2],1) if hasattr(val,"__len__") and len(val)>=3 else (val,val,val,1)
            rgb.outputs[0].default_value = v
            src = rgb.outputs[0]
        if settings and socket_name == 'rough' and getattr(settings, 'rough_inv', False):
            inv = self._add_node(mat, 'ShaderNodeInvert'); inv.inputs[0].default_value=1.0
            tree.links.new(src, inv.inputs[1]); src = inv.outputs[0]
        return src

    def _create_mesh_map_logic(self, mat, mtype, attr, s):
        if mtype == 'ID': return self._add_node(mat, 'ShaderNodeAttribute', attribute_name=attr).outputs['Color']
        elif mtype == 'AO':
            n = self._add_node(mat, 'ShaderNodeAmbientOcclusion')
            n.samples = getattr(s, 'ao_sample', 16); n.inputs['Distance'].default_value = getattr(s, 'ao_dis', 1.0)
            n.inside = getattr(s, 'ao_inside', False); return n.outputs['Color']
        elif mtype == 'POS': return self._add_node(mat, 'ShaderNodeNewGeometry').outputs['Position']
        elif mtype == 'UV': return self._add_node(mat, 'ShaderNodeUVMap').outputs['UV']
        elif mtype == 'WF':
            n = self._add_node(mat, 'ShaderNodeWireframe'); n.use_pixel_size = getattr(s, 'wireframe_use_pix', False)
            n.inputs[0].default_value = getattr(s, 'wireframe_dis', 0.01); return n.outputs[0]
        elif mtype == 'BEVEL':
            n = self._add_node(mat, 'ShaderNodeBevel'); n.samples = getattr(s, 'bevel_sample', 8)
            n.inputs['Radius'].default_value = getattr(s, 'bevel_rad', 0.05); return n.outputs[0]
        return None

    def _create_extension_logic(self, mat, socket_name, settings):
        threshold = settings.pbr_conv_threshold; tree = mat.node_tree
        spec_src = self._find_socket_source(mat, 'specular', None)
        sep = self._add_node(mat, 'ShaderNodeSeparateColor'); tree.links.new(spec_src, sep.inputs[0])
        math1 = self._add_node(mat, 'ShaderNodeMath', operation='MAXIMUM')
        tree.links.new(sep.outputs[0], math1.inputs[0]); tree.links.new(sep.outputs[1], math1.inputs[1])
        math2 = self._add_node(mat, 'ShaderNodeMath', operation='MAXIMUM')
        tree.links.new(math1.outputs[0], math2.inputs[0]); tree.links.new(sep.outputs[2], math2.inputs[1])
        sub = self._add_node(mat, 'ShaderNodeMath', operation='SUBTRACT')
        tree.links.new(math2.outputs[0], sub.inputs[0]); sub.inputs[1].default_value = threshold
        div = self._add_node(mat, 'ShaderNodeMath', operation='DIVIDE')
        tree.links.new(sub.outputs[0], div.inputs[0]); div.inputs[1].default_value = max(1e-5, 1.0 - threshold)
        clamp = self._add_node(mat, 'ShaderNodeClamp'); tree.links.new(div.outputs[0], clamp.inputs[0])
        metallic_out = clamp.outputs[0]
        if socket_name == 'pbr_conv_metal': return metallic_out
        elif socket_name == 'pbr_conv_base':
            diff_src = self._find_socket_source(mat, 'color', None)
            mix = self._add_node(mat, 'ShaderNodeMix', data_type='RGBA')
            tree.links.new(metallic_out, mix.inputs[0])
            tree.links.new(diff_src, mix.inputs[6]); tree.links.new(spec_src, mix.inputs[7])
            return mix.outputs[2]
        return None
