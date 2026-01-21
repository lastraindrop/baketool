import unittest
import bpy
import os
import tempfile
import shutil
import time
from .helpers import cleanup_scene, create_test_object, JobBuilder
from ..core import engine, image_manager

class TestStressScenarios(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            try: shutil.rmtree(self.temp_dir)
            except: pass

    def test_high_object_count_performance(self):
        """Stress test: 100 objects in a single job."""
        objs = []
        for i in range(100):
            objs.append(create_test_object(f"Stress_{i}"))
        
        job = (JobBuilder("HighCount")
               .mode('COMBINE_OBJECT')
               .add_objects(objs)
               .resolution(32)
               .build())
        
        start_time = time.time()
        queue = engine.JobPreparer.prepare_execution_queue(bpy.context, [job])
        prep_time = time.time() - start_time
        
        self.assertEqual(len(queue), 1)
        # Preparation for 100 objects should be fast (< 1s usually)
        self.assertLess(prep_time, 2.0, f"Preparation too slow: {prep_time:.2f}s")

    def test_deep_material_slots_stress(self):
        """Stress test: Object with many material slots (some null)."""
        obj = create_test_object("MultiMat", mat_count=20)
        # Add some empty slots
        for i in range(5):
            obj.data.materials.append(None)
            
        job = (JobBuilder("DeepMat")
               .add_objects(obj)
               .build())
        
        queue = engine.JobPreparer.prepare_execution_queue(bpy.context, [job])
        self.assertGreater(len(queue), 0)
        
        runner = engine.BakeStepRunner(bpy.context)
        # Just run the setup logic part if possible, or a full small bake
        # We'll run one pass to ensure NodeGraphHandler doesn't choke
        runner.run(queue[0])

    def test_massive_path_depth(self):
        """Stress test: Very deep folder structures for export."""
        obj = create_test_object("DeepPathObj")
        deep_path = self.temp_dir
        for i in range(10):
            deep_path = os.path.join(deep_path, f"level_{i}")
            
        job = (JobBuilder("PathStress")
               .add_objects(obj)
               .save_to(deep_path)
               .build())
        
        # Manually trigger export
        engine.ModelExporter.export(bpy.context, obj, job.setting, folder_name="EndNode")
        
        final_file = os.path.join(deep_path, "EndNode", "DeepPathObj.fbx")
        self.assertTrue(os.path.exists(final_file), "Deep path export failed")

    def test_concurrent_job_preparations(self):
        """Test preparing multiple jobs at once."""
        jobs = []
        for i in range(5):
            obj = create_test_object(f"Concurrent_{i}")
            jobs.append(JobBuilder(f"Job_{i}").add_objects(obj).build())
            
        queue = engine.JobPreparer.prepare_execution_queue(bpy.context, jobs)
        self.assertEqual(len(queue), 5)

    def test_select_active_with_heavy_sources(self):
        """Test Select to Active with 10 high poly source objects."""
        target = create_test_object("LowPolyTarget")
        sources = []
        for i in range(10):
            s = create_test_object(f"HighPolySource_{i}")
            sources.append(s)
            
        job = (JobBuilder("S2A_Heavy")
               .mode('SELECT_ACTIVE')
               .add_objects(sources + [target])
               .build())
        job.setting.active_object = target
        
        queue = engine.JobPreparer.prepare_execution_queue(bpy.context, [job])
        self.assertEqual(len(queue), 1)
        self.assertEqual(len(queue[0].task.objects), 11)
