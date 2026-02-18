import unittest
import bpy
from .helpers import cleanup_scene, create_test_object, ensure_cycles
from ..core import compat, image_manager, uv_manager

class TestHeadlessSafety(unittest.TestCase):
    """
    Tests specifically desinged to ensure stability in headless (no-window) environments.
    """
    def setUp(self):
        cleanup_scene()
        ensure_cycles()
        
    def test_blender_5_type_safety(self):
        """Verify Blender 5.0 BakeSettings.type access safety."""
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'
        
        # Test get_bake_settings safety
        bset = compat.get_bake_settings(scene)
        self.assertIsNotNone(bset)
        
        # Test set_bake_type safety
        # This shouldn't crash even if version mismatch, should return False or True
        res = compat.set_bake_type(scene, 'EMIT')
        self.assertTrue(res, "set_bake_type should return True for valid type")
        
        # Verify property existence based on engine
        if scene.render.engine == 'CYCLES' and hasattr(scene, "cycles"):
            self.assertEqual(scene.cycles.bake_type, 'EMIT')
        else:
            # Fallback for non-cycles (Internal, etc in old versions)
            if hasattr(scene.render, "bake"):
                # Blender 4.x / 5.0
                prop = "type" if hasattr(scene.render.bake, "type") else "bake_type"
                self.assertEqual(getattr(scene.render.bake, prop), 'EMIT')
            else:
                # Blender 3.6
                self.assertEqual(scene.render.bake_type, 'EMIT')

    def test_robust_context_headless_simulation(self):
        """Simulate a headless context where window might be None."""
        # We can't easily force context.window to be None in a real Blender session,
        # but we can verify that the image editor context manager survives 
        # when we pass it a context that might be partial, or just verify it works 
        # in the current (likely headless-like execution of tests) environment.
        
        img = bpy.data.images.new("SafetyTest", 32, 32)
        
        # In a real GUI session, this returns True. In headless, it should return False gracefully (or True if it finds a way).
        # We just want to ensure NO CRASH.
        try:
            with image_manager.robust_image_editor_context(bpy.context, img) as valid:
                pass
        except Exception as e:
            self.fail(f"robust_image_editor_context crashed: {e}")

    def test_smart_uv_no_active_object(self):
        """Test _apply_smart_uv robustness when context.object is None."""
        # Deselect all and ensure no active object
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = None
        
        # Create dummy setup for UVManager
        obj = create_test_object("UV_Safe_Obj")
        # We intentionally DON'T select it or make it active here to test internal handling
        # But UVManager.__init__ filters objects.
        
        class MockSettings:
            use_auto_uv = True
            auto_uv_angle = 66
            auto_uv_margin = 0.001
            bake_mode = 'SINGLE_OBJECT'
            udim_mode = 'NONE'

        mgr = uv_manager.UVLayoutManager([obj], MockSettings())
        
        # Manually invoke _apply_smart_uv
        try:
            mgr._apply_smart_uv()
        except AttributeError as e:
             self.fail(f"UVLayoutManager crashed on None active object: {e}")
        except Exception as e:
             self.fail(f"UVLayoutManager crashed with unexpected error: {e}")
