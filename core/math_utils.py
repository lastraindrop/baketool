import bpy
import bmesh
import numpy as np
import colorsys
import logging
from typing import Dict, List, Optional, Tuple
from mathutils.bvhtree import BVHTree
from ..constants import SYSTEM_NAMES

logger = logging.getLogger(__name__)


def get_image_pixels_as_numpy(image: bpy.types.Image) -> Optional[np.ndarray]:
    """Efficiently retrieve image pixels as a NumPy array."""
    if not image:
        return None
    width, height = image.size
    num_pixels = width * height * 4
    raw_pixels = np.empty(num_pixels, dtype=np.float32)
    image.pixels.foreach_get(raw_pixels)
    return raw_pixels.reshape(-1, 4)


def _get_cached_array(img, cache=None):
    """Get image pixels as a NumPy array, with optional caching."""
    if cache is not None and img in cache:
        return cache[img]
    arr = get_image_pixels_as_numpy(img)
    if cache is not None and arr is not None:
        cache[img] = arr
    return arr


def process_pbr_numpy(
    target_img: bpy.types.Image,
    spec_img: bpy.types.Image,
    diff_img: bpy.types.Image,
    map_id: str,
    threshold: float = 0.04,
    array_cache: Optional[Dict] = None,
) -> bool:
    """Optimized PBR conversion using NumPy."""
    try:
        def get_arr(img):
            return _get_cached_array(img, array_cache)

        spec_arr = get_arr(spec_img)
        if spec_arr is None:
            return False

        spec_max = np.max(spec_arr[:, :3], axis=1)
        denom = max(1e-5, 1.0 - threshold)
        metal_mask = np.clip((spec_max - threshold) / denom, 0.0, 1.0)

        result_arr = np.zeros_like(spec_arr)
        result_arr[:, 3] = 1.0

        if map_id == "pbr_conv_metal":
            result_arr[:, 0] = metal_mask
            result_arr[:, 1] = metal_mask
            result_arr[:, 2] = metal_mask

        elif map_id == "pbr_conv_base":
            diff_arr = get_arr(diff_img)
            if diff_arr is None:
                return False
            m = metal_mask[:, np.newaxis]
            result_arr[:, :3] = diff_arr[:, :3] * (1.0 - m) + spec_arr[:, :3] * m
            result_arr[:, 3] = diff_arr[:, 3]

        target_img.pixels.foreach_set(result_arr.ravel())
        return True

    except (ValueError, AttributeError, RuntimeError) as e:
        logger.error(f"PBR Conv Failed: {e}")
        return False


def pack_channels_numpy(
    target_img: bpy.types.Image,
    channel_map: Dict[int, bpy.types.Image],
    array_cache: Optional[Dict] = None,
) -> bool:
    """Pack multiple grayscale images into RGBA channels."""
    if not target_img:
        return False

    try:
        width, height = target_img.size
        num_pixels = width * height

        result_arr = np.zeros((num_pixels, 4), dtype=np.float32)
        result_arr[:, 3] = 1.0

        def get_arr(img):
            return _get_cached_array(img, array_cache)

        any_packed = False
        for idx, src_img in channel_map.items():
            if not src_img or idx < 0 or idx > 3:
                continue
            src_arr = get_arr(src_img)
            if src_arr is None:
                continue
            if src_arr.shape[0] != num_pixels:
                continue
            result_arr[:, idx] = src_arr[:, 0]
            any_packed = True

        if any_packed:
            target_img.pixels.foreach_set(result_arr.ravel())
            return True
        return False

    except (ValueError, AttributeError, RuntimeError) as e:
        logger.error(f"Channel Packing Failed: {e}")
        return False


