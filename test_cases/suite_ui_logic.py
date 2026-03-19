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

    def test_panel_poll(self):
        class MockContext:
            def __init__(self, scene, obj):
                self.scene = scene
                self.active_object = obj
                self.mode = 'OBJECT'
        
        ctx = MockContext(bpy.context.scene, self.obj)
        # Check if draw method exists as BAKE_PT_BakePanel doesn't implement custom poll
        self.assertTrue(hasattr(BAKE_PT_BakePanel, "draw"))

    def test_ui_message_consistency(self):
        # Ensure messages exist for critical keys
        self.assertIn('JOB_SKIPPED_NO_OBJS', UI_MESSAGES)
        self.assertIn('VALIDATION_SUCCESS', UI_MESSAGES)
        self.assertGreater(len(UI_MESSAGES['VALIDATION_SUCCESS']), 0)

if __name__ == '__main__':
    unittest.main()
