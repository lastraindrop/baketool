import unittest
import bpy
from .helpers import cleanup_scene, create_test_object, get_job_setting
from ..core import common

class TestRefactorIntegrity(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        self.setting = get_job_setting()

    def test_non_destructive_channel_sync(self):
        """验证切换烘焙类型时，原有通道数据是否被保留（仅标记为无效而不删除）"""
        s = self.setting
        s.bake_type = 'BSDF'
        common.reset_channels_logic(s)
        
        # 1. 在 BSDF 模式下修改 color 通道的后缀
        color_chan = next(c for c in s.channels if c.id == 'color')
        color_chan.suffix = "_BSDF_SPECIFIC"
        
        # 2. 切换到 BASIC 模式（该模式通常不包含特定的 BSDF 通道）
        s.bake_type = 'BASIC'
        common.reset_channels_logic(s)
        
        # 验证 color 通道依然存在但可能被隐藏（valid_for_mode 为 True，因为 BASIC 也有 color）
        # 让我们找一个只有 BSDF 有而 BASIC 没有的通道，例如 'metal'
        metal_chan = next((c for c in s.channels if c.id == 'metal'), None)
        self.assertIsNotNone(metal_chan)
        self.assertFalse(metal_chan.valid_for_mode) # 它应该被标记为无效
        
        # 修改这个“无效”通道的参数
        metal_chan.suffix = "_HIDDEN_DATA"
        
        # 3. 切回 BSDF 模式
        s.bake_type = 'BSDF'
        common.reset_channels_logic(s)
        
        # 验证数据是否找回
        self.assertTrue(metal_chan.valid_for_mode)
        self.assertEqual(metal_chan.suffix, "_HIDDEN_DATA")
        self.assertEqual(color_chan.suffix, "_BSDF_SPECIFIC")

    def test_multi_material_slot_consistency(self):
        """测试：一个物体有多个材质槽，其中某些材质是共享的，某些是唯一的"""
        obj1 = create_test_object("Obj1", mat_count=3)
        # 共享一个材质
        obj2 = create_test_object("Obj2")
        obj2.data.materials[0] = obj1.data.materials[0]
        
        from ..core.engine import TaskBuilder
        tasks = TaskBuilder.build(bpy.context, self.setting, [obj1, obj2], obj1)
        
        # 验证任务拆分是否正确（单物体模式下应为两个任务）
        self.assertEqual(len(tasks), 2)
        # 验证材质收集是否去重
        all_mats = set(tasks[0].materials)
        self.assertEqual(len(all_mats), 3)

class TestVersionCompatibility(unittest.TestCase):
    def test_scene_context_mapping(self):
        """测试 SceneSettingsContext 在不同属性路径下的映射安全性"""
        from ..core.common import SceneSettingsContext
        
        # 模拟 5.0 的 BakeSettings 访问（如果环境支持）
        ctx = SceneSettingsContext('bake', {'margin': 10})
        target = ctx._get_target()
        
        if hasattr(bpy.context.scene.render, "bake"):
            self.assertEqual(target, bpy.context.scene.render.bake)
        else:
            self.assertEqual(target, bpy.context.scene.render)
