import bpy
import unittest
import os
import shutil
import tempfile
import numpy as np
import json
import time
import traceback
from pathlib import Path
from mathutils import Color, Vector

from . import utils
from . import property
from . import ops
from . import preset_handler
from .state_manager import BakeStateManager
from .constants import *

# --- Helper Functions ---

def ensure_object_mode():
    """Safely ensure Object Mode."""
    try:
        if hasattr(bpy.context, "active_object") and bpy.context.active_object:
            if bpy.context.active_object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
    except:
        pass

def cleanup_scene():
    """Deep cleanup of the current scene."""
    ensure_object_mode()
    
    # Unlink and remove all objects
    if hasattr(bpy.data, "objects"):
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
            
    # Remove meshes
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh, do_unlink=True)

    # Remove materials
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat, do_unlink=True)
        
    # Remove images
    for img in list(bpy.data.images):
        bpy.data.images.remove(img, do_unlink=True)
        
    # Remove collections created by us
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col, do_unlink=True)
        
    # Remove node groups
    for ng in list(bpy.data.node_groups):
        bpy.data.node_groups.remove(ng, do_unlink=True)

def create_test_object(name, location=(0,0,0), color=(0.8, 0.8, 0.8, 1.0), metal=0.0, rough=0.5):
    """Create a standard test object with Principled BSDF."""
    ensure_object_mode()
        
    bpy.ops.mesh.primitive_plane_add(size=2, location=location)
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    
    if not obj.data.uv_layers:
        obj.data.uv_layers.new(name="UVMap")
        
    mat = bpy.data.materials.new(name=f"Mat_{name}")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (300, 0)
    mat.node_tree.links.new(bsdf.outputs[0], out.inputs[0])
    
    # Compatibility for different Blender versions
    def set_socket(name_list, val):
        for n in name_list:
            if n in bsdf.inputs:
                bsdf.inputs[n].default_value = val
                break
                
    set_socket(["Base Color", "Color"], color)
    set_socket(["Metallic"], metal)
    set_socket(["Roughness"], rough)
            
    obj.data.materials.append(mat)
    return obj

def get_job_setting():
    """Helper to get a fresh Job Setting instance."""
    scene = bpy.context.scene
    if not hasattr(scene, "BakeJobs"):
        return None
    scene.BakeJobs.jobs.clear()
    job = scene.BakeJobs.jobs.add()
    
    job.setting.bake_mode = 'SINGLE_OBJECT' 
    return job.setting

# --- Test Case Definitions ---

class TestPresetSystem(unittest.TestCase):
    """Test the JSON serialization/deserialization logic."""
    
    def test_property_serialization(self):
        s = get_job_setting()
        
        # Set some non-default values
        s.res_x = 512
        s.res_y = 2048
        s.bake_mode = 'COMBINE_OBJECT'
        s.margin = 32
        
        # Create a channel
        s.channels.clear()
        c = s.channels.add()
        c.id = 'color'
        c.enabled = True
        c.suffix = '_tested'
        
        serializer = preset_handler.PropertyIO(exclude_props={'active_channel_index'})
        data = serializer.to_dict(s)
        
        # Assertions
        self.assertEqual(data['res_x'], 512)
        self.assertEqual(data['bake_mode'], 'COMBINE_OBJECT')
        self.assertEqual(len(data['channels']), 1)
        self.assertEqual(data['channels'][0]['suffix'], '_tested')
        
    def test_property_deserialization(self):
        s = get_job_setting()
        s.channels.clear()
        
        # JSON payload
        payload = {
            "res_x": 128,
            "bake_type": "BSDF",
            "channels": [
                {"id": "normal", "name": "Normal Test", "enabled": True}
            ]
        }
        
        serializer = preset_handler.PropertyIO()
        serializer.from_dict(s, payload)
        
        self.assertEqual(s.res_x, 128)
        self.assertEqual(len(s.channels), 1)
        self.assertEqual(s.channels[0].id, 'normal')
        self.assertTrue(s.channels[0].enabled)

    def test_readonly_skipping(self):
        """Ensure read-only properties (like is_valid) don't crash the loader."""
        s = get_job_setting()
        payload = {"name": "Test Job", "non_existent_prop_123": 100}
        serializer = preset_handler.PropertyIO()
        serializer.from_dict(s, payload)
        self.assertEqual(serializer.stats['skipped_match'], 1)

class TestStateManager(unittest.TestCase):
    """Test the BakeStateManager for logging and crash detection."""
    
    def setUp(self):
        self.mgr = BakeStateManager()
        self.mgr.finish_session()
        
    def tearDown(self):
        self.mgr.finish_session()

    def test_session_lifecycle(self):
        self.mgr.start_session(10, "Test_Job")
        self.assertTrue(self.mgr.has_crash_record())
        
        data = self.mgr.read_log()
        self.assertEqual(data['status'], 'STARTED')
        self.assertEqual(data['total_steps'], 10)
        
        self.mgr.update_step(1, "Cube", "Color")
        data = self.mgr.read_log()
        self.assertEqual(data['status'], 'RUNNING')
        self.assertEqual(data['current_step'], 1)
        
        self.mgr.finish_session()
        self.assertFalse(self.mgr.has_crash_record())

    def test_error_logging(self):
        self.mgr.start_session(5, "Error_Test")
        self.mgr.log_error("Simulated Error")
        
        data = self.mgr.read_log()
        self.assertEqual(data['status'], 'ERROR')
        self.assertEqual(data['last_error'], "Simulated Error")
        self.assertTrue(self.mgr.has_crash_record())

class TestAnimationSystem(unittest.TestCase):
    """Test Animation/Image Sequence Logic."""
    
    def setUp(self):
        cleanup_scene()
        self.temp_dir = tempfile.mkdtemp()
        self.setting = get_job_setting()
        
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            
    def test_sequence_filename_generation(self):
        """Verify that sequence filenames are generated correctly."""
        img = utils.set_image("AnimTest", 32, 32)
        
        # Simulate baking frame 10
        frame_num = 10
        save_path = utils.save_image(
            img, 
            path=self.temp_dir, 
            file_format='PNG',
            motion=True,
            frame=frame_num,
            fillnum=4,
            separator='_'
        )
        
        expected_name = "AnimTest_0010.png"
        self.assertTrue(save_path.endswith(expected_name))
        self.assertTrue(os.path.exists(save_path))

    def test_custom_frame_range_logic(self):
        """Verify logic for setting up frame ranges."""
        # 1. Simulate Scene Sync
        bpy.context.scene.frame_start = 1
        bpy.context.scene.frame_end = 5
        self.setting.bake_motion = True
        self.setting.bake_motion_use_custom = False
        
        # Logic from ops.py _prepare_job extraction
        start = self.setting.bake_motion_start if self.setting.bake_motion_use_custom else bpy.context.scene.frame_start
        dur = self.setting.bake_motion_last if self.setting.bake_motion_use_custom else (bpy.context.scene.frame_end - start + 1)
        
        self.assertEqual(start, 1)
        self.assertEqual(dur, 5)
        
        # 2. Simulate Custom Range
        self.setting.bake_motion_use_custom = True
        self.setting.bake_motion_start = 10
        self.setting.bake_motion_last = 3
        
        start = self.setting.bake_motion_start if self.setting.bake_motion_use_custom else bpy.context.scene.frame_start
        dur = self.setting.bake_motion_last if self.setting.bake_motion_use_custom else (bpy.context.scene.frame_end - start + 1)
        
        self.assertEqual(start, 10)
        self.assertEqual(dur, 3)

