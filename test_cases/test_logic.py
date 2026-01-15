import unittest
import bpy
import os
from pathlib import Path
from .helpers import cleanup_scene, create_test_object, get_job_setting
from ..core import common, uv_manager
from .. import ops
from .. import property

class TestNamingConvention(unittest.TestCase):
    """Test file naming logic."""
    
    def setUp(self):
        cleanup_scene()
        self.obj = create_test_object("MyObject")
        self.mat = self.obj.data.materials[0]
        self.setting = get_job_setting()
        
    def test_naming_modes(self):
        self.setting.name_setting = 'OBJECT'
        name = common.get_safe_base_name(self.setting, self.obj, self.mat)
        self.assertEqual(name, "MyObject")
        
        self.setting.name_setting = 'MAT'
        name = common.get_safe_base_name(self.setting, self.obj, self.mat)
        self.assertEqual(name, self.mat.name)
        
        self.setting.name_setting = 'OBJ_MAT'
        name = common.get_safe_base_name(self.setting, self.obj, self.mat)
        self.assertEqual(name, f"MyObject_{self.mat.name}")
        
        self.setting.name_setting = 'CUSTOM'
        self.setting.custom_name = "MyCustomBake"
        name = common.get_safe_base_name(self.setting, self.obj, self.mat)
        self.assertEqual(name, "MyCustomBake")

    def test_batch_naming_split_material(self):
        self.setting.bake_mode = 'SPLIT_MATERIAL'
        self.setting.name_setting = 'CUSTOM'
        self.setting.custom_name = "Base"
        name = common.get_safe_base_name(self.setting, self.obj, self.mat, is_batch=True)
        expected = f"Base_MyObject_{self.mat.name}"
        self.assertEqual(name, expected)

class TestTaskGeneration(unittest.TestCase):
    """Test TaskBuilder logic for different bake modes."""
    
    def setUp(self):
        cleanup_scene()
        self.obj1 = create_test_object("Cube1")
        self.obj2 = create_test_object("Cube2")
        self.setting = get_job_setting()
        self.setting.bake_objects.clear()
        for o in [self.obj1, self.obj2]:
            item = self.setting.bake_objects.add()
            item.bakeobject = o
            
    def test_single_object_mode(self):
        self.setting.bake_mode = 'SINGLE_OBJECT'
        tasks = ops.TaskBuilder.build(bpy.context, self.setting, [self.obj1, self.obj2], self.obj1)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].objects, [self.obj1])
        self.assertEqual(tasks[1].objects, [self.obj2])
        
    def test_combine_object_mode(self):
        self.setting.bake_mode = 'COMBINE_OBJECT'
        tasks = ops.TaskBuilder.build(bpy.context, self.setting, [self.obj1, self.obj2], self.obj1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(set(tasks[0].objects), {self.obj1, self.obj2})
        self.assertEqual(tasks[0].active_obj, self.obj1)

class TestTaskBuilder_Logic(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        self.high = create_test_object("HighPoly")
        self.low = create_test_object("LowPoly")
        self.setting = get_job_setting()
        self.mat_high = self.high.data.materials[0]
        self.mat_low = self.low.data.materials[0]

    def test_selected_to_active_grouping(self):
        self.setting.bake_type = 'BASIC'
        self.setting.bake_mode = 'SELECT_ACTIVE'
        tasks = ops.TaskBuilder.build(
            bpy.context, 
            self.setting, 
            objects=[self.high, self.low], 
            active_obj=self.low
        )
        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        self.assertEqual(task.active_obj, self.low)
        self.assertIn(self.high, task.objects)

class TestPropertyLogic(unittest.TestCase):
    """Test dynamic property logic helpers."""
    def setUp(self):
        self.setting = get_job_setting()

    def test_valid_depths(self):
        self.setting.save_format = 'PNG'
        items = property.get_valid_depths(self.setting, None)
        keys = [i[0] for i in items]
        self.assertIn('8', keys)
        self.assertIn('16', keys)
        
        self.setting.save_format = 'OPEN_EXR'
        items = property.get_valid_depths(self.setting, None)
        keys = [i[0] for i in items]
        self.assertIn('32', keys)

class TestObjectManagement(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        self.s = get_job_setting()
        self.obj1 = create_test_object("Obj1")
        
    def test_duplicate_prevention(self):
        def add_obj_logic(setting, obj):
            for item in setting.bake_objects:
                if item.bakeobject == obj: return
            new = setting.bake_objects.add()
            new.bakeobject = obj

        add_obj_logic(self.s, self.obj1)
        self.assertEqual(len(self.s.bake_objects), 1)
        add_obj_logic(self.s, self.obj1)
        self.assertEqual(len(self.s.bake_objects), 1)

    def test_smart_set_logic(self):
        """测试 SMART_SET 操作逻辑：设置 Active 并将其他选物体加入列表"""
        obj_act = create_test_object("ActiveObj")
        obj_sel1 = create_test_object("Sel1")
        obj_sel2 = create_test_object("Sel2")
        
        # 模拟 Operator 逻辑
        self.s.bake_type = 'BASIC' # Ensure SELECT_ACTIVE is available
        self.s.bake_mode = 'SELECT_ACTIVE'
        self.s.active_object = obj_act
        self.s.bake_objects.clear()
        
        # Logic: Add all selected EXCEPT active
        selected = [obj_act, obj_sel1, obj_sel2]
        
        for o in selected:
            if o != self.s.active_object:
                new = self.s.bake_objects.add()
                new.bakeobject = o
                
        self.assertEqual(len(self.s.bake_objects), 2)
        objs = [o.bakeobject for o in self.s.bake_objects]
        self.assertIn(obj_sel1, objs)
        self.assertIn(obj_sel2, objs)
        self.assertNotIn(obj_act, objs)

class TestJobInitialization(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        if hasattr(bpy.context.scene, "BakeJobs"):
            bpy.context.scene.BakeJobs.jobs.clear()
            
    def test_add_job_defaults(self):
        bpy.ops.bake.generic_channel_op(action_type='ADD', target='jobs_channel')
        self.assertEqual(len(bpy.context.scene.BakeJobs.jobs), 1)
        job = bpy.context.scene.BakeJobs.jobs[0]
        self.assertEqual(job.setting.bake_type, 'BSDF')
        self.assertEqual(job.setting.bake_mode, 'SINGLE_OBJECT')

class TestPathSafety(unittest.TestCase):
    def test_cross_platform_path_join(self):
        base = Path("/tmp/bake")
        folder_name = "Textures"
        fname = "Test_Color.png"
        full_path = base / folder_name / fname
        self.assertTrue(len(str(full_path)) > 0)

class TestTranslationSystem(unittest.TestCase):
    def test_translation_loading(self):
        from .. import translations
        data = translations.load_translations()
        self.assertIsInstance(data, dict)
        
    def test_udim_detect(self):
        obj = create_test_object("UDIM_Test")
        # Ensure it works with direct core imports
        tile = uv_manager.detect_object_udim_tile(obj)
        self.assertEqual(tile, 1001)
