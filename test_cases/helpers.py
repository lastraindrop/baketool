import bpy
from ..constants import *

def ensure_object_mode():
    """Safely ensure Object Mode."""
    try:
        if hasattr(bpy.context, "active_object") and bpy.context.active_object:
            if bpy.context.active_object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
    except:
        pass

def cleanup_scene():
    """Deep cleanup of the current scene."""
    ensure_object_mode()
    
    if hasattr(bpy.data, "objects"):
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
            
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh, do_unlink=True)

    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat, do_unlink=True)
        
    for img in list(bpy.data.images):
        bpy.data.images.remove(img, do_unlink=True)
        
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col, do_unlink=True)
        
    for ng in list(bpy.data.node_groups):
        bpy.data.node_groups.remove(ng, do_unlink=True)

def create_test_object(name, location=(0,0,0), color=(0.8, 0.8, 0.8, 1.0), metal=0.0, rough=0.5, mat_count=1):
    """Create a standard test object with Principled BSDF and multiple slots."""
    ensure_object_mode()
        
    bpy.ops.mesh.primitive_plane_add(size=2, location=location)
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    
    if not obj.data.uv_layers:
        obj.data.uv_layers.new(name="UVMap")
        
    for i in range(mat_count):
        mat = bpy.data.materials.new(name=f"Mat_{name}_{i}")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()
        
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        out = nodes.new('ShaderNodeOutputMaterial')
        mat.node_tree.links.new(bsdf.outputs[0], out.inputs[0])
        
        def set_socket(name_list, val):
            for n in name_list:
                if n in bsdf.inputs:
                    bsdf.inputs[n].default_value = val
                    break
                    
        set_socket(["Base Color", "Color"], color)
        set_socket(["Metallic"], metal)
        set_socket(["Roughness"], rough)
        obj.data.materials.append(mat)
        
    return obj

def get_job_setting():
    """Helper to get a fresh Job Setting instance."""
    scene = bpy.context.scene
    if not hasattr(scene, "BakeJobs"):
        return None
    scene.BakeJobs.jobs.clear()
    job = scene.BakeJobs.jobs.add()
    
    job.setting.bake_mode = 'SINGLE_OBJECT' 
    return job.setting
