import bpy
from contextlib import contextmanager


def ensure_object_mode():
    """Safely ensure Object Mode."""
    try:
        if hasattr(bpy.context, "active_object") and bpy.context.active_object:
            if bpy.context.active_object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
    except (RuntimeError, AttributeError):
        pass


def ensure_cycles():
    """Idempotent enable of Cycles addon."""
    try:
        import addon_utils

        addon_utils.enable("cycles")
    except (ImportError, KeyError):
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

    # Remove images that are not persistent (use_fake_user=False)
    # Preserve images with use_fake_user=True to maintain user data
    for img in list(bpy.data.images):
        if not img.use_fake_user:
            bpy.data.images.remove(img, do_unlink=True)

    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col, do_unlink=True)

    for ng in list(bpy.data.node_groups):
        try:
            bpy.data.node_groups.remove(ng, do_unlink=True)
        except (ReferenceError, RuntimeError):
            pass

    # Purge any leaked BT_ scenes
    for s in list(bpy.data.scenes):
        if s.name.startswith("BT_"):
            try:
                if s != bpy.context.scene:  # Do not remove current context scene
                    bpy.data.scenes.remove(s)
            except (ReferenceError, RuntimeError):
                pass


def create_test_object(
    name,
    location=(0, 0, 0),
    color=(0.8, 0.8, 0.8, 1.0),
    metal=0.0,
    rough=0.5,
    mat_count=1,
):
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

        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        out = nodes.new("ShaderNodeOutputMaterial")
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

    job.setting.bake_mode = "SINGLE_OBJECT"
    return job.setting


class JobBuilder:
    """Fluent API for building Bake Jobs in tests."""

    def __init__(self, name="TestJob"):
        self.scene = bpy.context.scene
        if not hasattr(self.scene, "BakeJobs"):
            raise RuntimeError("BakeNexus addon not registered or property missing.")

        self.scene.BakeJobs.jobs.clear()
        self.job = self.scene.BakeJobs.jobs.add()
        self.job.name = name
        self.setting = self.job.setting
        self._defaults()

    def _defaults(self):
        self.setting.bake_mode = "SINGLE_OBJECT"
        self.setting.bake_type = "BSDF"
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

    def save_to(self, path, format="PNG"):
        self.setting.use_external_save = True
        self.setting.external_save_path = path
        self.setting.external_save_format = format
        return self

    def folder(self, name):
        self.setting.create_new_folder = True
        self.setting.folder_name = name
        return self

    def packing(self, r="NONE", g="NONE", b="NONE", a="NONE", suffix="_ORM"):
        self.setting.use_packing = True
        self.setting.pack_r = r
        self.setting.pack_g = g
        self.setting.pack_b = b
        self.setting.pack_a = a
        self.setting.pack_suffix = suffix
        return self

    def denoise(self, enabled=True):
        self.setting.use_denoise = enabled
        return self

    def auto_cage(self, mode="PROXIMITY", margin=0.1):
        self.setting.auto_cage_mode = mode
        self.setting.auto_cage_margin = margin
        return self

    def target_density(self, density):
        self.setting.texel_density = density
        return self

    def enable_channel(self, channel_id):
        for c in self.setting.channels:
            if c.id == channel_id:
                c.enabled = True
        return self

    def build(self):
        return self.job


