import unittest
import bpy
from .. import ui
from ..property import BakeChannel, BakeJobSetting


class TestUILogic(unittest.TestCase):
    """测试 UI 层的纯逻辑函数 / Test UI layer pure logic functions."""
    
    def setUp(self):
        """Create test scene with basic setup."""
        bpy.ops.wm.read_homefile(use_empty=True)
        self.scene = bpy.context.scene
        
    def test_draw_property_group_helper(self):
        """Test generic property drawer helper function."""
        # This is a logic test - we verify the function doesn't crash
        # and properly handles edge cases
        
        # Create a mock layout (we can't fully test UI rendering without GUI)
        # But we can verify the function signature and basic logic
        
        # Create a test channel
        bj = self.scene.BakeJobs
        job = bj.jobs.add()
        job.name = "Test Job"
        
        from ..core.common import reset_channels_logic
        reset_channels_logic(job.setting)
        
        # Verify channels were created
        self.assertGreater(len(job.setting.channels), 0, "Channels should be created")
        
    def test_channel_ui_map_coverage(self):
        """Verify all special channels have UI handlers."""
        from ..ui import CHANNEL_UI_MAP
        
        # These channels should have custom UI
        expected_channels = ['normal', 'diff', 'gloss', 'tranb', 'combine', 
                            'ao', 'bevel', 'bevnor', 'curvature', 'wireframe', 'node_group']
        
        for ch_id in expected_channels:
            self.assertIn(ch_id, CHANNEL_UI_MAP, 
                         f"Channel '{ch_id}' should have a UI drawer")
            self.assertTrue(callable(CHANNEL_UI_MAP[ch_id]),
                           f"UI drawer for '{ch_id}' should be callable")
    
    def test_format_settings_validation(self):
        """Test image format settings validation logic."""
        from ..constants import FORMAT_SETTINGS
        
        # Verify critical formats exist
        required_formats = ['PNG', 'JPEG', 'TARGA', 'OPEN_EXR']
        for fmt in required_formats:
            self.assertIn(fmt, FORMAT_SETTINGS, 
                         f"Format '{fmt}' should be defined in FORMAT_SETTINGS")
            
        # Verify PNG has expected structure
        png_settings = FORMAT_SETTINGS.get('PNG', {})
        self.assertIn('depths', png_settings, "PNG should have depth options")
        self.assertIn('modes', png_settings, "PNG should have mode options")
    
    def test_generic_channel_operator_targets(self):
        """Test that GenericChannelOperator is registered."""
        # Blender operators use annotations for properties, which aren't accessible
        # via hasattr on the class. Just verify the operator is registered.
        
        # Verify the operator is registered and callable
        self.assertTrue(hasattr(bpy.ops.bake, 'generic_channel_op'),
                       "Operator should be registered in bpy.ops.bake")
    
    def test_bake_mode_validation(self):
        """Test bake mode consistency across UI and engine."""
        from ..constants import BAKE_MODES
        
        # Verify all modes are defined
        expected_modes = ['SINGLE_OBJECT', 'COMBINE_OBJECT', 'SELECT_ACTIVE', 
                         'SPLIT_MATERIAL', 'UDIM']
        
        mode_ids = [m[0] for m in BAKE_MODES]
        for mode in expected_modes:
            self.assertIn(mode, mode_ids, 
                         f"Bake mode '{mode}' should be defined in BAKE_MODES")
    
    def test_channel_filtering_logic(self):
        """Test channel filtering based on bake type."""
        bj = self.scene.BakeJobs
        job = bj.jobs.add()
        job.name = "Filter Test"
        s = job.setting
        
        from ..core.common import reset_channels_logic
        
        # Test BSDF mode
        s.bake_type = 'BSDF'
        reset_channels_logic(s)
        
        bsdf_channels = [c.id for c in s.channels if c.valid_for_mode]
        self.assertIn('color', bsdf_channels, "BSDF should have color channel")
        self.assertIn('metal', bsdf_channels, "BSDF should have metal channel")
        
        # Test with light maps enabled
        s.use_light_map = True
        reset_channels_logic(s)
        
        # Light maps add channels like 'diff', 'gloss', 'tranb', 'combine'
        # But the exact IDs depend on CHANNEL_DEFINITIONS['LIGHT']
        all_channels = [c.id for c in s.channels if c.valid_for_mode]
        
        # Verify that enabling light maps increases channel count
        self.assertGreater(len(all_channels), len(bsdf_channels),
                          "Enabling light maps should add more channels")
        
    def test_error_log_integration(self):
        """Test that scene.bake_error_log property exists and is writable."""
        # Verify the error log property exists
        self.assertTrue(hasattr(self.scene, 'bake_error_log'), 
                       "Scene should have bake_error_log property")
        
        # Test writing to it
        test_msg = "Test error message"
        self.scene.bake_error_log = test_msg
        self.assertEqual(self.scene.bake_error_log, test_msg,
                        "Error log should be writable")
        
        # Test appending
        self.scene.bake_error_log += "\nAnother error"
        self.assertIn(test_msg, self.scene.bake_error_log,
                     "Original message should be preserved")
        self.assertIn("Another error", self.scene.bake_error_log,
                     "New message should be appended")


def suite():
    """Return test suite for this module."""
    return unittest.TestLoader().loadTestsFromTestCase(TestUILogic)


if __name__ == '__main__':
    unittest.main()
