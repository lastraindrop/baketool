
"""UDIM tile detection and packing tests."""
import unittest
import bpy
import os
import sys
import numpy as np

# Ensure addon is in path
addon_dir = os.path.dirname(os.path.dirname(__file__))
if addon_dir not in sys.path:
    sys.path.append(addon_dir)

from baketool.test_cases.helpers import cleanup_scene, create_test_object
from baketool.core.uv_manager import detect_object_udim_tile, UDIMPacker

class SuiteUDIMAdvanced(unittest.TestCase):
    def setUp(self):
        cleanup_scene()

    def test_udim_detection_logic(self):
        """Test detection of UDIM tiles based on UV coordinates."""
        obj = create_test_object("UDIMObj")
        uv_layer = obj.data.uv_layers.active

        # Test 1001 (Default)
        self.assertEqual(detect_object_udim_tile(obj), 1001)

        # Move UVs to 1002 (U + 1)
        uvs = np.zeros(len(uv_layer.data) * 2, dtype=np.float32)
        uv_layer.data.foreach_get("uv", uvs)
        uvs_2d = uvs.reshape(-1, 2)
        uvs_2d[:, 0] += 1.0 # Move to U=1.x
        uv_layer.data.foreach_set("uv", uvs_2d.flatten())

        self.assertEqual(detect_object_udim_tile(obj), 1002)

        # Move UVs to 1011 (V + 1)
        uvs_2d[:, 0] -= 1.0 # Back to U=0.x
        uvs_2d[:, 1] += 1.0 # Move to V=1.x
        uv_layer.data.foreach_set("uv", uvs_2d.flatten())

        self.assertEqual(detect_object_udim_tile(obj), 1011)

    def test_udim_repack_logic(self):
        """Test UDIMPacker creates non-overlapping assignments."""
        obj1 = create_test_object("O1") # Defaults to 1001
        obj2 = create_test_object("O2") # Defaults to 1001

        assignments = UDIMPacker.calculate_repack([obj1, obj2])

        # Should assign to different tiles
        tile1 = assignments[obj1]
        tile2 = assignments[obj2]

        self.assertNotEqual(tile1, tile2, "Repack should assign unique tiles")
        self.assertIn(tile1, {1001, 1002})
        self.assertIn(tile2, {1001, 1002})

if __name__ == '__main__':
    unittest.main()
