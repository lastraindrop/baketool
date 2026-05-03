import unittest
import bpy
import numpy as np
from .helpers import cleanup_scene, create_test_object, JobBuilder
from ..core.engine import BakePassExecutor, BakeTask
from ..core import image_manager

class SuiteCustomChannelHardened(unittest.TestCase):
    def setUp(self):
        cleanup_scene()

    def tearDown(self):
        cleanup_scene()

    def test_custom_channel_default_value_logic(self):
        """Verify that custom channels use the user-defined default_value when use_map is False."""
        obj = create_test_object("DefaultValueObj")
        job = JobBuilder("DefaultValueJob").build()
        setting = job.setting
        setting.res_x = 8
        setting.res_y = 8

        custom = job.custom_bake_channels.add()
        custom.name = "TestDefault"
        custom.bw = True
        
        # Set a specific default value (e.g., 0.75 gray)
        custom.bw_settings.use_map = False
        custom.bw_settings.default_value = 0.75

        task = BakeTask(
            objects=[obj],
            materials=[obj.material_slots[0].material],
            active_obj=obj,
            base_name="DefaultTest",
            folder_name="",
        )
        
        c_config = {
            "id": "CUSTOM",
            "name": custom.name,
            "prop": custom,
            "bake_pass": "EMIT",
            "info": {"cat": "DATA"},
            "prefix": "",
            "suffix": "_def",
        }

        # Execute bake (NumPy path)
        img = BakePassExecutor.execute(
            bpy.context,
            setting,
            task,
            c_config,
            None, # handler
            {},   # current_results
            array_cache={},
        )

        self.assertIsNotNone(img)
        arr = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
        img.pixels.foreach_get(arr)
        
        # All pixels should be 0.75 (R, G, B)
        self.assertAlmostEqual(arr[0], 0.75, places=2)
        self.assertAlmostEqual(arr[1], 0.75, places=2)
        self.assertAlmostEqual(arr[2], 0.75, places=2)
        self.assertAlmostEqual(arr[3], 1.0, places=2) # Alpha default fallback is 1.0

    def test_custom_channel_missing_source_uses_default_value(self):
        """Verify missing mapped sources fall back instead of aborting custom channel generation."""
        obj = create_test_object("MissingSourceObj")
        job = JobBuilder("MissingSourceJob").build()
        setting = job.setting
        setting.res_x = 8
        setting.res_y = 8

        custom = job.custom_bake_channels.add()
        custom.name = "MissingSource"
        custom.bw = True
        custom.bw_settings.use_map = True
        custom.bw_settings.source = "rough"
        custom.bw_settings.default_value = 0.35

        task = BakeTask(
            objects=[obj],
            materials=[obj.material_slots[0].material],
            active_obj=obj,
            base_name="MissingSourceTest",
            folder_name="",
        )

        c_config = {
            "id": "CUSTOM",
            "name": custom.name,
            "prop": custom,
            "bake_pass": "EMIT",
            "info": {"cat": "DATA"},
            "prefix": "",
            "suffix": "_missing",
        }

        img = BakePassExecutor.execute(
            bpy.context,
            setting,
            task,
            c_config,
            None,
            {},
            array_cache={},
        )

        self.assertIsNotNone(img)
        arr = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
        img.pixels.foreach_get(arr)
        self.assertAlmostEqual(arr[0], 0.35, places=2)
        self.assertAlmostEqual(arr[1], 0.35, places=2)
        self.assertAlmostEqual(arr[2], 0.35, places=2)

    def test_custom_channel_self_reference_filter(self):
        """Verify that a custom channel cannot select itself as a source."""
        from ..property import get_channel_source_items
        
        job = JobBuilder("SelfRefJob").build()
        c1 = job.custom_bake_channels.add()
        c1.name = "Channel_A"
        
        c2 = job.custom_bake_channels.add()
        c2.name = "Channel_B"
        
        # Test context for EnumProperty
        # In Blender, when get_channel_source_items is called, 'self' is the PropertyGroup
        
        # Case 1: Checking items for Channel_A's settings
        # We simulate the call by passing c1.bw_settings as 'self'
        items = get_channel_source_items(c1.bw_settings, bpy.context)
        
        item_names = [it[1] for it in items]
        self.assertIn("Channel_B", item_names)
        self.assertNotIn("Channel_A", item_names, "Channel_A should be filtered out from its own source list")
        
        # Case 2: Checking items for Channel_B's settings
        items_b = get_channel_source_items(c2.bw_settings, bpy.context)
        item_names_b = [it[1] for it in items_b]
        self.assertIn("Channel_A", item_names_b)
        self.assertNotIn("Channel_B", item_names_b, "Channel_B should be filtered out from its own source list")

if __name__ == "__main__":
    unittest.main()
