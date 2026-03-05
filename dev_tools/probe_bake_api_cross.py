import bpy
import os

def probe():
    print(f"Blender Version: {bpy.app.version_string}")
    scene = bpy.context.scene
    
    # Enable cycles
    try:
        import addon_utils
        addon_utils.enable("cycles")
        print("Cycles enabled")
    except Exception as e:
        print(f"Failed to enable cycles: {e}")

    scene.render.engine = 'CYCLES'
    
    if hasattr(scene.render, "bake"):
        bake = scene.render.bake
        print(f"BakeSettings exists. use_multires: {getattr(bake, 'use_multires', 'N/A')}")
        
        # Check available enums for bake_type (or type in 5.0)
        prop_name = "type" if bpy.app.version[0] >= 5 else "bake_type"
        if hasattr(bake, prop_name):
            enums = bake.bl_rna.properties[prop_name].enum_items.keys()
            print(f"BakeSettings.{prop_name} enums: {list(enums)}")
        else:
            print(f"BakeSettings has no property '{prop_name}'")
            
        # Try setting use_multires to False and check enums again
        if hasattr(bake, "use_multires"):
            bake.use_multires = False
            print("Set use_multires to False")
            enums = bake.bl_rna.properties[prop_name].enum_items.keys()
            print(f"BakeSettings.{prop_name} enums (after False): {list(enums)}")
            
            bake.use_multires = True
            print("Set use_multires to True")
            enums = bake.bl_rna.properties[prop_name].enum_items.keys()
            print(f"BakeSettings.{prop_name} enums (after True): {list(enums)}")

    # Check scene.cycles.bake_type if version >= 5
    if hasattr(scene, "cycles") and hasattr(scene.cycles, "bake_type"):
        enums = scene.cycles.bl_rna.properties["bake_type"].enum_items.keys()
        print(f"scene.cycles.bake_type enums: {list(enums)}")

if __name__ == "__main__":
    probe()
