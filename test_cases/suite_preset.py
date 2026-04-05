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

    def tearDown(self):
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
        from ..constants import BAKE_CHANNEL_INFO
        from ..core import compat
        builder = JobBuilder("ChannelTest").type('BSDF')
        s = builder.setting
        channel_ids = [c.id for c in s.channels if c.valid_for_mode]
        bsdf_key = 'BSDF_4' if (compat.is_blender_4() or compat.is_blender_5()) else 'BSDF_3'
        required = [ch['id'] for ch in BAKE_CHANNEL_INFO[bsdf_key] if ch.get('defaults', {}).get('enabled')]
        for req in required:
            self.assertIn(req, channel_ids, f"Missing required channel: {req}")

    def test_channel_reset_basic_populates_channels(self):
        """Verify reset_channels_logic populates correct channels for BASIC type."""
        from ..constants import BAKE_CHANNEL_INFO
        builder = JobBuilder("BasicTest").type('BASIC')
        s = builder.setting
        channel_ids = [c.id for c in s.channels if c.valid_for_mode]
        required = [ch['id'] for ch in BAKE_CHANNEL_INFO['BASIC'] if ch.get('defaults', {}).get('enabled')]
        for req in required:
            self.assertIn(req, channel_ids, f"Missing required channel: {req}")

    # --- Register/Unregister Symmetry ---
    def test_registered_scene_properties_exist(self):
        """Verify all expected Scene properties are registered."""
        scene = bpy.context.scene
        expected = ['BakeJobs', 'baked_image_results', 'baked_image_results_index',
                    'is_baking', 'bake_progress', 'bake_status', 'bake_error_log',
                    'last_test_info', 'test_pass']
        for prop in expected:
            self.assertTrue(hasattr(scene, prop), f"Missing Scene property: {prop}")

    def test_migration_conflict_keys_no_crash(self):
        """Verify that PRESET_MIGRATION_MAP conflict keys (diff_dir -> use_direct) load without crashing."""
        bj = bpy.context.scene.BakeJobs
        io = PropertyIO()
        job_name = "MigrateJob"
        data = {
            "jobs": [{
                "name": job_name,
                "setting": {
                    "diff_dir": True,
                    "gloss_dir": False,
                    "tranb_dir": True
                }
            }]
        }
        
        try:
            io.from_dict(bj, data)
            job = next((j for j in bj.jobs if j.name == job_name), None)
            self.assertIsNotNone(job)
        except Exception as e:
            self.fail(f"Migration conflict caused crash: {e}")

    def test_from_dict_channel_order_consistent(self):
        """Verify that loading from dict maintains consistent channel order."""
        bj = bpy.context.scene.BakeJobs
        io = PropertyIO()
        bj.jobs.add()
        job = bj.jobs[-1]
        job.setting.bake_type = 'BSDF'
        reset_channels_logic(job.setting)
        orig_ids = [c.id for c in job.setting.channels]
        data = io.to_dict(bj)
        bj.jobs.clear()
        io.from_dict(bj, data)
        
        new_job = bj.jobs[0]
        new_ids = [c.id for c in new_job.setting.channels]
        # TB-2: Assert order is identical
        self.assertEqual(orig_ids, new_ids, "Channel order corrupted after preset roundtrip")

    def test_migration_conflict_last_value_wins(self):
        """Verify that when multiple old keys map to the same new key, the last one wins."""
        # 'diff_dir', 'gloss_dir', 'tranb_dir' all map to 'use_direct'
        data = {
            "jobs": [{
                "setting": {
                    "diff_dir": False,
                    "gloss_dir": True # This is later in alphabetical sort usually, or we check implementation
                }
            }]
        }
        bj = bpy.context.scene.BakeJobs
        io = PropertyIO()
        io.from_dict(bj, data)
        # Since gloss_dir: True was processed, use_direct should be True
        self.assertTrue(bj.jobs[0].setting.use_direct)

    def test_property_io_stats_accumulate(self):
        """Verify that stats counters increment correctly during IO."""
        io = PropertyIO()
        bj = bpy.context.scene.BakeJobs
        bj.jobs.clear()
        
        # Trigger an error by passing garbage to a simple integer property
        corrupt_data = {"jobs": [{"setting": {"res_x": "NotAnInt"}}]}
        io.from_dict(bj, corrupt_data)
        # res_x is IntProperty, setattr with string should fail and increment stats['error']
        self.assertGreater(io.stats['error'], 0)

if __name__ == '__main__':
    unittest.main()