class DataLeakChecker:
    """Monitors Blender data blocks to ensure no leaks during tests.

    Enhanced version that tracks both counts and specific IDs for more
    accurate leak detection.
    """

    def __init__(self):
        self.initial_counts = self._get_counts()
        self.initial_ids = self._get_ids()
        self.whitelist = set()

    def _get_counts(self):
        return {
            "images": len(bpy.data.images),
            "meshes": len(bpy.data.meshes),
            "materials": len(bpy.data.materials),
            "textures": len(bpy.data.textures),
            "node_groups": len(bpy.data.node_groups),
            "actions": len(bpy.data.actions),
            "brushes": len(bpy.data.brushes),
            "curves": len(bpy.data.curves),
            "worlds": len(bpy.data.worlds),
            "objects": len(bpy.data.objects),
            "collections": len(bpy.data.collections),
        }

    def _get_ids(self):
        return {
            "images": {img.name for img in bpy.data.images},
            "meshes": {mesh.name for mesh in bpy.data.meshes},
            "materials": {mat.name for mat in bpy.data.materials},
        }

    def add_whitelist(self, names, category="images"):
        """Add specific items to whitelist (won't be reported as leaks)."""
        if isinstance(names, str):
            names = [names]
        for name in names:
            self.whitelist.add((category, name))

    def check(self):
        current_counts = self._get_counts()
        current_ids = self._get_ids()
        leaks = []

        for key, initial in self.initial_counts.items():
            current = current_counts[key]
            if current > initial:
                new_ids = current_ids.get(key, set()) - self.initial_ids.get(key, set())
                new_ids = new_ids - {name for cat, name in self.whitelist if cat == key}
                leaks.append(f"{key}: {initial} -> {current} (New: {new_ids})")

        return leaks


@contextmanager
def assert_no_leak(test_case, aggressive=False):
    """Context manager to fail a test if data leaks are detected.

    Args:
        test_case: unittest.TestCase instance
        aggressive: If True, use cleanup_scene() after check (default: False)
                    Use this for isolated tests that shouldn't affect others.
    """
    checker = DataLeakChecker()
    yield

    leaks = checker.check()
    if leaks:
        test_case.fail(f"Data leak detected after operation: {', '.join(leaks)}")

    if aggressive:
        cleanup_scene()


def selective_cleanup(keep_images=None):
    """Selectively clean up only BakeNexus temporary data.

    This preserves user-created data while removing BT_ prefixed items
    and other known temporary structures.
    """
    keep_images = keep_images or []

    for img in list(bpy.data.images):
        if img.name.startswith("BT_"):
            try:
                bpy.data.images.remove(img, do_unlink=True)
            except (ReferenceError, RuntimeError):
                pass

    for s in list(bpy.data.scenes):
        if s.name.startswith("BT_"):
            try:
                bpy.data.scenes.remove(s, do_unlink=True)
            except (ReferenceError, RuntimeError):
                pass

    for ng in list(bpy.data.node_groups):
        if ng.name.startswith("BT_"):
            try:
                bpy.data.node_groups.remove(ng, do_unlink=True)
            except (ReferenceError, RuntimeError):
                pass


class MockSetting:
    """Mock object for PropertyGroup settings used in tests."""

    def __init__(self, **kwargs):
        # Default mandatory attributes for context/node managers
        self.res_x = 1024
        self.res_y = 1024
        self.bake_mode = "SINGLE_OBJECT"
        self.bake_type = "BSDF"
        self.use_auto_uv = False
        self.island_margin = 0.001
        self.margin = 16
        self.device = "GPU"
        self.use_denoise = False
        self.denoise_method = "OPENIMAGEIO"
        self.samples = 64
        self.sample = 64
        self.color_depth = "8"
        self.color_mode = "RGB"
        self.quality = 50
        self.use_motion = False
        self.frame = 1
        self.exr_code = "ZIP"
        self.tiff_code = "NONE"
        self.use_clear = True
        self.color_base = (0.0, 0.0, 0.0)
        self.use_external_save = False
        self.external_save_path = "//"
        self.external_save_format = "PNG"
        self.create_new_folder = False
        self.folder_name = "baked"
        self.channels = []
        self.id_start_color = (1.0, 0.0, 0.0, 1.0)
        self.id_manual_start_color = True
        self.id_seed = 0
        self.id_iterations = 50

        # Shading specific
        self.pack_r = "NONE"
        self.pack_g = "NONE"
        self.pack_b = "NONE"
        self.pack_a = "NONE"
        self.pack_suffix = "_ORM"

        # Override defaults
        for k, v in kwargs.items():
            setattr(self, k, v)
