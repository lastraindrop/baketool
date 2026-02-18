import unittest
import bpy
import os
import tempfile
import shutil
import numpy as np
from .helpers import cleanup_scene, create_test_object, get_job_setting, JobBuilder, ensure_cycles
from ..core import common, uv_manager, image_manager
from .. import ops
from ..constants import CHANNEL_BAKE_INFO

class TestFullBakeIntegration(unittest.TestCase):
    def setUp(self):
        ensure_cycles()
        cleanup_scene()
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        if os.path.exists(self.temp_dir): shutil.rmtree(self.temp_dir)

    def test_complete_bake_workflow(self):
        """Test a standard single object bake workflow."""
        obj = create_test_object("Integrate_Obj", color=(1, 0, 0, 1))
        
        # Use Builder for clearer setup
        job = (JobBuilder("IntegrationJob")
               .mode('SINGLE_OBJECT')
               .type('BSDF')
               .resolution(64)
               .add_objects(obj)
               .save_to(self.temp_dir, 'PNG')
               .enable_channel('color')
               .build())
        
        # Ensure only color is enabled (Builder enables it, but let's be sure others are off if needed)
        # The builder reset logic handles defaults.

        # Use the same logic as BAKETOOL_OT_BakeOperator
        queue = ops.JobPreparer.prepare_execution_queue(bpy.context, [job])
        self.assertEqual(len(queue), 1)
        step = queue[0]
        
        # Call the production runner
        runner = ops.BakeStepRunner(bpy.context)
        runner.run(step)
        
        # Expected image name
        expected_img_name = f"{step.task.base_name}_color"
        
        self.assertIn(expected_img_name, bpy.data.images)
        expected_file = os.path.join(self.temp_dir, f"{expected_img_name}.png")
        self.assertTrue(os.path.exists(expected_file))

    def test_configuration_matrix(self):
        """Matrix test for various bake configurations to ensure stability."""
        modes = ['SINGLE_OBJECT', 'COMBINE_OBJECT']
        types = ['BSDF', 'BASIC']
        
        obj = create_test_object("MatrixObj")
        
        for mode in modes:
            for b_type in types:
                with self.subTest(mode=mode, type=b_type):
                    # Setup using Builder
                    builder = (JobBuilder(f"Matrix_{mode}_{b_type}")
                               .mode(mode)
                               .type(b_type)
                               .resolution(32)
                               .add_objects(obj)
                               .save_to(self.temp_dir))
                    
                    if mode == 'COMBINE_OBJECT':
                        obj2 = create_test_object(f"MatrixObj2_{mode}_{b_type}")
                        builder.add_objects(obj2)
                        
                    job = builder.build()
                    
                    # Execute
                    try:
                        queue = ops.JobPreparer.prepare_execution_queue(bpy.context, [job])
                        if not queue:
                            self.fail("Queue generation failed")
                        
                        runner = ops.BakeStepRunner(bpy.context)
                        for step in queue:
                            runner.run(step)
                            
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        self.fail(f"Crash in configuration {mode}/{b_type}: {e}")
                    
                    # Cleanup images to keep memory low
                    for img in list(bpy.data.images):
                        if img.users == 0: bpy.data.images.remove(img)

class TestQuickBakeLogic(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        self.obj = create_test_object("QuickObj")
        self.s = get_job_setting()
        
    def test_ephemeral_task_build(self):
        bpy.ops.object.select_all(action='DESELECT')
        self.obj.select_set(True)
        bpy.context.view_layer.objects.active = self.obj
        
        tasks = ops.TaskBuilder.build(bpy.context, self.s, [self.obj], self.obj)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(len(self.s.bake_objects), 0)

    def test_quick_bake_multi_object(self):
        """测试：Quick Bake 多选物体时的逻辑"""
        obj2 = create_test_object("QuickObj2")
        self.obj.select_set(True)
        obj2.select_set(True)
        bpy.context.view_layer.objects.active = self.obj
        
        # Mode: SINGLE_OBJECT -> Expect 2 tasks
        self.s.bake_mode = 'SINGLE_OBJECT'
        tasks = ops.TaskBuilder.build(bpy.context, self.s, [self.obj, obj2], self.obj)
        self.assertEqual(len(tasks), 2)
        
        # Mode: COMBINE_OBJECT -> Expect 1 task
        self.s.bake_mode = 'COMBINE_OBJECT'
        tasks = ops.TaskBuilder.build(bpy.context, self.s, [self.obj, obj2], self.obj)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(len(tasks[0].objects), 2)
        
        # Verify bake_objects list remains empty (ephemeral nature)
        self.assertEqual(len(self.s.bake_objects), 0)
