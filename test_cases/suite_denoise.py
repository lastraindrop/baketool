import unittest
import bpy
import os
import sys

# Ensure addon is in path
addon_dir = os.path.dirname(os.path.dirname(__file__))
if addon_dir not in sys.path:
    sys.path.append(addon_dir)

from baketool.test_cases.helpers import cleanup_scene, ensure_cycles
from baketool.core.engine import BakePostProcessor
from baketool.core import compat

class SuiteDenoise(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        ensure_cycles()

    def test_denoise_compositor_setup(self):
        """Test HP-1: Verify compositor tree setup across versions (especially B5.0)."""
        img = bpy.data.images.new("TestDenoise", 128, 128)
        
        # Test apply_denoise (will create temp scene internally)
        # Note: We can't easily check pixels in headless without a real render,
        # but we can verify the node structure logic doesn't crash.
        try:
            BakePostProcessor.apply_denoise(bpy.context, img)
        except Exception as e:
            self.fail(f"BakePostProcessor.apply_denoise failed: {e}")
            
    def test_get_compositor_tree_persistence(self):
        """Test that get_compositor_tree correctly handles B5.0 scene.compositor."""
        scene = bpy.context.scene
        tree = compat.get_compositor_tree(scene)
        self.assertIsNotNone(tree, "Compositor tree should be accessible/creatable")
        
        if compat.is_blender_5():
            # In B5.0+, the property was renamed to compositing_node_group
            self.assertTrue(hasattr(scene, "compositing_node_group"), "Blender 5.0 scene should have compositing_node_group property")
            self.assertEqual(scene.compositing_node_group, tree, "Tree should match scene.compositing_node_group in B5.0")
        else:
            self.assertTrue(scene.use_nodes, "Legacy Blender should have use_nodes enabled")
            self.assertEqual(scene.node_tree, tree, "Tree should match scene.node_tree in legacy")

if __name__ == '__main__':
    unittest.main()
