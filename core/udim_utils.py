"""Leaf-level UDIM helpers shared without depending on UV management."""

import logging

import bpy
import numpy as np


logger = logging.getLogger(__name__)


def detect_object_udim_tile(obj: bpy.types.Object) -> int:
    """Return the dominant valid UDIM tile for an object's active UV layer."""
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
        valid = (
            (u_indices >= 0)
            & (u_indices < 10)
            & (v_indices >= 0)
            & (v_indices < 10)
        )
        if not np.any(valid):
            return 1001
        tiles = 1001 + u_indices[valid] + (v_indices[valid] * 10)
        values, counts = np.unique(tiles, return_counts=True)
        return int(values[np.argmax(counts)])
    except (AttributeError, IndexError, ValueError) as error:
        logger.warning("UDIM detection failed for %s: %s", obj.name, error)
        return 1001
