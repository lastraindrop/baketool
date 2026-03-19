import bpy
import logging
from bpy import (props, types)
from bpy.props import IntProperty, CollectionProperty, StringProperty, PointerProperty
from . import translations
from . import ui
from . import ops
from . import property
from . import preset_handler
from .core import cleanup
# 稳健加载测试模块 // Robust test module loading
try:
    from . import tests
    HAS_TESTS = True
except ImportError:
    logging.getLogger(__name__).warning("Failed to load test module", exc_info=True)
    HAS_TESTS = False

from .constants import CHANNEL_BAKE_INFO

from bpy.app.handlers import persistent
from bpy.types import AddonPreferences

# NOTE: No logging.basicConfig here. We use localized loggers.
logger = logging.getLogger(__name__)

# --- Preferences ---
class BakeToolPreferences(AddonPreferences):
    bl_idname = __name__

    default_preset_path: StringProperty(
        name="Default Preset",
        description="Path to the JSON preset file to load on new scenes",
        subtype='FILE_PATH',
    )
    
    auto_load: props.BoolProperty(
        name="Auto Load on Startup/New File",
        description="Automatically load this preset if the scene has no bake jobs",
        default=False
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="Default Startup Configuration")
        row = layout.row()
        row.prop(self, "auto_load")
        row.prop(self, "default_preset_path")


bl_info = {
    "name": "Simple Bake Tool",
    "author": "lastraindrop",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "3D VIEW > N panel > Baking",
    "description": "A simplified, high-efficiency baking solution for Blender. Robust architecture with cross-version compatibility.",
    "warning": "",
    "doc_url": "",
    "category": "Bake",
}


def get_classes():
    """Dynamically collect all classes from submodules that need registration."""
    import inspect
    classes = []
    
    # 1. Add local preferences
    classes.append(BakeToolPreferences)
    
    # 2. Add classes from relevant modules
    # Priority classes require specific registration order due to dependencies
    priority_classes = [
        property.BakeNormalSettings,
        property.BakePassSettings,
        property.BakeCombineSettings,
        property.BakeMeshSettings,
        property.BakeExtensionSettings,
        property.BakeObject,
        property.BakeChannelSource,
        property.BakeChannel,
        property.CustomBakeChannel,
        property.BakeImageSettings,
        property.BakeNodeSettings,
        property.BakeResultSettings,
        property.BakeJobSetting,
        property.BakeJob,
        property.BakeJobs,
        property.BakedImageResult,
        
        # Primary Panels (must be registered before subpanels)
        ui.BAKE_PT_BakePanel,
        ui.BAKE_PT_NodePanel,
        ui.BAKETOOL_PT_ImageEditorResults,
    ]
    classes.extend(priority_classes)
    
    # Auto-discover other modules (Operators, UI lists, etc.)
    other_modules = [ops, ui]
    if HAS_TESTS:
        other_modules.append(tests)
    other_modules.append(cleanup)

    # Filter to avoid duplicates and ensure they are modules
    other_modules = [m for m in other_modules if inspect.ismodule(m)]
    
    blender_bases = (bpy.types.Operator, bpy.types.Panel, bpy.types.PropertyGroup, 
                     bpy.types.UIList, bpy.types.Menu, bpy.types.Header)

    for mod in other_modules:
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if obj.__module__ == mod.__name__:
                try:
                    if obj in classes: continue
                    if issubclass(obj, blender_bases) and obj not in blender_bases:
                        classes.append(obj)
                except TypeError:
                    continue
    
    return classes

classes_to_register = [] # Will be populated during register()
        
addon_keymaps=[]

def menu_func_quick_bake(self, context):
    self.layout.separator()
    self.layout.operator("bake.quick_bake", icon='RENDER_STILL')

def register():
    global classes_to_register
    classes_to_register = get_classes()
    
    for cls in classes_to_register:
        bpy.utils.register_class(cls)
    
    bpy.types.Object.bake_map_index = props.IntProperty(default=0, min=0, name='Texture set index')

    bpy.types.Scene.BakeJobs = props.PointerProperty(type=property.BakeJobs)
    
    bpy.types.Scene.baked_image_results = CollectionProperty(
        type=property.BakedImageResult,
        name="Baked Image Results",
        description="List of baked image results with metadata"
    )
    bpy.types.Scene.baked_image_results_index = IntProperty(
        name="Index for baked image results",
        default=-1,
        description="Currently selected index in the baked image results list"
    )
    
    # 进度与状态反馈 / Progress and Status
    bpy.types.Scene.is_baking = props.BoolProperty(name="Is Baking", default=False)
    bpy.types.Scene.bake_progress = props.FloatProperty(name="Progress", default=0.0, min=0.0, max=100.0, subtype='PERCENTAGE')
    bpy.types.Scene.bake_status = props.StringProperty(name="Status", default="Idle")
    bpy.types.Scene.bake_error_log = props.StringProperty(name="Error Log", default="")
    
    # 测试反馈 / Test Feedback
    bpy.types.Scene.last_test_info = props.StringProperty(name="Last Test Info", default="")
    bpy.types.Scene.test_pass = props.BoolProperty(name="Test Passed", default=False)
    
    # Add to Object Context Menu
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func_quick_bake)
    
    # Register Auto Load Handler
    preset_handler.AutoLoadHandler.register()
    
    # 制作 keymap // Create keymap
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="Object Mode")
        kmi = km.keymap_items.new('wm.call_panel', 'B', 'PRESS', ctrl=True, shift=True)
        kmi.properties.name = 'BAKE_PT_BakePanel'
        addon_keymaps.append((km, kmi))
    # 制作翻译 // Create translations
    # Register all loaded languages using the package name as the context/domain
    bpy.app.translations.register(__name__, translations.translation_dict)
    
    
def unregister():
    # Remove Auto Load Handler
    preset_handler.AutoLoadHandler.unregister()

    # Remove from Object Context Menu
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func_quick_bake)
    
    for cls in reversed(classes_to_register):
        bpy.utils.unregister_class(cls)
    
    if hasattr(bpy.types.Object, 'bake_map_index'):
        del bpy.types.Object.bake_map_index
    
    del bpy.types.Scene.BakeJobs
    del bpy.types.Scene.baked_image_results
    del bpy.types.Scene.baked_image_results_index
    
    del bpy.types.Scene.is_baking
    del bpy.types.Scene.bake_progress
    del bpy.types.Scene.bake_status
    del bpy.types.Scene.bake_error_log

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
        
    addon_keymaps.clear()
    # 注销翻译 // Unregister translations
    bpy.app.translations.unregister(__name__)
    
if __name__ == "__main__":
    register()
