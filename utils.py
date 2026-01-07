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

def check_objects_uv(objects):
    """Return a list of object names that are missing UV layers."""
    return [obj.name for obj in objects if obj.type == 'MESH' and not obj.data.uv_layers]

def reset_channels_logic(setting):
    """
    Reset and repopulate channels based on the current bake_type and enabled map toggles.
    Directly modifies the collection property, safe to call from UI/Operators.
    """
    defs = []
    
    # 1. Base Definitions based on Bake Type
    b_type = setting.bake_type
    if b_type == 'BSDF':
        # Compatibility check for Blender 4.0+
        key = 'BSDF_4' if bpy.app.version >= (4, 0, 0) else 'BSDF_3'
        defs.extend(CHANNEL_DEFINITIONS.get(key, []))
    else:
        defs.extend(CHANNEL_DEFINITIONS.get(b_type, []))
    
    # 2. Optional Maps
    if setting.use_light_map: 
        defs.extend(CHANNEL_DEFINITIONS.get('LIGHT', []))
    if setting.use_mesh_map: 
        defs.extend(CHANNEL_DEFINITIONS.get('MESH', []))
    if setting.use_extension_map:
        defs.extend(CHANNEL_DEFINITIONS.get('EXTENSION', []))
    
    target_ids = {d['id'] for d in defs}
    
    # 3. Remove invalid channels (iterate backwards)
    for i in range(len(setting.channels)-1, -1, -1):
         if setting.channels[i].id not in target_ids: 
             setting.channels.remove(i)
    
    # 4. Add new channels
    existing_ids = {c.id for c in setting.channels}
    for d in defs:
        if d['id'] not in existing_ids:
            new_chan = setting.channels.add()
            new_chan.id = d['id']
            new_chan.name = d['name']
            # Apply defaults
            defaults = d.get('defaults', {})
            for k, v in defaults.items():
                if hasattr(new_chan, k):
                    setattr(new_chan, k, v)

