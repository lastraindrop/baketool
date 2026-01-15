import bpy
import unittest
import importlib
import os
import sys

class BAKETOOL_OT_RunTests(bpy.types.Operator):
    """Run the modularized test suite for BakeTool."""
    bl_idname = "bake.run_dev_tests"
    bl_label = "Run Full Test Suite"
    
    def execute(self, context):
        print("\n" + "="*60)
        print(f"STARTING BAKETOOL MODULAR TEST SUITE (AUTO-DISCOVERY)")
        print("="*60)
        
        addon_root = os.path.dirname(__file__)
        parent_dir = os.path.dirname(addon_root)
        test_dir = os.path.join(addon_root, "test_cases")
        
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
            pattern='test_*.py', 
            top_level_dir=parent_dir
        )
        
        print(f">>> Discovered {suite.countTestCases()} tests")
            
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        print("\n" + "="*60)
        if result.wasSuccessful():
            self.report({'INFO'}, f"ALL TESTS PASSED: {result.testsRun} tests.")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, f"TESTS FAILED: {len(result.errors)} Errors, {len(result.failures)} Failures.")
            return {'CANCELLED'}
