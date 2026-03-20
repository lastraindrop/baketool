import unittest
import bpy
from .helpers import cleanup_scene, create_test_object
from ..ui import BAKE_PT_BakePanel
from ..constants import UI_MESSAGES

class SuiteUILogic(unittest.TestCase):
    """
    Tests for UI Poll functions and display logic.
    Uses mock context where necessary.
    """
    
    def setUp(self):
        cleanup_scene()
        self.obj = create_test_object("UIObj")

    def tearDown(self):
        cleanup_scene()

    def test_ui_message_consistency(self):
        """Ensure all expected system feedback strings exist."""
        expected_keys = [
            'NO_JOBS', 'PREP_FAILED', 'QUICK_PREP_FAILED', 'NO_OBJECTS',
            'JOB_SKIPPED_NO_OBJS', 'JOB_SKIPPED_NO_TARGET', 'JOB_SKIPPED_MISSING_UV',
            'JOB_SKIPPED_NO_MESH', 'CAGE_MISSING', 'VALIDATION_SUCCESS', 'VALIDATION_ERROR',
            'B5_SYNC_NOTICE'
        ]
        for key in expected_keys:
            self.assertIn(key, UI_MESSAGES, f"UI Message key missing: {key}")

    def test_baked_image_result_attributes(self):
        """Verify the BakedImageResult property group has expected fields."""
        scene = bpy.context.scene
        res = scene.baked_image_results.add()
        expected_attrs = [
            'name', 'filepath', 'image', 'channel_type',
            'res_x', 'res_y', 'duration', 'file_size'
        ]
        for attr in expected_attrs:
            self.assertTrue(hasattr(res, attr), f"BakedImageResult missing attribute: {attr}")
        
        # Cleanup the test result
        scene.baked_image_results.remove(len(scene.baked_image_results)-1)

if __name__ == '__main__':
    unittest.main()
