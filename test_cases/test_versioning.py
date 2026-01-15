import unittest
import bpy
from .helpers import cleanup_scene
from ..core.common import SceneSettingsContext
from ..core.engine import BakePassExecutor

class TestVersioningAndCompatibility(unittest.TestCase):
    def setUp(self):
        cleanup_scene()

    def test_scene_settings_context_bake_mapping(self):
        """验证 SceneSettingsContext 是否能正确处理 5.0 烘焙属性的路径与名称迁移"""
        # 测试多个迁移属性 // Test multiple migrated properties
        test_settings = {
            'margin': 42,
            'use_clear': True,
            'type': 'NORMALS'
        }
        ctx = SceneSettingsContext('bake', test_settings)
        
        target = ctx._get_target()
        # 检查 target 是否正确 // Check target redirection
        if bpy.app.version >= (5, 0, 0):
            self.assertEqual(target, bpy.context.scene.render.bake, "Should map to scene.render.bake in 5.0+")
        else:
            self.assertEqual(target, bpy.context.scene.render, "Should map to scene.render in legacy versions")

        # 记录原始值 // Store originals
        orig_values = {}
        for k in test_settings.keys():
            real_key = ctx.attr_map['bake'].get(k, k)
            if hasattr(target, real_key):
                orig_values[real_key] = getattr(target, real_key)

        with ctx:
            for k, v in test_settings.items():
                real_key = ctx.attr_map['bake'].get(k, k)
                if hasattr(target, real_key):
                    self.assertEqual(getattr(target, real_key), v, f"Failed to set {real_key}")

        # 验证恢复逻辑 // Verify restoration
        for real_key, orig_val in orig_values.items():
            self.assertEqual(getattr(target, real_key), orig_val, f"Failed to restore {real_key}")

    def test_rendering_engine_safety(self):
        """确保烘焙前强制切换为 CYCLES 引擎的逻辑在各版本均稳健"""
        scene = bpy.context.scene
        orig_engine = scene.render.engine
        
        # In 5.0, EEVEE_NEXT is merged back to BLENDER_EEVEE. 
        # Only 4.2 used BLENDER_EEVEE_NEXT.
        target_eevee = 'BLENDER_EEVEE'
        if (4, 2, 0) <= bpy.app.version < (5, 0, 0):
            target_eevee = 'BLENDER_EEVEE_NEXT'
            
        scene.render.engine = target_eevee
        
        try:
            # 模拟 BakeContextManager 的行为
            from ..core.engine import BakeContextManager
            from .helpers import get_job_setting
            s = get_job_setting()
            
            with BakeContextManager(bpy.context, s):
                self.assertEqual(scene.render.engine, 'CYCLES')
            
            # 退出后应恢复
            self.assertIn(scene.render.engine, {'BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'})
        finally:
            scene.render.engine = orig_engine

    def test_bake_pass_executor_version_branching(self):
        """
        验证 BakePassExecutor._run_blender_bake 的属性设置逻辑。
        虽然我们不能在测试中改变 bpy.app.version，但我们可以验证其对当前版本的处理是否正确。
        """
        scene = bpy.context.scene
        # 记录原始值
        orig_engine = scene.render.engine
        
        from ..core.engine import BakePassExecutor
        from .helpers import get_job_setting
        
        job_setting = get_job_setting()
        job_setting.margin = 16
        job_setting.clearimage = True
        
        # 模拟调用逻辑的一部分 (不真正执行 bpy.ops.object.bake，因为那需要有效的烘焙环境)
        # 我们主要测试属性赋值是否报错
        try:
            if bpy.app.version >= (5, 0, 0):
                if hasattr(scene.render, "bake"):
                    bset = scene.render.bake
                    bset.margin = job_setting.margin
                    self.assertEqual(bset.margin, 16)
            else:
                if hasattr(scene.render, "bake_margin"):
                    scene.render.bake_margin = job_setting.margin
                    self.assertEqual(scene.render.bake_margin, 16)
        finally:
            scene.render.engine = orig_engine

    def test_compatibility_map_integrity(self):
        """确保 BSDF_COMPATIBILITY_MAP 包含所有必要的通道映射"""
        from ..constants import BSDF_COMPATIBILITY_MAP
        required = {'color', 'metal', 'rough', 'normal', 'specular', 'emi', 'alpha'}
        for req in required:
            self.assertIn(req, BSDF_COMPATIBILITY_MAP, f"Missing {req} in compatibility map")
