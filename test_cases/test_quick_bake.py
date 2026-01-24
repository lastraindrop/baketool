import unittest
import bpy
from .helpers import cleanup_scene, create_test_object, JobBuilder
from ..core.engine import JobPreparer

class TestQuickBake(unittest.TestCase):
    def setUp(self):
        cleanup_scene()

    def test_quick_bake_queue_generation(self):
        """Test the engine logic for Quick Bake queue generation."""
        # 1. Setup template job
        obj_ref = create_test_object("RefObj")
        job = (JobBuilder("Template")
               .mode('SINGLE_OBJECT')
               .add_objects(obj_ref)
               .enable_channel('color')
               .build())
        job.setting.name_setting = 'OBJECT'
        
        # 2. Setup selection to bake
        obj1 = create_test_object("Selection1")
        obj2 = create_test_object("Selection2")
        
        # 3. Call engine logic
        queue = JobPreparer.prepare_quick_bake_queue(
            bpy.context, 
            job, 
            selected_objects=[obj1, obj2], 
            active_object=obj1
        )
        
        # 4. Assertions
        # Should have 2 steps (one for each selected object)
        self.assertEqual(len(queue), 2)
        # Verify active object assignment in tasks
        names = [s.task.base_name for s in queue]
        self.assertIn("Selection1", names)
        self.assertIn("Selection2", names)
        
        # Ensure reference job objects were restored
        self.assertEqual(len(job.setting.bake_objects), 1)
        self.assertEqual(job.setting.bake_objects[0].bakeobject, obj_ref)

    def test_quick_bake_select_active_mode(self):
        """Test Quick Bake in Select-to-Active mode."""
        lp = create_test_object("LowPoly")
        hp = create_test_object("HighPoly")
        
        job = (JobBuilder("S2A_Template")
               .mode('SELECT_ACTIVE')
               .add_objects(lp) # Dummy
               .enable_channel('color')
               .build())
        
        # In S2A, we bake HIGH to LOW. 
        # selected = [LP, HP], active = LP
        queue = JobPreparer.prepare_quick_bake_queue(
            bpy.context,
            job,
            selected_objects=[lp, hp],
            active_object=lp
        )
        
        # Should have 1 step (HP -> LP)
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0].task.active_obj, lp)
        self.assertIn(hp, queue[0].task.objects)

    def test_quick_bake_invalid_input(self):
        """Ensure it handles None or empty inputs gracefully."""
        res = JobPreparer.prepare_quick_bake_queue(bpy.context, None, [], None)
        self.assertEqual(res, [])
