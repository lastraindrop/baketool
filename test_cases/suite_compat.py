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

if __name__ == '__main__':
    unittest.main()