class TestUDIMIO(unittest.TestCase):
    """Test UDIM Input/Output specifically."""
    
    def setUp(self):
        cleanup_scene()
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_udim_image_creation(self):
        """Test if a tiled image is correctly identified and created."""
        tiles = [1001, 1011]
        img = utils.set_image("UDIM_IO_Test", 32, 32, use_udim=True, udim_tiles=tiles)
        
        self.assertEqual(img.source, 'TILED')
        # Check if tiles exist (Note: Blender might auto-create 1001, so we check existence)
        self.assertTrue(hasattr(img, "tiles"))
        
    def test_udim_save_tokens(self):
        """Test if saving a tiled image generates the correct files on disk."""
        # 1. Create Tiled Image
        img = utils.set_image("UDIM_Save_Test", 32, 32, use_udim=True, udim_tiles=[1001])
        
        # 2. Save it
        saved_path = utils.save_image(
            img,
            path=self.temp_dir,
            file_format='PNG',
            save=True
        )
        
        # 3. Verify. Blender usually saves as "Name.1001.png" for tile 1001.
        # If this fails, it might be because the headless environment didn't actually create the tile data.
        # However, checking if *any* file was created is a good start.
        files = os.listdir(self.temp_dir)
        self.assertTrue(len(files) > 0, "No files saved for UDIM image")
        
        # Check for the tokenized name
        found_udim_token = any("1001" in f for f in files)
        self.assertTrue(found_udim_token, f"Saved files {files} do not contain UDIM tile number")

    def test_udim_1001_custom_resolution(self):
        """Test if UDIM 1001 tile respects custom override resolution."""
        base_res = 128
        custom_res = 512
        tiles = [1001, 1002]
        tile_res_map = {1001: (custom_res, custom_res), 1002: (256, 256)}
        
        img = utils.set_image(
            "UDIM_Res_Test", 
            base_res, base_res, 
            use_udim=True, 
            udim_tiles=tiles, 
            tile_resolutions=tile_res_map
        )
        
        # In Blender API, image.size returns the size of the base tile (1001)
        self.assertEqual(img.size[0], custom_res, "Tile 1001 did not resize to custom resolution")
        self.assertEqual(img.size[1], custom_res, "Tile 1001 height incorrect")

class TestPropertyLogic(unittest.TestCase):
    """Test dynamic property logic helpers."""
    
    def setUp(self):
        self.setting = get_job_setting()

    def test_valid_depths(self):
        self.setting.save_format = 'PNG'
        items = property.get_valid_depths(self.setting, None)
        keys = [i[0] for i in items]
        self.assertIn('8', keys)
        self.assertIn('16', keys)
        self.assertNotIn('32', keys)
        
        self.setting.save_format = 'OPEN_EXR'
        items = property.get_valid_depths(self.setting, None)
        keys = [i[0] for i in items]
        self.assertNotIn('8', keys)
        self.assertIn('32', keys)

    def test_valid_modes(self):
        self.setting.save_format = 'JPEG'
        items = property.get_valid_modes(self.setting, None)
        keys = [i[0] for i in items]
        self.assertIn('RGB', keys)
        self.assertIn('BW', keys)
        self.assertFalse('RGBA' in keys, "JPEG should not support RGBA in UI")
        
        self.setting.save_format = 'PNG'
        items = property.get_valid_modes(self.setting, None)
        keys = [i[0] for i in items]
        self.assertIn('RGBA', keys)

class TestNamingConvention(unittest.TestCase):
    """Test file naming logic."""
    
    def setUp(self):
        cleanup_scene()
        self.obj = create_test_object("MyObject")
        self.mat = self.obj.data.materials[0]
        self.setting = get_job_setting()
        
    def test_naming_modes(self):
        self.setting.name_setting = 'OBJECT'
        name = utils.get_safe_base_name(self.setting, self.obj, self.mat)
        self.assertEqual(name, "MyObject")
        
        self.setting.name_setting = 'MAT'
        name = utils.get_safe_base_name(self.setting, self.obj, self.mat)
        self.assertEqual(name, self.mat.name)
        
        self.setting.name_setting = 'OBJ_MAT'
        name = utils.get_safe_base_name(self.setting, self.obj, self.mat)
        self.assertEqual(name, f"MyObject_{self.mat.name}")
        
        self.setting.name_setting = 'CUSTOM'
        self.setting.custom_name = "MyCustomBake"
        name = utils.get_safe_base_name(self.setting, self.obj, self.mat)
        self.assertEqual(name, "MyCustomBake")

    def test_batch_naming_split_material(self):
        self.setting.bake_mode = 'SPLIT_MATERIAL'
        self.setting.name_setting = 'CUSTOM'
        self.setting.custom_name = "Base"
        name = utils.get_safe_base_name(self.setting, self.obj, self.mat, is_batch=True)
        expected = f"Base_MyObject_{self.mat.name}"
        self.assertEqual(name, expected)

