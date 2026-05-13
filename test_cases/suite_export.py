
"""Model and texture export safety tests."""
import unittest
import bpy
import os
import sys
from pathlib import Path

addon_dir = os.path.dirname(os.path.dirname(__file__))
if addon_dir not in sys.path:
    sys.path.append(addon_dir)

from baketool.test_cases.helpers import cleanup_scene, create_test_object, MockSetting
from baketool.core.engine import ModelExporter


class SuiteExport(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        self.output_dir = Path(addon_dir) / "test_output" / "export"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def test_exporter_material_clearing_safety(self):
        """Test HP-8/C-07: Material clearing on export copies shouldn't affect original materials."""
        obj = create_test_object("Original")
        orig_mat = obj.material_slots[0].material
        self.assertIsNotNone(orig_mat)

        s = MockSetting(
            external_save_path=str(self.output_dir),
            export_format="FBX",
            export_textures_with_model=False,
            create_new_folder=False,
        )

        ModelExporter.export(bpy.context, obj, s, file_name="TestSafeClear")

        self.assertIn(
            orig_mat.name, bpy.data.materials, "Original material should not be deleted"
        )
        self.assertEqual(
            obj.material_slots[0].material,
            orig_mat,
            "Original object material slot should remain unchanged",
        )

    def test_export_hidden_object_safety(self):
        """Verify exporting hidden objects doesn't crash."""
        obj = create_test_object("HiddenExportObj")

        obj.hide_set(True)
        obj.hide_viewport = True

        s = MockSetting(
            external_save_path=str(self.output_dir),
            export_format="GLB",
            export_textures_with_model=False,
        )

        try:
            ModelExporter.export(bpy.context, obj, s, file_name="HiddenObj")
        except RuntimeError as e:
            if "can't be selected" in str(e):
                self.fail(f"Exporter failed to handle hidden object safely: {e}")
            raise

    def test_export_object_visibility_restored(self):
        """Verify export restores original visibility state."""
        obj = create_test_object("ExportVisTest")
        original_hide = obj.hide_get()
        original_hide_viewport = obj.hide_viewport

        s = MockSetting(
            external_save_path=str(self.output_dir),
            export_format="GLB",
            export_textures_with_model=False,
        )

        ModelExporter.export(bpy.context, obj, s, file_name="VisRestore")

        self.assertEqual(
            obj.hide_get(),
            original_hide,
            "Object visibility should be restored after export",
        )
        self.assertEqual(
            obj.hide_viewport,
            original_hide_viewport,
            "Viewport visibility should be restored after export",
        )

    def test_export_hidden_viewport_state_restored(self):
        """Hidden viewport flag should survive export round-trips."""
        obj = create_test_object("ExportHiddenViewport")
        obj.hide_set(True)
        obj.hide_viewport = True

        s = MockSetting(
            external_save_path=str(self.output_dir),
            export_format="GLB",
            export_textures_with_model=False,
        )

        ModelExporter.export(bpy.context, obj, s, file_name="HiddenViewportRestore")

        self.assertTrue(obj.hide_get())
        self.assertTrue(obj.hide_viewport)

    def test_export_hidden_select_object(self):
        """Verify objects hidden from selection can still be exported."""
        obj = create_test_object("HiddenSelectObj")

        if hasattr(obj, "hide_select"):
            obj.hide_select = True

        s = MockSetting(
            external_save_path=str(self.output_dir),
            export_format="GLB",
            export_textures_with_model=False,
        )

        try:
            ModelExporter.export(bpy.context, obj, s, file_name="HiddenSelect")
        except RuntimeError as e:
            if "can't be selected" in str(e):
                self.fail(f"Failed to handle hide_select object: {e}")
            raise

    def test_export_in_viewlayer_collection(self):
        """Verify objects outside current viewlayer are handled."""
        obj = create_test_object("ViewLayerObj")

        s = MockSetting(
            external_save_path=str(self.output_dir),
            export_format="GLB",
            export_textures_with_model=False,
        )

        try:
            ModelExporter.export(bpy.context, obj, s, file_name="ViewLayerTest")
        except RuntimeError as e:
            if "not in View Layer" in str(e):
                self.fail(f"Failed to handle object not in view layer: {e}")
            raise

    def test_fbx_export_presence(self):
        """Verify FBX exporter operator exists."""
        self.assertTrue(
            hasattr(bpy.ops.export_scene, "fbx"),
            "io_scene_fbx addon should be enabled in test environment",
        )

    def test_glb_export_presence(self):
        """Verify GLB exporter operator exists."""
        self.assertTrue(
            hasattr(bpy.ops.export_scene, "gltf"),
            "io_scene_gltf2 addon should be enabled in test environment",
        )

    def test_usd_export_presence(self):
        """Verify USD exporter operator exists (may not be available in all builds)."""
        has_usd = hasattr(bpy.ops.wm, "usd_export")
        self.assertTrue(
            has_usd, "USD export may not be available in this Blender build"
        )

    def test_export_selection_state_preserved(self):
        """Verify export doesn't permanently change object selection state."""
        obj = create_test_object("SelectionTest")
        other_obj = create_test_object("OtherObj", location=(3, 0, 0))

        bpy.context.view_layer.objects.active = other_obj
        other_obj.select_set(True)
        obj.select_set(True)

        s = MockSetting(
            external_save_path=str(self.output_dir),
            export_format="GLB",
            export_textures_with_model=False,
        )

        ModelExporter.export(bpy.context, obj, s, file_name="SelectionPreserve")

        self.assertEqual(bpy.context.view_layer.objects.active, other_obj)
        self.assertTrue(other_obj.select_get())

    def test_export_multiple_formats_no_crash(self):
        """Verify export handles different formats gracefully."""
        obj = create_test_object("MultiFormatObj")

        formats = []
        if hasattr(bpy.ops.export_scene, "fbx"):
            formats.append(("FBX", "FBX"))
        if hasattr(bpy.ops.export_scene, "gltf"):
            formats.append(("GLB", "GLB"))

        for fmt_name, fmt in formats:
            s = MockSetting(
                external_save_path=str(self.output_dir),
                export_format=fmt,
                export_textures_with_model=False,
            )

            try:
                ModelExporter.export(
                    bpy.context, obj, s, file_name=f"FormatTest_{fmt_name}"
                )
            except Exception as e:
                self.fail(f"Export failed for {fmt_name}: {e}")


if __name__ == "__main__":
    unittest.main()
