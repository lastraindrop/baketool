import bpy
import sys

print("Probing Blender 5.0 API for Bake Settings...")
scene = bpy.context.scene
scene.render.engine = 'CYCLES'

print(f"Render Engine: {scene.render.engine}")

try:
    if hasattr(scene, 'cycles'):
        print("scene.cycles keys: ", [p for p in dir(scene.cycles) if 'bake' in p])
        try:
            print(f"scene.cycles.bake_type enums: {scene.cycles.bl_rna.properties['bake_type'].enum_items.keys()}")
        except Exception as e:
            print(f"Could not get scene.cycles.bake_type enums: {e}")
except: pass

print("scene.render keys: ", [p for p in dir(scene.render) if 'bake' in p])

if hasattr(scene.render, 'bake'):
    print("scene.render.bake type:", type(scene.render.bake))
    print("scene.render.bake keys: ", [p for p in dir(scene.render.bake) if 'type' in p or 'bake' in p])
    try:
        print(f"scene.render.bake.type enums: {scene.render.bake.bl_rna.properties['type'].enum_items.keys()}")
    except Exception as e:
        print(f"Could not get scene.render.bake.type enums: {e}")

# Check if scene.render.bake_type exists
if hasattr(scene.render, 'bake_type'):
    print(f"scene.render.bake_type exists. Value: {scene.render.bake_type}")
else:
    print("scene.render.bake_type does NOT exist")

# Try to find valid assignments
try:
    scene.render.bake.type = 'EMIT'
    print("SUCCESS: Set scene.render.bake.type = 'EMIT'")
except Exception as e:
    print(f"FAIL: Set scene.render.bake.type = 'EMIT' -> {e}")
