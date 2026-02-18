import sys
import os
import unittest
import bpy
import addon_utils

# 1. Setup path
current_dir = os.path.dirname(os.path.realpath(__file__))
addon_root = os.path.dirname(current_dir)
parent_dir = os.path.dirname(addon_root)
addon_name = "baketool"

if parent_dir in sys.path:
    sys.path.remove(parent_dir)
sys.path.insert(0, parent_dir)

for mod in list(sys.modules.keys()):
    if mod == addon_name or mod.startswith(f"{addon_name}."):
        del sys.modules[mod]

print(f"\n>>> DEBUG RUNNER: Blender {bpy.app.version_string}")

def run():
    try:
        import baketool
        baketool.register()
        
        # Load specific test
        suite = unittest.TestSuite()
        from baketool.test_cases.test_headless_safety import TestHeadlessSafety
        suite.addTest(unittest.makeSuite(TestHeadlessSafety))
        
        print(f">>> Running {suite.countTestCases()} tests...")
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        if not result.wasSuccessful():
            sys.exit(1)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run()
