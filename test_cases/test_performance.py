import unittest
import time
import bpy
import numpy as np
from .helpers import cleanup_scene
from ..core import math_utils, image_manager

class TestPerformance(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        self.report_data = []

    def log_perf(self, task_name, duration, details=""):
        res = f"| {task_name:<30} | {duration:>10.4f}s | {details}"
        self.report_data.append(res)
        print(res)

    def test_numpy_color_gen_scaling(self):
        """测试向量化颜色生成的性能随规模增长的变化"""
        print("\n--- Performance: ID Color Generation ---")
        counts = [100, 1000, 10000]
        for count in counts:
            start = time.perf_counter()
            colors = math_utils.generate_optimized_colors(count)
            end = time.perf_counter()
            self.log_perf(f"Gen {count} ID Colors", end - start, f"Array shape: {colors.shape}")
            self.assertEqual(len(colors), count)

    def test_channel_packing_performance(self):
        """测试不同分辨率下 NumPy 通道打包的性能"""
        print("\n--- Performance: Channel Packing (NumPy) ---")
        resolutions = [1024, 2048, 4096]
        
        for res in resolutions:
            # Prepare mock images
            img_r = image_manager.set_image(f"R_{res}", res, res, basiccolor=(1,0,0,1))
            img_g = image_manager.set_image(f"G_{res}", res, res, basiccolor=(0,1,0,1))
            img_b = image_manager.set_image(f"B_{res}", res, res, basiccolor=(0,0,1,1))
            target = image_manager.set_image(f"Target_{res}", res, res)
            
            pack_map = {0: img_r, 1: img_g, 2: img_b}
            cache = {}
            
            start = time.perf_counter()
            success = math_utils.pack_channels_numpy(target, pack_map, array_cache=cache)
            end = time.perf_counter()
            
            self.assertTrue(success)
            self.log_perf(f"Pack ORM {res}x{res}", end - start, f"Pixels: {res*res/1e6:.1f}M")

    def test_pbr_conversion_performance(self):
        """测试 PBR 转换（Specular -> Metallic/BaseColor）的性能"""
        print("\n--- Performance: PBR Conversion (NumPy) ---")
        res = 2048
        spec = image_manager.set_image("Spec_Perf", res, res, basiccolor=(0.5, 0.5, 0.5, 1.0))
        diff = image_manager.set_image("Diff_Perf", res, res, basiccolor=(0.8, 0.1, 0.1, 1.0))
        target = image_manager.set_image("Target_Perf", res, res)
        
        start = time.perf_counter()
        success = math_utils.process_pbr_numpy(target, spec, diff, 'pbr_conv_metal', array_cache={})
        end = time.perf_counter()
        
        self.assertTrue(success)
        self.log_perf(f"PBR Conv Metal {res}x{res}", end - start)

    @classmethod
    def tearDownClass(cls):
        print("\n" + "="*60)
        print(f"{'Performance Task':<32} | {'Time':<11} | Notes")
        print("-" * 60)