@contextmanager
def safe_context_override(context, active_object=None, selected_objects=None):
    """
    Safe context override for Blender 3.2+.
    Falls back to selection manipulation if temp_override is unavailable.
    """
    kw = {}
    if active_object:
        kw['active_object'] = active_object
    if selected_objects:
        kw['selected_objects'] = selected_objects
        kw['selected_editable_objects'] = selected_objects
    
    if hasattr(context, "temp_override"):
        with context.temp_override(**kw):
            yield
    else:
        # Legacy fallback
        original_active = context.view_layer.objects.active
        original_selected = context.selected_objects[:]
        try:
            bpy.ops.object.select_all(action='DESELECT')
            if active_object:
                context.view_layer.objects.active = active_object
            for obj in (selected_objects or []):
                obj.select_set(True)
            yield
        finally:
            try:
                bpy.ops.object.select_all(action='DESELECT')
                if original_active:
                    context.view_layer.objects.active = original_active
                for obj in original_selected:
                    obj.select_set(True)
            except: pass

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
            'scene': {'res_x': 'resolution_x', 'res_y': 'resolution_y'}
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
        """Execute Smart UV or UDIM Repacking logic."""
        s = self.settings
        
        # Mode A: Smart UV Project (Overrides everything)
        if s.use_auto_uv:
            self._apply_smart_uv()
        
        # Mode B: UDIM Repacking (Only if UDIM mode is ON and we are NOT in 'AUTO' detection mode)
        # If mode is AUTO, we assume user set up UVs correctly.
        # If mode is MANUAL/SEQUENCE, we force distribute islands into that grid.
        if s.bake_mode == 'UDIM' and s.udim_mode in {'MANUAL', 'SEQUENCE'}:
            self._distribute_udim()

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

    def _distribute_udim(self):
        """
        Distributes UV islands from the 0-1 space into the target UDIM grid.
        Supports SEQUENCE (Per-Object) and MANUAL (Grid Distribution).
        Uses BMesh for direct data manipulation to avoid Context Errors.
        """
        s = self.settings
        start_tile = s.udim_start_tile
        
        # 1. Calculate Offsets
        offsets = []
        if s.udim_mode == 'SEQUENCE':
            # One object -> One tile
            for i in range(len(self.objects)):
                offsets.append((i, 0))
        elif s.udim_mode == 'MANUAL':
            # Grid Distribution
            grid_u, grid_v = s.udim_grid_u, s.udim_grid_v
            for v in range(grid_v):
                for u in range(grid_u):
                    offsets.append((u, v))
        
        if not offsets: return

        # 2. Execute Distribution
        
        # SEQUENCE Mode: Assign entire object to one tile
        if s.udim_mode == 'SEQUENCE':
            # Ensure we are in object mode
            if bpy.context.object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
                
            for i, obj in enumerate(self.objects):
                if i >= len(offsets): break 
                
                offset_x, offset_y = offsets[i]
                if offset_x == 0 and offset_y == 0: continue
                
                # BMesh Operation - Safe & Fast
                bm = bmesh.new()
                bm.from_mesh(obj.data)
                uv_layer = bm.loops.layers.uv.verify()
                
                # Shift all UVs
                for face in bm.faces:
                    for loop in face.loops:
                        loop[uv_layer].uv[0] += offset_x
                        loop[uv_layer].uv[1] += offset_y
                
                bm.to_mesh(obj.data)
                bm.free()

        # MANUAL Mode: Distribute islands (Round Robin)
        else:
            # For Manual Grid packing, we still rely on Select Linked which works best with Ops,
            # BUT we must avoid uv.cursor_set. 
            # We can use bmesh translation or simple uv property shifting if we select loops.
            
            # Since Manual Mode relies on complex island detection, let's refine it to be safer.
            # We will use the robust round-robin selection but translate via BMesh manually 
            # or ensure we don't use context-sensitive pivot ops.
            
            ctx_override = self._get_context_override()
            with ctx_override:
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                if not s.use_auto_uv:
                    bpy.ops.uv.pack_islands(margin=s.auto_uv_margin)
                bpy.ops.mesh.select_all(action='DESELECT')
                bpy.ops.object.mode_set(mode='OBJECT')

                for obj in self.objects:
                    self._distribute_obj_islands_round_robin(obj, offsets)

    def _distribute_obj_islands_round_robin(self, obj, tile_offsets):
        """
        Moves islands of a single object to target tiles in a round-robin fashion.
        Uses BMesh translation to avoid context issues.
        """
        # 1. Identify Islands using BMesh (Pure Data approach is hard for UVs, so we mix)
        # We use Edit Mode selection to FIND islands, but BMesh to MOVE them? 
        # Actually, bpy.ops.transform.translate works in VIEW_3D if we don't set constraint to UV specific.
        # But we want to move UVs. 
        # Safer approach: Select faces in Edit Mode -> Get selected faces in BMesh -> Move UVs in BMesh.
        
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='FACE')
        bpy.ops.mesh.select_all(action='DESELECT')
        
        import bmesh
        bm = bmesh.from_edit_mesh(obj.data)
        uv_layer = bm.loops.layers.uv.verify()
        
        tile_idx = 0
        total_tiles = len(tile_offsets)
        
        while True:
            # Find a visible, unselected face
            seed = None
            for f in bm.faces:
                if not f.hide and not f.select:
                    seed = f
                    break
            
            if not seed: break
            
            # Select Island
            seed.select = True
            bm.select_history.add(seed)
            bpy.ops.uv.select_linked() 
            
            # Update BMesh selection from Ops
            # (select_linked updates the internal mesh, we need to refresh bmesh view?)
            # bmesh.update_edit_mesh(obj.data) # This syncs
            # Actually select_linked works on the edit mesh.
            
            # Identify selected faces
            selected_faces = [f for f in bm.faces if f.select]
            if not selected_faces: break # Should not happen

            # Move UVs using BMesh Data (No Ops!)
            offset_x, offset_y = tile_offsets[tile_idx]
            if offset_x != 0 or offset_y != 0:
                for f in selected_faces:
                    for loop in f.loops:
                        loop[uv_layer].uv[0] += offset_x
                        loop[uv_layer].uv[1] += offset_y

            # Hide processed faces
            bpy.ops.mesh.hide(unselected=False)
            bpy.ops.mesh.select_all(action='DESELECT') # Clear for next pass
            
            tile_idx = (tile_idx + 1) % total_tiles
            
            # Sync back to ensure hiding works for next iteration
            bmesh.update_edit_mesh(obj.data)

        # Unhide everything
        bpy.ops.mesh.reveal()
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
        # Remove Temp Layers
        for obj, layer in self.created_layers:
            try:
                if layer: obj.data.uv_layers.remove(layer)
            except: pass
            
        # Restore Indices
        for obj in self.objects:
            if obj.name in self.original_states:
                state = self.original_states[obj.name]
                try:
                    obj.data.uv_layers.active_index = state['active']
                    # Restore render active
                    if state['render'] < len(obj.data.uv_layers):
                         obj.data.uv_layers[state['render']].active_render = True
                except: pass

