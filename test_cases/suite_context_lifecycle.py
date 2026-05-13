
"""Context manager and state lifecycle tests."""
import unittest
import bpy
import os
import sys

# Ensure addon is in path
addon_dir = os.path.dirname(os.path.dirname(__file__))
if addon_dir not in sys.path:
    sys.path.append(addon_dir)

from baketool.test_cases.helpers import cleanup_scene, create_test_object, MockSetting
from baketool.core.engine import BakeContextManager
from baketool.core.node_manager import NodeGraphHandler
from baketool.core.common import safe_context_override

class SuiteContextLifecycle(unittest.TestCase):
    def setUp(self):
        cleanup_scene()

    def test_bake_context_manager_restoration(self):
        """Test HP-2: Render settings are restored after context manager exits."""
        scene = bpy.context.scene
        orig_res_x = scene.render.resolution_x
        orig_engine = scene.render.engine

        s = MockSetting(res_x=512, sample=10, device='CPU')

        with BakeContextManager(bpy.context, s):
            self.assertEqual(scene.render.resolution_x, 512)
            self.assertEqual(scene.render.engine, 'CYCLES')
            self.assertEqual(scene.cycles.samples, 10)

        self.assertEqual(scene.render.resolution_x, orig_res_x, "Resolution X not restored")
        self.assertEqual(scene.render.engine, orig_engine, "Engine not restored")

    def test_node_graph_handler_link_restoration(self):
        """Test HP-5: Node links are restored correctly even if session links were added."""
        obj = create_test_object("NodeTest")
        mat = obj.material_slots[0].material
        tree = mat.node_tree

        # Create an original link
        bsdf = next(n for n in tree.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled')
        out = next(n for n in tree.nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
        tree.links.new(bsdf.outputs[0], out.inputs[0])
        self.assertEqual(len(tree.links), 1)

        with NodeGraphHandler([mat]) as h:
            # Simulate setup_for_pass which adds links
            tex_n = h.session_nodes[mat]['tex']
            tree.links.new(tex_n.outputs[0], bsdf.inputs[0])
            self.assertEqual(len(tree.links), 2)

        # Verify restoration
        self.assertEqual(len(tree.links), 1, "Links not restored to original count")
        self.assertEqual(tree.links[0].from_node, bsdf, "Link from node mismatch after restore")
        self.assertEqual(tree.links[0].to_node, out, "Link to node mismatch after restore")

    def test_safe_context_override_nesting(self):
        """Verify that safe_context_override can be nested without side effects."""
        obj1 = create_test_object("Obj1")
        obj2 = create_test_object("Obj2")

        with safe_context_override(bpy.context, obj1, [obj1]):
            self.assertEqual(bpy.context.active_object, obj1)
            with safe_context_override(bpy.context, obj2, [obj1, obj2]):
                self.assertEqual(bpy.context.active_object, obj2)
            self.assertEqual(bpy.context.active_object, obj1)

if __name__ == '__main__':
    unittest.main()
