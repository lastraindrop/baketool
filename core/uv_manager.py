import bpy
import numpy as np
import logging
from typing import Any, Dict, List, Set
from .common import safe_context_override
from ..constants import SYSTEM_NAMES

logger = logging.getLogger(__name__)


def detect_object_udim_tile(obj: bpy.types.Object) -> int:
    """Detect the dominant UDIM tile number for an object.

    Analyzes the active UV layer using NumPy to find the most common
    UDIM tile based on UV coordinates.

    Args:
        obj: Mesh object to analyze.

    Returns:
        UDIM tile number (1001-1999), defaults to 1001 if no valid tiles found.
    """
    if obj.type != "MESH" or not obj.data.uv_layers:
        return 1001

    try:
        uv_layer = obj.data.uv_layers.active
        n_loops = len(obj.data.loops)
        if n_loops == 0:
            return 1001

        uvs = np.zeros(n_loops * 2, dtype=np.float32)
        uv_layer.data.foreach_get("uv", uvs)
        uvs = uvs.reshape(-1, 2)

        u_indices = np.floor(uvs[:, 0]).astype(int)
        v_indices = np.floor(uvs[:, 1]).astype(int)

        # Valid UDIM range is 0-9 for both U and V (Standard 10x10)
        valid = (
            (u_indices >= 0) & (u_indices < 10) & (v_indices >= 0) & (v_indices < 10)
        )

        if not np.any(valid):
            logger.debug(
                f"No valid UDIM tiles found for {obj.name}, defaulting to 1001"
            )
            return 1001

        # Filter only valid indices before counting
        tiles = 1001 + u_indices[valid] + (v_indices[valid] * 10)
        vals, counts = np.unique(tiles, return_counts=True)
        return int(vals[np.argmax(counts)])
    except (ValueError, AttributeError, IndexError) as e:
        logger.warning(f"UV Detect Failed for {obj.name}: {e}")
        return 1001


def detect_object_udim_tiles(obj: bpy.types.Object) -> Set[int]:
    """Detect all UDIM tiles used by an object's active UV layer."""
    if obj.type != "MESH" or not obj.data.uv_layers:
        return {1001}

    try:
        uv_layer = obj.data.uv_layers.active
        n_loops = len(obj.data.loops)
        if n_loops == 0:
            return {1001}

        uvs = np.zeros(n_loops * 2, dtype=np.float32)
        uv_layer.data.foreach_get("uv", uvs)
        uvs = uvs.reshape(-1, 2)

        u_indices = np.floor(uvs[:, 0]).astype(int)
        v_indices = np.floor(uvs[:, 1]).astype(int)
        valid = (
            (u_indices >= 0) & (u_indices < 10) & (v_indices >= 0) & (v_indices < 10)
        )

        if not np.any(valid):
            return {1001}

        tiles = 1001 + u_indices[valid] + (v_indices[valid] * 10)
        return {int(tile) for tile in np.unique(tiles)}
    except (ValueError, AttributeError, IndexError) as e:
        logger.warning(f"UV Detect Failed for {obj.name}: {e}")
        return {1001}


def get_active_uv_udim_tiles(objects: List[bpy.types.Object]) -> List[int]:
    """Get all unique UDIM tiles used by a list of objects.

    Args:
        objects: List of mesh objects to scan.

    Returns:
        Sorted list of UDIM tile numbers.
    """
    tiles = set()
    for obj in objects:
        tiles.update(detect_object_udim_tiles(obj))
    if not tiles:
        tiles.add(1001)
    return sorted(list(tiles))


class UDIMPacker:
    """Utility class for calculating optimal UDIM tile layouts."""

    @staticmethod
    def calculate_repack(
        objects: List[bpy.types.Object],
    ) -> Dict[bpy.types.Object, int]:
        """Calculate new UDIM tile assignments for objects.

        Preserves existing UDIM assignments and assigns 1001 to objects
        without UDIM tiles, avoiding conflicts.

        Args:
            objects: List of mesh objects to assign tiles to.

        Returns:
            Dict mapping objects to their assigned tile numbers.
        """
        assignments: Dict[bpy.types.Object, int] = {}
        used_tiles: set = set()
        pending_objects = []

        for obj in objects:
            current_tile = detect_object_udim_tile(obj)
            if current_tile > 1001:
                assignments[obj] = current_tile
                used_tiles.add(current_tile)
            else:
                pending_objects.append(obj)

        pending_objects.sort(key=lambda o: o.name)
        next_tile = 1001
        for obj in pending_objects:
            while next_tile in used_tiles:
                next_tile += 1
            assignments[obj] = next_tile
            used_tiles.add(next_tile)

        return assignments


