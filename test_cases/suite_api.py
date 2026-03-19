import unittest
import bpy
import os
from .helpers import cleanup_scene, create_test_object, ensure_cycles
from ..core import api

class SuiteAPI(unittest.TestCase):
    """
    Public API Contract Verification.
    Ensures that the external interface (api.py) is stable and correct.
    """
    
    def setUp(self):
        cleanup_scene()
        self.obj = create_test_object("ApiObj")

    def test_udim_detection_api(self):
        # Default 1001
        self.assertEqual(api.get_udim_tiles([self.obj]), [1001])
        
        # Shift to 1003
        uv_layer = self.obj.data.uv_layers.active.data
        for l in uv_layer:
            l.uv[0] += 2.0
        self.assertEqual(api.get_udim_tiles([self.obj]), [1003])

    def test_validation_api(self):
        # Invalid job (no objects)
        class MockJob:
            def __init__(self):
                self.name = "BadJob"
                class MockS:
                    def __init__(self): self.bake_objects = []; self.bake_mode = 'SINGLE_OBJECT'
                self.setting = MockS()
        
        res = api.validate_settings(MockJob())
        self.assertFalse(res.success)
        self.assertIn("skipped", res.message)

    def test_bake_trigger_api(self):
        # We can't actually run modal ops in background easily, but we test the entry point logic
        # if objects are valid
        res = api.bake([self.obj], use_selection=False)
        # Note: bpy.ops.bake.bake_operator() might fail if not registered
        # but the API logic should return accordingly.
        self.assertTrue(res)

if __name__ == '__main__':
    unittest.main()