def generate_optimized_colors(
    count: int,
    start_color: Tuple[float, float, float, float] = (1, 0, 0, 1),
    manual_start: bool = True,
    seed: int = 0,
) -> np.ndarray:
    """Generate visually distinct colors using golden ratio distribution."""
    if count <= 0:
        return np.zeros((0, 4), dtype=np.float32)

    indices = np.arange(count, dtype=np.float32)
    golden_ratio = 0.618033988749895

    if manual_start:
        h_start, _, _ = colorsys.rgb_to_hsv(start_color[0], start_color[1], start_color[2])
        hues = (h_start + indices * golden_ratio) % 1.0
    else:
        rng = np.random.default_rng(seed)
        hues = (rng.random() + indices * golden_ratio) % 1.0

    if not manual_start:
        sats = 0.5 + rng.random(count).astype(np.float32) * 0.3
        vals = 0.8 + rng.random(count).astype(np.float32) * 0.2
    else:
        rng_sv = np.random.default_rng(seed)
        sats = 0.5 + rng_sv.random(count).astype(np.float32) * 0.3
        vals = 0.8 + rng_sv.random(count).astype(np.float32) * 0.2

    h6 = hues * 6.0
    i = np.floor(h6).astype(int)
    f = h6 - i
    p = vals * (1.0 - sats)
    q = vals * (1.0 - sats * f)
    t = vals * (1.0 - sats * (1.0 - f))

    i = i % 6
    rgb = np.zeros((count, 3), dtype=np.float32)

    m0 = i == 0
    rgb[m0] = np.stack([vals[m0], t[m0], p[m0]], axis=-1)
    m1 = i == 1
    rgb[m1] = np.stack([q[m1], vals[m1], p[m1]], axis=-1)
    m2 = i == 2
    rgb[m2] = np.stack([p[m2], vals[m2], t[m2]], axis=-1)
    m3 = i == 3
    rgb[m3] = np.stack([p[m3], q[m3], vals[m3]], axis=-1)
    m4 = i == 4
    rgb[m4] = np.stack([t[m4], p[m4], vals[m4]], axis=-1)
    m5 = i == 5
    rgb[m5] = np.stack([vals[m5], p[m5], q[m5]], axis=-1)

    colors = np.column_stack((rgb, np.ones(count, dtype=np.float32)))
    if manual_start:
        colors[0] = np.array(start_color, dtype=np.float32)

    return colors


def setup_mesh_attribute(obj, id_type="ELEMENT", start_color=(1, 0, 0, 1), manual_start=True, seed=0):
    """Generate mesh attributes for ID maps."""
    if obj.type != "MESH":
        return None
    if id_type == "ELE":
        id_type = "ELEMENT"
    attr_name = f"{SYSTEM_NAMES['ATTR_PREFIX']}{id_type}"
    if attr_name in obj.data.attributes:
        return attr_name

    current_mode = obj.mode
    if current_mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    try:
        if id_type == "MAT":
            return _setup_material_id_numpy(obj, attr_name, start_color, manual_start, seed)
        return _setup_island_id_bmesh(obj, id_type, attr_name, start_color, manual_start, seed)
    finally:
        if obj.mode != current_mode:
            try:
                bpy.ops.object.mode_set(mode=current_mode)
            except (RuntimeError, AttributeError):
                pass


def _setup_material_id_numpy(obj, attr_name, start_color, manual_start, seed):
    """Use NumPy to generate material-based ID map."""
    poly_count = len(obj.data.polygons)
    if poly_count == 0:
        return None

    mat_indices = np.zeros(poly_count, dtype=np.int32)
    obj.data.polygons.foreach_get("material_index", mat_indices)

    unique_mats = np.unique(mat_indices)
    palette = generate_optimized_colors(len(unique_mats), start_color, manual_start, seed)

    max_idx = np.max(mat_indices) if len(mat_indices) > 0 else 0
    full_palette = np.zeros((max_idx + 1, 4), dtype=np.float32)
    full_palette[unique_mats] = palette

    loop_totals = np.zeros(poly_count, dtype=np.int32)
    obj.data.polygons.foreach_get("loop_total", loop_totals)
    loop_colors = np.repeat(full_palette[mat_indices], loop_totals, axis=0)

    obj.data.attributes.new(name=attr_name, type="BYTE_COLOR", domain="CORNER")
    attr = obj.data.attributes[attr_name]
    attr.data.foreach_set("color", loop_colors.flatten())

    return attr_name


