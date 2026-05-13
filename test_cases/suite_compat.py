
"""Blender version compatibility layer tests."""
import unittest
import bpy
from ..core import compat

class SuiteCompat(unittest.TestCase):
    """Verifies version compatibility layer and API stability."""

    def test_version_detection_consistency(self):
        """Ensure compat functions match bpy.app.version."""
        v = bpy.app.version
        if v >= (5, 0, 0):
            self.assertTrue(compat.is_blender_5())
            self.assertFalse(compat.is_blender_4())
        elif v >= (4, 0, 0):
            self.assertTrue(compat.is_blender_4())
            self.assertFalse(compat.is_blender_5())
        else:
            self.assertTrue(compat.is_blender_3())

    def test_set_bake_type_emit_returns_true(self):
        """Verify set_bake_type is stable for basic types."""
        scene = bpy.context.scene
        success = compat.set_bake_type(scene, 'EMIT')
        self.assertTrue(success)

    def test_set_bake_type_normal_returns_true(self):
        """Verify set_bake_type is stable for Normal baking."""
        scene = bpy.context.scene
        success = compat.set_bake_type(scene, 'NORMAL')
        self.assertTrue(success)

    def test_set_bake_type_all_standard_types(self):
        """Verify all major bake types are supported by the compat layer."""
        # Note: BAKE_MAPPING fallback logic might fail if a type is purely engine-missing.
        # But for CYCLES, the core set is mandatory.
        types = ['COMBINED', 'DIFFUSE', 'GLOSSY', 'TRANSMISSION', 'EMIT', 'AO', 'NORMAL', 'SHADOW']
        scene = bpy.context.scene
        for t in types:
            with self.subTest(type=t):
                success = compat.set_bake_type(scene, t)
                self.assertTrue(success, f"Failed to set bake type: {t}")

    def test_set_bake_type_invalid_string_returns_false(self):
        """Verify unknown bake type handling."""
        self.assertFalse(compat.set_bake_type(bpy.context.scene, 'VOID_MAGIC'))

    def test_get_bake_settings_returns_valid_object(self):
        """Verify settings discovery logic."""
        settings = compat.get_bake_settings(bpy.context.scene)
        self.assertIsNotNone(settings)

if __name__ == '__main__':
    unittest.main()