# --- UDIM System Utilities ---

def get_active_uv_udim_tiles(objects):
    """
    Scans the active UV layers of given objects and returns a set of used UDIM indices.
    """
    tiles = set()
    for obj in objects:
        if obj.type != 'MESH' or not obj.data.uv_layers: continue
        uv_layer = obj.data.uv_layers.active
        if not uv_layer: continue
        
        data_len = len(obj.data.loops)
        uvs = np.zeros(data_len * 2, dtype=np.float32)
        uv_layer.data.foreach_get("uv", uvs)
        uvs = uvs.reshape(-1, 2)
        
        u_floor = np.floor(uvs[:, 0]).astype(np.int32)
        v_floor = np.floor(uvs[:, 1]).astype(np.int32)
        
        mask = (u_floor >= 0) & (v_floor >= 0) & (u_floor < 10)
        
        if not np.any(mask): 
            tiles.add(1001)
            continue
            
        valid_u = u_floor[mask]
        valid_v = v_floor[mask]
        
        indices = 1001 + valid_u + (valid_v * 10)
        tiles.update(np.unique(indices).tolist())
        
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
              use_udim=False, udim_tiles=None):
    """Get or create an image with specified settings (Supports UDIM)."""
    image = bpy.data.images.get(name)
    
    if not image:
        image = bpy.data.images.new(name, width=x, height=y, alpha=alpha, float_buffer=full, tiled=use_udim)
    else:
        if image.size[0] != x or image.size[1] != y: 
            image.scale(x, y)

    image.file_format = 'PNG' 
    image.use_fake_user = True
    
    if not full:
        try: image.colorspace_settings.name = space
        except: pass 
    
    if alpha: image.alpha_mode = 'STRAIGHT'
    
    if use_udim and image.source == 'TILED':
        target_tiles = set(udim_tiles) if udim_tiles else {1001}
        existing_tiles = {t.number for t in image.tiles}
        
        # 1. Add Missing Tiles
        missing_tiles = target_tiles - existing_tiles
        if missing_tiles:
            # Use the robust context manager to create filled tiles via Operator
            with robust_image_editor_context(bpy.context, image) as valid:
                if valid:
                    for t_idx in missing_tiles:
                        try: 
                            bpy.ops.image.tile_add(number=t_idx, count=1, label=str(t_idx), fill=True)
                        except Exception as e:
                            logger.warning(f"Failed to add UDIM tile {t_idx}: {e}")
                else:
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
    except: return None
    
    info = FORMAT_SETTINGS.get(file_format, {})
    ext = info.get("extensions", ["." + file_format.lower()])[0]
    
    fname = f"{image.name}{separator}{str(frame).zfill(fillnum)}{ext}" if motion else f"{image.name}{ext}"
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
    
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.ensure_lookup_table()
        face_island_map = np.zeros(len(bm.faces), dtype=np.int32)
        island_count = 0
        
        if id_type == 'MAT':
            for i, f in enumerate(bm.faces):
                face_island_map[i] = f.material_index
            island_count = np.max(face_island_map) + 1 if len(face_island_map) > 0 else 0
        else:
            visited = np.zeros(len(bm.faces), dtype=bool)
            faces = bm.faces
            uv_lay = bm.loops.layers.uv.active if id_type == 'UVI' else None
            
            for i in range(len(faces)):
                if visited[i]: continue
                stack = [faces[i]]
                visited[i] = True
                face_island_map[i] = island_count
                
                while stack:
                    curr = stack.pop()
                    for edge in curr.edges:
                        if id_type == 'SEAM' and edge.seam: continue
                        for other_f in edge.link_faces:
                            if visited[other_f.index]: continue
                            should_join = True
                            if id_type == 'UVI' and uv_lay:
                                is_continuous = True
                                for v in edge.verts:
                                    l1 = next((l for l in curr.loops if l.vert == v), None)
                                    l2 = next((l for l in other_f.loops if l.vert == v), None)
                                    if l1 and l2:
                                        if (l1[uv_lay].uv - l2[uv_lay].uv).length_squared > 1e-5:
                                            is_continuous = False; break
                                if not is_continuous: should_join = False
                            
                            if should_join:
                                visited[other_f.index] = True
                                face_island_map[other_f.index] = island_count
                                stack.append(other_f)
                island_count += 1

        if island_count < 1: island_count = 1
        palette = generate_optimized_colors(island_count, start_color, iterations, manual_start, seed)
        unique, counts = np.unique(face_island_map, return_counts=True)
        remap_table = np.zeros(island_count + 1, dtype=np.int32)
        valid_mask = unique < len(remap_table)
        remap_table[unique[valid_mask]] = np.arange(len(unique[valid_mask]))
        
        remapped_indices = np.clip(remap_table[face_island_map], 0, len(palette)-1)
        loop_totals = np.zeros(len(obj.data.polygons), dtype=np.int32)
        obj.data.polygons.foreach_get("loop_total", loop_totals)
        loop_colors = np.repeat(palette[remapped_indices], loop_totals, axis=0)
        
        obj.data.attributes.new(name=attr_name, type='BYTE_COLOR', domain='CORNER')
        obj.data.attributes[attr_name].data.foreach_set("color", loop_colors.flatten())
    except Exception as e:
        logger.error(f"ID Map Gen Failed: {e}")
        attr_name = None
    finally:
        bm.free()
    
    if current_mode != 'OBJECT': 
        try: bpy.ops.object.mode_set(mode=current_mode)
        except: pass
    return attr_name

