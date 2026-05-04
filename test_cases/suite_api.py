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

    def tearDown(self):
        cleanup_scene()

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
        """Verify API can initialize and attempt a bake without crashing."""
        # In headless/cross-version, cli_runner.py registers the addon.
        # We just ensure BakeJobs is available before calling the API.
        if not hasattr(bpy.context.scene, "BakeJobs"):
            self.fail("BakeJobs property not registered - addon init failed")

        # Ensure we have a valid job set up
        scene = bpy.context.scene
        if not scene.BakeJobs.jobs:
            scene.BakeJobs.jobs.add()

        try:
            res = api.bake([self.obj], use_selection=False)
            # In headless mode, this might return False due to context restrictions
            self.assertIsInstance(res, bool, f"API did not return bool: {res}")
        except RuntimeError as e:
            # Poll failed errors are acceptable in headless
            self.assertIn("poll", str(e).lower(), f"Unexpected API crash: {e}")
        except Exception as e:
            self.fail(f"API crashed unexpectedly: {e}")

if __name__ == '__main__':
    unittest.main()
