import bpy
import bmesh
import numpy as np
import colorsys
import logging

logger = logging.getLogger(__name__)

def get_image_pixels_as_numpy(image):
    """
    Efficiently retrieve image pixels as a NumPy array (N, 4).
    """
    if not image: return None
    width, height = image.size
    num_pixels = width * height * 4
    
    # Pre-allocate
    raw_pixels = np.empty(num_pixels, dtype=np.float32)
    image.pixels.foreach_get(raw_pixels)
    
    return raw_pixels.reshape(-1, 4)

def process_pbr_numpy(target_img, spec_img, diff_img, map_id, threshold=0.04, array_cache=None):
    """
    Optimized PBR conversion (Specular -> Metallic/BaseColor) using NumPy.
    """
    try:
        # Helper to get cached array
        def get_arr(img):
            if array_cache is not None and img in array_cache:
                return array_cache[img]
            arr = get_image_pixels_as_numpy(img)
            if array_cache is not None and arr is not None:
                array_cache[img] = arr
            return arr

        spec_arr = get_arr(spec_img)
        if spec_arr is None: return False
        
        # Calculate Metalness: Spec > Threshold is Metal
        # Take max of RGB as intensity
        spec_max = np.max(spec_arr[:, :3], axis=1)
        
        denom = max(1e-5, 1.0 - threshold)
        metal_mask = np.clip((spec_max - threshold) / denom, 0.0, 1.0)
        
        # Prepare result (Default Alpha = 1.0)
        result_arr = np.zeros_like(spec_arr)
        result_arr[:, 3] = 1.0 
        
        if map_id == 'pbr_conv_metal':
            # Broadcast mask to RGB
            result_arr[:, 0] = metal_mask
            result_arr[:, 1] = metal_mask
            result_arr[:, 2] = metal_mask
            
        elif map_id == 'pbr_conv_base':
            diff_arr = get_arr(diff_img)
            if diff_arr is None: return False
            
            # BaseColor = Diffuse * (1 - Metal) + Specular * Metal
            # Expand mask dimensions for broadcasting: (N,) -> (N, 1)
            m = metal_mask[:, np.newaxis]
            
            # Vectorized mix
            result_arr[:, :3] = diff_arr[:, :3] * (1.0 - m) + spec_arr[:, :3] * m
            result_arr[:, 3] = diff_arr[:, 3] # Keep diffuse alpha
            
        # Write back to Blender image
        target_img.pixels.foreach_set(result_arr.ravel())
        return True
        
    except Exception as e:
        logger.error(f"PBR Conv Failed: {e}")
        return False

def pack_channels_numpy(target_img, channel_map, array_cache=None):
    """
    Highly optimized channel packing using NumPy.
    channel_map: {channel_index(0-3): source_image}
    """
    if not target_img: return False
    
    try:
        width, height = target_img.size
        num_pixels = width * height
        
        # Pre-allocate RGBA buffer (initialized to 0, Alpha to 1.0)
        result_arr = np.zeros((num_pixels, 4), dtype=np.float32)
        result_arr[:, 3] = 1.0 
        
        def get_arr(img):
            if array_cache is not None and img in array_cache:
                return array_cache[img]
            arr = get_image_pixels_as_numpy(img)
            if array_cache is not None and arr is not None:
                array_cache[img] = arr
            return arr

        any_packed = False
        for idx, src_img in channel_map.items():
            if not src_img or idx < 0 or idx > 3: continue
            
            src_arr = get_arr(src_img)
            if src_arr is None: continue
            
            # If source image has different size, we skip or handle (here we assume matching sizes)
            if src_arr.shape[0] != num_pixels:
                logger.warning(f"Packing size mismatch: {src_img.name} vs {target_img.name}")
                continue
            
            # Take the luminance or the first channel (R) as data
            # For grayscale images, R=G=B, so src_arr[:, 0] is enough
            result_arr[:, idx] = src_arr[:, 0]
            any_packed = True
            
        if any_packed:
            target_img.pixels.foreach_set(result_arr.ravel())
            return True
            
        return False
    except Exception as e:
        logger.error(f"Channel Packing Failed: {e}")
        return False

def generate_optimized_colors(count, start_color=(1,0,0,1), iterations=0, manual_start=True, seed=0) :
    """Generate distinct colors for ID maps."""
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
    """
    Generate mesh attributes (Vertex Colors) for ID Maps using BMesh or NumPy.
    """
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
        
        # Safe indexing
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

    # --- Islands (BMesh) ---
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        
        if len(bm.faces) == 0:
            bm.free()
            return None
        
        islands = [] 
        # Reset tags
        for f in bm.faces: f.tag = 0
        visited_tag = 1

        if id_type == 'ELEMENT':
            try:
                # Fast C-based island finding
                res = bmesh.ops.find_adjacent_mesh_islands(bm, faces=bm.faces[:])
                islands = res.get('faces', res.get('regions', []))
            except Exception as e:
                logger.warning(f"BMesh island op failed: {e}")
                islands = []
        
        # Fallback / Other modes
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
                        if id_type == 'SEAM' and edge.seam: continue
                        for other_f in edge.link_faces:
                            if other_f.tag == visited_tag: continue
                            
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