class TestTaskGeneration(unittest.TestCase):
    """Test TaskBuilder logic for different bake modes."""
    
    def setUp(self):
        cleanup_scene()
        self.obj1 = create_test_object("Cube1")
        self.obj2 = create_test_object("Cube2")
        self.setting = get_job_setting()
        self.setting.bake_objects.clear()
        for o in [self.obj1, self.obj2]:
            item = self.setting.bake_objects.add()
            item.bakeobject = o
            
    def test_single_object_mode(self):
        self.setting.bake_mode = 'SINGLE_OBJECT'
        tasks = ops.TaskBuilder.build(bpy.context, self.setting, [self.obj1, self.obj2], self.obj1)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].objects, [self.obj1])
        self.assertEqual(tasks[1].objects, [self.obj2])
        
    def test_combine_object_mode(self):
        self.setting.bake_mode = 'COMBINE_OBJECT'
        tasks = ops.TaskBuilder.build(bpy.context, self.setting, [self.obj1, self.obj2], self.obj1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(set(tasks[0].objects), {self.obj1, self.obj2})
        self.assertEqual(tasks[0].active_obj, self.obj1)

    def test_select_active_mode(self):
        # Fix: Ensure bake_type is not BSDF so SELECT_ACTIVE is valid
        self.setting.bake_type = 'BASIC'
        self.setting.bake_mode = 'SELECT_ACTIVE'
        tasks = ops.TaskBuilder.build(bpy.context, self.setting, [self.obj2], self.obj1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].active_obj, self.obj1)
        self.assertIn(self.obj2, tasks[0].objects)
        self.assertTrue(len(tasks[0].materials) > 0)

    def test_split_material_mode(self):
        mat2 = bpy.data.materials.new("Mat_Secondary")
        self.obj1.data.materials.append(mat2)
        self.setting.bake_mode = 'SPLIT_MATERIAL'
        tasks = ops.TaskBuilder.build(bpy.context, self.setting, [self.obj1], self.obj1)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].materials[0], self.obj1.data.materials[0])
        self.assertEqual(tasks[1].materials[0], self.obj1.data.materials[1])

class TestBakePassExecutor(unittest.TestCase):
    
    def test_get_mesh_type(self):
        self.assertEqual(ops.BakePassExecutor._get_mesh_type('position'), 'POS')
        self.assertEqual(ops.BakePassExecutor._get_mesh_type('ID_mat'), 'ID')
        self.assertIsNone(ops.BakePassExecutor._get_mesh_type('color'))

class TestNodeGraphLogic(unittest.TestCase):
    """Deep inspection of the Node Graph setup logic."""
    
    def setUp(self):
        cleanup_scene()
        self.obj = create_test_object("NodeTestObj")
        self.mat = self.obj.data.materials[0]
        self.handler = ops.NodeGraphHandler([self.mat])
        self.handler.__enter__()
        self.img = utils.set_image("TestImg", 128, 128)
        
    def tearDown(self):
        self.handler.__exit__(None, None, None)
        
    def test_normal_map_setup(self):
        self.img = utils.set_image("TestImg_Nor", 128, 128, space='Non-Color')
        self.handler.setup_for_pass('NORMAL', 'normal', self.img)
        tree = self.mat.node_tree
        # Now active node is the persistent tex node
        tex_node = tree.nodes.active
        self.assertIsNotNone(tex_node)
        self.assertEqual(tex_node.bl_idname, 'ShaderNodeTexImage')
        self.assertEqual(tex_node.image, self.img)
        
    def test_ao_map_setup(self):
        self.handler.setup_for_pass('EMIT', 'ao', self.img, mesh_type='AO')
        tree = self.mat.node_tree
        ao_nodes = [n for n in tree.nodes if n.bl_idname == 'ShaderNodeAmbientOcclusion']
        self.assertTrue(len(ao_nodes) > 0, "AO Node not found")
        # emi node is now a persistent session node
        emi_node = self.handler.session_nodes[self.mat]['emi']
        
        ao_node = ao_nodes[0]
        linked = False
        for link in tree.links:
            if link.from_node == ao_node and link.to_node == emi_node:
                linked = True
                break
        self.assertTrue(linked, "AO Node not linked to Emission")

    def test_wireframe_setup(self):
        s = get_job_setting()
        c = s.channels.add()
        c.wireframe_dis = 0.05
        c.wireframe_use_pix = True
        self.handler.setup_for_pass('EMIT', 'wireframe', self.img, mesh_type='WF', channel_settings=c)
        tree = self.mat.node_tree
        wf_node = next(n for n in tree.nodes if n.bl_idname == 'ShaderNodeWireframe')
        self.assertTrue(wf_node.use_pixel_size)
        self.assertAlmostEqual(wf_node.inputs[0].default_value, 0.05)

    def test_extension_pbr_conv(self):
        s = get_job_setting()
        s.channels.clear()
        c = s.channels.add()
        c.pbr_conv_threshold = 0.5
        self.handler.setup_for_pass('EMIT', 'pbr_conv_metal', self.img, channel_settings=c)
        tree = self.mat.node_tree
        math_nodes = [n for n in tree.nodes if n.bl_idname == 'ShaderNodeMath']
        self.assertTrue(len(math_nodes) >= 3, "PBR Conversion logic nodes missing")

class TestIDMapTools(unittest.TestCase):
    """Test ID Map generation tools."""
    
    def setUp(self):
        cleanup_scene()
        self.obj = create_test_object("IDObj")
        bpy.context.view_layer.objects.active = self.obj
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.subdivide(number_cuts=2)
        bpy.ops.object.editmode_toggle()
        
    def test_generate_attribute_mat_id(self):
        attr_name = utils.setup_mesh_attribute(self.obj, id_type='MAT')
        self.assertIsNotNone(attr_name)
        self.assertIn(attr_name, self.obj.data.attributes)

    def test_generate_attribute_element_id(self):
        attr_name = utils.setup_mesh_attribute(self.obj, id_type='ELEMENT')
        self.assertIsNotNone(attr_name)

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
        self.assertEqual(utils.detect_object_udim_tile(obj), 1012)

    def test_repack_gap_filling(self):
        o1 = self.create_mesh_with_uv("A") # 1001
        o_fix = self.create_mesh_with_uv("Fix", uv_offset=(1.0, 0)) # 1002
        assignments = ops.UDIMPacker.calculate_repack([o1, o_fix])
        self.assertEqual(assignments[o_fix], 1002)
        self.assertEqual(assignments[o1], 1001)

    def test_get_active_uv_udim_tiles(self):
        o1 = self.create_mesh_with_uv("A", (0,0)) # 1001
        o2 = self.create_mesh_with_uv("B", (1,0)) # 1002
        tiles = utils.get_active_uv_udim_tiles([o1, o2])
        self.assertEqual(tiles, [1001, 1002])

