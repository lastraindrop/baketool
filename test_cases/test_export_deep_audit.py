import unittest
import bpy
import os
import tempfile
import shutil
from pathlib import Path
from .helpers import cleanup_scene, create_test_object, JobBuilder
from ..core.engine import JobPreparer, BakeStepRunner

class TestExportDeepAudit(unittest.TestCase):
    def setUp(self):
        cleanup_scene()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except:
                pass

    def test_export_constraint_logic(self):
        """测试约束逻辑：只有当 Apply to Scene 和 External Save 均为 True 时，导出才会执行"""
        obj = create_test_object("ConstraintObj")
        
        # 场景 1: Export=True, Apply=True, but SaveOut=False (应该不执行导出)
        job = (JobBuilder("ConstraintJob")
               .add_objects(obj)
               .enable_channel('color')
               .build())
        
        s = job.setting
        s.export_model = True
        s.bake_texture_apply = True
        s.save_out = False # 缺少此条件
        s.save_path = self.temp_dir
        
        runner = BakeStepRunner(bpy.context)
        queue = JobPreparer.prepare_execution_queue(bpy.context, [job])
        runner.run(queue[0])
        
        # 检查目录下是否生成了模型文件
        model_files = list(Path(self.temp_dir).glob("**/*.fbx"))
        self.assertEqual(len(model_files), 0, "Export should have been blocked because save_out is False")

    def test_animation_frame_writing(self):
        """深度验证：动画序列帧是否被物理写入磁盘"""
        obj = create_test_object("AnimAudit")
        job = (JobBuilder("AnimAuditJob")
               .add_objects(obj)
               .enable_channel('color')
               .save_to(self.temp_dir)
               .build())
        
        s = job.setting
        s.name_setting = 'OBJECT' # 强制使用物体名，确保断言匹配
        s.bake_motion = True
        s.bake_motion_use_custom = True
        s.bake_motion_start = 1
        s.bake_motion_last = 3 # 烘焙 3 帧
        
        runner = BakeStepRunner(bpy.context)
        queue = JobPreparer.prepare_execution_queue(bpy.context, [job])
        self.assertEqual(len(queue), 3)
        
        for step in queue:
            runner.run(step)
            
        # 验证磁盘上的图片数量
        # Naming: [ObjName]_color_[Frame].png
        img_files = list(Path(self.temp_dir).glob("**/AnimAudit_color_*.png"))
        self.assertEqual(len(img_files), 3, f"Expected 3 frame images, found {len(img_files)}")

    def test_udim_tile_writing(self):
        """深度验证：UDIM Tile (1001, 1002) 是否被物理写入磁盘"""
        # 创建两个物体，分别放置在 1001 和 1002 象限
        obj1 = create_test_object("UDIM_Obj1") # 默认 1001
        
        obj2 = create_test_object("UDIM_Obj2")
        uv_layer2 = obj2.data.uv_layers.active.data
        for loop in uv_layer2:
            loop.uv[0] += 1.0 # 将 UV 整体右移 1 个单位到 1002 象限 (U=1)
            
        job = (JobBuilder("UDIM_AuditJob")
               .mode('UDIM')
               .add_objects([obj1, obj2])
               .enable_channel('color')
               .save_to(self.temp_dir)
               .build())
        
        # 强制使用 CUSTOM 命名，避免默认的 "UDIM_Bake" 干扰断言
        job.setting.name_setting = 'CUSTOM'
        job.setting.custom_name = 'UDIM_Audit'
        
        runner = BakeStepRunner(bpy.context)
        queue = JobPreparer.prepare_execution_queue(bpy.context, [job])
        self.assertGreater(len(queue), 0, "Execution queue should not be empty")
        
        for step in queue:
            runner.run(step)
        
        # 验证物理文件。由于没有开启 create_new_folder，文件应直接在 temp_dir 下
        tile_1001 = Path(self.temp_dir) / "UDIM_Audit_color.1001.png"
        tile_1002 = Path(self.temp_dir) / "UDIM_Audit_color.1002.png"
        
        self.assertTrue(tile_1001.exists(), f"UDIM Tile 1001 missing at {tile_1001}")
        self.assertTrue(tile_1002.exists(), f"UDIM Tile 1002 missing at {tile_1002}")

    def test_exported_model_integrity(self):
        """深度验证：导出的模型文件是否完整（大小 > 0）"""
        obj = create_test_object("IntegrityObj")
        job = (JobBuilder("IntegrityJob")
               .add_objects(obj)
               .enable_channel('color')
               .save_to(self.temp_dir)
               .build())
        
        s = job.setting
        s.export_model = True
        s.bake_texture_apply = True
        s.save_out = True
        s.name_setting = 'OBJECT'
        
        runner = BakeStepRunner(bpy.context)
        queue = JobPreparer.prepare_execution_queue(bpy.context, [job])
        runner.run(queue[0])
        
        # 验证路径逻辑：
        # Folder = task.folder_name = "IntegrityObj"
        # Object Name = "IntegrityObj_Baked" (由 apply_baked_result 生成)
        # File = "IntegrityObj_Baked.fbx"
        clean_folder = bpy.path.clean_name("IntegrityObj")
        clean_file = bpy.path.clean_name("IntegrityObj_Baked")
        model_path = Path(self.temp_dir) / clean_folder / f"{clean_file}.fbx"
        
        self.assertTrue(model_path.exists(), f"Model file missing at {model_path}")
        self.assertGreater(os.path.getsize(model_path), 0, "Exported model file is empty (0 bytes)")

if __name__ == '__main__':
    unittest.main()
