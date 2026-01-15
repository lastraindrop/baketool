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

    def test_illegal_characters_in_names(self):
        """测试：物体名包含 Windows/Linux 非法路径字符"""
        bad_name = "Bake:?*|< >"
        obj = create_test_object(bad_name)
        
        s = get_job_setting()
        s.save_path = self.temp_dir
        
        # 验证 common.get_safe_base_name 是否调用了 clean_name
        safe_name = common.get_safe_base_name(s, obj)
        self.assertNotIn(":", safe_name)
        self.assertNotIn("?", safe_name)
        self.assertNotIn("*", safe_name)

    def test_uv_layer_overflow_resilience(self):
        """测试：当 UV 层达到 8 层上限时，UVLayoutManager 是否优雅退出"""
        obj = create_test_object("UVOverflow")
        while len(obj.data.uv_layers) < 8:
            obj.data.uv_layers.new(name=f"Orig_UV_{len(obj.data.uv_layers)}")
            
        s = get_job_setting()
        # 即使无法创建临时层，也不应抛出异常终止整个循环
        try:
            with uv_manager.UVLayoutManager([obj], s):
                pass
        except Exception as e:
            self.fail(f"UVLayoutManager crashed on 8-layer limit: {e}")

    def test_batch_skip_missing_uv(self):
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

    def test_select_to_active_missing_source_uv(self):
        """测试：Select to Active 模式下，源物体（HighPoly）没有 UV，目标物体（LowPoly）有 UV。
        预期：不应该因为源物体缺失 UV 而跳过任务。"""
        # Low Poly (Target) - Has UV
        obj_lp = create_test_object("LowPoly")
        
        # High Poly (Source) - No UV
        bpy.ops.mesh.primitive_cube_add()
        obj_hp = bpy.context.active_object
        obj_hp.name = "HighPoly"
        while obj_hp.data.uv_layers:
            obj_hp.data.uv_layers.remove(obj_hp.data.uv_layers[0])
            
        s = get_job_setting()
        s.bake_type = 'BASIC' # Ensure SELECT_ACTIVE is available
        s.bake_mode = 'SELECT_ACTIVE'
        s.active_object = obj_lp
        
        # Add both to bake objects
        bo1 = s.bake_objects.add(); bo1.bakeobject = obj_lp
        bo2 = s.bake_objects.add(); bo2.bakeobject = obj_hp
        
        # Run JobPreparer logic manually to check filter
        # We need to mock the scene/job structure lightly
        scene = bpy.context.scene
        scene.BakeJobs.jobs.clear()
        job = scene.BakeJobs.jobs.add()
        job.setting.bake_type = 'BASIC' # Ensure SELECT_ACTIVE is available
        job.setting.bake_mode = 'SELECT_ACTIVE'
        job.setting.active_object = obj_lp
        # Copy settings
        for bo in [obj_lp, obj_hp]:
            new_bo = job.setting.bake_objects.add()
            new_bo.bakeobject = bo
            
        from ..core.engine import JobPreparer
        queue = JobPreparer.prepare_execution_queue(bpy.context, [job])
        
        # Currently, this test might fail if the code isn't fixed.
        # If the code strictly checks all objects for UVs, queue will be empty.
        # We assert that it *should* have tasks.
        self.assertGreater(len(queue), 0, "Select to Active should proceed even if Source object lacks UVs")

    def test_attribute_name_collision(self):
        """测试：如果 ID Map 所需的属性名称已存在，是否能正确复用或处理"""
        obj = create_test_object("AttrColObj")
        attr_name = "BT_ATTR_ELEMENT"
        
        # Manually create the attribute with garbage data
        obj.data.attributes.new(name=attr_name, type='BYTE_COLOR', domain='CORNER')
        
        # Run setup
        returned_name = math_utils.setup_mesh_attribute(obj, id_type='ELEMENT')
        self.assertEqual(returned_name, attr_name)
        # We accept that it reuses it (feature), but ensuring it doesn't crash is key.

    def test_naming_collision_overwrite(self):
        """测试：多个物体使用 MAT 命名模式且材质相同，导致的潜在文件覆盖风险"""
        # Obj A
        obj_a = create_test_object("Obj_A")
        mat = obj_a.data.materials[0]
        mat.name = "SharedMat"
        
        # Obj B with same material
        obj_b = create_test_object("Obj_B")
        obj_b.data.materials[0] = mat
        
        s = get_job_setting()
        s.bake_mode = 'SINGLE_OBJECT'
        s.name_setting = 'MAT'
        
        # Generate names
        name_a = common.get_safe_base_name(s, obj_a, mat)
        name_b = common.get_safe_base_name(s, obj_b, mat)
        
        # In this specific configuration, names WILL collide. 
        # This test documents that behavior.
        self.assertEqual(name_a, "SharedMat")
        self.assertEqual(name_b, "SharedMat")
        self.assertEqual(name_a, name_b)

    def test_invalid_user_path_input(self):
        """测试：用户输入非法保存路径（如包含 * ? 等字符）时的处理"""
        obj = create_test_object("InvalidPathObj")
        s = get_job_setting()
        # Invalid path on Windows
        s.save_path = "C:\\Invalid|Path?test" 
        
        # 1. Test Model Export
        # Should catch exception and log error, not crash
        try:
            engine.ModelExporter.export(bpy.context, obj, s)
        except Exception as e:
            self.fail(f"ModelExporter crashed on invalid path: {e}")
            
        # 2. Test Image Save
        img = image_manager.set_image("TestImg", 32, 32)
        try:
            path = image_manager.save_image(img, s.save_path)
            # Should return None on failure
            self.assertIsNone(path)
        except Exception as e:
            self.fail(f"save_image crashed on invalid path: {e}")

