import unittest
import bpy
from .helpers import cleanup_scene, create_test_object, get_job_setting
from ..core import node_manager, engine, image_manager

class TestShadingComplexity(unittest.TestCase):
    def setUp(self):
        cleanup_scene()

    def test_no_bsdf_material(self):
        """测试只有发射节点（无 Principled BSDF）的材质"""
        obj = create_test_object("NoBSDF")
        mat = obj.data.materials[0]
        nodes = mat.node_tree.nodes
        nodes.clear()
        
        emi = nodes.new('ShaderNodeEmission')
        out = nodes.new('ShaderNodeOutputMaterial')
        mat.node_tree.links.new(emi.outputs[0], out.inputs[0])
        
        handler = node_manager.NodeGraphHandler([mat])
        img = image_manager.set_image("TestNoBSDF", 32, 32)
        
        with handler:
            # 应该能回退到默认颜色或找到 Emission 节点（取决于实现）
            # 目前的实现主要寻找 Principled BSDF，如果没有，会尝试通过 _find_socket_source 获取默认值
            handler.setup_for_pass('EMIT', 'color', img)
            # 验证 links 是否建立
            self.assertTrue(out.inputs[0].is_linked)

    def test_nested_node_groups(self):
        """测试嵌套节点组的烘焙能力"""
        obj = create_test_object("NestedNG")
        mat = obj.data.materials[0]
        
        # 创建内层节点组
        inner_ng = bpy.data.node_groups.new("Inner", 'ShaderNodeTree')
        if bpy.app.version >= (4, 0, 0):
            inner_ng.interface.new_socket(name="Out", in_out='OUTPUT', socket_type='NodeSocketColor')
        else:
            inner_ng.outputs.new('NodeSocketColor', "Out")
        
        # 创建外层节点组
        outer_ng = bpy.data.node_groups.new("Outer", 'ShaderNodeTree')
        if bpy.app.version >= (4, 0, 0):
            outer_ng.interface.new_socket(name="Final", in_out='OUTPUT', socket_type='NodeSocketColor')
        else:
            outer_ng.outputs.new('NodeSocketColor', "Final")
        
        inner_node = outer_ng.nodes.new('ShaderNodeGroup')
        inner_node.node_tree = inner_ng
        
        # 烘焙设置指向外层
        s = get_job_setting()
        c = s.channels.add()
        c.id = 'node_group'; c.enabled = True
        c.node_group = outer_ng.name
        c.node_group_output = "Final"
        
        handler = node_manager.NodeGraphHandler([mat])
        img = image_manager.set_image("TestNestedNG", 32, 32)
        with handler:
            handler.setup_for_pass('EMIT', 'node_group', img, channel_settings=c)
            # 确保外部节点组被正确实例化
            self.assertTrue(any(n.bl_idname == 'ShaderNodeGroup' and n.node_tree == outer_ng 
                               for n in mat.node_tree.nodes))

    def test_illegal_material_indices(self):
        """测试网格面引用了不存在的材质槽位"""
        obj = create_test_object("IllegalIndex")
        # 制造只有 1 个槽位但面索引为 5 的情况
        obj.data.polygons[0].material_index = 5
        
        s = get_job_setting()
        # 验证 TaskBuilder 是否能处理超过索引范围的情况
        tasks = engine.TaskBuilder.build(bpy.context, s, [obj], obj)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(len(tasks[0].materials), 1)

    def test_empty_object_no_materials(self):
        """测试完全没有材质槽位的物体"""
        bpy.ops.mesh.primitive_cube_add()
        obj = bpy.context.active_object
        obj.data.materials.clear()
        
        s = get_job_setting()
        tasks = engine.TaskBuilder.build(bpy.context, s, [obj], obj)
        # 不应崩溃，materials 列表应为空
        self.assertEqual(len(tasks[0].materials), 0)
        
        # 进一步验证 NodeGraphHandler 是否能处理空列表
        handler = node_manager.NodeGraphHandler(tasks[0].materials)
        with handler:
            self.assertEqual(len(handler.materials), 0)
