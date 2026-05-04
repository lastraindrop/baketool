import unittest
import bpy
import tracemalloc
from .helpers import cleanup_scene, create_test_object, MockSetting

class SuiteVerification(unittest.TestCase):
    """
    Consolidated verification suite for critical release-gating fixes.
    """

    def setUp(self):
        cleanup_scene()

    def tearDown(self):
        cleanup_scene()

    def test_fix_memory_leak_use_fake_user(self):
        """[FIX] Verify that use_fake_user is not set by default for temp images."""
        from ..core import image_manager
        img = image_manager.set_image("Verify_NoFakeUser", 64, 64)
        self.assertFalse(img.use_fake_user, "Temporary images should not use fake user by default")

        # Images with external save setting SHOULD use fake user
        mock_s = MockSetting(use_external_save=True, external_save_path="/tmp")
        img2 = image_manager.set_image("Verify_WithSetting", 64, 64, setting=mock_s)
        self.assertTrue(img2.use_fake_user)

    def test_fix_image_cleanup_delete_result(self):
        """[FIX] Verify that DeleteResult properly removes image datablocks."""
        from ..core import image_manager
        img = image_manager.set_image("Verify_DeleteImg", 64, 64)
        img_name = img.name
        
        res = bpy.context.scene.bakenexus_results.add()
        res.image = img
        bpy.context.scene.bakenexus_results_index = len(bpy.context.scene.bakenexus_results) - 1
        
        self.assertIn(img_name, bpy.data.images)
        # Use string operator call to avoid static import dependency
        bpy.ops.baketool.delete_result()
        self.assertNotIn(img_name, bpy.data.images, "Image datablock remained after deletion")

    def test_fix_numpy_memory_optimization(self):
        """[FIX] Verify memory-efficient clearing of large images."""
        from ..core import image_manager
        img = image_manager.set_image("Verify_4K", 2048, 2048) 
        tracemalloc.start()
        image_manager._physical_clear_pixels(img, (0.5, 0.5, 0.5, 1.0))
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        peak_mb = peak / 1024 / 1024
        self.assertLess(peak_mb, 100, f"Peak memory usage too high: {peak_mb:.2f}MB")

    def test_fix_ui_poll_safety(self):
        """[FIX] Verify that UI poll functions handle None space_data."""
        from ..ui import BAKE_PT_NodePanel
        class MockContext: pass
        ctx = MockContext()
        # Should return False instead of crashing with AttributeError
        self.assertFalse(BAKE_PT_NodePanel.poll(ctx))

    def test_fix_scene_settings_storage(self):
        """[FIX] Verify SceneSettingsContext stores constructor parameters."""
        from ..core import common
        ctx = common.SceneSettingsContext("scene", {"samples": 128}, bpy.context.scene)
        self.assertEqual(ctx.category, "scene")
        self.assertEqual(ctx.settings["samples"], 128)

    def test_fix_uv_layout_manager_storage(self):
        """[FIX] Verify UVLayoutManager stores constructor parameters."""
        from ..core import uv_manager
        obj = create_test_object("UVTest")
        ms = MockSetting()
        with uv_manager.UVLayoutManager([obj], ms) as m:
            self.assertEqual(m.objects, [obj])
            self.assertEqual(m.settings, ms)

if __name__ == '__main__':
    unittest.main()
