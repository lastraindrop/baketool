bl_info = {
    "name": "BakeNexus",
    "description": "Professional Texture Baking Pipeline for Blender",
    "author": "lastraindrop",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Baking",
    "warning": "BakeNexus 1.0.0: Backup your scenes before production use",
    "doc_url": "https://github.com/lastraindrop/baketool",
    "tracker_url": "https://github.com/lastraindrop/baketool/issues",
    "category": "Render",
}

# Standard library
import logging

# Third-party (Blender)
import bpy
from bpy import props
from bpy import types
from bpy.app.handlers import persistent
from bpy.props import (
    IntProperty,
    CollectionProperty,
    StringProperty,
    PointerProperty,
)
from bpy.types import AddonPreferences

# Local application
from .core import cleanup
from . import ops
from . import preset_handler
from . import translations
from . import ui
from . import property as prop_module
from .constants import CHANNEL_BAKE_INFO

logger = logging.getLogger(__name__)


# --- Preferences ---
class BakeNexusPreferences(AddonPreferences):
    bl_idname = __package__

    default_preset_path: StringProperty(
        name="Default Preset",
        description="Path to the JSON preset file to load on new scenes",
        subtype="FILE_PATH",
    )

    auto_load: props.BoolProperty(
        name="Auto Load on Startup/New File",
        description="Automatically load this preset if the scene has no bake jobs",
        default=False,
    )

    library_path: StringProperty(
        name="Preset Library Path",
        description="Directory containing .json presets and matching .png thumbnails",
        subtype="DIR_PATH",
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="Default Startup Configuration")
        col = layout.column(align=True)
        col.prop(self, "auto_load")
        col.prop(self, "default_preset_path")

        layout.separator()
        layout.label(text="Preset Library")
        layout.prop(self, "library_path")


def get_classes():
    """Dynamically collect all classes from submodules that need registration."""
    import inspect

    classes = []

    # 1. Add local preferences
    classes.append(BakeNexusPreferences)

    # 2. Add classes from relevant modules
    # Priority classes require specific registration order due to dependencies
    priority_classes = [
        # Base settings (no dependencies)
        prop_module.BakeNormalSettings,
        prop_module.BakePassSettings,
        prop_module.BakeCombineSettings,
        prop_module.BakeMeshSettings,
        prop_module.BakeExtensionSettings,
        prop_module.BakeImageSettings,
        prop_module.BakeChannelSource,
        prop_module.BakeObject,
        prop_module.BakedImageResult,
        # Intermediate groups
        prop_module.BakeChannel,
        prop_module.CustomBakeChannel,
        prop_module.BakeJobSetting,
        # Top-level groups
        prop_module.BakeJob,
        prop_module.BakeNodeSettings,
        prop_module.BakeResultSettings,
        prop_module.BakeJobs,
        # Primary Panels
        ui.BAKE_PT_BakePanel,
        ui.BAKE_PT_BakedResults,
        ui.BAKE_PT_NodePanel,
        ui.BAKE_PT_ImageEditorResults,
    ]
    classes.extend(priority_classes)

    # Auto-discover other modules (Operators, UI lists, etc.)
    other_modules = [ops, ui, prop_module, cleanup]

    # Filter to avoid duplicates and ensure they are modules
    other_modules = [m for m in other_modules if inspect.ismodule(m)]

    blender_bases = (
        bpy.types.Operator,
        bpy.types.Panel,
        bpy.types.PropertyGroup,
        bpy.types.UIList,
        bpy.types.Menu,
        bpy.types.Header,
    )

    for mod in other_modules:
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if obj.__module__ == mod.__name__:
                try:
                    if obj in classes:
                        continue
                    if issubclass(obj, blender_bases) and obj not in blender_bases:
                        classes.append(obj)
                except TypeError:
                    continue

    return classes


class _RegistryState:
    """Encapsulates mutable module-level state for safe register/unregister."""

    def __init__(self):
        self.classes_to_register: list = []
        self.addon_keymaps: list = []


registry = _RegistryState()


def menu_func_quick_bake(self, context):
    self.layout.separator()
    self.layout.operator("baketool.quick_bake", icon="RENDER_STILL")


