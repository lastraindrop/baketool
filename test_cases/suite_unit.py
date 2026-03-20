import unittest
import bpy
import numpy as np
from .helpers import cleanup_scene, create_test_object, get_job_setting, ensure_cycles
from ..core import image_manager, uv_manager, math_utils, common, compat
from ..core.node_manager import NodeGraphHandler

class SuiteUnit(unittest.TestCase):
    """
    Consolidated Unit Test Suite for BakeTool Core Components.
    Covers: Image Manager, UV Manager, Math Utils, Compat Layer, and Node Graph Logic.
    """
    
    @classmethod
    def setUpClass(cls):
        ensure_cycles()

    def setUp(self):
        cleanup_scene()

    # --- Image & Math Utils (from test_core.py) ---
    def test_image_setting(self):
        img = image_manager.set_image("TestImg", 64, 64, space='sRGB')
        self.assertEqual(img.size[0], 64)
        self.assertEqual(img.colorspace_settings.name, 'sRGB')

    def test_pbr_conversion_math(self):
        spec = image_manager.set_image("Mock_Spec", 16, 16, basiccolor=(0.5, 0.5, 0.5, 1.0))
        diff = image_manager.set_image("Mock_Diff", 16, 16, basiccolor=(1.0, 0.0, 0.0, 1.0))
        target = image_manager.set_image("Mock_Target", 16, 16)
        
        math_utils.process_pbr_numpy(target, spec, diff, 'pbr_conv_metal', threshold=0.04)
        arr = np.empty(16*16*4, dtype=np.float32)
        target.pixels.foreach_get(arr)
        # Verify metal calculation sanity
        self.assertGreater(np.mean(arr), 0.4)

    # --- UV & UDIM Logic ---
    def test_udim_detection(self):
        obj = create_test_object("UDIM_Obj")
        # Shift UV to 1002
        uv_layer = obj.data.uv_layers.active.data
        for loop in uv_layer: loop.uv[0] += 1.0
        self.assertEqual(uv_manager.detect_object_udim_tile(obj), 1002)

    # --- UI Config Integrity ---
    def test_ui_layout_config_integrity(self):
        from ..constants import CHANNEL_UI_LAYOUT
        from ..property import BakeChannel
        
        # Verify that all props in CHANNEL_UI_LAYOUT exist in BakeChannel or its sub-properties
        for chan_id, config in CHANNEL_UI_LAYOUT.items():
            if config.get('type') in {'PROPS', 'TOGGLES'}:
                for prop_data in config.get('props', []):
                    prop_path = prop_data[0]
                    target = BakeChannel
                    root_part = prop_path.split('.')[0]
                    # Ensure class has the attribute either directly or via annotations
                    has_prop = hasattr(target, root_part) or (hasattr(target, '__annotations__') and root_part in target.__annotations__)
                    self.assertTrue(has_prop, f"Root property '{root_part}' (from '{prop_path}') not found in {target} for channel {chan_id}")
                        # For pointer properties, testing deeper requires instances, so we skip deep validation of nested classes here

    # --- Auto-Cage 2.0 Proximity Logic ---
    def test_cage_proximity_analysis(self):
        low = create_test_object("Low")
        high = create_test_object("High", location=(0,0,0.1)) # Slightly offset
        
        # Test the utility directly
        exts = math_utils.calculate_cage_proximity(low, [high], margin=0.05)
        self.assertIsNotNone(exts)
        self.assertTrue(all(e >= 0.1 for e in exts)) # 0.1 offset + 0.05 margin

if __name__ == '__main__':
    unittest.main()
