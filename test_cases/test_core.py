import unittest
import bpy
import os
import tempfile
import shutil
import numpy as np
from .helpers import cleanup_scene, create_test_object, get_job_setting
from ..core import image_manager, uv_manager, math_utils, common
from .. import ops

class TestNodeGraphLogic(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        self.obj = create_test_object("NodeTestObj")
        self.mat = self.obj.data.materials[0]
        self.handler = ops.NodeGraphHandler([self.mat])
        self.handler.__enter__()
        self.img = image_manager.set_image("TestImg", 128, 128)
        
    def tearDown(self):
        self.handler.__exit__(None, None, None)
        
    def test_normal_map_setup(self):
        self.img = image_manager.set_image("TestImg_Nor", 128, 128, space='Non-Color')
        self.handler.setup_for_pass('NORMAL', 'normal', self.img)
        tree = self.mat.node_tree
        tex_node = tree.nodes.active
        self.assertEqual(tex_node.bl_idname, 'ShaderNodeTexImage')
        self.assertEqual(tex_node.image, self.img)
        
    def test_ao_map_setup(self):
        self.handler.setup_for_pass('EMIT', 'ao', self.img, mesh_type='AO')
        tree = self.mat.node_tree
        ao_nodes = [n for n in tree.nodes if n.bl_idname == 'ShaderNodeAmbientOcclusion']
        self.assertTrue(len(ao_nodes) > 0)
        emi_node = self.handler.session_nodes[self.mat]['emi']
        linked = any(l.from_node == ao_nodes[0] and l.to_node == emi_node for l in tree.links)
        self.assertTrue(linked)

class TestUDIMLogic(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        
    def create_mesh_with_uv(self, name, uv_offset=(0,0)):
        bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
        obj = bpy.context.view_layer.objects.active
        obj.name = name
        if not obj.data.uv_layers: obj.data.uv_layers.new()
        uv_layer = obj.data.uv_layers.active.data
        for loop in uv_layer:
            loop.uv[0] += uv_offset[0]
            loop.uv[1] += uv_offset[1]
        return obj

    def test_detect_tile(self):
        obj = self.create_mesh_with_uv("Obj_1012", uv_offset=(1.1, 1.1))
        self.assertEqual(uv_manager.detect_object_udim_tile(obj), 1012)

class TestPBRConversion(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        
    def test_pbr_conversion_logic(self):
        spec = image_manager.set_image("Mock_Spec", 32, 32, basiccolor=(0.5, 0.5, 0.5, 1.0))
        diff = image_manager.set_image("Mock_Diff", 32, 32, basiccolor=(1.0, 0.0, 0.0, 1.0))
        target = image_manager.set_image("Mock_Target", 32, 32)
        
        expected_metal = (0.5 - 0.04) / (1.0 - 0.04)
        math_utils.process_pbr_numpy(target, spec, diff, 'pbr_conv_metal', threshold=0.04)
        
        arr = np.empty(32*32*4, dtype=np.float32)
        target.pixels.foreach_get(arr)
        avg = np.mean(arr.reshape(-1, 4), axis=0)
        self.assertTrue(abs(avg[0] - expected_metal) < 0.02)

class TestAnimationSystem(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        if os.path.exists(self.temp_dir): shutil.rmtree(self.temp_dir)
            
    def test_sequence_filename_generation(self):
        img = image_manager.set_image("AnimTest", 32, 32)
        save_path = image_manager.save_image(img, path=self.temp_dir, motion=True, frame=10)
        self.assertTrue(save_path.endswith("AnimTest_0010.png"))

class TestUVDataManipulation(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        bpy.ops.mesh.primitive_plane_add()
        self.obj = bpy.context.active_object
        
    def test_smart_uv_creation(self):
        s = get_job_setting()
        s.use_auto_uv = True
        with ops.UVLayoutManager([self.obj], s):
            self.assertEqual(self.obj.data.uv_layers.active.name, "BT_Bake_Temp_UV")
        self.assertNotEqual(self.obj.data.uv_layers.active.name, "BT_Bake_Temp_UV")

class TestEmergencyCleanup(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        
    def test_cleanup_temp_data(self):
        obj = create_test_object("JunkObj")
        obj.data.uv_layers.new(name="BT_Bake_Temp_UV")
        bpy.data.images.new("BT_Protection_Dummy", 32, 32)
        
        from ..core import cleanup
        bpy.ops.bake.emergency_cleanup()
        
        self.assertNotIn("BT_Bake_Temp_UV", [l.name for l in obj.data.uv_layers])
        self.assertNotIn("BT_Protection_Dummy", [i.name for i in bpy.data.images])

class TestApplyBakedResult(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        self.obj = create_test_object("Original")
        self.img = image_manager.set_image("Baked_Color", 32, 32)
        
    def test_apply_single_object(self):
        baked_images = {'color': self.img}
        setting = get_job_setting()
        new_obj = common.apply_baked_result(self.obj, baked_images, setting, "TestBake")
        self.assertIsNotNone(new_obj)
        self.assertEqual(len(new_obj.data.materials), 1)

class TestNodeGroupChannel(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        self.obj = create_test_object("NG_Obj")
        self.mat = self.obj.data.materials[0]
        self.ng = bpy.data.node_groups.new("TestGroup", 'ShaderNodeTree')
        if bpy.app.version >= (4, 0, 0):
            self.ng.interface.new_socket(name="MyOutput", in_out='OUTPUT', socket_type='NodeSocketColor')
        else:
            self.ng.outputs.new('NodeSocketColor', "MyOutput")
        
    def test_node_group_baking_setup(self):
        s = get_job_setting()
        c = s.channels.add()
        c.id = 'node_group'; c.enabled = True
        c.node_group = self.ng.name; c.node_group_output = "MyOutput"
        img = image_manager.set_image("NG_Bake", 64, 64)
        
        with ops.NodeGraphHandler([self.mat]) as h:
            h.setup_for_pass('EMIT', 'node_group', img, channel_settings=c)
            tree = self.mat.node_tree
            out_node = next(n for n in tree.nodes if n.bl_idname == 'ShaderNodeOutputMaterial' and n.is_active_output)
            emi_node = out_node.inputs[0].links[0].from_node
            group_node = emi_node.inputs[0].links[0].from_node
            self.assertEqual(group_node.node_tree, self.ng)
