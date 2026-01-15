import unittest
import bpy
from .helpers import cleanup_scene, create_test_object, get_job_setting
from ..core import node_manager, image_manager

class TestNodeCompatibility(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        self.obj = create_test_object("NodeCompObj")
        self.mat = self.obj.data.materials[0]
        self.handler = node_manager.NodeGraphHandler([self.mat])
        self.img = image_manager.set_image("TestNodeImg", 32, 32)

    def test_geometry_node_naming(self):
        """验证 Geometry 节点的命名兼容性 (Blender 3.6 - 5.0)"""
        with self.handler:
            # 尝试创建 Geometry 节点
            # 注意：我们将测试 ShaderNodeNewGeometry 是否在当前版本有效
            try:
                node = self.mat.node_tree.nodes.new('ShaderNodeNewGeometry')
                self.assertIsNotNone(node)
                self.assertIn('Position', node.outputs)
            except RuntimeError:
                # 如果 ShaderNodeNewGeometry 失败，尝试 ShaderNodeGeometry
                node = self.mat.node_tree.nodes.new('ShaderNodeGeometry')
                self.assertIsNotNone(node)
                self.assertIn('Position', node.outputs)

    def test_principled_bsdf_sockets(self):
        """验证 Principled BSDF 插槽名称的跨版本稳定性 (重点 4.0+ 迁移)"""
        nodes = self.mat.node_tree.nodes
        bsdf = next((n for n in nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled'), None)
        self.assertIsNotNone(bsdf)
        
        # 4.0+ 关键插槽检测
        expected_sockets = ['Base Color', 'Roughness', 'Metallic']
        if bpy.app.version >= (4, 0, 0):
            # 4.0+ 特有/更名的插槽
            expected_sockets.extend(['Specular IOR Level', 'Coat Weight'])
        else:
            # 旧版插槽
            expected_sockets.extend(['Specular', 'Clearcoat'])
            
        for s_name in expected_sockets:
            self.assertIn(s_name, bsdf.inputs, f"Socket '{s_name}' not found in Principled BSDF for Blender {bpy.app.version_string}")

    def test_mesh_map_nodes_creation(self):
        """验证所有 Mesh Map 相关的节点创建逻辑"""
        with self.handler:
            # 测试 AO 节点
            src = self.handler._create_mesh_map_logic(self.mat, 'AO', None, None)
            self.assertIsNotNone(src)
            self.assertEqual(src.node.bl_idname, 'ShaderNodeAmbientOcclusion')
            
            # 测试 Bevel 节点 (仅 Cycles 支持，但节点创建应成功)
            src = self.handler._create_mesh_map_logic(self.mat, 'BEVEL', None, None)
            self.assertIsNotNone(src)
            self.assertEqual(src.node.bl_idname, 'ShaderNodeBevel')

    def test_pbr_conversion_nodes_4_0_plus(self):
        """测试 4.0+ 下 PBR 转换逻辑中使用的 ShaderNodeMix (取代了 ShaderNodeMixRGB)"""
        if bpy.app.version >= (4, 0, 0):
            with self.handler:
                # 模拟 PBR BaseColor 转换逻辑
                # 它应该使用 ShaderNodeMix 且 data_type 为 'RGBA'
                src = self.handler._create_extension_logic(self.mat, 'pbr_conv_base', get_job_setting())
                self.assertIsNotNone(src)
                # 在 4.0+ 中，MixRGB 已被 Mix 节点取代
                self.assertEqual(src.node.bl_idname, 'ShaderNodeMix')
                self.assertEqual(src.node.data_type, 'RGBA')
