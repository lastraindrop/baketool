import unittest
import json
import os
import tempfile
import shutil
import bpy
from .. import preset_handler
from .helpers import get_job_setting, cleanup_scene

class TestPresetSystem(unittest.TestCase):
    """Test the JSON serialization/deserialization logic."""
    
    def test_property_serialization(self):
        s = get_job_setting()
        
        s.res_x = 512
        s.res_y = 2048
        s.bake_mode = 'COMBINE_OBJECT'
        s.margin = 32
        
        s.channels.clear()
        c = s.channels.add()
        c.id = 'color'
        c.enabled = True
        c.suffix = '_tested'
        
        serializer = preset_handler.PropertyIO(exclude_props={'active_channel_index'})
        data = serializer.to_dict(s)
        
        self.assertEqual(data['res_x'], 512)
        self.assertEqual(data['bake_mode'], 'COMBINE_OBJECT')
        self.assertEqual(len(data['channels']), 1)
        self.assertEqual(data['channels'][0]['suffix'], '_tested')
        
    def test_property_deserialization(self):
        s = get_job_setting()
        s.channels.clear()
        
        payload = {
            "res_x": 128,
            "bake_type": "BSDF",
            "channels": [
                {"id": "normal", "name": "Normal Test", "enabled": True}
            ]
        }
        
        serializer = preset_handler.PropertyIO()
        serializer.from_dict(s, payload)
        
        self.assertEqual(s.res_x, 128)
        self.assertEqual(len(s.channels), 1)
        self.assertEqual(s.channels[0].id, 'normal')
        self.assertTrue(s.channels[0].enabled)

    def test_readonly_skipping(self):
        s = get_job_setting()
        payload = {"name": "Test Job", "non_existent_prop_123": 100}
        serializer = preset_handler.PropertyIO()
        serializer.from_dict(s, payload)
        self.assertEqual(serializer.stats['skipped_match'], 1)

class TestAutoLoadPreset(unittest.TestCase):
    """Test the startup preset loading mechanism."""
    
    def setUp(self):
        cleanup_scene()
        self.temp_dir = tempfile.mkdtemp()
        self.preset = os.path.join(self.temp_dir, "test_startup.json")
        
        self.prefs = None
        for mod in bpy.context.preferences.addons.keys():
            if "baketool" in mod:
                self.prefs = bpy.context.preferences.addons[mod].preferences
                break
        
        with open(self.preset, 'w') as f:
            json.dump({"jobs": [{"name": "StartupJob"}]}, f)

    def tearDown(self):
        if os.path.exists(self.temp_dir): shutil.rmtree(self.temp_dir)
        if self.prefs:
            self.prefs.auto_load = False
            self.prefs.default_preset_path = ""

    def test_handler_logic(self):
        if not self.prefs: return 
        
        from .. import load_default_preset
        
        self.prefs.auto_load = True
        self.prefs.default_preset_path = self.preset
        
        bpy.context.scene.BakeJobs.jobs.clear()
        load_default_preset(None)
        self.assertEqual(len(bpy.context.scene.BakeJobs.jobs), 1)
        self.assertEqual(bpy.context.scene.BakeJobs.jobs[0].name, "StartupJob")
        
        load_default_preset(None)
        self.assertEqual(len(bpy.context.scene.BakeJobs.jobs), 1)