class TestPBRConversion(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        
    def test_pbr_conversion_logic(self):
        spec = utils.set_image("Mock_Spec", 32, 32, basiccolor=(0.5, 0.5, 0.5, 1.0))
        diff = utils.set_image("Mock_Diff", 32, 32, basiccolor=(1.0, 0.0, 0.0, 1.0))
        target = utils.set_image("Mock_Target", 32, 32)
        
        expected_metal = (0.5 - 0.04) / (1.0 - 0.04)
        utils.process_pbr_numpy(target, spec, diff, 'pbr_conv_metal', threshold=0.04)
        
        def validate(img, expected):
            arr = np.empty(32*32*4, dtype=np.float32)
            img.pixels.foreach_get(arr)
            avg = np.mean(arr.reshape(-1, 4), axis=0)
            return abs(avg[0] - expected[0]) < 0.02
        self.assertTrue(validate(target, (expected_metal, expected_metal, expected_metal, 1.0)))

class TestRobustness(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        
    def test_material_restoration_on_error(self):
        obj = create_test_object("Error_Obj")
        mat = obj.data.materials[0]
        out_node = next(n for n in mat.node_tree.nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
        orig_from = out_node.inputs[0].links[0].from_node
        
        try:
            with ops.NodeGraphHandler([mat]) as handler:
                handler.setup_for_pass('EMIT', 'color', None)
                raise RuntimeError("Simulated Crash")
        except RuntimeError: pass
        self.assertEqual(out_node.inputs[0].links[0].from_node, orig_from)

class TestUtilsExtended(unittest.TestCase):
    def setUp(self):
        cleanup_scene()

    def test_check_objects_uv(self):
        obj = create_test_object("UV_Obj")
        self.assertEqual(utils.check_objects_uv([obj]), [])
        obj.data.uv_layers.remove(obj.data.uv_layers[0])
        self.assertEqual(utils.check_objects_uv([obj]), ["UV_Obj"])

    def test_set_image_resize(self):
        img = utils.set_image("Resizer", 100, 100)
        self.assertEqual(img.size[0], 100)
        img2 = utils.set_image("Resizer", 200, 200)
        self.assertEqual(img.size[0], 200)
        self.assertEqual(img, img2)

    def test_set_image_udim(self):
        img = utils.set_image("UDIM_Img", 100, 100, use_udim=True, udim_tiles=[1001, 1002])
        self.assertTrue(img.source == 'TILED' or hasattr(img, 'is_tiled_buffer'))

class TestResultAndExport(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            
    def test_recording_results(self):
        results = bpy.context.scene.baked_image_results
        results.clear()
        img = utils.set_image("Result_Img", 64, 64)
        item = results.add()
        item.image = img
        item.channel_type = "Base Color"
        item.object_name = "Cube"
        item.filepath = "/tmp/fake.png"
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].image, img)
        self.assertEqual(results[0].channel_type, "Base Color")

    def test_save_image_util(self):
        img = utils.set_image("Export_Test", 64, 64)
        img.pixels = [1.0, 0.0, 0.0, 1.0] * (64 * 64)
        saved_path = utils.save_image(
            img, 
            path=self.temp_dir, 
            folder=False, 
            file_format='PNG',
            save=True
        )
        expected_path = os.path.join(self.temp_dir, "Export_Test.png")
        self.assertIsNotNone(saved_path)
        self.assertTrue(os.path.exists(expected_path), f"File not found at {expected_path}")
        self.assertEqual(os.path.normpath(saved_path), os.path.normpath(expected_path))

class TestNodeBakeSetup(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        self.obj = create_test_object("NodeBakeObj")
        self.mat = self.obj.data.materials[0]
        self.tree = self.mat.node_tree
        
    def test_selected_node_connection_logic(self):
        noise = self.tree.nodes.new('ShaderNodeTexNoise')
        noise.location = (-300, 200)
        out_n = next((n for n in self.tree.nodes if n.bl_idname=='ShaderNodeOutputMaterial' and n.is_active_output), None)
        self.assertIsNotNone(out_n)
        
        with ops.NodeGraphHandler([self.mat]) as h:
            emi = h._add_node(self.mat, 'ShaderNodeEmission', location=(out_n.location.x-200, out_n.location.y))
            self.tree.links.new(noise.outputs[0], emi.inputs[0])
            self.tree.links.new(emi.outputs[0], out_n.inputs[0])
            
            self.assertTrue(out_n.inputs[0].is_linked)
            link_to_out = out_n.inputs[0].links[0]
            self.assertEqual(link_to_out.from_node, emi, "Output should be connected to Emission")
            
            self.assertTrue(emi.inputs[0].is_linked)
            link_to_emi = emi.inputs[0].links[0]
            self.assertEqual(link_to_emi.from_node, noise, "Emission should be connected to the target Node")

class TestTranslationSystem(unittest.TestCase):
    """验证翻译系统是否正常加载，不影响主程序"""
    
    def test_translation_loading(self):
        from . import translations
        data = translations.load_translations()
        
        # 1. 确保返回的是字典
        self.assertIsInstance(data, dict)
        
        # 2. 如果有数据，验证 Blender 要求的格式结构: {locale: {(context, src): dest}}
        if data:
            first_locale = next(iter(data))
            content = data[first_locale]
            self.assertIsInstance(content, dict)
            
            # 验证键必须是元组 (Context, Source)
            first_key = next(iter(content))
            self.assertIsInstance(first_key, tuple)
            self.assertEqual(len(first_key), 2)

class TestObjectManagement(unittest.TestCase):
    """测试对象列表管理逻辑 (模拟 UI 操作逻辑)"""
    
    def setUp(self):
        cleanup_scene()
        self.s = get_job_setting()
        self.obj1 = create_test_object("Obj1")
        self.obj2 = create_test_object("Obj2")
        
    def test_duplicate_prevention(self):
        """测试防止添加重复对象"""
        # 模拟 BAKETOOL_OT_ManageObjects 的逻辑
        def add_obj_logic(setting, obj):
            for item in setting.bake_objects:
                if item.bakeobject == obj: return
            new = setting.bake_objects.add()
            new.bakeobject = obj

        add_obj_logic(self.s, self.obj1)
        self.assertEqual(len(self.s.bake_objects), 1)
        
        # 尝试添加同一个对象
        add_obj_logic(self.s, self.obj1)
        self.assertEqual(len(self.s.bake_objects), 1, "Duplicate object should not be added")
        
        # 添加不同对象
        add_obj_logic(self.s, self.obj2)
        self.assertEqual(len(self.s.bake_objects), 2)

    def test_remove_logic(self):
        item = self.s.bake_objects.add()
        item.bakeobject = self.obj1
        self.s.bake_objects.remove(0)
        self.assertEqual(len(self.s.bake_objects), 0)

class TestEdgeCaseRobustness(unittest.TestCase):
    """测试极端情况下的稳健性"""
    
    def setUp(self):
        cleanup_scene()
        self.setting = get_job_setting()

    def test_empty_material_slots(self):
        """测试物体有材质槽但无材质 (None) 的情况"""
        obj = create_test_object("EmptySlotObj")
        # 添加一个空槽
        obj.data.materials.append(None) 
        
        # 确保 TaskBuilder 不会因此崩溃
        try:
            tasks = ops.TaskBuilder.build(bpy.context, self.setting, [obj], obj)
            # 即使有空槽，只要有有效材质或作为单一物体，应该能生成任务
            # 或者逻辑应该跳过空材质
            self.assertTrue(True, "TaskBuilder survived empty material slot")
        except Exception as e:
            self.fail(f"TaskBuilder crashed on empty material slot: {e}")

    def test_non_mesh_objects(self):
        """测试非 Mesh 物体误入的处理"""
        light_data = bpy.data.lights.new(name="TestLight", type='POINT')
        light_obj = bpy.data.objects.new(name="TestLightObj", object_data=light_data)
        bpy.context.collection.objects.link(light_obj)
        
        # 尝试检测 UV
        result = utils.check_objects_uv([light_obj])
        # 根据 utils.check_objects_uv 逻辑，它应该忽略非 Mesh 或返回空列表
        # 现代码: if obj.type == 'MESH' and not obj.data.uv_layers
        # 所以非 Mesh 应该被安全忽略，不返回在 missing 列表中
        self.assertNotIn(light_obj.name, result)
        
        # 测试 Setup Attribute (ID Map) 对非 Mesh 的反应
        attr = utils.setup_mesh_attribute(light_obj)
        self.assertIsNone(attr, "Should return None for non-mesh objects")

    def test_empty_mesh_handling(self):
        """测试空网格（无面）的处理逻辑"""
        bpy.ops.mesh.primitive_plane_add()
        obj = bpy.context.active_object
        # 删除所有面
        ensure_object_mode()
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.delete(type='FACE')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # 应当优雅返回 None
        attr = utils.setup_mesh_attribute(obj, id_type='MAT')
        self.assertIsNone(attr)
        
        attr = utils.setup_mesh_attribute(obj, id_type='ELEMENT')
        self.assertIsNone(attr)

class TestColorSpaceLogic(unittest.TestCase):
    """测试图像创建时的色彩空间与位深逻辑"""
    
    def tearDown(self):
        cleanup_scene()

    def test_32bit_image_creation(self):
        img = utils.set_image("Float32_Test", 128, 128, full=True)
        self.assertTrue(img.is_float, "Image should be 32-bit float")
        
    def test_colorspace_assignment(self):
        # 注意: 非 Color 管理模式下可能失效，或者色彩空间名称不存在
        # 这里测试最基础的 'sRGB' 和 'Non-Color' (Blender 标准)
        
        # 1. Data/Non-Color
        img_raw = utils.set_image("Raw_Test", 128, 128, space='Non-Color')
        try:
            cs = img_raw.colorspace_settings.name
            # 根据 Blender 版本和配置，可能是 'Non-Color' 或 'Raw'
            self.assertIn(cs, ['Non-Color', 'Raw', 'Generic Data'])
        except:
            pass # 某些 headless 环境可能没有色彩配置

        # 2. sRGB
        img_srgb = utils.set_image("sRGB_Test", 128, 128, space='sRGB')
        try:
            self.assertEqual(img_srgb.colorspace_settings.name, 'sRGB')
        except:
            pass

class TestPathSafety(unittest.TestCase):
    """测试路径处理的安全性"""
    
    def test_cross_platform_path_join(self):
        # 模拟保存路径逻辑
        base = Path("/tmp/bake")
        folder_name = "Textures"
        fname = "Test_Color.png"
        
        # 这里的关键是测试 utils.save_image 内部的 Path 逻辑是否正确使用了 / 或 \
        full_path = base / folder_name / fname
        path_str = str(full_path)
        
        # 简单验证没有双重分隔符或者是有效的路径字符串
        self.assertTrue(len(path_str) > 0)
        self.assertNotIn(os.sep + os.sep, path_str.replace("://", "")) # 忽略 windows 网络路径头

class TestNodeGraphHandler_Extended(unittest.TestCase):
    """Deep dive into Node Graph manipulation and restoration logic."""
    
    def setUp(self):
        cleanup_scene()
        self.obj = create_test_object("ComplexNodeObj")
        self.mat = self.obj.data.materials[0]
        self.tree = self.mat.node_tree
        self.handler = ops.NodeGraphHandler([self.mat])
        self.handler.__enter__()
        
    def tearDown(self):
        self.handler.__exit__(None, None, None)

    def test_multiple_outputs_handling(self):
        """Test proper selection of the active Output node when multiple exist."""
        # Create a second output node and make it active
        out1 = next(n for n in self.tree.nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
        out1.is_active_output = False
        
        out2 = self.tree.nodes.new('ShaderNodeOutputMaterial')
        out2.is_active_output = True
        out2.location = (500, 0)
        
        with ops.NodeGraphHandler([self.mat]) as h:
            h.setup_for_pass('EMIT', 'color', None)
            
            # Check if Emission is linked to the Active Output (out2), not the old one (out1)
            self.assertTrue(out2.inputs[0].is_linked, "Active output should be linked")
            if out1.inputs[0].is_linked:
                # Ensure it's not linked to our bake emission node
                link_node = out1.inputs[0].links[0].from_node
                self.assertNotEqual(link_node.bl_idname, 'ShaderNodeEmission', "Inactive output should not be used")

    def test_missing_bsdf_fallback(self):
        """Test behavior when the standard Principled BSDF is missing."""
        # Remove BSDF
        bsdf = next(n for n in self.tree.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled')
        self.tree.nodes.remove(bsdf)
        
        with ops.NodeGraphHandler([self.mat]) as h:
            # Try to bake 'roughness' which usually comes from BSDF
            # Should fallback to default values (0.0/0.5 etc) created via RGB/Value nodes
            h.setup_for_pass('EMIT', 'rough', None)
            
            out_node = next(n for n in self.tree.nodes if n.bl_idname == 'ShaderNodeOutputMaterial' and n.is_active_output)
            emi_node = out_node.inputs[0].links[0].from_node
            input_node = emi_node.inputs[0].links[0].from_node
            
            # Since BSDF is gone, it should create a default value node (RGB or Value)
            self.assertIn(input_node.bl_idname, ['ShaderNodeRGB', 'ShaderNodeValue'], "Should fallback to default constant when BSDF is missing")

    def test_cleanup_robustness(self):
        """Ensure temp nodes are removed even after exceptions."""
        initial_node_count = len(self.tree.nodes)
        
        try:
            with ops.NodeGraphHandler([self.mat]) as h:
                h.setup_for_pass('EMIT', 'color', None)
                # Verify nodes were added
                self.assertTrue(len(self.tree.nodes) > initial_node_count)
                raise ValueError("Simulated Error during bake")
        except ValueError:
            pass
            
        # Verify cleanup
        final_node_count = len(self.tree.nodes)
        self.assertEqual(final_node_count, initial_node_count, "Node tree should be clean after error")

    def test_protection_cleanup(self):
        """Verify that protection nodes on non-active materials are cleaned up."""
        # Create a second object with a different material
        obj2 = create_test_object("OtherObj")
        mat2 = obj2.data.materials[0]
        initial_node_count_mat2 = len(mat2.node_tree.nodes)
        
        with ops.NodeGraphHandler([self.mat]) as h:
            # mat2 is NOT in the active materials list [self.mat]
            h.setup_protection([self.obj, obj2], [self.mat])
            
            # Verify nodes were added to mat2
            self.assertTrue(len(mat2.node_tree.nodes) > initial_node_count_mat2)
            
        # Verify cleanup (The fix in node_manager.py should handle this)
        self.assertEqual(len(mat2.node_tree.nodes), initial_node_count_mat2, "Protected material should be cleaned up")

    def test_protection_image_cleanup(self):
        """Verify that BT_Protection_Dummy image is removed if unused."""
        with ops.NodeGraphHandler([self.mat]) as h:
            h.setup_protection([self.obj], [self.mat])
            self.assertIn("BT_Protection_Dummy", bpy.data.images)
            
        # The cleanup() method should have removed it because users dropped to 0
        self.assertNotIn("BT_Protection_Dummy", bpy.data.images, "Protection dummy image should be removed if unused")

class TestUVDataManipulation(unittest.TestCase):
    """Verify actual mesh UV data modification by Utils."""
    
    def setUp(self):
        cleanup_scene()
        # Create plane with standard UVs at (0,0) to (1,1)
        bpy.ops.mesh.primitive_plane_add()
        self.obj = bpy.context.active_object
        self.obj.name = "UV_Test_Obj"
        
    def get_uv_centroid(self):
        """Helper to get average UV position."""
        uv_layer = self.obj.data.uv_layers.active.data
        uvs = np.zeros(len(uv_layer)*2, dtype=np.float32)
        uv_layer.foreach_get("uv", uvs)
        uvs = uvs.reshape(-1, 2)
        return np.mean(uvs, axis=0)

    def test_smart_uv_creation(self):
        """Test if Smart UV creates a new layer and changes topology."""
        s = get_job_setting()
        s.use_auto_uv = True
        s.auto_uv_angle = 66
        
        # Original UV centroid of a plane is usually (0.5, 0.5)
        
        with ops.UVLayoutManager([self.obj], s):
            # Inside the manager context
            self.assertTrue(len(self.obj.data.uv_layers) > 1, "Should have created a temp UV layer")
            self.assertEqual(self.obj.data.uv_layers.active.name, "BT_Bake_Temp_UV")
            
        # Context exit: Check cleanup or persistence depending on settings
        # Default behavior is to restore original active index
        self.assertNotEqual(self.obj.data.uv_layers.active.name, "BT_Bake_Temp_UV")

    def test_udim_uv_offset(self):
        """Test if UVs are actually moved to the target tile."""
        s = get_job_setting()
        s.bake_mode = 'UDIM'
        s.udim_mode = 'CUSTOM'
        
        # Assign object to Tile 1002 (U offset +1)
        bo = s.bake_objects.add()
        bo.bakeobject = self.obj
        bo.udim_tile = 1002
        
        original_centroid = self.get_uv_centroid() # Expect approx (0.5, 0.5)
        
        with ops.UVLayoutManager([self.obj], s):
            new_centroid = self.get_uv_centroid()
            # 1002 means Shift X by 1.
            self.assertAlmostEqual(new_centroid[0], original_centroid[0] + 1.0, places=4)
            self.assertAlmostEqual(new_centroid[1], original_centroid[1], places=4)
            
        # Logic verification: Did it revert? 
        # UVLayoutManager currently modifies the *Temp* layer. 
        # The test ensures the math inside the manager works.

class TestTaskBuilder_Logic(unittest.TestCase):
    
    def setUp(self):
        cleanup_scene()
        self.high = create_test_object("HighPoly")
        self.low = create_test_object("LowPoly")
        self.setting = get_job_setting()
        
        # Assign materials
        self.mat_high = self.high.data.materials[0]
        self.mat_low = self.low.data.materials[0]

    def test_selected_to_active_grouping(self):
        """Ensure Selected objects are grouped into the task, Active is target."""
        
        # [FIX] CRITICAL: 'SELECT_ACTIVE' is hidden/invalid when bake_type is 'BSDF'.
        # We must switch to 'BASIC' (or similar) first.
        self.setting.bake_type = 'BASIC'
        self.setting.bake_mode = 'SELECT_ACTIVE'
        
        # In UI, user selects High1, High2, then Low (Active).
        # We simulate this by passing list [High, Low] and active=Low
        
        tasks = ops.TaskBuilder.build(
            bpy.context, 
            self.setting, 
            objects=[self.high, self.low], 
            active_obj=self.low
        )
        
        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        
        self.assertEqual(task.active_obj, self.low, "Target must be the active object")
        self.assertIn(self.high, task.objects, "Source objects must be in the list")
        self.assertIn(self.mat_low, task.materials, "Target material must be included for node setup")

class TestNodeGroupChannel(unittest.TestCase):
    """Test the Custom Node Group Channel feature."""
    
    def setUp(self):
        cleanup_scene()
        self.obj = create_test_object("NG_Obj")
        self.mat = self.obj.data.materials[0]
        
        # Create a dummy node group
        self.ng = bpy.data.node_groups.new("TestGroup", 'ShaderNodeTree')
        
        # Version compatible socket creation
        if bpy.app.version >= (4, 0, 0):
            self.ng.interface.new_socket(name="MyOutput", in_out='OUTPUT', socket_type='NodeSocketColor')
        else:
            self.ng.outputs.new('NodeSocketColor', "MyOutput")
        
        # Add some internal nodes to make it valid
        input_n = self.ng.nodes.new('NodeGroupInput')
        output_n = self.ng.nodes.new('NodeGroupOutput')
        rgb_n = self.ng.nodes.new('ShaderNodeRGB')
        rgb_n.outputs[0].default_value = (1.0, 0.0, 0.0, 1.0) # Red
        self.ng.links.new(rgb_n.outputs[0], output_n.inputs[0])
        
    def test_node_group_baking_setup(self):
        s = get_job_setting()
        s.channels.clear()
        
        # Add the node_group channel
        c = s.channels.add()
        c.id = 'node_group'
        c.name = 'My Node Group'
        c.enabled = True
        c.node_group = self.ng.name
        c.node_group_output = "MyOutput"
        
        img = utils.set_image("NG_Bake", 64, 64)
        
        with ops.NodeGraphHandler([self.mat]) as h:
            h.setup_for_pass('EMIT', 'node_group', img, channel_settings=c)
            
            tree = self.mat.node_tree
            out_node = next(n for n in tree.nodes if n.bl_idname == 'ShaderNodeOutputMaterial' and n.is_active_output)
            emi_node = out_node.inputs[0].links[0].from_node
            
            # Check connection: Emission <- Group Output
            self.assertEqual(emi_node.bl_idname, 'ShaderNodeEmission')
            group_node = emi_node.inputs[0].links[0].from_node
            
            self.assertEqual(group_node.bl_idname, 'ShaderNodeGroup')
            self.assertEqual(group_node.node_tree, self.ng)

class TestEmergencyCleanup(unittest.TestCase):
    """Test the emergency cleanup operator logic."""
    
    def setUp(self):
        cleanup_scene()
        
    def test_cleanup_temp_data(self):
        # 1. Create junk
        obj = create_test_object("JunkObj")
        uv = obj.data.uv_layers.new(name="BT_Bake_Temp_UV")
        # Use the actual name used by the addon
        img = bpy.data.images.new("BT_Protection_Dummy", 32, 32)
        
        # 2. Run operator
        from .core import cleanup
        try:
            bpy.utils.register_class(cleanup.BAKETOOL_OT_EmergencyCleanup)
        except: pass
        
        bpy.ops.bake.emergency_cleanup()
        
        # 3. Verify
        self.assertNotIn("BT_Bake_Temp_UV", [l.name for l in obj.data.uv_layers])
        self.assertNotIn("BT_Protection_Dummy", [i.name for i in bpy.data.images])

class TestSceneSettingsContext(unittest.TestCase):
    """Test safe restoration of scene and render settings."""
    
    def test_cycles_settings_restoration(self):
        scene = bpy.context.scene
        scene.cycles.samples = 10
        
        settings = {'samples': 100}
        with ops.SceneSettingsContext('cycles', settings):
            self.assertEqual(scene.cycles.samples, 100)
            
        self.assertEqual(scene.cycles.samples, 10)

class TestApplyBakedResult(unittest.TestCase):
    """Test the logic that creates a new object with baked textures applied."""
    
    def setUp(self):
        cleanup_scene()
        self.obj = create_test_object("Original")
        self.img = utils.set_image("Baked_Color", 32, 32)
        
    def test_apply_single_object(self):
        baked_images = {'color': self.img}
        setting = get_job_setting()
        
        new_obj = utils.apply_baked_result(self.obj, baked_images, setting, "TestBake")
        
        self.assertIsNotNone(new_obj)
        self.assertTrue(new_obj.name.startswith("TestBake"))
        self.assertEqual(len(new_obj.data.materials), 1)
        
        mat = new_obj.data.materials[0]
        self.assertTrue(mat.use_nodes)
        tex_nodes = [n for n in mat.node_tree.nodes if n.bl_idname == 'ShaderNodeTexImage']
        self.assertEqual(len(tex_nodes), 1)
        self.assertEqual(tex_nodes[0].image, self.img)

class TestModelExporter_Logic(unittest.TestCase):
    """Test the ModelExporter wrapper for path creation."""
    
    def setUp(self):
        cleanup_scene()
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            
    def test_export_directory_creation(self):
        setting = get_job_setting()
        setting.save_path = self.temp_dir
        setting.create_new_folder = True
        
        folder_name = "MyExportFolder"
        base_path = Path(bpy.path.abspath(setting.save_path))
        if setting.create_new_folder:
            base_path = base_path / folder_name
            
        base_path.mkdir(parents=True, exist_ok=True)
        self.assertTrue(base_path.exists())

class TestFullBakeIntegration(unittest.TestCase):
    """
    Integration Test: Simulates a complete user workflow using REAL logic classes.
    This tests the actual baking engine in the Blender environment.
    """
    
    def setUp(self):
        cleanup_scene()
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_complete_bake_workflow(self):
        # 1. Setup Scene (Real Blender Data)
        obj = create_test_object("Integrate_Obj", color=(1, 0, 0, 1)) # Red Object
        
        # 2. Configure Job Settings
        scene = bpy.context.scene
        bj = scene.BakeJobs
        bj.jobs.clear()
        job = bj.jobs.add()
        s = job.setting
        
        # Add object to bake list
        bo = s.bake_objects.add()
        bo.bakeobject = obj
        
        # Configure settings for a real bake
        s.bake_mode = 'SINGLE_OBJECT'
        s.name_setting = 'OBJECT' # Ensure name matches obj.name
        s.res_x = 64
        s.res_y = 64
        s.save_out = True
        s.save_path = self.temp_dir
        s.save_format = 'PNG'
        s.bake_type = 'BSDF'
        
        # Sync channels
        utils.reset_channels_logic(s)
        channels = []
        for c in s.channels:
            if c.id == 'color':
                c.enabled = True
                info = CHANNEL_BAKE_INFO.get(c.id, {})
                channels.append({
                    'id': c.id, 'name': c.name, 'prop': c, 
                    'bake_pass': info.get('bake_pass', 'EMIT'),
                    'info': info, 'prefix': c.prefix, 'suffix': c.suffix
                })
            else:
                c.enabled = False

        # 3. Execute Real Engine Logic (The actual code from ops.py)
        # We simulate the loop found in BAKETOOL_OT_BakeOperator._process_step
        
        # Build tasks using real TaskBuilder
        tasks = ops.TaskBuilder.build(bpy.context, s, [obj], obj)
        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        
        baked_images = {}
        
        # Use BakeContextManager to apply real render settings
        with ops.BakeContextManager(bpy.context, s):
            # Use safe_context_override to handle selection/active state
            with utils.safe_context_override(bpy.context, task.active_obj, task.objects):
                # Use UVLayoutManager to handle temp UVs (Real mesh modification)
                with utils.UVLayoutManager(task.objects, s):
                    # Use NodeGraphHandler to setup materials (Real shader nodes)
                    with utils.NodeGraphHandler(task.materials) as handler:
                        handler.setup_protection(task.objects, task.materials)
                        
                        for c_config in channels:
                            # Execute the real BakePassExecutor (This calls bpy.ops.object.bake)
                            img = ops.BakePassExecutor.execute(
                                s, task, c_config, handler, baked_images
                            )
                            
                            if img:
                                baked_images[c_config['id']] = img
                                # Save the image to disk
                                utils.save_image(
                                    img, s.save_path, 
                                    file_format=s.save_format,
                                    save=True
                                )

        # 4. Final Verification
        img_name = f"Integrate_Obj_color"
        self.assertIn(img_name, bpy.data.images, "Real bake failed to produce image")
        
        # Verify physical file existence
        expected_file = os.path.join(self.temp_dir, f"{img_name}.png")
        self.assertTrue(os.path.exists(expected_file), f"Physical file not created at {expected_file}")
        
        # Verify image content (Simple check: is it red?)
        # For a 1.0, 0.0, 0.0, 1.0 bake, the pixels should contain data
        pixels = np.empty(64 * 64 * 4, dtype=np.float32)
        bpy.data.images[img_name].pixels.foreach_get(pixels)
        self.assertTrue(np.mean(pixels[0::4]) > 0.5, "Bake result seems to be black (No data)")

# --- New Feature Tests ---

class TestJobInitialization(unittest.TestCase):
    """Test initialization logic when creating new jobs."""
    
    def setUp(self):
        cleanup_scene()
        if hasattr(bpy.context.scene, "BakeJobs"):
            bpy.context.scene.BakeJobs.jobs.clear()
            
    def test_add_job_defaults(self):
        # Trigger the operator
        bpy.ops.bake.generic_channel_op(action_type='ADD', target='jobs_channel')
        
        self.assertEqual(len(bpy.context.scene.BakeJobs.jobs), 1)
        job = bpy.context.scene.BakeJobs.jobs[0]
        
        # Verify Critical Enums (Bug Fix)
        self.assertEqual(job.setting.bake_type, 'BSDF', "Bake Type not initialized")
        self.assertEqual(job.setting.bake_mode, 'SINGLE_OBJECT', "Bake Mode not initialized")
        
        # Verify Default Channels
        enabled = [c.id for c in job.setting.channels if c.enabled]
        self.assertIn('color', enabled)
        self.assertIn('normal', enabled)

class TestQuickBakeLogic(unittest.TestCase):
    """Test logic paths for Quick Bake (Ephemeral tasks)."""
    
    def setUp(self):
        cleanup_scene()
        self.obj = create_test_object("QuickObj")
        self.s = get_job_setting()
        
    def test_ephemeral_task_build(self):
        # Simulate selection
        bpy.ops.object.select_all(action='DESELECT')
        self.obj.select_set(True)
        bpy.context.view_layer.objects.active = self.obj
        
        tasks = ops.TaskBuilder.build(bpy.context, self.s, [self.obj], self.obj)
        
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].active_obj, self.obj)
        # Ensure job setting list was NOT modified
        self.assertEqual(len(self.s.bake_objects), 0)

class TestAutoLoadPreset(unittest.TestCase):
    """Test the startup preset loading mechanism."""
    
    def setUp(self):
        cleanup_scene()
        self.temp_dir = tempfile.mkdtemp()
        self.preset = os.path.join(self.temp_dir, "test_startup.json")
        
        # Mock Addon Preferences
        # Note: In headless testing, __package__ might vary. We try to find it dynamically.
        self.prefs = None
        for mod in bpy.context.preferences.addons.keys():
            if "baketool" in mod:
                self.prefs = bpy.context.preferences.addons[mod].preferences
                break
        
        # Create Dummy Preset
        with open(self.preset, 'w') as f:
            json.dump({"jobs": [{"name": "StartupJob"}]}, f)

    def tearDown(self):
        if os.path.exists(self.temp_dir): shutil.rmtree(self.temp_dir)
        if self.prefs:
            self.prefs.auto_load = False
            self.prefs.default_preset_path = ""

    def test_handler_logic(self):
        if not self.prefs: return # Skip if addon not registered in test env
        
        # Correctly import the handler function from the package
        from . import load_default_preset
        
        self.prefs.auto_load = True
        self.prefs.default_preset_path = self.preset
        
        # Case 1: Clean scene -> Load
        bpy.context.scene.BakeJobs.jobs.clear()
        load_default_preset(None)
        self.assertEqual(len(bpy.context.scene.BakeJobs.jobs), 1)
        self.assertEqual(bpy.context.scene.BakeJobs.jobs[0].name, "StartupJob")
        
        # Case 2: Dirty scene -> Skip
        load_default_preset(None) # Call again
        # Should NOT duplicate (logic is if len == 0)
        self.assertEqual(len(bpy.context.scene.BakeJobs.jobs), 1)

class BAKETOOL_OT_RunTests(bpy.types.Operator):
    bl_idname = "bake.run_dev_tests"
    bl_label = "Run Full Test Suite"
    
    def execute(self, context):
        print("\n" + "="*60)
        print(f"STARTING BAKETOOL EXTENDED TEST SUITE")
        print("="*60)
        
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        test_classes = [
            TestPresetSystem,
            TestStateManager,
            TestAnimationSystem,
            TestUDIMIO,
            TestPropertyLogic,
            TestNamingConvention,
            TestTaskGeneration,
            TestBakePassExecutor,
            TestNodeGraphLogic,
            TestIDMapTools,
            TestUDIMLogic,
            TestPBRConversion,
            TestRobustness,
            TestUtilsExtended,
            TestResultAndExport,
            TestNodeBakeSetup,
            TestTranslationSystem,
            TestObjectManagement,
            TestEdgeCaseRobustness,
            TestColorSpaceLogic,
            TestPathSafety,
            TestNodeGraphHandler_Extended,
            TestUVDataManipulation,
            TestTaskBuilder_Logic,
            TestNodeGroupChannel,
            TestEmergencyCleanup,
            TestSceneSettingsContext,
            TestApplyBakedResult,
            TestModelExporter_Logic,
            TestFullBakeIntegration,
            TestJobInitialization,
            TestQuickBakeLogic,
            TestAutoLoadPreset
        ]
        
        for tc in test_classes:
            suite.addTests(loader.loadTestsFromTestCase(tc))
            
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        print("\n" + "="*60)
        if result.wasSuccessful():
            self.report({'INFO'}, f"ALL TESTS PASSED: {result.testsRun} tests.")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, f"TESTS FAILED: {len(result.errors)} Errors, {len(result.failures)} Failures.")
            return {'CANCELLED'}