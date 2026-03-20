import unittest
import bpy
import os
import shutil
import tempfile
from .helpers import cleanup_scene, create_test_object, JobBuilder, ensure_cycles, assert_no_leak
from ..core.engine import JobPreparer, BakeStepRunner

class SuiteProductionWorkflow(unittest.TestCase):
    """
    High-level Integration Tests verifying the actual E2E engine execution.
    NO MOCK DATA. This runs the real blender bake pipeline at ultra-low res.
    """

    @classmethod
    def setUpClass(cls):
        ensure_cycles()
        cls.temp_dir = tempfile.mkdtemp(prefix="bt_test_e2e_")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)

    def setUp(self):
        cleanup_scene()
        
    def tearDown(self):
        cleanup_scene()
        
    def test_full_pipeline_execution(self):
        """
        [E2E] Run complete bake loops for major architectures.
        Verifies: Builder -> Preparer -> Runner -> Result IO.
        """
        # Test Cases: (Mode, Architecture Name, Mat Count)
        test_cases = [
            ('SINGLE_OBJECT', "Single_E2E", 1),
            ('SELECT_ACTIVE', "HiLow_E2E", 1),
            ('UDIM', "UDIM_E2E", 1),
            ('SINGLE_OBJECT', "MultiMat_E2E", 3)
        ]

        for mode, name, mat_count in test_cases:
            with self.subTest(mode=mode):
                with assert_no_leak(self):
                    cleanup_scene() # Fresh start
                    
                    # 1. Setup Scene Data
                    obj = create_test_object(name, color=(1, 0, 0, 1), mat_count=mat_count)
                    objs = [obj]
                    
                    if mode == 'SELECT_ACTIVE':
                        high = create_test_object(f"{name}_High", location=(0,0,0.1), color=(0, 1, 0, 1))
                        objs = [high] # High poly is the source
                    
                    if mode == 'UDIM':
                        # Use default UVs (0-1) which should detect as Tile 1001
                        pass
                    
                    # 2. Build Job
                    builder = JobBuilder(name)
                    builder.mode(mode).type('BASIC').resolution(32)
                    builder.add_objects(objs)
                    builder.save_to(self.temp_dir, format='PNG')
                    
                    if mode == 'UDIM':
                        builder.setting.use_udim = True
                    
                    builder.setting.name_setting = 'CUSTOM'
                    builder.setting.custom_name = name
                    
                    if mode == 'SELECT_ACTIVE':
                        builder.setting.active_object = obj # Low poly is target
                        
                    job = builder.build()
                    
                    # 3. Prepare & Execute Engine
                    queue = JobPreparer.prepare_execution_queue(bpy.context, [job])
                    self.assertGreater(len(queue), 0, f"Preparation failed for {mode}")
                    
                    runner = BakeStepRunner(bpy.context)
                    for i, step in enumerate(queue):
                        results = runner.run(step, queue_idx=i)
                        from ..core.execution import add_bake_result_to_ui
                        for res in results:
                            add_bake_result_to_ui(bpy.context, res['image'], res['type'], res['obj'], res['path'], res.get('meta'))

                    # 4. Final Assertions
                    scene = bpy.context.scene
                    self.assertGreater(len(scene.baked_image_results), 0, "No result added to UI list")
                    
                    res = scene.baked_image_results[-1]
                    self.assertEqual(res.res_x, 32)
                    self.assertIsNotNone(res.image, "Baked image is None")
                    self.assertTrue(res.duration > 0, "Duration was not tracked")
                    
                    # File existence check
                    abs_path = bpy.path.abspath(res.filepath)
                    if "<UDIM>" in abs_path:
                        found = any(os.path.exists(abs_path.replace("<UDIM>", str(t))) for t in [1001, 1002])
                        self.assertTrue(found, f"UDIM tiles not found on disk: {res.filepath}")
                    else:
                        self.assertTrue(os.path.exists(abs_path), f"File not found on disk: {res.filepath}")
                    
                    if mode != 'SELECT_ACTIVE':
                        self.assertIn(name, res.image.name)
                    
                    # Ensure cleanup happens BEFORE checking for leaks
                    cleanup_scene()

    def test_export_formats(self):
        """Verify different export formats are rendered and written correctly."""
        formats_to_test = ['PNG', 'JPEG', 'OPEN_EXR', 'TIFF']
        for fmt in formats_to_test:
            with self.subTest(format=fmt):
                with assert_no_leak(self):
                    cleanup_scene()
                    obj = create_test_object(f"Fmt_{fmt}")
                    builder = JobBuilder(f"Job_{fmt}")
                    builder.mode('SINGLE_OBJECT').type('BASIC').resolution(16)
                    builder.add_objects([obj])
                    builder.save_to(self.temp_dir, format=fmt)
                    builder.enable_channel('diff')
                    job = builder.build()
                    
                    queue = JobPreparer.prepare_execution_queue(bpy.context, [job])
                    runner = BakeStepRunner(bpy.context)
                    for i, step in enumerate(queue):
                        runner.run(step, queue_idx=i)
                    
                    files = os.listdir(self.temp_dir)
                    ext_map = {'PNG': '.png', 'JPEG': '.jpg', 'OPEN_EXR': '.exr', 'TIFF': '.tif'}
                    target_ext = ext_map.get(fmt, '.png')
                    found = any(f.endswith(target_ext) or f.endswith(target_ext + 'f') for f in files)
                    self.assertTrue(found, f"Output file for format {fmt} not generated. Dir contents: {files}")
                    
                    # Cleanup WITHIN the leak context to avoid false positives
                    cleanup_scene()

    def test_crash_recovery_resilience(self):
        with assert_no_leak(self):
            from ..state_manager import BakeStateManager
            mgr = BakeStateManager()
            mgr.finish_session()
        
        # 写入格式不正确的日志文件，验证读取时不会崩溃
        import json
        mgr._write({'invalid': 'data', 'status': 'CORRUPTED'})
        self.assertTrue(mgr.has_crash_record())
        try:
            data = mgr.read_log()
            self.assertIsNotNone(data)
            mgr.finish_session()
        except Exception as e:
            self.fail(f"State manager crashed with malformed data: {e}")

if __name__ == '__main__':
    unittest.main()
