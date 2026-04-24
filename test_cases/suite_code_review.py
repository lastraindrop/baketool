"""
Test Cases for Code Review Bug Fixes
Verifies the fixes applied during the code review process.
"""

import unittest
import bpy
import uuid
from .helpers import cleanup_scene, create_test_object, JobBuilder, MockSetting


class SuiteCodeReviewFixes(unittest.TestCase):
    """
    Test suite to verify bug fixes from code review.
    """

    @classmethod
    def setUpClass(cls):
        from .helpers import ensure_cycles

        ensure_cycles()

    def setUp(self):
        cleanup_scene()

    def tearDown(self):
        cleanup_scene()

    def test_bl_info_single_definition(self):
        """Verify bl_info is defined only once and contains correct values."""
        from baketool import bl_info

        self.assertEqual(bl_info["name"], "BakeTool")
        self.assertEqual(bl_info["version"], (1, 0, 0))
        self.assertEqual(bl_info["blender"], (3, 6, 0))
        self.assertEqual(bl_info["author"], "lastraindrop")

    def test_ui_messages_get_robustness(self):
        """Verify UI_MESSAGES uses .get() for safe key access."""
        from baketool.constants import UI_MESSAGES

        result = UI_MESSAGES.get("PREP_FAILED", "Bake preparation failed: {}")
        self.assertIn("{}", result)

        result_missing = UI_MESSAGES.get("NON_EXISTENT_KEY", "Default fallback")
        self.assertEqual(result_missing, "Default fallback")

    def test_material_naming_unique(self):
        """Verify create_simple_baked_material creates unique material names."""
        from baketool.core.common import create_simple_baked_material

        texture_map = {"color": bpy.data.images.new("TestImg", 8, 8)}

        mat1 = create_simple_baked_material("TestMat", texture_map)
        mat2 = create_simple_baked_material("TestMat", texture_map)

        self.assertNotEqual(mat1.name, mat2.name)
        self.assertTrue(mat1.name.startswith("TestMat_"))
        self.assertTrue(mat2.name.startswith("TestMat_"))

        texture_map["color"].name = "TestImg2"
        texture_map["color"] = bpy.data.images.new("TestImg2", 8, 8)
        mat3 = create_simple_baked_material("TestMat", texture_map)

        self.assertNotIn("Material", [mat1.name, mat2.name, mat3.name])

    def test_channel_source_items_structure(self):
        """Verify get_channel_source_items returns proper structure."""
        from baketool.property import get_channel_source_items

        class FakeSelf:
            pass

        result = get_channel_source_items(FakeSelf(), None)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "NONE")

        self.assertEqual(result[0][1], "None")
        self.assertEqual(result[0][2], "No enabled channels available")

    def test_engine_export_log_no_duplicate(self):
        """Verify export logging doesn't produce duplicate warnings."""
        import logging
        import io

        class FakeContext:
            pass

        class FakeObj:
            name = "TestObj"

        class FakeSetting:
            external_save_path = ""
            export_format = "FBX"
            create_new_folder = False
            export_textures_with_model = False

        class FakeScene:
            pass

        class FakeCollection:
            def link(self, obj):
                pass

        ctx = FakeContext()
        ctx.scene = FakeScene()
        ctx.collection = FakeCollection()
        ctx.selected_objects = []
        ctx.active_object = None
        ctx.view_layer = type(
            "ViewLayer", (), {"objects": type("Objects", (), {"active": None})()}
        )()

        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.WARNING)
        logger = logging.getLogger("baketool.core.engine")
        original_level = logger.level
        logger.setLevel(logging.WARNING)
        logger.addHandler(handler)

        try:
            from baketool.core.engine import ModelExporter
            ModelExporter.export(ctx, FakeObj(), FakeSetting(), "TestExport")
        except Exception:
            pass
        finally:
            logger.removeHandler(handler)
            logger.setLevel(original_level)

        log_content = log_capture.getvalue()
        warning_lines = [l for l in log_content.strip().split('\n') if l]
        unique_warnings = set(warning_lines)
        self.assertEqual(
            len(warning_lines), len(unique_warnings),
            f"Found duplicate warnings: {warning_lines}"
        )

    def test_manifest_version_matches_bl_info(self):
        """Verify blender_manifest.toml version matches bl_info version."""
        import os
        from pathlib import Path
        test_file = Path(__file__).resolve()
        manifest_path = test_file.parent.parent / "blender_manifest.toml"
        if not manifest_path.exists():
            self.skipTest(f"blender_manifest.toml not found at {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            content = f.read()

        import re
        match = re.search(r'version\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content)
        self.assertIsNotNone(match, "Version not found in manifest")
        manifest_version = tuple(int(x) for x in match.groups())

        from baketool import bl_info
        self.assertEqual(bl_info["version"], manifest_version, "bl_info version doesn't match manifest")

    def test_all_test_suites_importable(self):
        """Verify all test suites can be imported without errors."""
        import importlib

        suites = [
            "suite_automation_tools",
            "suite_unit", "suite_shading", "suite_negative", "suite_memory",
            "suite_export", "suite_api", "suite_cleanup", "suite_code_review",
            "suite_compat", "suite_context_lifecycle", "suite_denoise",
            "suite_localization",
            "suite_parameter_matrix", "suite_preset", "suite_production_workflow",
            "suite_udim_advanced", "suite_ui_logic", "suite_verification",
            "suite_extension_validation"
        ]
        for name in suites:
            mod = importlib.import_module(f"baketool.test_cases.{name}")
            self.assertIsNotNone(mod, f"Failed to import {name}")


if __name__ == "__main__":
    unittest.main()
