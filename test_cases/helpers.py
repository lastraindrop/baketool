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

def ensure_cycles():
    """Idempotent enable of Cycles addon."""
    try:
        import addon_utils
        addon_utils.enable("cycles")
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

class JobBuilder:
    """Fluent API for building Bake Jobs in tests."""
    def __init__(self, name="TestJob"):
        self.scene = bpy.context.scene
        if not hasattr(self.scene, "BakeJobs"):
            raise RuntimeError("BakeTool addon not registered or property missing.")
        
        self.scene.BakeJobs.jobs.clear()
        self.job = self.scene.BakeJobs.jobs.add()
        self.job.name = name
        self.setting = self.job.setting
        self._defaults()

    def _defaults(self):
        self.setting.bake_mode = 'SINGLE_OBJECT'
        self.setting.bake_type = 'BSDF'
        self.setting.res_x = 128
        self.setting.res_y = 128
        # Ensure default channels are reset
        from ..core import common
        common.reset_channels_logic(self.setting)

    def mode(self, mode):
        self.setting.bake_mode = mode
        return self

    def type(self, bake_type):
        self.setting.bake_type = bake_type
        # Reset channels when type changes
        from ..core import common
        common.reset_channels_logic(self.setting)
        return self

    def resolution(self, size):
        self.setting.res_x = size
        self.setting.res_y = size
        return self

    def add_objects(self, objects):
        if not isinstance(objects, (list, tuple)):
            objects = [objects]
        for obj in objects:
            bo = self.setting.bake_objects.add()
            bo.bakeobject = obj
        return self

    def save_to(self, path, format='PNG'):
        self.setting.use_external_save = True
        self.setting.external_save_path = path
        self.setting.external_save_format = format
        return self
    
    def enable_channel(self, channel_id):
        for c in self.setting.channels:
            if c.id == channel_id:
                c.enabled = True
        return self

    def build(self):
        return self.job

class DataLeakChecker:
    """Monitors Blender data blocks to ensure no leaks during tests."""
    def __init__(self):
        self.initial_counts = self._get_counts()

    def _get_counts(self):
        return {
            'images': len(bpy.data.images),
            'meshes': len(bpy.data.meshes),
            'materials': len(bpy.data.materials),
            'textures': len(bpy.data.textures),
            'node_groups': len(bpy.data.node_groups),
            'actions': len(bpy.data.actions),
            'brushes': len(bpy.data.brushes),
            'curves': len(bpy.data.curves),
            'worlds': len(bpy.data.worlds),
            'objects': len(bpy.data.objects),
            'collections': len(bpy.data.collections)
        }

    def check(self):
        current_counts = self._get_counts()
        leaks = []
        for key, initial in self.initial_counts.items():
            current = current_counts[key]
            if current > initial:
                leaks.append(f"{key}: {initial} -> {current}")
        return leaks

from contextlib import contextmanager

@contextmanager
def assert_no_leak(test_case):
    """Context manager to fail a test if data leaks are detected."""
    checker = DataLeakChecker()
    yield
    leaks = checker.check()
    if leaks:
        test_case.fail(f"Data leak detected after test: {', '.join(leaks)}")
