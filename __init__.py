import bpy
import logging
from bpy import (props, types)
from bpy.props import PointerProperty, StringProperty, IntProperty, CollectionProperty
from . import translations
from . import ui
from . import ops
from . import property
from .core import cleanup
# 稳健加载测试模块 // Robust test module loading
try:
    from . import tests
    HAS_TESTS = True
except ImportError:
    import traceback
    traceback.print_exc()
    HAS_TESTS = False

from .constants import *

from bpy.app.handlers import persistent
from bpy.types import AddonPreferences

# 日志初始化 / Logging initialization
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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

# --- Auto Load Handler ---
@persistent
def load_default_preset(dummy):
    """Handler to load default preset on file load if enabled and safe to do so."""
    try:
        prefs = bpy.context.preferences.addons[__name__].preferences
    except KeyError:
        return

    if not prefs.auto_load or not prefs.default_preset_path:
        return

    import os
    import json
    from . import preset_handler

    filepath = prefs.default_preset_path
    # Remove quotes if user copied as string
    filepath = filepath.strip('"').strip("'")
    
    if not os.path.exists(filepath):
        return

    # Only load if the current scene is "clean" (has no jobs)
    # This prevents overwriting existing data in saved .blend files
    scene = bpy.context.scene
    if scene and hasattr(scene, "BakeJobs") and len(scene.BakeJobs.jobs) == 0:
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            preset_handler.PropertyIO().from_dict(scene.BakeJobs, data)
            logger.info(f"BakeTool: Auto-loaded default preset from {filepath}")
        except Exception as e:
            logger.warning(f"BakeTool: Failed to auto-load preset: {e}")

bl_info = {
    "name": "Simple Bake Tool",
    "author": "lastraindrop",
    "version": (0, 9, 4),
    "blender": (3, 6, 0),
    "location": "3D VIEW > N panel > Baking",
    "description": "A simplified, high-efficiency baking solution for Blender. Current undergoing heavy refactoring and optimization.",
    "warning": "Beta Version: Still in testing and optimization phase. Please back up your files before use.",
    "doc_url": "",
    "category": "Bake",
}

# Define lists of classes for registration
property_classes = [
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
    BakeToolPreferences, # Add Preferences to list
]

operator_classes = [
    ops.BAKETOOL_OT_ResetChannels,
    ops.BAKETOOL_OT_BakeOperator,
    ops.BAKETOOL_OT_BakeSelectedNode,
    ops.BAKETOOL_OT_SetSaveLocal,
    ops.BAKETOOL_OT_ManageObjects,
    ops.BAKETOOL_OT_RefreshUDIM,
    ops.BAKETOOL_OT_GenericChannelOperator,
    ops.BAKETOOL_OT_DeleteResult,
    ops.BAKETOOL_OT_DeleteAllResults,
    ops.BAKETOOL_OT_ExportResult,
    ops.BAKETOOL_OT_ExportAllResults,
    ops.BAKETOOL_OT_SaveSetting,
    ops.BAKETOOL_OT_LoadSetting,
    ops.BAKETOOL_OT_ClearCrashLog,
    ops.BAKETOOL_OT_QuickBake,
    cleanup.BAKETOOL_OT_EmergencyCleanup,
]

if HAS_TESTS:
    operator_classes.append(tests.BAKETOOL_OT_RunTests)

ui_classes = [
    ui.UI_UL_ObjectList,
    ui.LIST_UL_CustomBakeChannelList,
    ui.LIST_UL_JobsList,
    ui.BAKETOOL_UL_ChannelList,
    ui.BAKE_PT_BakePanel,
    ui.BAKE_PT_NodePanel,
    ui.BAKETOOL_UL_BakedImageResults,
    ui.BAKETOOL_PT_BakedResults,
    ui.BAKETOOL_PT_ImageEditorResults,
]

classes_to_register = property_classes + operator_classes + ui_classes
        
addon_keymaps=[]

def menu_func_quick_bake(self, context):
    self.layout.separator()
    self.layout.operator("bake.quick_bake", icon='RENDER_STILL')

def register():
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
    
    # Add to Object Context Menu
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func_quick_bake)
    
    # Register Auto Load Handler
    if load_default_preset not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_default_preset)
    
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
    if load_default_preset in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_default_preset)

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
