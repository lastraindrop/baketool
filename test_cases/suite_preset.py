import unittest
import bpy
import os
import tempfile
from .helpers import cleanup_scene, create_test_object, JobBuilder, ensure_cycles
from ..preset_handler import PropertyIO
from ..state_manager import BakeStateManager
from ..core.common import reset_channels_logic

class SuitePresetAndState(unittest.TestCase):
    """Tests for preset serialization and state management."""

    @classmethod
    def setUpClass(cls):
        ensure_cycles()

    def setUp(self):
        cleanup_scene()

    # --- Preset Roundtrip ---
    def test_preset_roundtrip(self):
        """Serialize → Deserialize → Verify consistency."""
        obj = create_test_object("PresetObj")
        builder = JobBuilder("RoundtripJob")
        builder.add_objects(obj).mode('SINGLE_OBJECT').type('BSDF')
        builder.setting.res_x = 512
        builder.setting.res_y = 256
        builder.setting.sample = 4
        builder.enable_channel('color')
        builder.enable_channel('normal')

        bj = bpy.context.scene.BakeJobs
        io = PropertyIO(exclude_props={'active_channel_index'})
        data = io.to_dict(bj)

        # Verify export
        self.assertIn('jobs', data)
        self.assertGreater(len(data['jobs']), 0)
        job_data = data['jobs'][0]
        self.assertIn('setting', job_data)
        self.assertEqual(job_data['setting']['res_x'], 512)
        self.assertEqual(job_data['setting']['res_y'], 256)

        # Clear and reimport
        bj.jobs.clear()
        self.assertEqual(len(bj.jobs), 0)

        io2 = PropertyIO()
        io2.from_dict(bj, data)

        # Verify import
        self.assertEqual(len(bj.jobs), 1)
        s = bj.jobs[0].setting
        self.assertEqual(s.res_x, 512)
        self.assertEqual(s.res_y, 256)
        self.assertEqual(s.sample, 4)

    # --- State Manager Lifecycle ---
    def test_state_manager_lifecycle(self):
        """start → update → finish → verify cleanup."""
        mgr = BakeStateManager()
        # Ensure clean start
        mgr.finish_session()

        mgr.start_session(10, "TestJob")
        self.assertTrue(mgr.has_crash_record())

        data = mgr.read_log()
        self.assertEqual(data["status"], "STARTED")
        self.assertEqual(data["total_steps"], 10)

        mgr.update_step(3, "Cube", "Normal", queue_idx=1)
        data = mgr.read_log()
        self.assertEqual(data["status"], "RUNNING")
        self.assertEqual(data["current_step"], 3)

        mgr.finish_session()
        self.assertFalse(mgr.has_crash_record())

    # --- Channel Reset Completeness ---
    def test_channel_reset_bsdf_populates_channels(self):
        """Verify reset_channels_logic populates correct channels for BSDF type."""
        builder = JobBuilder("ChannelTest").type('BSDF')
        s = builder.setting
        channel_ids = [c.id for c in s.channels if c.valid_for_mode]
        # BSDF must always include 'color', 'normal', 'rough', 'metal'
        for required in ['color', 'normal', 'rough', 'metal']:
            self.assertIn(required, channel_ids, f"Missing required channel: {required}")

    def test_channel_reset_basic_populates_channels(self):
        """Verify reset_channels_logic populates correct channels for BASIC type."""
        builder = JobBuilder("BasicTest").type('BASIC')
        s = builder.setting
        channel_ids = [c.id for c in s.channels if c.valid_for_mode]
        for required in ['diff', 'normal', 'combine']:
            self.assertIn(required, channel_ids, f"Missing required channel: {required}")

    # --- Register/Unregister Symmetry ---
    def test_registered_scene_properties_exist(self):
        """Verify all expected Scene properties are registered."""
        scene = bpy.context.scene
        expected = ['BakeJobs', 'baked_image_results', 'baked_image_results_index',
                    'is_baking', 'bake_progress', 'bake_status', 'bake_error_log',
                    'last_test_info', 'test_pass']
        for prop in expected:
            self.assertTrue(hasattr(scene, prop), f"Missing Scene property: {prop}")

if __name__ == '__main__':
    unittest.main()
