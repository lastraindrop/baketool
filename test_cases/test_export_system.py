import unittest
import bpy
import os
import tempfile
import shutil
from pathlib import Path
from .helpers import cleanup_scene, create_test_object, get_job_setting
from ..core import image_manager, common
from ..core.engine import ModelExporter

class TestExportSystem(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        self.temp_dir = tempfile.mkdtemp()
        self.setting = get_job_setting()
        
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_basic_formats_export(self):
        """测试基础格式（FBX, GLB）的导出路径生成与执行 // Test FBX/GLB export"""
        obj = create_test_object("ExportCube")
        self.setting.save_path = self.temp_dir
        
        for fmt in ['FBX', 'GLB']:
            self.setting.export_format = fmt
            # 显式使用 folder_name 进行测试
            folder = f"test_{fmt}"
            ModelExporter.export(bpy.context, obj, self.setting, folder_name=folder)
            
            expected_ext = ".fbx" if fmt == 'FBX' else ".glb"
            # 注意：ModelExporter 现在会对 folder_name 和 obj.name 进行 clean_name
            clean_folder = bpy.path.clean_name(folder)
            clean_obj_name = bpy.path.clean_name(obj.name)
            
            expected_path = Path(self.temp_dir) / clean_folder / f"{clean_obj_name}{expected_ext}"
            self.assertTrue(expected_path.exists(), f"{fmt} export failed. Expected: {expected_path}")

    def test_special_characters_in_path(self):
        """测试带空格和特殊字符的路径安全性 // Test paths with spaces/special chars"""
        special_name = "Bake & Tool @ Test"
        obj = create_test_object(special_name)
        
        subdir = "My Export Folder"
        self.setting.save_path = self.temp_dir
        self.setting.export_format = 'FBX'
        
        ModelExporter.export(bpy.context, obj, self.setting, folder_name=subdir)
        
        clean_folder = bpy.path.clean_name(subdir)
        clean_name = bpy.path.clean_name(obj.name)
        expected_path = Path(self.temp_dir) / clean_folder / f"{clean_name}.fbx"
        self.assertTrue(expected_path.exists(), f"Failed to handle special characters. Expected: {expected_path}")

    def test_multi_job_isolation(self):
        """测试多个 Job 同时导出时的目录隔离 // Test directory isolation for multiple jobs"""
        obj1 = create_test_object("Cube_Job1")
        obj2 = create_test_object("Cube_Job2")
        
        self.setting.save_path = self.temp_dir
        self.setting.export_format = 'FBX'
        
        ModelExporter.export(bpy.context, obj1, self.setting, folder_name="Job_Alpha")
        ModelExporter.export(bpy.context, obj2, self.setting, folder_name="Job_Beta")
        
        path1 = Path(self.temp_dir) / "Job_Alpha" / "Cube_Job1.fbx"
        path2 = Path(self.temp_dir) / "Job_Beta" / "Cube_Job2.fbx"
        
        self.assertTrue(path1.exists())
        self.assertTrue(path2.exists())

    def test_apply_and_export_lifecycle(self):
        """测试‘烘焙并应用到物体’后导出的完整生命周期。"""
        obj = create_test_object("LifeCycleObj")
        img = image_manager.set_image("FakeBakedTex", 32, 32)
        baked_images = {'color': img}
        
        self.setting.save_path = self.temp_dir
        self.setting.export_model = True
        self.setting.bake_texture_apply = False 
        
        res_obj = common.apply_baked_result(obj, baked_images, self.setting, "FinalTask")
        self.assertIn(res_obj.name, bpy.data.objects)
        
        ModelExporter.export(bpy.context, res_obj, self.setting, folder_name="FinalExport")
        
        clean_obj_name = bpy.path.clean_name(res_obj.name)
        expected_file = Path(self.temp_dir) / "FinalExport" / f"{clean_obj_name}.fbx"
        self.assertTrue(expected_file.exists())
        
        # 清理
        res_obj_name = res_obj.name
        bpy.data.objects.remove(res_obj, do_unlink=True)
        self.assertNotIn(res_obj_name, bpy.data.objects)

    def test_udim_mesh_export(self):
        """测试 UDIM 物体的导出 // Test UDIM mesh export"""
        obj = create_test_object("UDIM_Mesh")
        for loop in obj.data.uv_layers.active.data:
            loop.uv[0] += 1.0 
            
        self.setting.save_path = self.temp_dir
        self.setting.export_format = 'GLB'
        
        ModelExporter.export(bpy.context, obj, self.setting, folder_name="UDIM_Export")
            
        expected_path = Path(self.temp_dir) / "UDIM_Export" / "UDIM_Mesh.glb"
        self.assertTrue(expected_path.exists())

    def test_animation_export_readiness(self):
        """测试动画导出的准备情况 // Test animation export state"""
        obj = create_test_object("AnimObj")
        obj.location = (0, 0, 0)
        obj.keyframe_insert(data_path="location", frame=1)
        obj.location = (1, 1, 1)
        obj.keyframe_insert(data_path="location", frame=10)
        
        self.setting.save_path = self.temp_dir
        self.setting.export_format = 'FBX'
        
        ModelExporter.export(bpy.context, obj, self.setting, folder_name="Anim_Export")
        
        expected_path = Path(self.temp_dir) / "Anim_Export" / "AnimObj.fbx"
        self.assertTrue(expected_path.exists())