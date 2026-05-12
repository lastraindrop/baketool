import unittest
import bpy
import numpy as np
from .helpers import (
    cleanup_scene,
    create_test_object,
    JobBuilder,
    ensure_cycles,
    MockSetting,
    DataLeakChecker,
)
from ..core import image_manager, uv_manager, math_utils, common, compat
from ..core.engine import BakePassExecutor, BakeStepRunner, BakeTask
from ..core.node_manager import NodeGraphHandler


class SuiteUnit(unittest.TestCase):
    """
    Consolidated Unit Test Suite for BakeNexus Core Components.
    Covers: Image Manager, UV Manager, Math Utils, Compat Layer, and Node Graph Logic.
    """

    @classmethod
    def setUpClass(cls):
        ensure_cycles()

    def setUp(self):
        cleanup_scene()

    def tearDown(self):
        cleanup_scene()

    def test_ui_panel_poll_safe_access(self):
        """Verify UI Panel poll function handles edge cases safely."""
        from ..ui import BAKE_PT_NodePanel

        class MockSpaceData:
            tree_type = "ShaderNodeTree"

        class MockContext:
            space_data = MockSpaceData()

        result = BAKE_PT_NodePanel.poll(MockContext())
        self.assertTrue(result)

        class MockContextNone:
            space_data = None

        result = BAKE_PT_NodePanel.poll(MockContextNone())
        self.assertFalse(result)

        class MockContextNoAttr:
            pass

        result = BAKE_PT_NodePanel.poll(MockContextNoAttr())
        self.assertFalse(result)

    def test_image_manager_needs_persistent_reference(self):
        """Verify _needs_persistent_reference logic."""
        from ..core.image_manager import _needs_persistent_reference

        self.assertFalse(_needs_persistent_reference(None))

        setting_no_external = MockSetting(use_external_save=False, apply_to_scene=False)
        self.assertFalse(_needs_persistent_reference(setting_no_external))

        setting_with_external = MockSetting(
            use_external_save=True, external_save_path="/tmp/test"
        )
        self.assertTrue(_needs_persistent_reference(setting_with_external))

    def test_apply_baked_result_mesh_cleanup(self):
        """Verify apply_baked_result properly cleans up old mesh data."""
        obj = create_test_object("MeshCleanupTest")
        initial_mesh_count = len(bpy.data.meshes)

        task_images = {
            "color": image_manager.set_image("ColorMap", 64, 64),
            "normal": image_manager.set_image("NormalMap", 64, 64),
        }

        from ..core.common import apply_baked_result

        new_obj = apply_baked_result(
            bpy.context, obj, task_images, MockSetting(), "TestBake"
        )

        self.assertIsNotNone(new_obj)
        
        # Verify collection logic (Baked_Results)
        found_in_coll = False
        if "Baked_Results" in bpy.data.collections:
            if new_obj.name in bpy.data.collections["Baked_Results"].objects:
                found_in_coll = True
        self.assertTrue(found_in_coll, "New baked object was not moved to 'Baked_Results' collection")

        if new_obj and new_obj.name in bpy.data.objects:
            bpy.data.objects.remove(new_obj, do_unlink=True)

        final_mesh_count = len(bpy.data.meshes)
        self.assertLessEqual(
            final_mesh_count - initial_mesh_count,
            3,
            f"Mesh accumulation detected: {final_mesh_count - initial_mesh_count}",
        )

    def test_image_set_setting_parameter(self):
        """Verify set_image accepts and uses setting parameter."""
        setting = MockSetting(use_external_save=True, external_save_path="/tmp")

        img = image_manager.set_image("TestWithSetting", 64, 64, setting=setting)
        self.assertIsNotNone(img)
        self.assertTrue(img.use_fake_user)

        img2 = image_manager.set_image("TestWithoutSetting", 64, 64)
        self.assertFalse(img2.use_fake_user)

    # --- Image & Math Utils (from test_core.py) ---
    def test_image_setting(self):
        img = image_manager.set_image("TestImg", 64, 64, space="sRGB")
        self.assertEqual(img.size[0], 64)
        self.assertEqual(img.colorspace_settings.name, "sRGB")

    def test_process_pbr_numpy_metallic_conversion(self):
        """Verify PBR metallic conversion math logic in NumPy."""
        spec = image_manager.set_image(
            "Spec_PBR", 8, 8, basiccolor=(0.5, 0.5, 0.5, 1.0)
        )
        diff = image_manager.set_image(
            "Diff_PBR", 8, 8, basiccolor=(1.0, 0.0, 0.0, 1.0)
        )
        target = image_manager.set_image("Target_PBR", 8, 8)

        # Specular 0.5 > Threshold 0.04 -> Should be metallic
        success = math_utils.process_pbr_numpy(
            target, spec, diff, "pbr_conv_metal", threshold=0.04
        )
        self.assertTrue(success)

        arr = np.empty(8 * 8 * 4, dtype=np.float32)
        target.pixels.foreach_get(arr)
        # metal = (0.5 - 0.04) / (1.0 - 0.04) = 0.46 / 0.96 ?0.479
        # Precision: 8-bit color rounding (128/255 ?0.5019)
        self.assertAlmostEqual(arr[0], 0.4791666, places=2)

    def test_process_pbr_numpy_specular_threshold(self):
        """Verify threshold affects PBR conversion output."""
        spec = image_manager.set_image(
            "Spec_Thresh", 4, 4, basiccolor=(0.1, 0.1, 0.1, 1.0)
        )
        diff = image_manager.set_image("Diff_Thresh", 4, 4, basiccolor=(1, 1, 1, 1))
        target = image_manager.set_image("Target_Thresh", 4, 4)

        # Threshold 0.2 > Specular 0.1 -> Should be 0 metallic
        math_utils.process_pbr_numpy(
            target, spec, diff, "pbr_conv_metal", threshold=0.2
        )
        arr = np.empty(4 * 4 * 4, dtype=np.float32)
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

        arr = np.empty(4 * 4 * 4, dtype=np.float32)
        target.pixels.foreach_get(arr)
        self.assertAlmostEqual(arr[0], 1.0, places=2)  # R
        self.assertAlmostEqual(arr[1], 0.5, places=2)  # G
        self.assertAlmostEqual(arr[2], 0.0, places=2)  # B

    # --- UV & UDIM Logic ---
    def test_udim_detection(self):
        obj = create_test_object("UDIM_Obj")
        # Shift UV to 1002
        uv_layer = obj.data.uv_layers.active.data
        for loop in uv_layer:
            loop.uv[0] += 1.0
        self.assertEqual(uv_manager.detect_object_udim_tile(obj), 1002)

    # --- UI & Property Integrity (Hardened v1.0.0-p2) ---
    def test_ui_layout_config_integrity(self):
        from ..constants import CHANNEL_UI_LAYOUT
        from ..property import BakeChannel

        # Verify that all props in CHANNEL_UI_LAYOUT exist in BakeChannel or its sub-properties
        for chan_id, config in CHANNEL_UI_LAYOUT.items():
            if config.get("type") in {"PROPS", "TOGGLES"}:
                for prop_data in config.get("props", []):
                    prop_path = prop_data[0]
                    target = BakeChannel
                    root_part = prop_path.split(".")[0]
                    # Ensure class has the attribute either directly or via annotations
                    has_prop = hasattr(target, root_part) or (
                        hasattr(target, "__annotations__")
                        and root_part in target.__annotations__
                    )
                    self.assertTrue(
                        has_prop,
                        f"Root property '{root_part}' (from '{prop_path}') not found in {target} for channel {chan_id}",
                    )

    def test_property_group_integrity(self):
        """Regression test for common RNA pitfalls (Dynamic Enum Defaults, etc.)"""
        from ..property import BakeJobSetting

        # 1. Verify existence of critical properties
        target = BakeJobSetting
        has_depth = hasattr(target, "color_depth") or (
            hasattr(target, "__annotations__")
            and "color_depth" in target.__annotations__
        )
        self.assertTrue(
            has_depth, f"BakeJobSetting missing 'color_depth' in annotations or members"
        )

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
        """Audit all operators referenced in ui.py to ensure they resolve to RNA."""
        import os
        import re

        # 1. Get all operator IDs from ui.py
        ui_path = os.path.join(os.path.dirname(__file__), "..", "ui.py")
        if not os.path.exists(ui_path):
            return  # Skip if not local

        with open(ui_path, "r", encoding="utf-8") as f:
            content = f.read()

        operator_ids = re.findall(r'\.operator\("([^"]+)"', content)

        # 2. Check if they are registered in bpy.ops
        for op_id in operator_ids:
            parts = op_id.split(".")
            if len(parts) != 2:
                continue

            self.assertTrue(
                hasattr(bpy.ops, parts[0]),
                f"Operator module '{parts[0]}' not found for '{op_id}'",
            )
            sub = getattr(bpy.ops, parts[0])
            operator_ref = getattr(sub, parts[1])
            try:
                rna_type = operator_ref.get_rna_type()
            except KeyError:
                self.fail(
                    f"Operator '{op_id}' is referenced in UI but not registered in Blender"
                )
            self.assertTrue(rna_type.identifier)

    def test_custom_result_key_normalization(self):
        """Custom outputs must use stable prefixed IDs for reuse and packing."""
        custom_cfg = {"id": "CUSTOM", "name": "MaskA"}
        result_key = BakePassExecutor.get_result_key(custom_cfg)
        self.assertEqual(result_key, "BT_CUSTOM_MaskA")

        dummy_img = image_manager.set_image("MaskA_Source", 4, 4)
        resolved = BakePassExecutor.normalize_source_id(
            "MaskA", {"BT_CUSTOM_MaskA": dummy_img}
        )
        self.assertEqual(resolved, "BT_CUSTOM_MaskA")

    def test_custom_channel_numpy_composition(self):
        """Custom channel sources should compose directly from baked results."""
        obj = create_test_object("CustomMapObj")
        job = JobBuilder("CustomMapJob").build()
        setting = job.setting
        setting.res_x = 32
        setting.res_y = 32

        custom = job.custom_bake_channels.add()
        custom.name = "MaskA"
        custom.bw = False
        for channel in setting.channels:
            if channel.id == "alpha":
                channel.enabled = True
                break

        custom.r_settings.use_map = True
        custom.r_settings.source = "color"

        custom.g_settings.use_map = True
        custom.g_settings.source = "color"
        custom.g_settings.sep_col = True
        custom.g_settings.col_chan = "B"

        custom.b_settings.use_map = True
        custom.b_settings.source = "color"
        custom.b_settings.invert = True

        custom.a_settings.use_map = True
        custom.a_settings.source = "alpha"

        task = BakeTask(
            objects=[obj],
            materials=[obj.material_slots[0].material],
            active_obj=obj,
            base_name="CustomOut",
            folder_name="",
        )
        current_results = {
            "color": image_manager.set_image(
                "CustomColorSrc", 32, 32, basiccolor=(0.2, 0.4, 0.6, 1.0)
            ),
            "alpha": image_manager.set_image(
                "CustomAlphaSrc", 32, 32, basiccolor=(0.1, 0.1, 0.1, 0.25)
            ),
        }
        c_config = {
            "id": "CUSTOM",
            "name": custom.name,
            "prop": custom,
            "bake_pass": "EMIT",
            "info": {"cat": "DATA"},
            "prefix": "",
            "suffix": "_mask",
        }

        img = BakePassExecutor.execute(
            bpy.context,
            setting,
            task,
            c_config,
            None,
            current_results,
            array_cache={},
        )

        self.assertIsNotNone(img)
        arr = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
        img.pixels.foreach_get(arr)
        self.assertAlmostEqual(arr[0], 0.2, places=3)
        self.assertAlmostEqual(arr[1], 0.6, places=3)
        self.assertAlmostEqual(arr[2], 0.4, places=3)
        self.assertAlmostEqual(arr[3], 0.25, places=2)

    def test_channel_packing_supports_custom_sources(self):
        """Packed outputs should accept the prefixed custom source IDs."""
        obj = create_test_object("PackCustomObj")
        setting = MockSetting(
            res_x=4,
            res_y=4,
            pack_r="BT_CUSTOM_MaskA",
            pack_suffix="_PACK",
        )

        task = BakeTask(
            objects=[obj],
            materials=[obj.material_slots[0].material],
            active_obj=obj,
            base_name="PackCustom",
            folder_name="",
        )
        src_img = image_manager.set_image(
            "PackCustomSrc", 4, 4, basiccolor=(0.7, 0.7, 0.7, 1.0)
        )

        packed = BakeStepRunner(bpy.context)._handle_channel_packing(
            setting,
            task,
            {"BT_CUSTOM_MaskA": src_img},
            None,
            {},
        )

        self.assertIsNotNone(packed)
        arr = np.empty(4 * 4 * 4, dtype=np.float32)
        packed["image"].pixels.foreach_get(arr)
        self.assertAlmostEqual(arr[0], 0.7, places=2)

    def test_pass_filter_settings_mapping(self):
        """Light and combined pass toggles must map to Blender bake settings."""
        job = JobBuilder("PassSettingsJob").type("BASIC").build()
        setting = job.setting

        diff = next(c for c in setting.channels if c.id == "diff")
        diff.pass_settings.use_direct = False
        diff.pass_settings.use_indirect = True
        diff.pass_settings.use_color = False
        diff_filters = BakePassExecutor._get_pass_filter_settings(
            setting, diff, "DIFFUSE"
        )
        self.assertEqual(
            diff_filters,
            {
                "use_pass_direct": False,
                "use_pass_indirect": True,
                "use_pass_color": False,
            },
        )

        combine = next(c for c in setting.channels if c.id == "combine")
        combine.combine_settings.use_direct = True
        combine.combine_settings.use_indirect = False
        combine.combine_settings.use_diffuse = True
        combine.combine_settings.use_glossy = False
        combine.combine_settings.use_transmission = True
        combine.combine_settings.use_emission = False
        combine_filters = BakePassExecutor._get_pass_filter_settings(
            setting, combine, "COMBINED"
        )
        self.assertEqual(
            combine_filters,
            {
                "use_pass_direct": True,
                "use_pass_indirect": False,
                "use_pass_diffuse": True,
                "use_pass_glossy": False,
                "use_pass_transmission": True,
                "use_pass_emit": False,
            },
        )

    def test_headless_entry_can_initialize_properties(self):
        """Headless entry point should expose a registration bootstrap."""
        from ..automation import headless_bake

        self.assertTrue(headless_bake.ensure_addon_registered())

    # --- Auto-Cage 2.0 Proximity Logic ---
    def test_cage_proximity_analysis(self):
        low = create_test_object("Low")
        high = create_test_object("High", location=(0, 0, 0.1))  # Slightly offset

        # Test the utility directly
        exts = math_utils.calculate_cage_proximity(low, [high], margin=0.05)
        self.assertIsNotNone(exts)
        self.assertTrue(all(e >= 0.1 for e in exts))  # 0.1 offset + 0.05 margin

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
        extension_sockets = ["pbr_conv_metal", "pbr_conv_base", "rough_inv"]
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

        img = image_manager.set_image(
            "TestDenoise", 16, 16, basiccolor=(0.1, 0.4, 0.2, 1.0)
        )
        # inject noise
        arr = np.random.rand(16 * 16 * 4).astype(np.float32)
        arr[3::4] = 1.0  # fixed alpha
        img.pixels.foreach_set(arr)

        try:
            BakePostProcessor.apply_denoise(bpy.context, img)
            new_arr = np.empty(16 * 16 * 4, dtype=np.float32)
            img.pixels.foreach_get(new_arr)
            self.assertFalse(
                np.array_equal(arr, new_arr), "Denoise did not modify pixels"
            )
        except Exception as e:
            self.fail(f"Denoise crashed: {e}")

    def test_emergency_cleanup_removes_temp_nodes(self):
        """Verify EmergencyCleanup removes tagged temporary nodes."""
        mat = bpy.data.materials.new("TestCleanup")
        mat.use_nodes = True
        tree = mat.node_tree
        # Add a dummy node and tag it exactly as cleanup.py expects: is_bt_temp
        val_node = tree.nodes.new("ShaderNodeValue")
        val_node["is_bt_temp"] = True
        val_node.name = "BakeNexus_Temp_Node"

        self.assertIn(val_node, tree.nodes.values())

        # Execute actual cleanup operator
        res = bpy.ops.bake.emergency_cleanup()
        self.assertEqual(res, {"FINISHED"})

        # Verify removal
        remaining = [n for n in tree.nodes if n.get("is_bt_temp", False)]
        self.assertEqual(len(remaining), 0)

    def test_cage_raycast_hit_detection(self):
        """Verify Raycast analysis for cage overlap."""
        from ..core.cage_analyzer import CageAnalyzer

        with common.safe_context_override(bpy.context):
            cleanup_scene()
            low = create_test_object("Low_Cage_Test")
            high = create_test_object(
                "High_Cage_Test", location=(0, 0, 0.5)
            )  # Offset high

            # Since high is offset by 0.5, rays from low with extrusion 0.1 should FAIL completely
            success, msg = CageAnalyzer.run_raycast_analysis(
                bpy.context, low, [high], extrusion=0.1
            )
            self.assertTrue(success)
            self.assertIn("errors", msg)  # Indicates failure to hit

            # Extrusion of 1.0 is enough to reach the high poly offset
            success, msg2 = CageAnalyzer.run_raycast_analysis(
                bpy.context, low, [high], extrusion=1.0
            )
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
            BakePostProcessor.apply_denoise(bpy.context, img)
        finally:
            # TB-3: Only check for leaked BT_ scenes to avoid interference from elsewhere
            bt_scenes = [s for s in bpy.data.scenes if s.name.startswith("BT_")]
            self.assertEqual(
                len(bt_scenes),
                0,
                f"Leaked BT scenes found: {[s.name for s in bt_scenes]}",
            )

    def test_cage_proximity_multi_highpoly(self):
        """Verify proximity calculation handles multiple highpolys."""
        low = create_test_object("Low_P")
        high1 = create_test_object("High_1", location=(0, 0, 0.1))
        high2 = create_test_object("High_2", location=(0, 0, 0.2))

        # Test with multiple high polys
        exts = math_utils.calculate_cage_proximity(low, [high1, high2], margin=0.0)
        self.assertIsNotNone(exts)
        # Even before the multi-highpoly fix in Phase 3, this test should pass if it picks at least one.
        # After Phase 3 fix, it should pick the NEAREST one for each vertex.
        self.assertGreater(len(exts), 0)

    def test_custom_channel_packing_lookup(self):
        """Verify that CUSTOM channels can be correctly looked up for packing."""
        # Mock a channel config
        c = {"id": "CUSTOM", "name": "MyMask"}
        baked_images = {}
        img = image_manager.set_image("MaskImg", 16, 16)

        key = BakePassExecutor.get_result_key(c)
        baked_images[key] = img

        self.assertIn("BT_CUSTOM_MyMask", baked_images)
        self.assertEqual(baked_images["BT_CUSTOM_MyMask"], img)

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
        """Verify basic texel density calculation logic exists."""
        self.assertTrue(hasattr(math_utils, "TexelDensityCalculator"))
        self.assertTrue(hasattr(math_utils.TexelDensityCalculator, "get_mesh_density"))

    # --- Expanded Component Lifecycle Tests ---
    def test_context_manager_exception_restores_state(self):
        """Verify that BakeContextManager performs cleanup even if an exception occurs."""
        from ..core.engine import BakeContextManager

        orig_engine = bpy.context.scene.render.engine

        try:
            with BakeContextManager(bpy.context, MockSetting()):
                bpy.context.scene.render.engine = "CYCLES"
                raise RuntimeError("Simulated crash")
        except RuntimeError:
            pass
        self.assertEqual(bpy.context.scene.render.engine, orig_engine)

    def test_node_graph_handler_link_restoration(self):
        """Verify material links are restored by NodeGraphHandler even if manually cleared."""
        mat = bpy.data.materials.new("LinkRestoreMat")
        mat.use_nodes = True
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        out = nodes.new("ShaderNodeOutputMaterial")
        links.new(bsdf.outputs[0], out.inputs[0])

        count = len(links)
        with NodeGraphHandler([mat]) as h:
            links.clear()
        self.assertEqual(
            len(links), count, "Links not restored after NodeGraphHandler exit"
        )

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
        import os
        import shutil
        from pathlib import Path

        img = image_manager.set_image("DiskTest", 8, 8)
        out_dir = Path(__file__).resolve().parents[1] / "test_output" / "unit_disk"
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            path = image_manager.save_image(img, path=str(out_dir))
            self.assertIsNotNone(path, "Image save returned None")
            self.assertTrue(os.path.exists(path), f"File not found: {path}")
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_id_map_optimized_colors_integrity(self):
        """Verify generated colors contain no NaNs and are within [0,1]."""
        colors = math_utils.generate_optimized_colors(20)
        self.assertEqual(colors.shape, (20, 4))
        self.assertTrue(np.all(colors >= 0.0) and np.all(colors <= 1.0))
        self.assertFalse(np.any(np.isnan(colors)))

    def test_scene_settings_context_stores_params(self):
        """Verify SceneSettingsContext stores constructor parameters."""
        from ..core.common import SceneSettingsContext

        scene = bpy.context.scene
        ctx = SceneSettingsContext("scene", {"samples": 128}, scene)
        self.assertEqual(ctx.category, "scene")
        self.assertEqual(ctx.settings, {"samples": 128})
        self.assertEqual(ctx.scene, scene)

    def test_node_graph_handler_stores_materials(self):
        """Verify NodeGraphHandler stores and filters materials."""
        if not bpy.data.materials:
            mat = bpy.data.materials.new("TestMat")
            mat.use_nodes = True
        else:
            mat = bpy.data.materials[0]
            mat.use_nodes = True

        with NodeGraphHandler([mat]) as h:
            self.assertTrue(hasattr(h, "materials"))
            self.assertIn(mat, h.materials)

    def test_uv_layout_manager_stores_params(self):
        """Verify UVLayoutManager stores constructor parameters."""
        obj = create_test_object("UVStoreTest")
        ms = MockSetting(use_auto_uv=False)
        with uv_manager.UVLayoutManager([obj], ms) as m:
            self.assertEqual(m.objects, [obj])
            self.assertEqual(m.settings, ms)


if __name__ == "__main__":
    unittest.main()
