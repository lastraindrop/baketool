import sys
from pathlib import Path
import unittest
import bpy

# 1. Setup paths
current_dir = str(Path(__file__).resolve().parent)
addon_root = str(Path(current_dir).parent)
parent_dir = str(Path(addon_root).parent)
addon_name = "baketool"

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 2. Forcing local addon path
print(f"\n>>> Running Consolidated Suites in Blender {bpy.app.version_string}")

def run():
    try:
        import baketool
        baketool.register()
        print(">>> Addon registered.")
        
        loader = unittest.TestLoader()
        # Specifically look for suite_*.py
        suite = loader.discover(
            start_dir=str(Path(addon_root) / "test_cases"),
            pattern='suite_*.py',
            top_level_dir=parent_dir
        )
        
        print(f">>> Discovered {suite.countTestCases()} tests in consolidated suites.")
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        if result.wasSuccessful():
            print("\n>>> CONSOLIDATED SUITES PASSED")
            sys.exit(0)
        else:
            print("\n>>> CONSOLIDATED SUITES FAILED")
            sys.exit(1)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run()
