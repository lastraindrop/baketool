import bpy
import os
import sys

# Add current directory to path
addon_dir = os.path.dirname(os.path.abspath(__file__))
if addon_dir not in sys.path:
    sys.path.append(addon_dir)

# Register addon
import baketool
try:
    baketool.register()
    print("Addon registered successfully.")
except Exception as e:
    print(f"Failed to register addon: {e}")
    sys.exit(1)

# Run tests
try:
    res = bpy.ops.bake.run_dev_tests()
    if res == {'FINISHED'}:
        print("Test Result: PASS")
        sys.exit(0)
    else:
        print("Test Result: FAIL")
        sys.exit(1)
except Exception as e:
    print(f"Error running tests: {e}")
    sys.exit(1)
finally:
    baketool.unregister()
