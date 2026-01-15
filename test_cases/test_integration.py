import unittest
import bpy
import os
import tempfile
import shutil
import numpy as np
from .helpers import cleanup_scene, create_test_object, get_job_setting
from ..core import common, uv_manager, image_manager
from .. import ops
from ..constants import CHANNEL_BAKE_INFO

class TestFullBakeIntegration(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        if os.path.exists(self.temp_dir): shutil.rmtree(self.temp_dir)

    def test_complete_bake_workflow(self):
        obj = create_test_object("Integrate_Obj", color=(1, 0, 0, 1))
        scene = bpy.context.scene
        bj = scene.BakeJobs
        bj.jobs.clear()
        job = bj.jobs.add()
        s = job.setting
        
        bo = s.bake_objects.add()
        bo.bakeobject = obj
        
        s.bake_mode = 'SINGLE_OBJECT'
        s.name_setting = 'OBJECT' 
        s.res_x, s.res_y = 64, 64
        s.save_out = True
        s.save_path = self.temp_dir
        s.save_format = 'PNG'
        s.bake_type = 'BSDF'
        
        common.reset_channels_logic(s)
        for c in s.channels:
            c.enabled = (c.id == 'color')

        # Use the same logic as BAKETOOL_OT_BakeOperator
        queue = ops.JobPreparer.prepare_execution_queue(bpy.context, [job])
        self.assertEqual(len(queue), 1)
        step = queue[0]
        
        # Call the production runner
        runner = ops.BakeStepRunner(bpy.context)
        results = runner.run(step)
        
        # 期望的图像名称 // Expected image name
        expected_img_name = f"{step.task.base_name}_color"
        
        self.assertIn(expected_img_name, bpy.data.images)
        expected_file = os.path.join(self.temp_dir, f"{expected_img_name}.png")
        self.assertTrue(os.path.exists(expected_file))

        self.assertIn(expected_img_name, bpy.data.images)
        expected_file = os.path.join(self.temp_dir, f"{expected_img_name}.png")
        self.assertTrue(os.path.exists(expected_file))

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
