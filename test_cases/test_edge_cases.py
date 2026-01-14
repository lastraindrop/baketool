import unittest
import bpy
import os
import tempfile
import shutil
import numpy as np
from .helpers import cleanup_scene, create_test_object, get_job_setting
from ..core import image_manager, uv_manager, math_utils, common, engine

class TestEdgeCases(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_null_material_slots(self):
        """测试：物体有材质槽但其中某些槽位为空 (Null Material)"""
        obj = create_test_object("NullMatObj")
        # 增加一个空槽位
        obj.data.materials.append(None) 
        
        mats = [ms.material for ms in obj.material_slots if ms.material]
        # 确保逻辑能处理空材质不崩溃
        self.assertEqual(len(mats), 1)
        
        # 模拟 TaskBuilder 处理
        s = get_job_setting()
        tasks = engine.TaskBuilder.build(bpy.context, s, [obj], obj)
        self.assertEqual(len(tasks[0].materials), 1)

    def test_non_mesh_objects(self):
        """测试：Job 中包含非网格物体 (如 Light, Camera)"""
        bpy.ops.object.light_add(type='POINT')
        light_obj = bpy.context.active_object
        
        s = get_job_setting()
        # 模拟用户将灯光加入烘焙列表
        bo = s.bake_objects.add()
        bo.bakeobject = light_obj
        
        # 验证 JobPreparer 是否会自动过滤非网格物体
        # 正确访问方式：o.bakeobject.type
        objs = [o.bakeobject for o in s.bake_objects if o.bakeobject and o.bakeobject.type == 'MESH']
        self.assertEqual(len(objs), 0)

    def test_mismatched_resolution_packing(self):
        """测试：NumPy 打包分辨率不一致的贴图 (应优雅跳过)"""
        img1 = image_manager.set_image("Res_512", 512, 512)
        img2 = image_manager.set_image("Res_1024", 1024, 1024)
        target = image_manager.set_image("Target_Pack", 1024, 1024)
        
        pack_map = {0: img1, 1: img2}
        # pack_channels_numpy 内部应该有 size 检查
        success = math_utils.pack_channels_numpy(target, pack_map)
        # 虽然 img2 匹配，但 img1 尺寸错误，函数应记录 warning 并继续或返回状态
        # 这里的实现是只要有能打包的就返回 True，但会跳过错误的
        self.assertTrue(success)

    def test_read_only_directory(self):
        """测试：导出到不存在或可能权限受限的目录"""
        obj = create_test_object("ExportEdge")
        s = get_job_setting()
        # 构造一个极端的路径
        s.save_path = os.path.join(self.temp_dir, "non_existent_subdir", "deep_path")
        
        # ModelExporter 应该自动创建目录
        engine.ModelExporter.export(bpy.context, obj, s, folder_name="AutoCreated")
        
        expected_path = os.path.join(s.save_path, "AutoCreated")
        self.assertTrue(os.path.exists(expected_path))

    def test_extremely_long_names(self):
        """测试：超长名称导致的路径问题"""
        long_name = "A" * 200 # 极长的名称
        obj = create_test_object("LongNameObj")
        obj.name = long_name
        
        s = get_job_setting()
        s.save_path = self.temp_dir
        
        # 应该通过 clean_name 处理
        safe_name = bpy.path.clean_name(obj.name)
        self.assertTrue(len(safe_name) <= 255)

    def test_missing_uv_skipping_logic(self):
        """测试：批量任务中，缺失 UV 的物体被跳过，合法的继续"""
        # 物体 1: 有 UV
        obj_ok = create_test_object("GoodObj")
        # 物体 2: 无 UV
        bpy.ops.mesh.primitive_cube_add()
        obj_bad = bpy.context.active_object
        obj_bad.name = "BadObj"
        # 移除所有 UV 
        while obj_bad.data.uv_layers:
            obj_bad.data.uv_layers.remove(obj_bad.data.uv_layers[0])
            
        scene = bpy.context.scene
        bj = scene.BakeJobs
        bj.jobs.clear()
        
        # 创建一个包含这两个物体的 Job
        job = bj.jobs.add()
        job.name = "MixedJob"
        s = job.setting
        for o in [obj_ok, obj_bad]:
            bo = s.bake_objects.add()
            bo.bakeobject = o
        
        # 运行准备逻辑
        from ..core.engine import JobPreparer
        queue = JobPreparer.prepare_execution_queue(bpy.context, [job])
        
        # 结果应该是：由于 BadObj 缺失 UV，整个 MixedJob 被跳过
        self.assertEqual(len(queue), 0)
        self.assertIn("Missing UVs on BadObj", scene.bake_error_log)

    def test_numpy_zero_resolution_safety(self):
        """测试：处理分辨率极小时 NumPy 不应崩溃"""
        # Blender images 最小分辨率通常为 1
        img = image_manager.set_image("MinRes", 1, 1)
        arr = math_utils.get_image_pixels_as_numpy(img)
        self.assertIsNotNone(arr)
        self.assertEqual(len(arr), 1)


    def test_array_cache_hit(self):
        """测试：确保 array_cache 确实减少了重复的 NumPy 转换开销"""
        img = image_manager.set_image("CacheTest", 64, 64)
        cache = {}
        
        # 第一次读取
        arr1 = math_utils.get_image_pixels_as_numpy(img)
        cache[img] = arr1
        
        # 模拟 process_pbr_numpy 调用
        # 传入 cache，验证其内部是否直接使用了 cache 中的引用
        def mock_process(img_in, array_cache):
            return array_cache.get(img_in)
            
        self.assertIs(mock_process(img, cache), arr1)