def register():
    registry.classes_to_register = get_classes()

    for cls in registry.classes_to_register:
        bpy.utils.register_class(cls)

    bpy.types.Object.bake_map_index = props.IntProperty(
        default=0, min=0, name="Texture set index"
    )

    bpy.types.Scene.BakeJobs = props.PointerProperty(type=prop_module.BakeJobs)

    bpy.types.Scene.baked_image_results = CollectionProperty(
        type=prop_module.BakedImageResult,
        name="Baked Image Results",
        description="List of baked image results with metadata",
    )
    bpy.types.Scene.baked_image_results_index = IntProperty(
        name="Index for baked image results",
        default=-1,
        description="Currently selected index in the baked image results list",
    )

    # Progress and Status / 进度与状态反馈
    bpy.types.Scene.is_baking = props.BoolProperty(name="Is Baking", default=False)
    bpy.types.Scene.bake_progress = props.FloatProperty(
        name="Progress", default=0.0, min=0.0, max=100.0, subtype="PERCENTAGE"
    )
    bpy.types.Scene.bake_status = props.StringProperty(name="Status", default="Idle")
    bpy.types.Scene.bake_error_log = props.StringProperty(name="Error Log", default="")

    # 测试反馈 / Test Feedback
    bpy.types.Scene.last_test_info = props.StringProperty(
        name="Last Test Info", default=""
    )
    bpy.types.Scene.test_pass = props.BoolProperty(name="Test Passed", default=False)

    # Crash Recovery Cache
    bpy.types.Scene.baketool_has_crash_record = props.BoolProperty(
        name="Has Crash Record", default=False
    )
    bpy.types.Scene.baketool_crash_data_cache = props.StringProperty(
        name="Crash Data Cache", default=""
    )

    # Add to Object Context Menu
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func_quick_bake)

    # Register Auto Load Handler
    preset_handler.AutoLoadHandler.register()
    preset_handler.UpdateCrashCacheHandler.register()
    preset_handler.RestorePreviewMaterialsHandler.register()

    # 制作 keymap // Create keymap
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="Object Mode")
        kmi = km.keymap_items.new("wm.call_panel", "B", "PRESS", ctrl=True, shift=True)
        kmi.properties.name = "BAKE_PT_BakePanel"
        registry.addon_keymaps.append((km, kmi))
    # 制作翻译 // Create translations
    # Register all loaded languages using the package name as the context/domain
    bpy.app.translations.register(__name__, translations.translation_dict)


def unregister():
    # 1. Register Translations was last, so Unregister Translations is first
    bpy.app.translations.unregister(__name__)

    # 2. Keymaps
    for km, kmi in registry.addon_keymaps:
        km.keymap_items.remove(kmi)
    registry.addon_keymaps.clear()

    # 3. Handlers
    preset_handler.AutoLoadHandler.unregister()
    preset_handler.UpdateCrashCacheHandler.unregister()
    preset_handler.RestorePreviewMaterialsHandler.unregister()

    # 4. Menus
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func_quick_bake)

    # 5. Properties
    if hasattr(bpy.types.Object, "bake_map_index"):
        del bpy.types.Object.bake_map_index

    if hasattr(bpy.types.Scene, "BakeJobs"):
        del bpy.types.Scene.BakeJobs
    if hasattr(bpy.types.Scene, "baked_image_results"):
        del bpy.types.Scene.baked_image_results
    if hasattr(bpy.types.Scene, "baked_image_results_index"):
        del bpy.types.Scene.baked_image_results_index

    if hasattr(bpy.types.Scene, "is_baking"):
        del bpy.types.Scene.is_baking
    if hasattr(bpy.types.Scene, "bake_progress"):
        del bpy.types.Scene.bake_progress
    if hasattr(bpy.types.Scene, "bake_status"):
        del bpy.types.Scene.bake_status
    if hasattr(bpy.types.Scene, "bake_error_log"):
        del bpy.types.Scene.bake_error_log

    if hasattr(bpy.types.Scene, "last_test_info"):
        del bpy.types.Scene.last_test_info
    if hasattr(bpy.types.Scene, "test_pass"):
        del bpy.types.Scene.test_pass
    if hasattr(bpy.types.Scene, "baketool_has_crash_record"):
        del bpy.types.Scene.baketool_has_crash_record
    if hasattr(bpy.types.Scene, "baketool_crash_data_cache"):
        del bpy.types.Scene.baketool_crash_data_cache

    # 6. Classes (Registered first, unregister last)
    for cls in reversed(registry.classes_to_register):
        bpy.utils.unregister_class(cls)

    # Cleanup Previews (Side effect)
    from .core import thumbnail_manager

    thumbnail_manager.clear_all_previews()


if __name__ == "__main__":
    register()
