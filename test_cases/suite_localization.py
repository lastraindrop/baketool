
"""Translation extraction and audit tool tests."""
import ast
import textwrap
import unittest
from pathlib import Path
from unittest import mock

from ..dev_tools import extract_translations


class SuiteLocalization(unittest.TestCase):
    """Tests for translation extraction and sync helpers."""

    def test_extractor_filters_internal_ids_and_keeps_labels(self):
        tree = ast.parse(
            textwrap.dedent(
                """
                import bpy

                class TEST_OT_Demo(bpy.types.Operator):
                    bl_label = "Bake Selected Node"
                    bl_description = "Bake the active node"
                    enabled: bpy.props.BoolProperty(
                        name="Auto Load",
                        description="Automatically load this preset",
                    )

                UI_MESSAGES = {"NO_JOBS": "No enabled jobs."}
                CAT_DATA = "DATA"
                PANEL_LAYOUT = {
                    "props": [("extension_settings.output_name", "Output", "OUTPUT")]
                }

                def draw(layout, settings):
                    layout.operator("bake.quick_bake", text="Quick Bake")
                    layout.prop(settings, "use_packing", text="Auto Pack Channels")

                def update_image(img, info):
                    img.source, img.filepath, img.frame_duration = (
                        "SEQUENCE",
                        info["first_path"],
                        info["count"],
                    )
                """
            )
        )
        extractor = extract_translations.TranslationExtractor()
        extractor.visit(tree)
        strings = extractor.strings

        self.assertIn("Bake Selected Node", strings)
        self.assertIn("Bake the active node", strings)
        self.assertIn("Auto Load", strings)
        self.assertIn("Automatically load this preset", strings)
        self.assertIn("Quick Bake", strings)
        self.assertIn("Auto Pack Channels", strings)
        self.assertIn("No enabled jobs.", strings)
        self.assertIn("Output", strings)
        self.assertNotIn("bake.quick_bake", strings)
        self.assertNotIn("use_packing", strings)
        self.assertNotIn("DATA", strings)
        self.assertNotIn("OUTPUT", strings)
        self.assertNotIn("SEQUENCE", strings)

    def test_sync_translation_payload_preserves_existing_translations(self):
        existing_payload = {
            "header": {"author": "lastraindrop", "version": "1.0.0"},
            "data": {
                "Bake Selected Node": {"zh_CN": "烘焙选中节点"},
                "stale_key": {"zh_CN": "旧键"},
            },
        }

        with mock.patch.object(
            extract_translations,
            "extract_strings",
            return_value=["Bake Selected Node", "Bake the active node"],
        ), mock.patch.object(
            extract_translations,
            "load_translation_payload",
            return_value=existing_payload,
        ):
            payload, audit = extract_translations.sync_translation_payload(
                source_dir=Path("ignored"),
                translation_path=Path("ignored.json"),
                locales=["zh_CN"],
                prune=True,
                excludes=set(),
            )

        self.assertIn("Bake Selected Node", payload["data"])
        self.assertIn("Bake the active node", payload["data"])
        self.assertNotIn("stale_key", payload["data"])
        self.assertEqual(payload["data"]["Bake Selected Node"]["zh_CN"], "烘焙选中节点")
        self.assertEqual(
            payload["data"]["Bake Selected Node"]["en_US"], "Bake Selected Node"
        )
        self.assertEqual(
            payload["data"]["Bake the active node"]["en_US"], "Bake the active node"
        )
        self.assertIn("stale_key", audit["stale_keys"])

    def test_audit_report_flags_suspicious_existing_keys(self):
        audit = extract_translations.build_audit_report(
            extracted_strings=["Quick Bake"],
            existing_payload={
                "data": {
                    "bake.quick_bake": {"zh_CN": "错误键"},
                    "Quick Bake": {"zh_CN": "快速烘焙"},
                }
            },
            locales=["en_US", "zh_CN"],
        )
        self.assertIn("bake.quick_bake", audit["suspicious_existing_keys"])
        self.assertEqual(audit["missing_by_locale"]["zh_CN"], [])

    def test_audit_report_flags_broken_and_untranslated_locale_values(self):
        audit = extract_translations.build_audit_report(
            extracted_strings=["Bake Objects", "PNG", "Output"],
            existing_payload={
                "data": {
                    "Bake Objects": {"zh_CN": "Bake Objects"},
                    "PNG": {"zh_CN": "PNG"},
                    "Output": {"zh_CN": "??"},
                }
            },
            locales=["en_US", "zh_CN"],
        )
        self.assertIn("Output", audit["broken_by_locale"]["zh_CN"])
        self.assertIn("Bake Objects", audit["untranslated_by_locale"]["zh_CN"])
        self.assertNotIn("PNG", audit["untranslated_by_locale"]["zh_CN"])

    def test_audit_report_allows_configured_same_as_source_terms(self):
        audit = extract_translations.build_audit_report(
            extracted_strings=["Angle", "Transmission", "Bake Objects"],
            existing_payload={
                "data": {
                    "Angle": {"fr_FR": "Angle"},
                    "Transmission": {"fr_FR": "Transmission"},
                    "Bake Objects": {"fr_FR": "Bake Objects"},
                }
            },
            locales=["en_US", "fr_FR"],
        )
        self.assertNotIn("Angle", audit["untranslated_by_locale"]["fr_FR"])
        self.assertNotIn("Transmission", audit["untranslated_by_locale"]["fr_FR"])
        self.assertIn("Bake Objects", audit["untranslated_by_locale"]["fr_FR"])


if __name__ == "__main__":
    unittest.main()
