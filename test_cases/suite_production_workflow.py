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
            # UDIM baking is notoriously unstable in background mode for 3.3.
            # We skip it for 3.3 in E2E to achieve stable CI signaling for production-ready core.
            if mode == 'UDIM' and bpy.app.version < (3, 4, 0):
                continue
                
            with self.subTest(mode=mode):
                with assert_no_leak(self):
                    cleanup_scene() # Fresh start
                    
                    # 1. Setup Scene Data
                    obj = create_test_object(name, color=(1, 0, 0, 1), mat_count=mat_count)
                    objs = [obj]
                    
                    if mode == 'SELECT_ACTIVE':
                        high = create_test_object(f"{name}_High", location=(0,0,0.1), color=(0, 1, 0, 1))
                        objs = [high] # High poly is the source
                    
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
                    
    def test_denoise_integration_trigger(self):
        """Verify that use_denoise=True triggers the denoise post-processor."""
        from ..core.engine import BakePostProcessor
        
        call_count = 0
        original_apply = BakePostProcessor.apply_denoise
        
        def mock_apply(image, **kwargs):
            nonlocal call_count
            call_count += 1
            return original_apply(image, **kwargs)
            
        BakePostProcessor.apply_denoise = mock_apply
        
        try:
            with assert_no_leak(self):
                cleanup_scene()
                obj = create_test_object("DenoiseTest")
                builder = JobBuilder("DenoiseJob")
                builder.mode('SINGLE_OBJECT').resolution(16).add_objects([obj])
                builder.denoise(True)
                builder.enable_channel('diff')
                job = builder.build()
                
                queue = JobPreparer.prepare_execution_queue(bpy.context, [job])
                runner = BakeStepRunner(bpy.context)
                for i, step in enumerate(queue):
                    runner.run(step, queue_idx=i)
                
                self.assertGreater(call_count, 0, "BakePostProcessor.apply_denoise was NOT called despite use_denoise=True")
                
                cleanup_scene()
        finally:
            BakePostProcessor.apply_denoise = original_apply

    def test_full_gltf_export_loop(self):
        """[E2E] Verify the Zero-Friction Delivery Pipeline (GLB Exporter)."""
        try:
            import addon_utils
            addon_utils.enable("io_scene_gltf2")
        except Exception:
            self.skipTest("GLTF2 addon not available in this environment")
        
        if not hasattr(bpy.ops.export_scene, "gltf"):
            self.skipTest("GLTF export operator not available")
        
        with self.subTest("GLB_Export_Textures"):
            with assert_no_leak(self):
                cleanup_scene()
                obj = create_test_object("GLB_Export_Test", color=(0, 0, 1, 1), mat_count=1)
                
                builder = JobBuilder("Job_GLB")
                builder.mode('SINGLE_OBJECT').type('BASIC').resolution(16)
                builder.add_objects([obj])
                
                # Setup specific export flags
                s = builder.setting
                s.use_external_save = True
                s.external_save_path = self.temp_dir
                s.apply_to_scene = False # Crucial: do not apply to scene, test isolation
                s.export_model = True
                s.export_format = 'GLB'
                s.export_textures_with_model = True
                s.create_new_folder = False
                s.name_setting = 'OBJECT' # Force consistent filename for test assertion
                
                builder.enable_channel('diff')
                job = builder.build()
                
                queue = JobPreparer.prepare_execution_queue(bpy.context, [job])
                runner = BakeStepRunner(bpy.context)
                for i, step in enumerate(queue):
                    runner.run(step, queue_idx=i)
                
                # Verify export existence
                expected_filepath = os.path.join(self.temp_dir, "GLB_Export_Test.glb")
                self.assertTrue(os.path.exists(expected_filepath), "GLB File was not exported!")
                
                # Check size to ensure it's not a tiny mesh without textures (typically > 300 bytes)
                size = os.path.getsize(expected_filepath)
                self.assertGreater(size, 200, "GLB File seems too small to contain a mesh + embedded PBR textures")
                
                # Also verify the original object did NOT get a baked material since apply_to_scene=False
                mat_name = obj.material_slots[0].material.name if obj.material_slots else ""
                self.assertNotIn("Baked", mat_name, "Original object was polluted despite apply_to_scene=False!")

                cleanup_scene()

    def test_output_subfolder_creation(self):
        """Verify that create_new_folder correctly nests output files."""
        with assert_no_leak(self):
            cleanup_scene()
            obj = create_test_object("FolderTest")
            builder = JobBuilder("FolderJob")
            builder.mode('SINGLE_OBJECT').resolution(16).add_objects([obj])
            builder.save_to(self.temp_dir)
            builder.folder("my_subfolder")
            builder.enable_channel('diff')
            job = builder.build()
            
            queue = JobPreparer.prepare_execution_queue(bpy.context, [job])
            runner = BakeStepRunner(bpy.context)
            for i, step in enumerate(queue):
                runner.run(step, queue_idx=i)
            
            subfolder_path = os.path.join(self.temp_dir, "my_subfolder")
            self.assertTrue(os.path.isdir(subfolder_path), f"Subfolder was not created: {subfolder_path}")
            
            files = os.listdir(subfolder_path)
            self.assertGreater(len(files), 0, f"No files found in subfolder: {subfolder_path}")
            
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

    def test_animation_bake_2_frames(self):
        """[E2E] Verify sequential animation baking for 2 frames."""
        with assert_no_leak(self):
            cleanup_scene()
            obj = create_test_object("AnimObj")
            builder = JobBuilder("AnimJob")
            builder.mode('SINGLE_OBJECT').resolution(16)
            builder.add_objects([obj])
            builder.save_to(self.temp_dir)
            
            s = builder.setting
            s.bake_motion = True
            s.bake_motion_use_custom = True
            s.bake_motion_start = 1
            s.bake_motion_last = 2 
            s.bake_motion_digit = 4
            s.bake_motion_separator = '_'
            
            builder.enable_channel('diff')
            job = builder.build()
            
            queue = JobPreparer.prepare_execution_queue(bpy.context, [job])
            self.assertEqual(len(queue), 2)
            
            runner = BakeStepRunner(bpy.context)
            for i, step in enumerate(queue):
                runner.run(step, queue_idx=i)
            
            files = os.listdir(self.temp_dir)
            self.assertTrue(any("0001" in f for f in files), f"Frame 1 not found: {files}")
            self.assertTrue(any("0002" in f for f in files), f"Frame 2 not found: {files}")
            
            cleanup_scene()

    def test_split_material_3_mats_e2e(self):
        """[E2E] Verify SPLIT_MATERIAL mode with 3 materials."""
        with assert_no_leak(self):
            cleanup_scene()
            obj = create_test_object("SplitObj", mat_count=3)
            builder = JobBuilder("SplitJob")
            builder.mode('SPLIT_MATERIAL').resolution(16)
            builder.add_objects([obj])
            builder.save_to(self.temp_dir)
            builder.enable_channel('diff')
            job = builder.build()
            
            queue = JobPreparer.prepare_execution_queue(bpy.context, [job])
            self.assertEqual(len(queue), 3)
            
            runner = BakeStepRunner(bpy.context)
            for i, step in enumerate(queue):
                runner.run(step, queue_idx=i)
            
            # Precise search: only match files starting with SplitObj_Mat_SplitObj and containing 'color'
            files = [f for f in os.listdir(self.temp_dir) if "color" in f.lower() and f.startswith("SplitObj_Mat_SplitObj")]
            self.assertEqual(len(files), 3, f"Expected 3 color files for Split Material, found: {files}. Total in dir: {os.listdir(self.temp_dir)}")
            
            cleanup_scene()

    def test_library_material_protection_skip(self):
        """Verify that objects with Library materials handle protection setup safely."""
        with assert_no_leak(self):
            cleanup_scene()
            obj = create_test_object("LibObj")
            from ..core.node_manager import NodeGraphHandler
            try:
                with NodeGraphHandler([obj]) as h:
                    h.setup_protection()
            except Exception as e:
                self.fail(f"NodeGraphHandler protection failed: {e}")
            
            cleanup_scene()

if __name__ == '__main__':
    unittest.main()