def _setup_island_id_bmesh(obj, id_type, attr_name, start_color, manual_start, seed):
    """Generate island ID attribute based on BMesh topology analysis."""
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        if len(bm.faces) == 0:
            return None

        islands = _find_islands_bmesh(bm, id_type)
        island_count = len(islands)
        palette = generate_optimized_colors(island_count, start_color, manual_start, seed)

        corner_count = len(bm.loops)
        loop_colors = np.zeros((corner_count, 4), dtype=np.float32)

        for island_idx, island_faces in enumerate(islands):
            color = palette[island_idx]
            for face in island_faces:
                for loop_index in face.loops:
                    loop_colors[loop_index] = color

        attr = obj.data.attributes.new(name=attr_name, type="BYTE_COLOR", domain="CORNER")
        attr.data.foreach_set("color", loop_colors.flatten())
        return attr_name

    finally:
        bm.free()


def _find_islands_bmesh(bm, id_type):
    """Find connected face islands in BMesh."""
    visited = set()
    islands = []

    for face in bm.faces:
        if face in visited:
            continue
        if face.material_index != 0 and id_type == "MAT":
            continue

        island_faces = []
        stack = [face]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            island_faces.append(current)

            for edge in current.edges:
                for linked in edge.link_faces:
                    if linked not in visited:
                        stack.append(linked)

        if island_faces:
            islands.append(island_faces)

    return islands


def calculate_cage_proximity(low_poly, high_polys, margin=0.0):
    """Calculate optimal cage extrusion distance for each vertex."""
    try:
        import bpy

        lp_mesh = low_poly.data
        hp_data = []

        for hp_obj in high_polys:
            if hp_obj.type != "MESH":
                continue
            try:
                depsgraph = bpy.context.evaluated_depsgraph_get()
                bm = bmesh.new()
                bm.from_object(hp_obj, depsgraph)
                bm.transform(hp_obj.matrix_world)
                hp_tree = BVHTree.FromBMesh(bm)
                hp_data.append((hp_obj, hp_tree))
                bm.free()
            except (ValueError, RuntimeError) as e:
                logger.warning(f"Could not build BVHTree for {hp_obj.name}: {e}")

        if not hp_data:
            return np.full(len(lp_mesh.vertices), margin, dtype=np.float32)

        extrusions = np.zeros(len(lp_mesh.vertices), dtype=np.float32)

        for i, v in enumerate(lp_mesh.vertices):
            world_co = low_poly.matrix_world @ v.co
            min_dist = float("inf")

            for hp_obj, hp_tree in hp_data:
                local_co = hp_obj.matrix_world.inverted() @ world_co
                _, _, _, dist = hp_tree.find_nearest(local_co)
                if dist is not None and dist < min_dist:
                    min_dist = dist

            if min_dist != float("inf"):
                extrusions[i] = min_dist + margin
            else:
                extrusions[i] = margin

        return extrusions

    except (ValueError, AttributeError, RuntimeError) as e:
        logger.error(f"Cage Proximity Analysis Failed: {e}")
        return None


class TexelDensityCalculator:
    """Calculate texel density for objects."""

    @staticmethod
    def get_mesh_density(mesh, uv_layer):
        """Calculate average texel density for a mesh."""
        try:
            uv_data = uv_layer.data
            total_uv_area = 0.0
            for loop in uv_data:
                x1, y1 = loop.uv
                total_uv_area += abs(x1 * (loop[1].uv.y - loop[2].uv.y))

            world_area = sum(
                poly.area for poly in mesh.polygons if poly.select
            )

            if world_area <= 1e-6 or total_uv_area <= 1e-6:
                return 0.0

            res = mesh.uv_layers.active.name
            avg_res = float(res) if isinstance(res, (int, float)) else 1024.0
            return (avg_res * total_uv_area) / world_area

        except Exception:
            return 0.0