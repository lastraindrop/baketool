import bpy
import unittest
import importlib
from pathlib import Path
import sys

class BAKETOOL_OT_RunTests(bpy.types.Operator):
    """Run the modularized test suite for BakeTool."""
    bl_idname = "bake.run_dev_tests"
    bl_label = "Run Full Test Suite"
    
    def execute(self, context):
        print("\n" + "="*60)
        print(f"STARTING BAKETOOL MODULAR TEST SUITE (AUTO-DISCOVERY)")
        print("="*60)
        
        addon_root = Path(__file__).parent
        parent_dir = str(addon_root.parent)
        test_dir = str(addon_root / "test_cases")
        
        # 1. 自动发现并重新加载模块 // Discovery and force reload
        loader = unittest.TestLoader()
        
        package_name = __package__
        for mod_name in list(sys.modules.keys()):
            if mod_name.startswith(f"{package_name}."):
                try:
                    importlib.reload(sys.modules[mod_name])
                except Exception as e:
                    pass

        # 2. 执行发现逻辑 // Discover tests
        # 关键：从父目录开始 discover，以确保 test_cases 被识别为 baketool.test_cases
        suite = loader.discover(
            start_dir=test_dir, 
            pattern='suite_*.py', 
            top_level_dir=parent_dir
        )
        
        print(f">>> Discovered {suite.countTestCases()} tests")
            
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        # 3. 反馈到 UI // Feedback to UI
        scene = context.scene
        scene.test_pass = result.wasSuccessful()
        t = result.testsRun
        f = len(result.failures)
        e = len(result.errors)
        
        import datetime
        now = datetime.datetime.now().strftime("%H:%M:%S")
        
        if scene.test_pass:
            scene.last_test_info = f"[{now}] PASS: {t} tests"
        else:
            scene.last_test_info = f"[{now}] FAIL: {f} fail, {e} err"

        print("\n" + "="*60)
        if result.wasSuccessful():
            self.report({'INFO'}, f"ALL TESTS PASSED: {result.testsRun} tests.")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, f"TESTS FAILED: {len(result.errors)} Errors, {len(result.failures)} Failures.")
            return {'CANCELLED'}
