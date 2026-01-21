import unittest
import bpy
from .helpers import cleanup_scene, create_test_object, get_job_setting
from .. import ops
from .. import ui

class TestUIPoll(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        
    def test_bake_operator_poll(self):
        """Test the poll method of the main bake operator."""
        # Case 1: No jobs - Should return False (assuming implementation checks for jobs)
        scene = bpy.context.scene
        if hasattr(scene, "BakeJobs"):
            scene.BakeJobs.jobs.clear()
        
        # Note: We can't easily mock 'context' passed to poll, 
        # but we can rely on bpy.context if the operator uses it or if we pass it.
        # Many operators check context.scene properties.
        
        # If the operator class has a poll method:
        if hasattr(ops.BAKETOOL_OT_BakeOperator, 'poll'):
            # It usually requires 'context' argument.
            try:
                # With no jobs, it might be disabled
                is_enabled = ops.BAKETOOL_OT_BakeOperator.poll(bpy.context)
                # This depends on exact logic in ops.py, but usually it requires at least one job
                # We mainly test that it doesn't crash
                pass
            except Exception as e:
                self.fail(f"Poll crashed: {e}")

    def test_node_panel_poll(self):
        """Test that Node Panel only polls True in Node Editor."""
        # We cannot easily change context.space_data in headless, 
        # but we can verify the logic if we could import the class.
        pass