def process_pbr_numpy(target_img, spec_img, diff_img, map_id, threshold=0.04):
    try:
        if not target_img.pixels: return False
        count = len(target_img.pixels)
        spec_arr = np.empty(count, dtype=np.float32)
        spec_img.pixels.foreach_get(spec_arr)
        spec_arr = spec_arr.reshape(-1, 4)
        
        spec_max = np.max(spec_arr[:, :3], axis=1)
        denom = max(1e-5, 1.0 - threshold)
        metal_arr = np.clip((spec_max - threshold) / denom, 0.0, 1.0)
        
        result = np.zeros_like(spec_arr)
        result[:, 3] = 1.0
        
        if map_id == 'pbr_conv_metal':
            result[:, 0] = metal_arr; result[:, 1] = metal_arr; result[:, 2] = metal_arr
        elif map_id == 'pbr_conv_base' and diff_img:
            diff_arr = np.empty(count, dtype=np.float32)
            diff_img.pixels.foreach_get(diff_arr)
            diff_arr = diff_arr.reshape(-1, 4)
            m = metal_arr[:, np.newaxis]
            result[:, :3] = diff_arr[:, :3] * (1.0 - m) + spec_arr[:, :3] * m
            result[:, 3] = diff_arr[:, 3]
        
        target_img.pixels.foreach_set(result.flatten())
        return True
    except: return False

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
    socket_map = {'color': 'Base Color', 'metal': 'Metallic', 'rough': 'Roughness', 'specular': 'Specular IOR Level', 'emi': 'Emission Color', 'alpha': 'Alpha', 'ao': 'Base Color', 'combine': 'Base Color', 'normal': 'Normal'}
    for chan_id, image in texture_map.items():
        if chan_id not in socket_map: continue
        target = socket_map[chan_id]
        tex = tree.nodes.new('ShaderNodeTexImage'); tex.image = image
        tex.location = (-600 if target == 'Normal' else -300, y_pos); y_pos -= 280
        if chan_id in {'metal', 'rough', 'normal', 'specular', 'ao'}:
            try: tex.image.colorspace_settings.name = 'Non-Color'
            except: pass
        if target == 'Normal':
            nor = tree.nodes.new('ShaderNodeNormalMap'); nor.location = (-300, tex.location.y)
            tree.links.new(tex.outputs[0], nor.inputs['Color'])
            tree.links.new(nor.outputs['Normal'], bsdf.inputs['Normal'])
        elif target in bsdf.inputs: tree.links.new(tex.outputs[0], bsdf.inputs[target])
        if chan_id == 'alpha': mat.blend_method = 'BLEND'
    return mat

