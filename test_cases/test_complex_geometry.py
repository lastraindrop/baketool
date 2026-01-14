import unittest
import bpy
import numpy as np
from .helpers import cleanup_scene, create_test_object, get_job_setting
from ..core import uv_manager, engine, image_manager

class TestComplexGeometry(unittest.TestCase):
    def setUp(self):
        cleanup_scene()

    def test_extreme_uv_layers(self):
        """测试物体拥有大量 UV 层（达到 Blender 上限 8 层）时的处理能力"""
        obj = create_test_object("ManyUVs")
        # 添加到 8 个 UV 层
        while len(obj.data.uv_layers) < 8:
            obj.data.uv_layers.new(name=f"Extra_UV_{len(obj.data.uv_layers)}")
        
        self.assertEqual(len(obj.data.uv_layers), 8)
        
        s = get_job_setting()
        s.use_auto_uv = True
        
        # 此时 UVLayoutManager 应无法创建新层并记录错误，但不应崩溃
        with uv_manager.UVLayoutManager([obj], s):
            self.assertNotIn("BT_Bake_Temp_UV", obj.data.uv_layers)

    def test_degenerate_geometry(self):
        """测试包含退化几何体（零面积面）时的 UDIM 检测"""
        bpy.ops.mesh.primitive_plane_add()
        obj = bpy.context.active_object
        # 缩放一个轴到 0 制造零面积面，但我们直接修改数据更稳健
        mesh = obj.data
        # 将所有 UV 设为 0
        for loop in mesh.uv_layers.active.data:
            loop.uv = (0, 0)
            
        # 制造一个极小且重叠的面
        tile = uv_manager.detect_object_udim_tile(obj)
        self.assertEqual(tile, 1001)

    def test_high_poly_uv_stress(self):
        """测试高面数物体下的 UV 处理性能"""
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5) # 产生约 10k 个面
        obj = bpy.context.active_object
        
        # 模拟 UDIM 偏移
        tile = uv_manager.detect_object_udim_tile(obj)
        self.assertEqual(tile, 1001)
        
        s = get_job_setting()
        s.bake_mode = 'UDIM'
        s.udim_mode = 'REPACK'
        
        # 即使在高面数下也应快速完成偏移
        with uv_manager.UVLayoutManager([obj], s):
            pass

    def test_illegal_uv_ranges(self):
        """测试 UV 坐标在非法/极端范围时的稳健性（应被过滤掉）"""
        obj = create_test_object("ExtremeUV")
        uv_layer = obj.data.uv_layers.active.data
        
        # 混合极端坐标：负值、极大值。这些点不应参与 UDIM 统计
        uv_layer[0].uv = (-10.5, -5.2)
        uv_layer[1].uv = (100.1, 50.5)
        
        # 我们给剩余的点设置一个正常的 Tile（如 1002）来验证过滤
        for i in range(2, len(uv_layer)):
            uv_layer[i].uv = (1.5, 0.5) # Tile 1002
            
        tile = uv_manager.detect_object_udim_tile(obj)
        # 应该正确识别为 1002，因为极端值被过滤了
        self.assertEqual(tile, 1002)

    def test_multi_user_mesh_data(self):
        """测试多个物体共享同一个 Mesh 数据时的处理逻辑"""
        obj1 = create_test_object("User1")
        obj2 = bpy.data.objects.new("User2", obj1.data)
        bpy.context.collection.objects.link(obj2)
        
        s = get_job_setting()
        s.bake_mode = 'SINGLE_OBJECT'
        
        # 模拟任务构建
        tasks = engine.TaskBuilder.build(bpy.context, s, [obj1, obj2], obj1)
        # 虽然共享数据，但在单物体模式下应该是两个独立的任务
        self.assertEqual(len(tasks), 2)
        self.assertIs(tasks[0].objects[0].data, tasks[1].objects[0].data)
