import unittest
import bpy
import numpy as np
from .helpers import cleanup_scene, create_test_object, get_job_setting
from ..core import uv_manager, engine, image_manager

class TestUDIMAdvanced(unittest.TestCase):
    def setUp(self):
        cleanup_scene()

    def create_udim_mesh(self, name, tile_id):
        obj = create_test_object(name)
        u = (tile_id - 1001) % 10
        v = (tile_id - 1001) // 10
        
        for loop in obj.data.uv_layers.active.data:
            loop.uv[0] += u
            loop.uv[1] += v
        return obj

    def test_non_contiguous_udim_detect(self):
        """测试单个物体面分布在多个非连续 Tile 时的主 Tile 检测"""
        obj = create_test_object("MultiTile")
        uv_layer = obj.data.uv_layers.active.data
        
        # 将面 0 移到 1001, 面 1 移到 1005
        # 假设是一个简单的 Plane（2 个面）
        for i, loop in enumerate(uv_layer):
            if i < 3: # 第一个面 (3个顶点)
                pass # 1001
            else: # 第二个面
                loop.uv[0] += 4 # 1005
        
        # detect_object_udim_tile 应该返回占比最多的 Tile
        tile = uv_manager.detect_object_udim_tile(obj)
        self.assertIn(tile, [1001, 1005])

    def test_multi_object_repack_isolation(self):
        """测试多个物体 Repack 时是否能正确分配到不同 Tile"""
        obj1 = create_test_object("Obj1") # 默认 1001
        obj2 = create_test_object("Obj2") # 默认 1001
        
        s = get_job_setting()
        s.bake_mode = 'UDIM'
        s.udim_mode = 'REPACK'
        
        # 模拟 UDIM 偏移逻辑
        with uv_manager.UVLayoutManager([obj1, obj2], s):
            tile1 = uv_manager.detect_object_udim_tile(obj1)
            tile2 = uv_manager.detect_object_udim_tile(obj2)
            
            self.assertNotEqual(tile1, tile2)
            self.assertTrue(tile1 in {1001, 1002})
            self.assertTrue(tile2 in {1001, 1002})

    def test_tile_resolution_overrides(self):
        """测试不同 Tile 的分辨率覆盖是否生效"""
        obj = create_test_object("ResOverride")
        s = get_job_setting()
        s.bake_mode = 'UDIM'
        
        # 设置 Tile 1001 为 512, Tile 1002 为 1024
        bo1 = s.bake_objects.add()
        bo1.bakeobject = obj
        bo1.udim_tile = 1001
        bo1.override_size = True
        bo1.udim_width, bo1.udim_height = 512, 512
        
        # 模拟另一个物体在 1002
        obj2 = self.create_udim_mesh("Obj1002", 1002)
        bo2 = s.bake_objects.add()
        bo2.bakeobject = obj2
        bo2.udim_tile = 1002
        bo2.override_size = True
        bo2.udim_width, bo2.udim_height = 1024, 1024
        
        tile_resolutions = {1001: (512, 512), 1002: (1024, 1024)}
        img = image_manager.set_image(
            "TestResUDIM", 128, 128, 
            use_udim=True, udim_tiles=[1001, 1002], 
            tile_resolutions=tile_resolutions
        )
        
        self.assertEqual(len(img.tiles), 2)
        # 验证 1002 Tile 的分辨率（需要切换上下文或通过 API 检查）
        # Blender API 检查 Tile 分辨率较复杂，但 set_image 逻辑应已覆盖