# --- Node Graph Handler ---

class NodeGraphHandler:
    def __init__(self, materials):
        self.materials = [m for m in materials if m and m.use_nodes]
        self.active_nodes = {}
        self.temp_attributes = []
        self.original_links = {} # {mat: (from_node, from_socket)}

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): self.cleanup(); return False

    def cleanup(self):
        # 1. Remove Temp Nodes
        for mat, nodes in self.active_nodes.items():
            if not mat.node_tree: continue
            for n in nodes:
                try: mat.node_tree.nodes.remove(n)
                except: pass
        self.active_nodes.clear()
        
        # 2. Restore Original Links
        for mat, link_info in self.original_links.items():
            if not mat.node_tree: continue
            try:
                out_n = self._find_output(mat.node_tree)
                if out_n and link_info:
                    from_node, from_socket = link_info
                    # Validate if nodes still exist (user might have deleted them manually, unlikely but safe to check)
                    if from_node in mat.node_tree.nodes.values():
                        mat.node_tree.links.new(from_socket, out_n.inputs[0])
            except Exception as e:
                logger.warning(f"Failed to restore link for {mat.name}: {e}")
        self.original_links.clear()

        # 3. Cleanup Attributes & Dummy
        for obj, attr in self.temp_attributes:
            try: obj.data.attributes.remove(obj.data.attributes[attr])
            except: pass
        self.temp_attributes.clear()
        d = bpy.data.images.get("BT_Protection_Dummy")
        if d: bpy.data.images.remove(d)

    def setup_protection(self, objects, active_materials):
        active_set = set(active_materials)
        d = bpy.data.images.get("BT_Protection_Dummy") or bpy.data.images.new("BT_Protection_Dummy", 32, 32, alpha=True)
        d.use_fake_user=True
        for obj in objects:
            if obj.type!='MESH': continue
            for s in obj.material_slots:
                m = s.material
                if m and m.use_nodes and m not in active_set:
                    self._add_node(m, 'ShaderNodeTexImage', image=d, select=True)

    def setup_for_pass(self, bake_pass, socket_name, image, mesh_type=None, attr_name=None, channel_settings=None):
        targets = self.materials
        for mat in targets:
            # Clean previous pass nodes (specific to this handler)
            if mat in self.active_nodes:
                for n in self.active_nodes[mat]:
                    try: mat.node_tree.nodes.remove(n)
                    except: pass
                self.active_nodes[mat] = []
            
            tree = mat.node_tree
            out_n = self._find_output(tree)
            if not out_n: continue
            
            # Store Original Link (Only once per session)
            if mat not in self.original_links:
                socket = out_n.inputs[0]
                if socket.is_linked:
                    link = socket.links[0]
                    self.original_links[mat] = (link.from_node, link.from_socket)
                else:
                    self.original_links[mat] = None

            # Add Target Image
            img_n = self._add_node(mat, 'ShaderNodeTexImage', image=image, location=(-300,400), select=True)
            tree.nodes.active = img_n
            
            if bake_pass != 'EMIT' and not mesh_type and not socket_name.startswith('pbr_conv'): continue
            
            # Add Emission Wrapper
            emi = self._add_node(mat, 'ShaderNodeEmission', location=(out_n.location.x-200, out_n.location.y))
            tree.links.new(emi.outputs[0], out_n.inputs[0])
            
            src = None
            if mesh_type: src = self._create_mesh_map_logic(mat, mesh_type, attr_name, channel_settings)
            elif socket_name.startswith('pbr_conv'): src = self._create_extension_logic(mat, socket_name, channel_settings)
            else: src = self._find_socket_source(mat, socket_name, channel_settings)
            
            if src: tree.links.new(src, emi.inputs[0])

    def _add_node(self, mat, type, **kwargs):
        n = mat.node_tree.nodes.new(type)
        for k, v in kwargs.items():
            if k == 'select': n.select = v
            elif hasattr(n, k): setattr(n, k, v)
        if mat not in self.active_nodes: self.active_nodes[mat] = []
        self.active_nodes[mat].append(n)
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
