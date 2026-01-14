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
        s.name_setting = 'OBJECT' # 确保使用物体名作为基础名 // Use object name as base
        s.res_x, s.res_y = 64, 64
        s.save_out = True
        s.save_path = self.temp_dir
        s.save_format = 'PNG'
        s.bake_type = 'BSDF'
        
        common.reset_channels_logic(s)
        channels = []
        for c in s.channels:
            if c.id == 'color':
                c.enabled = True
                info = CHANNEL_BAKE_INFO.get(c.id, {})
                channels.append({
                    'id': c.id, 'name': c.name, 'prop': c, 
                    'bake_pass': info.get('bake_pass', 'EMIT'),
                    'info': info, 'prefix': c.prefix, 'suffix': c.suffix
                })
            else:
                c.enabled = False

        tasks = ops.TaskBuilder.build(bpy.context, s, [obj], obj)
        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        
        # 期望的图像名称 // Expected image name
        expected_img_name = f"{task.base_name}_color"
        
        baked_images = {}
        
        with ops.BakeContextManager(bpy.context, s):
            with common.safe_context_override(bpy.context, task.active_obj, task.objects):
                with uv_manager.UVLayoutManager(task.objects, s):
                    with ops.NodeGraphHandler(task.materials) as handler:
                        handler.setup_protection(task.objects, task.materials)
                        for c_config in channels:
                            img = ops.BakePassExecutor.execute(s, task, c_config, handler, baked_images)
                            if img:
                                baked_images[c_config['id']] = img
                                image_manager.save_image(img, s.save_path, file_format=s.save_format, save=True)

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
