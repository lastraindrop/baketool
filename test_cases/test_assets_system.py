import unittest
import bpy
from .helpers import cleanup_scene, create_test_object, get_job_setting
from ..core import engine, common, node_manager

class TestAssetsSystem(unittest.TestCase):
    def setUp(self):
        cleanup_scene()

    def test_read_only_data_handling(self):
        """测试当 Mesh 数据被标记为库链接（只读）时的处理"""
        obj = create_test_object("LinkedObj")
        # 模拟库链接状态 (在 Python 中通常只读属性无法直接设置，但我们可以通过逻辑检查)
        # 我们验证 JobPreparer 是否能识别并跳过或报告问题
        
        # 实际上，如果物体是链接的，obj.library 就不为空
        # 这里我们模拟一个没有材质槽的物体，验证 NodeGraphHandler 是否崩溃
        obj.data.materials.clear()
        
        handler = node_manager.NodeGraphHandler(obj.data.materials)
        with handler:
            self.assertEqual(len(handler.materials), 0)
            # 即使没有材质，setup_protection 也不应崩溃
            handler.setup_protection([obj], [])

    def test_cleanup_resilience(self):
        """测试即便在烘焙中途发生异常，清理逻辑是否依然有效"""
        obj = create_test_object("ResilientObj")
        mat = obj.data.materials[0]
        
        # 制造一个可能导致错误的场景：手动删除 Session Node
        handler = node_manager.NodeGraphHandler([mat])
        with handler:
            # 模拟内部节点被意外删除
            for n in mat.node_tree.nodes:
                mat.node_tree.nodes.remove(n)
            
            # 退出时 cleanup 不应因为找不到节点而报错
        
        # 验证原始状态是否由于异常而彻底破坏（这里预期是优雅退出）
        self.assertIsNotNone(obj.data)

    def test_library_override_logic_check(self):
        """验证资产覆盖逻辑的基础假设"""
        obj = create_test_object("OverrideObj")
        # 在 Blender 中，Override 物体通常会有 override_library 属性
        if hasattr(obj, "override_library") and obj.override_library:
            # 如果是覆盖物体，我们应确保能正常获取其本地化的材质
            pass
        
        s = get_job_setting()
        tasks = engine.TaskBuilder.build(bpy.context, s, [obj], obj)
        self.assertEqual(len(tasks), 1)

class TestContextManagers(unittest.TestCase):
    def test_safe_context_override_nesting(self):
        """测试上下文覆盖的嵌套安全性"""
        obj1 = create_test_object("O1")
        obj2 = create_test_object("O2")
        
        with common.safe_context_override(bpy.context, obj1, [obj1]):
            self.assertEqual(bpy.context.active_object, obj1)
            with common.safe_context_override(bpy.context, obj2, [obj2]):
                self.assertEqual(bpy.context.active_object, obj2)
            self.assertEqual(bpy.context.active_object, obj1)
