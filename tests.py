import bpy
import unittest
import importlib

# 导入子模块以便重新加载 // Import submodules for reloading
from .test_cases import (
    test_presets,
    test_state,
    test_logic,
    test_core,
    test_integration,
    test_crash_recovery,
    test_export_system,
    test_edge_cases,
    test_refactor,
    test_complex_geometry,
    test_assets_system,
    test_performance,
    test_shading_complexity,
    test_udim_advanced
)

class BAKETOOL_OT_RunTests(bpy.types.Operator):
    """Run the modularized test suite for BakeTool."""
    bl_idname = "bake.run_dev_tests"
    bl_label = "Run Full Test Suite"
    
    def execute(self, context):
        print("\n" + "="*60)
        print(f"STARTING BAKETOOL MODULAR TEST SUITE")
        print("="*60)
        
        # 强制重新加载测试模块，确保修改生效 // Force reload test modules
        test_modules = [
            test_presets, test_state, test_logic, test_core, 
            test_integration, test_crash_recovery, test_export_system, 
            test_edge_cases, test_refactor, test_complex_geometry, test_assets_system,
            test_performance, test_shading_complexity, test_udim_advanced
        ]
        
        for mod in test_modules:
            importlib.reload(mod)
        
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        for module in test_modules:
            suite.addTests(loader.loadTestsFromModule(module))
            
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        print("\n" + "="*60)
        if result.wasSuccessful():
            self.report({'INFO'}, f"ALL TESTS PASSED: {result.testsRun} tests.")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, f"TESTS FAILED: {len(result.errors)} Errors, {len(result.failures)} Failures.")
            # 可以在此处打印详细错误 // Could print detailed errors here if needed
            return {'CANCELLED'}
