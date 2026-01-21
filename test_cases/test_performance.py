import unittest
import bpy
import time
import numpy as np
from .helpers import cleanup_scene, create_test_object, JobBuilder
from ..core.math_utils import pack_channels_numpy

class TestPerformance(unittest.TestCase):
    def setUp(self):
        cleanup_scene()

    def test_numpy_packing_speed(self):
        """Benchmark NumPy channel packing vs potential loops (implicitly)."""
        res = 2048
        # Create 3 large images
        imgs = []
        for i in range(3):
            img = bpy.data.images.new(f"PerfSource_{i}", res, res)
            # Fill with some data
            pixels = np.random.random(res * res * 4).astype(np.float32)
            img.pixels.foreach_set(pixels)
            imgs.append(img)
            
        target = bpy.data.images.new("PerfTarget", res, res)
        
        start_time = time.time()
        pack_map = {0: imgs[0], 1: imgs[1], 2: imgs[2]}
        success = pack_channels_numpy(target, pack_map)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"NumPy Packing (2048x2048 x 3 channels): {duration:.4f}s")
        
        self.assertTrue(success)
        self.assertLess(duration, 1.0, "Packing should be sub-second for 2K images on most systems")

    def test_full_prep_overhead(self):
        """Measure JobPreparer overhead for a complex scene (100 objects)."""
        objs = []
        for i in range(100):
            objs.append(create_test_object(f"Obj_{i}"))
            
        job = (JobBuilder("StressPerf")
               .mode('SINGLE_OBJECT')
               .add_objects(objs)
               .enable_channel('color')
               .build())
               
        from ..core.engine import JobPreparer
        
        start_time = time.time()
        queue = JobPreparer.prepare_execution_queue(bpy.context, [job])
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"JobPreparer Prep (100 objects): {duration:.4f}s")
        
        self.assertEqual(len(queue), 100)
        self.assertLess(duration, 0.5, "Preparation for 100 objects should be very fast")

if __name__ == '__main__':
    unittest.main()