class UVLayoutManager:
    """Context manager for UV layer setup and teardown during baking.

    Handles temporary UV layer creation, UV layout processing (auto-UV,
    UDIM distribution), and state restoration on exit.

    Example:
        with UVLayoutManager(objects, settings) as uv_mgr:
            # UV layers are set up and ready for baking
            pass
        # Original UV state is restored automatically
    """

    def __init__(self, objects: List[bpy.types.Object], settings: Any):
        """Initialize UV layout manager.

        Args:
            objects: List of mesh objects to manage UV layers for.
            settings: BakeJob setting object with UV/bake mode configuration.
        """
        self.objects = objects
        self.settings = settings
        self.original_states = {}
        self.temp_layer_name = SYSTEM_NAMES["TEMP_UV"]
        self.created_layers = []
        self.objects_to_skip = set()

    def __enter__(self):
        self._record_and_setup_layers()
        if self.objects_to_skip:
            names = ", ".join(sorted(obj.name for obj in self.objects_to_skip))
            raise RuntimeError(f"Cannot create temporary UV layer for: {names}")
        self._process_layout()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._restore_state()

    def _record_and_setup_layers(self):
        for obj in self.objects:
            self.original_states[obj.name] = {
                "active": obj.data.uv_layers.active_index,
                "render": next(
                    (i for i, l in enumerate(obj.data.uv_layers) if l.active_render), 0
                ),
            }

            # Check for Blender's 8 UV layer limit
            if len(obj.data.uv_layers) >= 8:
                logger.error(
                    f"Cannot create temporary UV layer: Object '{obj.name}' already has 8 UV layers. Skipping object."
                )
                self.objects_to_skip.add(obj)
                continue

            src_uv = obj.data.uv_layers.active
            new_uv = obj.data.uv_layers.new(name=self.temp_layer_name)
            if new_uv:
                new_uv.active = True
                new_uv.active_render = True
                self.created_layers.append((obj, new_uv))

    def _process_layout(self):
        s = self.settings
        if s.use_auto_uv:
            self._apply_smart_uv()
        if s.bake_mode == "UDIM":
            if s.udim_mode == "CUSTOM":
                self._distribute_udim_custom()
            elif s.udim_mode == "REPACK":
                self._distribute_udim_repack()

    def _distribute_udim_repack(self):
        assignments = UDIMPacker.calculate_repack(self.objects)
        self._apply_assignments(assignments)

    def _distribute_udim_custom(self):
        s = self.settings
        assignments = {}
        for bo in s.bake_objects:
            if bo.bakeobject and bo.bakeobject in self.objects:
                assignments[bo.bakeobject] = bo.udim_tile
        self._apply_assignments(assignments)

    def _apply_assignments(self, assignments):
        for obj, target_tile in assignments.items():
            current_tile = detect_object_udim_tile(obj)
            if current_tile == target_tile:
                continue

            t_u = (target_tile - 1001) % 10
            t_v = (target_tile - 1001) // 10
            c_u = (current_tile - 1001) % 10
            c_v = (current_tile - 1001) // 10
            off_u = t_u - c_u
            off_v = t_v - c_v

            if off_u == 0 and off_v == 0:
                continue

            uv_layer = obj.data.uv_layers.active
            if not uv_layer:
                continue

            uvs = np.zeros(len(uv_layer.data) * 2, dtype=np.float32)
            uv_layer.data.foreach_get("uv", uvs)
            uvs_2d = uvs.reshape(-1, 2)
            uvs_2d[:, 0] += off_u
            uvs_2d[:, 1] += off_v
            uv_layer.data.foreach_set("uv", uvs_2d.flatten())

    def _apply_smart_uv(self):
        if bpy.context.object and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        # HP-6: Record original selection state to prevent pollution
        prev_sel = bpy.context.selected_objects[:]
        prev_act = bpy.context.view_layer.objects.active

        try:
            if not self.objects:
                logger.warning("UVLayoutManager: No objects to apply Smart UV")
                return
            bpy.ops.object.select_all(action="DESELECT")
            for o in self.objects:
                o.select_set(True)
            bpy.context.view_layer.objects.active = self.objects[0]

            with safe_context_override(bpy.context, self.objects[0], self.objects):
                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.mesh.select_all(action="SELECT")
                bpy.ops.uv.smart_project(
                    angle_limit=self.settings.auto_uv_angle,
                    island_margin=self.settings.auto_uv_margin,
                    area_weight=0.0,
                )
                bpy.ops.object.mode_set(mode="OBJECT")
        finally:
            # Restore selection state
            try:
                bpy.ops.object.select_all(action="DESELECT")
                for o in prev_sel:
                    if o and o.name in bpy.data.objects:
                        o.select_set(True)
                if prev_act and prev_act.name in bpy.data.objects:
                    bpy.context.view_layer.objects.active = prev_act
            except (AttributeError, RuntimeError, ReferenceError) as e:
                logger.debug(
                    f"BakeNexus: Failed to restore selection in UV manager: {e}"
                )

    def _restore_state(self):
        for obj, layer in self.created_layers:
            try:
                if obj and layer and layer.name in obj.data.uv_layers:
                    obj.data.uv_layers.remove(layer)
            except (KeyError, ReferenceError, AttributeError):
                pass

        for obj_name, state in self.original_states.items():
            obj = bpy.data.objects.get(obj_name)
            if not obj or obj.type != "MESH":
                continue
            try:
                if state["active"] < len(obj.data.uv_layers):
                    obj.data.uv_layers.active_index = state["active"]
                if state["render"] < len(obj.data.uv_layers):
                    obj.data.uv_layers[state["render"]].active_render = True
            except (IndexError, KeyError, AttributeError):
                pass
