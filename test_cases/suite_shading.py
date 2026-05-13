
"""Viewport preview material tests."""
import unittest
import bpy
from .helpers import cleanup_scene, create_test_object, ensure_cycles, MockSetting
from ..core import shading

class SuiteShading(unittest.TestCase):
    """
    Tests for core/shading.py.
    Verifies preview material creation, application, and restoration.
    """

    @classmethod
    def setUpClass(cls):
        ensure_cycles()

    def setUp(self):
        cleanup_scene()
        self.obj = create_test_object("ShadingObj")

    def tearDown(self):
        cleanup_scene()

    def test_create_preview_material_returns_material(self):
        """Verify that basic preview material creation returns a valid Material."""
        ms = MockSetting(pack_r='color', pack_g='rough', pack_b='metal')
        mat = shading.create_preview_material(self.obj, ms)
        self.assertIsInstance(mat, bpy.types.Material)
        self.assertTrue(mat.use_nodes)

        # Verify specific nodes exist
        nodes = mat.node_tree.nodes
        has_combine = any(n.bl_idname in {'ShaderNodeCombineColor', 'ShaderNodeCombineRGB'} for n in nodes)
        self.assertTrue(has_combine, "Preview material missing Combine node")

    def test_apply_and_remove_preview_lifecycle(self):
        """Full lifecycle: apply preview material and then restore original."""
        ms = MockSetting(pack_r='color', pack_g='rough', pack_b='metal')
        orig_mat = self.obj.material_slots[0].material
        orig_name = orig_mat.name

        # 1. Apply
        shading.apply_preview(self.obj, ms)
        new_mat = self.obj.data.materials[0]
        self.assertNotEqual(new_mat.name, orig_name)
        self.assertEqual(self.obj["_bt_orig_mat_name"], orig_name)

        # 2. Remove
        shading.remove_preview(self.obj)
        restored_mat = self.obj.data.materials[0]
        self.assertEqual(restored_mat.name, orig_name)
        self.assertNotIn("_bt_orig_mat_name", self.obj)

    def test_remove_preview_cleans_up_temp_material(self):
        """Verify that remove_preview deletes the temporary material if it's unused."""
        ms = MockSetting()
        mat_count_before = len(bpy.data.materials)
        shading.apply_preview(self.obj, ms)
        # The preview material name is BT_Packing_Preview (PREVIEW_MAT_NAME)
        self.assertIn(shading.PREVIEW_MAT_NAME, bpy.data.materials)

        # Unlink from object before removal to ensure 0 users
        self.obj.data.materials.clear()
        shading.remove_preview(self.obj)
        self.assertNotIn(shading.PREVIEW_MAT_NAME, bpy.data.materials)

    def test_apply_preview_skips_if_already_preview(self):
        """Verify idempotency to prevent double-wrapping."""
        ms = MockSetting()
        shading.apply_preview(self.obj, ms)
        initial_preview = self.obj.data.materials[0].name

        shading.apply_preview(self.obj, ms)
        self.assertEqual(self.obj.data.materials[0].name, initial_preview)

    def test_apply_preview_no_material_graceful(self):
        """Verify objects without materials are handled safely."""
        obj_no_mat = create_test_object("NoMatObj")
        obj_no_mat.data.materials.clear()

        try:
            shading.apply_preview(obj_no_mat, "NoMatPreview")
        except Exception as e:
            self.fail(f"apply_preview crashed on object with no materials: {e}")

if __name__ == '__main__':
    unittest.main()
