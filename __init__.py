# GPL声明
# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy
import logging
from bpy import (props, types)
from bpy.props import PointerProperty, StringProperty, IntProperty, CollectionProperty
from . import translations
from . import ui
from . import ops
from . import property

from .utils import *
from .constants import *

# 日志初始化 / Logging initialization
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


bl_info = {
    "name": "Simple Bake Tool",
    "author": "lastraindrop",
    "version": (0, 9, 0),
    "blender": (3, 6, 0),
    "location": "3D VIEW > N panel > Baking",
    "description": "Quite simple baking tool",
    "warning": "Testing",
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
]

operator_classes = [
    ops.BAKETOOL_OT_ResetChannels,
    ops.BAKETOOL_OT_BakeOperator,
    ops.BAKETOOL_OT_BakeSelectedNode,
    ops.BAKETOOL_OT_SetSaveLocal,
    ops.BAKETOOL_OT_ManageObjects,
    ops.BAKETOOL_OT_GenericChannelOperator,
    ops.BAKETOOL_OT_DeleteResult,
    ops.BAKETOOL_OT_DeleteAllResults,
    ops.BAKETOOL_OT_ExportResult,
    ops.BAKETOOL_OT_ExportAllResults,
    ops.BAKETOOL_OT_SaveSetting,
    ops.BAKETOOL_OT_LoadSetting,
    ops.BAKETOOL_OT_ClearCrashLog,
]

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
    
    # 制作 keymap // Create keymap
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="Object Mode")
        kmi = km.keymap_items.new('wm.call_panel', 'B', 'PRESS', ctrl=True, shift=True)
        kmi.properties.name = 'BAKE_PT_BakePanel'
        addon_keymaps.append((km, kmi))
    # 制作翻译 // Create translations
    bpy.app.translations.register("SBT_zh_CN", translations.trandict_CHN)
    
    
def unregister():
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
    bpy.app.translations.unregister("SBT_zh_CN")
    
if __name__ == "__main__":
    register()
