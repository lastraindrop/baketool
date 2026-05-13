
"""Scene cleanup and resource leak tests."""
import unittest
import bpy
import os
import sys

# Ensure addon is in path
addon_dir = os.path.dirname(os.path.dirname(__file__))
if addon_dir not in sys.path:
    sys.path.append(addon_dir)

import baketool
from baketool.test_cases.helpers import cleanup_scene, DataLeakChecker

class SuiteCleanup(unittest.TestCase):
    def setUp(self):
        cleanup_scene()

    def test_register_unregister_idempotency(self):
        """Test that unregistering and re-registering doesn't crash or leak properties."""
        # Unregister (should be registered already by CLI runner)
        try:
            baketool.unregister()
        except Exception as e:
            self.fail(f"Unregister failed: {e}")

        # Check properties are gone
        self.assertFalse(hasattr(bpy.types.Scene, "BakeJobs"), "BakeJobs property should be removed")

        # Register again
        try:
            baketool.register()
        except Exception as e:
            self.fail(f"Register failed: {e}")

        # Check properties exist
        self.assertTrue(hasattr(bpy.types.Scene, "BakeJobs"), "BakeJobs property should be restored")

    def test_thumbnail_cleanup(self):
        """Test that all preview collections are cleared on unregister."""
        from baketool.core import thumbnail_manager
        # Ensure a collection exists
        thumbnail_manager.get_preview_collection("test_leak")
        self.assertIn("test_leak", thumbnail_manager.preview_collections)

        # Unregister
        baketool.unregister()

        # Check collections are gone
        self.assertEqual(len(thumbnail_manager.preview_collections), 0, "All preview collections should be cleared on unregister")

        # Restore for other tests
        baketool.register()

if __name__ == '__main__':
    unittest.main()
