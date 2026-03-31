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

    def test_bake_operator_poll_blocks_while_baking(self):
        """Verify that the Bake Operator poll fails if a bake is already in progress."""
        from ..ops import BAKETOOL_OT_BakeOperator
        scene = bpy.context.scene
        scene.is_baking = False
        self.assertTrue(BAKETOOL_OT_BakeOperator.poll(bpy.context))
        
        scene.is_baking = True
        self.assertFalse(BAKETOOL_OT_BakeOperator.poll(bpy.context))
        scene.is_baking = False

    def test_manage_objects_smart_set_logic(self):
        """Verify the SMART_SET logic for managing bake objects."""
        scene = bpy.context.scene
        scene.BakeJobs.jobs.add()
        job = scene.BakeJobs.jobs[0]
        s = job.setting
        
        target = create_test_object("TargetObj")
        low = self.obj
        
        from ..core.common import manage_objects_logic
        manage_objects_logic(s, 'SMART_SET', [target, low], low)
        
        self.assertEqual(s.active_object, low)
        self.assertEqual(len(s.bake_objects), 1)
        self.assertEqual(s.bake_objects[0].bakeobject, target)
        
        # Cleanup
        bpy.data.objects.remove(target)

if __name__ == '__main__':
    unittest.main()
