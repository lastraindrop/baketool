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
import bpy_extras
import os
import copy
import random
import mathutils
import numpy
import json
import bmesh
import logging
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Callable, Dict
from contextlib import contextmanager
from bpy import (props, types)
from bpy.props import PointerProperty, StringProperty, IntProperty, CollectionProperty, IntProperty
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
    "name": "sinple bake tool",
    "author": "最后的雨滴",
    "version": (0, 9, 0),
    "blender": (3, 3, 0),
    "location": "3D VIEW > N panel > Baking",
    "description": "Quite simple baking tool",
    "warning": "Testing",
    "doc_url": "",
    "category": "Bake",
}
        
addon_keymaps=[]

def register():
    bpy.utils.register_class(property.BakeObject)
    bpy.utils.register_class(property.Custombakechannels)
    bpy.utils.register_class(property.BakeJobSetting)
    bpy.utils.register_class(property.BakeJob)
    bpy.utils.register_class(property.BakeJobSpecific)
    bpy.utils.register_class(property.BakeJobs)
    

    bpy.utils.register_class(ops.Baketool_bake_operator)
    bpy.utils.register_class(ops.selected_node_bake)
    #bpy.utils.register_class(mix_to_BSDF)
    
    bpy.utils.register_class(ui.LIST_UL_Custombakechannellist)
    bpy.utils.register_class(ui.LIST_UL_Basicbakechannellist)
    bpy.utils.register_class(ui.LIST_UL_Jobslist)
    bpy.utils.register_class(ui.BAKE_PT_bakepanel)
    bpy.utils.register_class(ui.BAKE_PT_nodepanel)
    
    bpy.utils.register_class(ops.set_save_local)
    bpy.utils.register_class(ops.record_objects)
    
    bpy.types.Object.Bakemapindex = props.IntProperty(default=0,min=0,name='Texture set index')

    bpy.types.Scene.BakeJobs = props.PointerProperty(type = property.BakeJobs)
    
    bpy.utils.register_class(property.BakedImageResult)
    bpy.utils.register_class(ui.BAKETOOL_UL_BakedImageResults)
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
    bpy.utils.register_class(ui.BAKETOOL_PT_BakedResults)
    bpy.utils.register_class(ui.BAKETOOL_PT_ImageEditorResults)
    bpy.utils.register_class(ops.GenericChannelOperator)
    bpy.utils.register_class(ops.BAKETOOL_OT_DeleteResult)
    bpy.utils.register_class(ops.BAKETOOL_OT_DeleteAllResults)
    bpy.utils.register_class(ops.BAKETOOL_OT_ExportResult)
    bpy.utils.register_class(ops.BAKETOOL_OT_ExportAllResults)
    
    #制作 keymap//Create keymap
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="Object Mode")
        kmi = km.keymap_items.new('wm.call_panel', 'B', 'PRESS', ctrl=True,shift=True)
        kmi.properties.name = 'BAKE_PT_bakepanel'
        addon_keymaps.append((km, kmi))
    #制作翻译//Create translations
    bpy.app.translations.register("SBT_zh_CN", translations.trandict_CHN)
    
    
def unregister():
    bpy.utils.unregister_class(property.BakeObject)
    
    bpy.utils.unregister_class(property.ustombakechannels)
    bpy.utils.unregister_class(property.BakeJobSetting)
    bpy.utils.unregister_class(property.BakeJob)
    bpy.utils.unregister_class(property.BakeJobSpecific)
    bpy.utils.unregister_class(property.BakeJobs)
    bpy.utils.unregister_class(property.GenericChannelOperator)
    bpy.utils.unregister_class(property.Baketool_bake_operator)
    bpy.utils.unregister_class(property.selected_node_bake)
    #bpy.utils.unregister_class(mix_to_BSDF)
    
    bpy.utils.unregister_class(ui.LIST_UL_Custombakechannellist)
    bpy.utils.unregister_class(ui.LIST_UL_Basicbakechannellist)
    bpy.utils.unregister_class(ui.LIST_UL_Jobslist)
    bpy.utils.unregister_class(ui.BAKE_PT_bakepanel)
    bpy.utils.unregister_class(ui.BAKE_PT_nodepanel)
    
    bpy.utils.unregister_class(ops.set_save_local)
    bpy.utils.unregister_class(ops.record_objects)
    
    del bpy.types.Scene.BakeJobs
    
    bpy.utils.unregister_class(property.BakedImageResult)
    bpy.utils.unregister_class(ui.BAKETOOL_UL_BakedImageResults)
    del bpy.types.Scene.baked_image_results
    del bpy.types.Scene.baked_image_results_index
    
    bpy.utils.unregister_class(ui.BAKETOOL_PT_BakedResults)
    bpy.utils.unregister_class(ui.BAKETOOL_PT_ImageEditorResults)
    bpy.utils.unregister_class(ops.BAKETOOL_OT_DeleteResult)
    bpy.utils.unregister_class(ops.BAKETOOL_OT_DeleteAllResults)
    bpy.utils.unregister_class(ops.BAKETOOL_OT_ExportResult)
    bpy.utils.unregister_class(ops.BAKETOOL_OT_ExportAllResults)
    
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
        
    addon_keymaps.clear()
    #注销翻译//Unregister translations
    bpy.app.translations.unregister("SBT_zh_CN")
    
if __name__ == "__main__":
    register()