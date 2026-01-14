import sys
import os
import unittest
import bpy

# 1. 获取插件根目录的父目录并加入 Python 路径
current_dir = os.path.dirname(os.path.realpath(__file__))
addon_root = os.path.dirname(current_dir)
parent_dir = os.path.dirname(addon_root)
addon_name = "baketool" # 显式指定包名

# 强制将开发目录放在最前面，防止加载已安装在 Blender 目录下的插件
if parent_dir in sys.path:
    sys.path.remove(parent_dir)
sys.path.insert(0, parent_dir)

# 如果已经加载过 baketool（例如从 Blender 的 scripts 目录），强制卸载它
for mod in list(sys.modules.keys()):
    if mod == addon_name or mod.startswith(f"{addon_name}."):
        del sys.modules[mod]

print(f"\n>>> Running tests in Blender {bpy.app.version_string}")
print(f">>> Forcing local addon path: {addon_root}")

def run():
    try:
        # 2. 以包的形式加载并注册插件 // Load and register the addon
        import baketool
        print(f">>> Successfully imported {addon_name} from {baketool.__file__}")
        
        # 手动执行注册逻辑，确保自定义属性挂载成功
        baketool.register()
        print(">>> Addon registered successfully.")
        
        from baketool.test_cases import (
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
        
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        modules = [
            test_presets, test_state, test_logic, 
            test_core, test_integration, test_crash_recovery, 
            test_export_system, test_edge_cases, test_refactor,
            test_complex_geometry, test_assets_system, test_performance,
            test_shading_complexity, test_udim_advanced
        ]
        
        for module in modules:
            suite.addTests(loader.loadTestsFromModule(module))
            
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        # 3. 根据结果退出
        if result.wasSuccessful():
            print(">>> ALL TESTS PASSED")
            sys.exit(0)
        else:
            print(">>> TESTS FAILED")
            sys.exit(1)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run()
