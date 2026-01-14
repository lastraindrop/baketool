import unittest
import os
import json
from pathlib import Path
import bpy
from ..state_manager import BakeStateManager

class TestCrashRecovery(unittest.TestCase):
    def setUp(self):
        self.mgr = BakeStateManager()
        self.mgr.finish_session()
        
    def tearDown(self):
        self.mgr.finish_session()

    def test_crash_detection_logic(self):
        """模拟 Blender 崩溃后残留日志的情况 // Simulate log residue after Blender crash"""
        # 手动创建模拟日志 // Manually create mock log
        data = {
            "status": "RUNNING",
            "job_name": "Crash_Job",
            "total_steps": 10,
            "current_step": 5
        }
        with open(self.mgr.log_file, 'w') as f:
            json.dump(data, f)
            
        self.assertTrue(self.mgr.has_crash_record())
        log = self.mgr.read_log()
        self.assertEqual(log['job_name'], "Crash_Job")
        
        # 验证清理逻辑 // Verify finish session clears it
        self.mgr.finish_session()
        self.assertFalse(self.mgr.has_crash_record())

    def test_ui_state_reset_after_crash(self):
        """测试清理操作符是否能重置全局状态 // Test if cleanup operator resets global state"""
        scene = bpy.context.scene
        scene.is_baking = True
        scene.bake_status = "Stuck"
        
        # 执行紧急清理 // Run emergency cleanup
        bpy.ops.bake.emergency_cleanup()
        
        # 状态应该被重置（如果我们在 cleanup.py 中实现了它）
        # Note: 待会儿我们会更新 cleanup.py 增加这部分逻辑
        self.assertFalse(scene.is_baking)
        self.assertEqual(scene.bake_status, "Idle")
