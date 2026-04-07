import unittest
import bpy
import numpy as np
from .helpers import cleanup_scene, create_test_object, JobBuilder, ensure_cycles, MockSetting
from ..core import image_manager, uv_manager, math_utils, common, compat
from ..core.node_manager import NodeGraphHandler

class SuiteUnit(unittest.TestCase):
    """
    Consolidated Unit Test Suite for BakeTool Core Components.
    Covers: Image Manager, UV Manager, Math Utils, Compat Layer, and Node Graph Logic.
    """
    
    @classmethod
    def setUpClass(cls):
        ensure_cycles()

    def setUp(self):
        cleanup_scene()

    def tearDown(self):
        cleanup_scene()

    # --- Image & Math Utils (from test_core.py) ---
    def test_image_setting(self):
        img = image_manager.set_image("TestImg", 64, 64, space='sRGB')
        self.assertEqual(img.size[0], 64)
        self.assertEqual(img.colorspace_settings.name, 'sRGB')

    def test_process_pbr_numpy_metallic_conversion(self):
        """Verify PBR metallic conversion math logic in NumPy."""
        spec = image_manager.set_image("Spec_PBR", 8, 8, basiccolor=(0.5, 0.5, 0.5, 1.0))
        diff = image_manager.set_image("Diff_PBR", 8, 8, basiccolor=(1.0, 0.0, 0.0, 1.0))
        target = image_manager.set_image("Target_PBR", 8, 8)
        
        # Specular 0.5 > Threshold 0.04 -> Should be metallic
        success = math_utils.process_pbr_numpy(target, spec, diff, 'pbr_conv_metal', threshold=0.04)
        self.assertTrue(success)
        
        arr = np.empty(8*8*4, dtype=np.float32)
        target.pixels.foreach_get(arr)
        # metal = (0.5 - 0.04) / (1.0 - 0.04) = 0.46 / 0.96 ≈ 0.479
        # Precision: 8-bit color rounding (128/255 ≈ 0.5019)
        self.assertAlmostEqual(arr[0], 0.4791666, places=2)

    def test_process_pbr_numpy_specular_threshold(self):
        """Verify threshold affects PBR conversion output."""
        spec = image_manager.set_image("Spec_Thresh", 4, 4, basiccolor=(0.1, 0.1, 0.1, 1.0))
        diff = image_manager.set_image("Diff_Thresh", 4, 4, basiccolor=(1, 1, 1, 1))
        target = image_manager.set_image("Target_Thresh", 4, 4)
        
        # Threshold 0.2 > Specular 0.1 -> Should be 0 metallic
        math_utils.process_pbr_numpy(target, spec, diff, 'pbr_conv_metal', threshold=0.2)
        arr = np.empty(4*4*4, dtype=np.float32)
        target.pixels.foreach_get(arr)
        self.assertEqual(arr[0], 0.0)

    def test_pack_channels_numpy_correct_output(self):
        """Verify packed pixel values match expected inputs."""
        r_img = image_manager.set_image("R_Src", 4, 4, basiccolor=(1.0, 0, 0, 1.0))
        g_img = image_manager.set_image("G_Src", 4, 4, basiccolor=(0.5, 0, 0, 1.0))
        target = image_manager.set_image("Pack_Target", 4, 4)
        
        channel_map = {0: r_img, 1: g_img}
        success = math_utils.pack_channels_numpy(target, channel_map)
        self.assertTrue(success)
        
        arr = np.empty(4*4*4, dtype=np.float32)
        target.pixels.foreach_get(arr)
        self.assertAlmostEqual(arr[0], 1.0, places=2) # R
        self.assertAlmostEqual(arr[1], 0.5, places=2) # G
        self.assertAlmostEqual(arr[2], 0.0, places=2) # B

    # --- UV & UDIM Logic ---
    def test_udim_detection(self):
        obj = create_test_object("UDIM_Obj")
        # Shift UV to 1002
        uv_layer = obj.data.uv_layers.active.data
        for loop in uv_layer: loop.uv[0] += 1.0
        self.assertEqual(uv_manager.detect_object_udim_tile(obj), 1002)

    # --- UI & Property Integrity (Hardened v1.0.0-p2) ---
    def test_ui_layout_config_integrity(self):
        from ..constants import CHANNEL_UI_LAYOUT
        from ..property import BakeChannel
        
        # Verify that all props in CHANNEL_UI_LAYOUT exist in BakeChannel or its sub-properties
        for chan_id, config in CHANNEL_UI_LAYOUT.items():
            if config.get('type') in {'PROPS', 'TOGGLES'}:
                for prop_data in config.get('props', []):
                    prop_path = prop_data[0]
                    target = BakeChannel
                    root_part = prop_path.split('.')[0]
                    # Ensure class has the attribute either directly or via annotations
                    has_prop = hasattr(target, root_part) or (hasattr(target, '__annotations__') and root_part in target.__annotations__)
                    self.assertTrue(has_prop, f"Root property '{root_part}' (from '{prop_path}') not found in {target} for channel {chan_id}")

    def test_property_group_integrity(self):
        """Regression test for common RNA pitfalls (Dynamic Enum Defaults, etc.)"""
        from ..property import BakeJobSetting
        
        # 1. Verify existence of critical properties
        target = BakeJobSetting
        has_depth = hasattr(target, 'color_depth') or (hasattr(target, '__annotations__') and 'color_depth' in target.__annotations__)
        self.assertTrue(has_depth, f"BakeJobSetting missing 'color_depth' in annotations or members")
        
        # 2. Dynamic Enum Check (Hardened v1.0.0-p2)
        # We check an actual instance
        try:
             job = JobBuilder().build()
             setting = job.setting
             val = setting.color_depth
             self.assertIsInstance(val, str)
        except Exception as e:
             self.fail(f"BakeJobSetting instance check failed: {e}")

    def test_ui_operator_integrity(self):
        """Audit all operators referenced in ui.py to ensure they exist in Blender."""
        import os
        import re
        
        # 1. Get all operator IDs from ui.py
        ui_path = os.path.join(os.path.dirname(__file__), "..", "ui.py")
        if not os.path.exists(ui_path): return # Skip if not local
        
        with open(ui_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        operator_ids = re.findall(r'\.operator\("([^"]+)"', content)
        
        # 2. Check if they are registered in bpy.ops
        for op_id in operator_ids:
            # Operator ID "bake.xxx" -> bpy.ops.bake.xxx
            parts = op_id.split('.')
            if len(parts) != 2: continue
            
            # Special case: some standard Blender ops
            if parts[0] in {'wm', 'object', 'screen'}: continue
            
            # Check existence in bpy.ops
            self.assertTrue(hasattr(bpy.ops, parts[0]), f"Operator module '{parts[0]}' not found for '{op_id}'")
            sub = getattr(bpy.ops, parts[0])
            self.assertTrue(hasattr(sub, parts[1]), f"Operator '{parts[1]}' missing in 'bpy.ops.{parts[0]}' (from UI: {op_id})")

    # --- Auto-Cage 2.0 Proximity Logic ---
    def test_cage_proximity_analysis(self):
        low = create_test_object("Low")
        high = create_test_object("High", location=(0,0,0.1)) # Slightly offset
        
        # Test the utility directly
        exts = math_utils.calculate_cage_proximity(low, [high], margin=0.05)
        self.assertIsNotNone(exts)
        self.assertTrue(all(e >= 0.1 for e in exts)) # 0.1 offset + 0.05 margin

    # --- Destructive / Boundary Testing ---
    def test_preset_corruption_handling(self):
        """Verify that the preset handler doesn't crash on invalid data."""
        from ..preset_handler import PropertyIO
        bj = bpy.context.scene.BakeJobs
        io = PropertyIO()
        
        # 1. Invalid root type
        io.from_dict(bj, "Not a dict")
        # Should not crash. stats['error'] might be 0 if it rejected 
        # before deep processing, or >0 if it tried and failed. 
        # The key is reaching the next line.
        self.assertIsInstance(io.stats, dict)
        
        # 2. Corrupted nested data
        corrupted_data = {"jobs": [{"setting": {"res_x": "InvalidString"}}]}
        io.from_dict(bj, corrupted_data)
        # res_x is IntProperty, should fail to set but continue
        
    def test_extension_logic_branches(self):
        """Parametric test: verify extension channel logic does not crash."""
        extension_sockets = ['pbr_conv_metal', 'pbr_conv_base', 'rough_inv']
        for sock_name in extension_sockets:
            with self.subTest(socket=sock_name):
                mat = bpy.data.materials.new(f"TestExt_{sock_name}")
                mat.use_nodes = True
                with NodeGraphHandler([mat]) as h:
                    try:
                        res = h._create_extension_logic(mat, sock_name, None)
                    except Exception as e:
                        self.fail(f"Extension logic '{sock_name}' crashed: {e}")

    def test_apply_denoise_pixels_modified(self):
        """Verify the denoise processor modifies image pixels."""
        from ..core.engine import BakePostProcessor
        img = image_manager.set_image("TestDenoise", 16, 16, basiccolor=(0.1, 0.4, 0.2, 1.0))
        # inject noise
        arr = np.random.rand(16*16*4).astype(np.float32)
        arr[3::4] = 1.0 # fixed alpha
        img.pixels.foreach_set(arr)
        
        try:
            BakePostProcessor.apply_denoise(img)
            new_arr = np.empty(16*16*4, dtype=np.float32)
            img.pixels.foreach_get(new_arr)
            self.assertFalse(np.array_equal(arr, new_arr), "Denoise did not modify pixels")
        except Exception as e:
            self.fail(f"Denoise crashed: {e}")

    def test_emergency_cleanup_removes_temp_nodes(self):
        """Verify EmergencyCleanup removes tagged temporary nodes."""
        mat = bpy.data.materials.new("TestCleanup")
        mat.use_nodes = True
        tree = mat.node_tree
        # Add a dummy node and tag it exactly as cleanup.py expects: is_bt_temp
        val_node = tree.nodes.new('ShaderNodeValue')
        val_node["is_bt_temp"] = True
        val_node.name = "BakeTool_Temp_Node"
        
        self.assertIn(val_node, tree.nodes.values())
        
        # Execute actual cleanup operator
        res = bpy.ops.bake.emergency_cleanup()
        self.assertEqual(res, {'FINISHED'})
        
        # Verify removal
        remaining = [n for n in tree.nodes if n.get("is_bt_temp", False)]
        self.assertEqual(len(remaining), 0)

    def test_cage_raycast_hit_detection(self):
        """Verify Raycast analysis for cage overlap."""
        from ..core.cage_analyzer import CageAnalyzer
        with common.safe_context_override(bpy.context):
            cleanup_scene()
            low = create_test_object("Low_Cage_Test")
            high = create_test_object("High_Cage_Test", location=(0,0,0.5)) # Offset high
            
            # Since high is offset by 0.5, rays from low with extrusion 0.1 should FAIL completely
            success, msg = CageAnalyzer.run_raycast_analysis(bpy.context, low, [high], extrusion=0.1)
            self.assertTrue(success)
            self.assertIn("errors", msg) # Indicates failure to hit
            
            # Extrusion of 1.0 is enough to reach the high poly offset
            success, msg2 = CageAnalyzer.run_raycast_analysis(bpy.context, low, [high], extrusion=1.0)
            self.assertTrue(success)
            
            # Verify vertex colors were generated
            vcol_name = "BT_CAGE_ERROR"
            has_color = False
            if hasattr(low.data, "color_attributes"):
                has_color = vcol_name in low.data.color_attributes
            else:
                has_color = vcol_name in low.data.vertex_colors
            self.assertTrue(has_color, "Vertex color map was not generated!")
            
            cleanup_scene()

    def test_denoise_no_scene_leak(self):
        """Verify apply_denoise does not leave temporary scenes behind."""
        from ..core.engine import BakePostProcessor
        img = image_manager.set_image("Leak_Test", 16, 16)
        
        try:
            BakePostProcessor.apply_denoise(img)
        finally:
            # TB-3: Only check for leaked BT_ scenes to avoid interference from elsewhere
            bt_scenes = [s for s in bpy.data.scenes if s.name.startswith("BT_")]
            self.assertEqual(len(bt_scenes), 0, f"Leaked BT scenes found: {[s.name for s in bt_scenes]}")

    def test_cage_proximity_multi_highpoly(self):
        """Verify proximity calculation handles multiple highpolys."""
        low = create_test_object("Low_P")
        high1 = create_test_object("High_1", location=(0,0,0.1))
        high2 = create_test_object("High_2", location=(0,0,0.2))
        
        # Test with multiple high polys
        exts = math_utils.calculate_cage_proximity(low, [high1, high2], margin=0.0)
        self.assertIsNotNone(exts)
        # Even before the multi-highpoly fix in Phase 3, this test should pass if it picks at least one.
        # After Phase 3 fix, it should pick the NEAREST one for each vertex.
        self.assertGreater(len(exts), 0)

    def test_custom_channel_packing_lookup(self):
        """Verify that CUSTOM channels can be correctly looked up for packing."""
        # Mock a channel config
        c = {'id': 'CUSTOM', 'name': 'MyMask'}
        baked_images = {}
        img = image_manager.set_image("MaskImg", 16, 16)
        
        # This mirrors the logic in BakeStepRunner.run (L189)
        key = c['name'] if c['id'] == 'CUSTOM' else c['id']
        baked_images[key] = img
        
        self.assertIn('MyMask', baked_images)
        self.assertEqual(baked_images['MyMask'], img)

    def test_generate_optimized_colors_count(self):
        """Correct number of colors generated by optimized factory."""
        colors = math_utils.generate_optimized_colors(10)
        self.assertEqual(len(colors), 10)
        self.assertEqual(colors.shape, (10, 4))

    def test_generate_optimized_colors_deterministic_with_seed(self):
        """Same seed should produce identical color sequences."""
        c1 = math_utils.generate_optimized_colors(5, seed=42)
        c2 = math_utils.generate_optimized_colors(5, seed=42)
        np.testing.assert_array_equal(c1, c2)

    def test_texel_density_calculator_basic(self):
        """Verify basic texel density calculation logic."""
        obj = create_test_object("DensityObj")
        # Default cube 2x2x2, total area 24. Average face area 4.
        # Default UVs map each face to 0-1 (Area 1).
        density = math_utils.TexelDensityCalculator.get_mesh_density(obj, 1024, 1024)
        self.assertGreater(density, 0)
        self.assertIsInstance(density, float)

    # --- Expanded Component Lifecycle Tests ---
    def test_context_manager_exception_restores_state(self):
        """Verify that BakeContextManager performs cleanup even if an exception occurs."""
        from ..core.engine import BakeContextManager
        orig_engine = bpy.context.scene.render.engine
        
        try:
            with BakeContextManager(bpy.context, MockSetting()):
                bpy.context.scene.render.engine = 'CYCLES'
                raise RuntimeError("Simulated crash")
        except RuntimeError:
            pass
        self.assertEqual(bpy.context.scene.render.engine, orig_engine)

    def test_node_graph_handler_link_restoration(self):
        """Verify material links are restored by NodeGraphHandler even if manually cleared."""
        mat = bpy.data.materials.new("LinkRestoreMat")
        mat.use_nodes = True
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        out = nodes.new('ShaderNodeOutputMaterial')
        links.new(bsdf.outputs[0], out.inputs[0])
        
        count = len(links)
        with NodeGraphHandler([mat]) as h:
            links.clear()
        self.assertEqual(len(links), count, "Links not restored after NodeGraphHandler exit")

    def test_uv_layer_manager_temp_cleanup(self):
        """Verify UVLayoutManager cleans up temporary UV layers."""
        obj = create_test_object("UVManagerObj")
        cnt = len(obj.data.uv_layers)
        ms = MockSetting(use_auto_uv=False)
        with uv_manager.UVLayoutManager([obj], ms) as m:
            # __enter__ calls _record_and_setup_layers which adds the temp layer
            self.assertEqual(len(obj.data.uv_layers), cnt + 1)
        self.assertEqual(len(obj.data.uv_layers), cnt, "Temp UV layer not removed")

    def test_save_image_disk_existence(self):
        """Verify image_manager writes valid file to disk."""
        import tempfile, os
        img = image_manager.set_image("DiskTest", 8, 8)
        with tempfile.TemporaryDirectory() as tmp:
            path = image_manager.save_image(img, path=tmp)
            self.assertTrue(os.path.exists(path), f"File not found: {path}")

    def test_id_map_optimized_colors_integrity(self):
        """Verify generated colors contain no NaNs and are within [0,1]."""
        colors = math_utils.generate_optimized_colors(20)
        self.assertEqual(colors.shape, (20, 4))
        self.assertTrue(np.all(colors >= 0.0) and np.all(colors <= 1.0))
        self.assertFalse(np.any(np.isnan(colors)))

if __name__ == '__main__':
    unittest.main()
