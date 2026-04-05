import bpy
import os
from .constants import (
    FORMAT_SETTINGS, CAT_MESH, CAT_LIGHT, CAT_DATA, CAT_EXTENSION, 
    CHANNEL_BAKE_INFO, CHANNEL_UI_LAYOUT, UI_MESSAGES
)
from .state_manager import BakeStateManager

def draw_header(layout, text, icon='NONE'):
    row = layout.row(align=True)
    row.alignment = 'LEFT'
    row.label(text=text, icon=icon)

def draw_file_path(layout, setting, path_prop, location):
    row = layout.row(align=True)
    row.prop(setting, path_prop, text="", icon='FILE_FOLDER')
    op = row.operator("bake.set_save_local", text='', icon='HOME')
    op.save_location = location

def draw_template_list_ops(layout, basic_name):
    col = layout.column(align=True)
    icons = {'ADD': 'ADD', 'DELETE': 'REMOVE', 'UP': 'TRIA_UP', 'DOWN': 'TRIA_DOWN', 'CLEAR': 'TRASH'}
    for item in ['ADD', 'DELETE', 'UP', 'DOWN', 'CLEAR']:
        ops = col.operator("bake.generic_channel_op", text='', icon=icons[item])
        ops.action_type = item
        ops.target = basic_name

def draw_image_format_options(layout, setting, prefix=""):
    f_p = f"{prefix}external_save_format"
    q_p = f"{prefix}quality"
    e_p = f"{prefix}exr_code"
    t_p = f"{prefix}tiff_codec"
    d_p = f"{prefix}color_depth"
    
    fmt = getattr(setting, f_p)
    fs = FORMAT_SETTINGS.get(fmt, {})
    
    row = layout.row(align=True)
    row.prop(setting, f_p, text="")
    
    if fs.get("quality"):
        row.prop(setting, q_p, text="Quality", slider=True)
    elif fs.get("codec"):
        row.prop(setting, e_p, text="")
    elif fs.get("tiff_codec"):
        row.prop(setting, t_p, text="")
        
    row = layout.row(align=True)
    if "depths" in fs and len(fs["depths"]) > 0:
        row.prop(setting, d_p, text="Depth")

# --- Specific Channel UI Drawers ---

def draw_active_channel_properties(layout, channel, setting):
    if not channel: return
    
    box = layout.box()
    row = box.row()
    row.label(text=f"{channel.name} Settings", icon='PREFERENCES')
    
    # 极简绘制公共属性 / Minimal public properties
    col = box.column(align=True)
    row = col.split(factor=0.3)
    row.label(text="Naming:")
    sub = row.row(align=True)
    sub.prop(channel, "prefix", text="Pre")
    sub.prop(channel, "suffix", text="Suf")
    
    col.separator()
    col.prop(channel, "override_defaults", toggle=True)
    if channel.override_defaults:
        sub = col.box()
        sub.prop(channel, "custom_cs", text="Space")
        sub.prop(channel, "custom_mode", text="Export Mode")

    box.separator()

    # 数据驱动绘制逻辑 / Data-driven drawing logic
    config = CHANNEL_UI_LAYOUT.get(channel.id)
    if not config: return

    layout_type = config.get('type')
    col = box.column(align=True)
    
    if 'header' in config:
        draw_header(col, config['header'], config.get('icon', 'NONE'))
        
    if layout_type == 'TOGGLES':
        r = col.row(align=True)
        for prop_data in config.get('props', []):
            prop_path, display_name = prop_data[0], prop_data[1]
            target, prop_name = _get_nested_attr(channel, prop_path)
            r.prop(target, prop_name, text=display_name, toggle=True)
            
    elif layout_type == 'PROPS':
        for prop_data in config.get('props', []):
            prop_path, display_name = prop_data[0], prop_data[1]
            icon = prop_data[2] if len(prop_data) > 2 else 'NONE'
            target, prop_name = _get_nested_attr(channel, prop_path)
            col.prop(target, prop_name, text=display_name, icon=icon)

def _get_nested_attr(obj, path):
    """Helper to resolve nested property paths."""
    parts = path.split('.')
    target = obj
    for part in parts[:-1]:
        target = getattr(target, part)
    return target, parts[-1]

def draw_results(scene, layout, bj):
    layout.label(text="Baked Results", icon='IMAGE_DATA')
    row = layout.row()
    row.template_list("BAKETOOL_UL_BakedImageResults", "", scene, "baked_image_results", scene, "baked_image_results_index", rows=5)
    
    col = row.column(align=True)
    col.operator("baketool.delete_result", text="", icon="TRASH")
    col.operator("baketool.delete_all_results", text="", icon="X")
    
    col.separator()
    col.operator("baketool.export_result", text="", icon="EXPORT")
    col.operator("baketool.export_all_results", text="", icon="FILE_FOLDER")
    
    # --- Detailed Metadata Inspector ---
    if scene.baked_image_results and scene.baked_image_results_index >= 0:
        res = scene.baked_image_results[scene.baked_image_results_index]
        box = layout.box()
        
        # Header with Channel and Object info
        row = box.row()
        row.label(text=f"Detail: {res.channel_type}", icon='INFO')
        row.label(text=f"Obj: {res.object_name}", icon='OBJECT_DATA')
        
        inner = box.column(align=True)
        
        # Row 1: File Info
        r = inner.row(align=True)
        r.label(text=res.file_size, icon='DISK_DRIVE')
        r.prop(res, "filepath", text="") # Read-only view
        
        # Row 2: Performance & Quality
        split = inner.split(factor=0.4)
        c1 = split.column()
        c1.label(text=f"{res.res_x} x {res.res_y}", icon='FULLSCREEN_ENTER')
        c1.label(text=f"Total: {res.duration:.2f} s", icon='TIME')
        
        c2 = split.column()
        row = c2.row(align=True)
        row.label(text=f"Bake: {res.bake_time:.2f}s")
        row.label(text=f"Save: {res.save_time:.2f}s")
        c2.label(text=f"{res.bake_type} ({res.device})", icon='NODE_COMPOSITING')

    layout.separator()
    box = layout.box()
    draw_header(box, "Export Settings", 'OUTPUT')
    col = box.column(align=True)
    
    col.prop(bj.bake_result_settings, "external_save_path", text="")
    draw_image_format_options(col, bj.bake_result_settings.image_settings, "")

def draw_crash_report(layout):
    mgr = BakeStateManager()
    if mgr.has_crash_record():
        data = mgr.read_log()
        if not data: return
        
        box = layout.box()
        box.alert = True 
        row = box.row()
        row.label(text="Detected Unexpected Exit (Crash)", icon='ERROR')
        row.operator("bake.clear_crash_log", text="", icon='X')
        
        col = box.column()
        col.scale_y = 0.8
        
        t = data.get('start_time', '?')
        obj = data.get('current_object', 'Unknown')
        curr = data.get('current_step', 0)
        total = data.get('total_steps', '?')
        err = data.get('last_error', '')
        
        col.label(text=f"Time: {t}")
        col.label(text=f"Last Object: {obj}")
        col.label(text=f"Progress: {curr} / {total}")
        
        if err:
            col.label(text=f"Last Error: {err}")
        else:
            col.label(text="Check this object's UV/Mesh complexity")
            
        box.separator()
        op = box.operator("bake.bake_operator", text="Resume Interrupted Bake", icon='RECOVER_LAST')
        op.is_resume = True

class UI_UL_ObjectList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        if item.bakeobject:
            obj = item.bakeobject
            has_uv = True
            if obj.type == 'MESH':
                has_uv = (len(obj.data.uv_layers) > 0)
            
            row.label(text=obj.name, icon='OBJECT_DATA' if has_uv else 'ERROR')
            if not has_uv:
                row.label(text="(No UV!)", icon='NONE')
        else:
            row.label(text="Missing", icon='ERROR')
            
        # Contextual UI for Custom UDIM
        scene = context.scene
        if hasattr(scene, "BakeJobs") and scene.BakeJobs.jobs:
            job = scene.BakeJobs.jobs[scene.BakeJobs.job_index]
            s = job.setting
            if s.bake_mode == 'UDIM':
                if s.udim_mode in {'CUSTOM', 'REPACK'}:
                    row.prop(item, "udim_tile", text="Tile", emboss=False)
                
                # Resolution Override UI
                row.separator()
                row.prop(item, "override_size", text="", icon='FULLSCREEN_ENTER')
                if item.override_size:
                    row.prop(item, "udim_width", text="W")
                    row.prop(item, "udim_height", text="H")

class BAKETOOL_UL_ChannelList(bpy.types.UIList):
    def filter_items(self, context, data, propname):
        channels = getattr(data, propname)
        flt_flags = []
        flt_neworder = []
        
        for i, item in enumerate(channels):
            if item.valid_for_mode:
                flt_flags.append(self.bitflag_filter_item)
            else:
                flt_flags.append(0)
                
        return flt_flags, flt_neworder

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        info = CHANNEL_BAKE_INFO.get(item.id, {})
        cat = info.get('cat', 'DATA')
        # Optimized mapping: Use RENDERLAYERS for passes/lighting results to avoid confusion with light objects
        icon_map = {
            CAT_MESH: 'MESH_DATA', 
            CAT_LIGHT: 'RENDERLAYERS', 
            CAT_DATA: 'MATERIAL',
            CAT_EXTENSION: 'NODETREE'
        }
        ic = icon_map.get(cat, 'TEXTURE')
        
        row = layout.row(align=True)
        row.prop(item, "enabled", text="")
        row.label(text=item.name, icon=ic)

class LIST_UL_JobsList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "enabled", text="")
        row.label(text=item.name or f"Job {index}", icon='PREFERENCES')

class LIST_UL_CustomBakeChannelList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.label(text=item.name or f"Ch {index}", icon='NODE_COMPOSITING')

class BAKETOOL_UL_BakedImageResults(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        # Use split to align resolution to the right or show it subtly
        row.prop(item, "image", text="", emboss=False, icon='IMAGE_DATA')
        row.label(text=item.channel_type)
        
        # Display resolution subtly on the right
        if item.res_x > 0:
            row.label(text=f"{item.res_x}x{item.res_y}", icon='NONE')

def draw_env_status(layout, setting):
    """Checks for project-wide potential issues (missing addons, invalid paths, etc)"""
    any_issue = False
    
    # 1. Check Export Addons
    if setting.export_model:
        op_map = {'FBX': 'fbx', 'GLB': 'gltf', 'USD': 'usd_export'}
        target_op = op_map.get(setting.export_format)
        
        has_addon = False
        if target_op == 'fbx': has_addon = hasattr(bpy.ops.export_scene, "fbx")
        elif target_op == 'gltf': has_addon = hasattr(bpy.ops.export_scene, "gltf")
        elif target_op == 'usd_export': has_addon = hasattr(bpy.ops.wm, "usd_export")
        
        if not has_addon:
            box = layout.box()
            box.alert = True
            row = box.row()
            row.label(text=f"{setting.export_format} Addon is disabled!", icon='ERROR')
            row.operator("bake.open_addon_prefs", text="Fix", icon='SETTINGS')
            any_issue = True

    # 2. Check Path Validity
    if setting.use_external_save or setting.export_model:
        path = bpy.path.abspath(setting.external_save_path)
        if not path or not os.path.exists(path):
            box = layout.box()
            box.alert = True
            box.label(text="Invalid Export Path!", icon='ERROR')
            any_issue = True

    if any_issue:
        layout.separator()

class BAKE_PT_NodePanel(bpy.types.Panel):
    bl_label = "Node Bake"
    bl_idname = "BAKE_PT_NodePanel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Baking'
    
    @classmethod
    def poll(cls, context): 
        return context.space_data.tree_type == 'ShaderNodeTree'
        
    def draw(self, context):
        l = self.layout
        bj = context.scene.BakeJobs
        nbs = bj.node_bake_settings
        
        b = l.box()
        draw_header(b, "Res & Save", 'PREFERENCES')
        
        r = b.row(align=True)
        r.prop(nbs, "res_x", text="X")
        r.prop(nbs, "res_y", text="Y")
        
        b.prop(nbs, "use_external_save", text="To Disk", icon='DISK_DRIVE')
        if nbs.use_external_save:
            draw_file_path(b, nbs, "external_save_path", 2)
            draw_image_format_options(b, nbs.image_settings, "")
            
        l.operator("bake.selected_node_bake", text="Bake Node", icon='RENDER_STILL')

class BAKE_PT_BakePanel(bpy.types.Panel):
    bl_label = "Baking Tool"
    bl_idname = "BAKE_PT_BakePanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Baking'
    
    def draw(self, context):
        l = self.layout
        draw_crash_report(l)
        
        scene = context.scene
        bj = scene.BakeJobs
        
        # --- Global Developer / Debug Mode ---
        row = l.row(align=True)
        row.alignment = 'RIGHT'
        row.prop(bj, "debug_mode", text="", icon='CONSOLE')
        
        if bj.debug_mode:
            box = l.box()
            box.label(text="Developer Zone", icon='CONSOLE')
            box.alert = True
            box.label(text="⚠ Warning: Developer use only!", icon='ERROR')
            box.label(text="Operations may reset scene data.", icon='INFO')
            
            row = box.row(align=True)
            row.operator("bake.run_dev_tests", text="Run Test Suite", icon='CHECKBOX_HLT')
            
            if scene.last_test_info:
                sub = box.box()
                if not scene.test_pass: sub.alert = True
                sub.label(text=scene.last_test_info, icon='INFO' if scene.test_pass else 'ERROR')
            l.separator()
        
        if scene.is_baking:
            col = l.column(align=True)
            col.label(text=scene.bake_status, icon='RENDER_STILL')
            col.prop(scene, "bake_progress", text="Progress", slider=True)
            l.separator()
            
        if scene.bake_error_log:
            box = l.box()
            box.alert = True
            box.label(text="Bake Errors:", icon='ERROR')
            for line in scene.bake_error_log.split('\n')[-5:]:
                if line: box.label(text=line)
            op = box.operator("wm.context_set_string", text="Clear Errors", icon='TRASH')
            op.data_path = "scene.bake_error_log"
            op.value = ""

        # Roadmap 2.3: Visual Preset Library
        b = l.box()
        draw_header(b, "Preset Library", 'ASSET_MANAGER')
        row = b.row(align=True)
        row.template_icon_view(bj, "library_preset", show_labels=True)
        row.operator("bake.refresh_presets", text="", icon='FILE_REFRESH')
        row.operator("bake.one_click_pbr", text="One-Click PBR", icon='MATERIAL')

        b = l.box()
        r = b.row()
        
        r.template_list("LIST_UL_JobsList", "", bj, "jobs", bj, "job_index", rows=3)
        draw_template_list_ops(r, "jobs_channel")

        row = b.row(align=True)
        row.operator("bake.save_setting", text="Save Preset", icon='IMPORT')
        row.operator("bake.load_setting", text="Load Preset", icon='EXPORT')
        
        if not bj.jobs:
            b.label(text="Add job to start", icon='INFO')
            return
            
        j = bj.jobs[bj.job_index]
        s = j.setting
        
        draw_env_status(l, s)
        
        b.prop(j, "name", text="")
        
        self.draw_inputs(context, l, bj, s)
        self.draw_channels(context, l, bj, s)
        self.draw_saves(context, l, bj, s)
        self.draw_others(context, l, bj, s)
        
        l.separator()
        r = l.row()
        r.scale_y = 2.0
        r.operator("bake.bake_operator", text="START BAKE", icon='RENDER_STILL')

    def draw_inputs(self, context, l, bj, s):
        l.prop(bj, "open_inputs", text="Inputs", icon="DISCLOSURE_TRI_DOWN" if bj.open_inputs else "DISCLOSURE_TRI_RIGHT", emboss=False)
        if not bj.open_inputs: return
        
        b = l.box()
        col = b.column(align=True)
        r = col.row(align=True)
        r.prop(s, "res_x")
        r.prop(s, "res_y")
        
        r = col.row(align=True)
        r.prop(s, "use_float32", text="32 Bit")
        r.prop(s, "use_denoise", text="Denoise")
        
        col.prop(s, "bake_type")
        col.prop(s, "bake_mode")
        
        draw_header(b, "Targets", 'OUTLINER_OB_MESH')
        
        if len(s.bake_objects) == 0:
            box = b.box()
            box.alert = True
            box.label(text="List is empty!", icon='ERROR')
            box.label(text="Add objects to bake.", icon='INFO')
            
        r = b.row()
        r.template_list("UI_UL_ObjectList", "", s, "bake_objects", s, "active_object_index", rows=3)
        
        c = r.column(align=True)
        op = c.operator("bake.manage_objects", icon='FILE_REFRESH', text="")
        op.action = 'SET'
        op = c.operator("bake.manage_objects", icon='ADD', text="")
        op.action = 'ADD'
        op = c.operator("bake.manage_objects", icon='REMOVE', text="")
        op.action = 'REMOVE'
        op = c.operator("bake.manage_objects", icon='TRASH', text="")
        op.action = 'CLEAR'
        
        # --- UV & Layout Settings ---
        sb = b.box()
        draw_header(sb, "UV Settings", 'GROUP_UVS')
        
        # Smart UV Toggle
        sb.prop(s, "use_auto_uv", toggle=True)
        if s.use_auto_uv:
            col = sb.column(align=True)
            row = col.row(align=True)
            row.prop(s, "auto_uv_angle")
            row.prop(s, "auto_uv_margin")
        
        # UDIM Settings
        if s.bake_mode == 'UDIM':
            sb.separator()
            draw_header(sb, "UDIM Tiling", 'FILE_IMAGE')
            
            col = sb.column(align=True)
            col.prop(s, "udim_mode", text="Method")
            
            if s.udim_mode == 'DETECT':
                col.label(text="Auto-detects tiles from object UVs", icon='INFO')
            elif s.udim_mode == 'CUSTOM':
                col.label(text="Assign tiles in the object list above", icon='INFO')
            elif s.udim_mode == 'REPACK':
                col.label(text="Re-packs 1001 objects to new tiles", icon='INFO')

            col.operator("bake.refresh_udim_locations", icon='FILE_REFRESH', text="Refresh / Repack UDIMs")

        # Common UV Output Settings (Name)
        # Show if we are creating new UVs (Smart UV) OR modifying them (UDIM)
        if s.use_auto_uv or s.bake_mode == 'UDIM':
            sb.separator()
            sb.prop(s, "auto_uv_name", text="Target UV Name")

        if any(c.id.startswith('ID_') for c in s.channels if c.enabled):
            sb = b.box(); draw_header(sb, "ID Map Optimization", 'COLOR')
            
            sb.prop(s, "id_manual_start_color")
            if s.id_manual_start_color:
                sb.prop(s, "id_start_color", text="")
                
            sb.prop(s, "id_iterations", slider=True)
            sb.prop(s, "id_seed")

        if s.bake_mode == 'SELECT_ACTIVE':
            sb = b.box()
            sb.label(text="Target (Active)", icon='TARGET')
            
            row = sb.row()
            row.scale_y = 1.2
            op = row.operator("bake.manage_objects", text="Smart Set (Sel -> Act)", icon='PIVOT_ACTIVE')
            op.action = 'SMART_SET'
            
            row = sb.row(align=True)
            row.prop(s, "active_object", text="")
            op = row.operator("bake.manage_objects", icon='EYEDROPPER', text="")
            op.action = 'SET_ACTIVE'

    def draw_channels(self, context, l, bj, s):
        l.prop(bj, "open_channels", text="Channels", icon="DISCLOSURE_TRI_DOWN" if bj.open_channels else "DISCLOSURE_TRI_RIGHT", emboss=False)
        if not bj.open_channels: return
        
        b = l.box()
        r = b.row()
        r.template_list("BAKETOOL_UL_ChannelList", "", s, "channels", s, "active_channel_index", rows=5)
        r.column().operator("bake.reset_channels", icon='FILE_REFRESH', text="")
        
        if s.channels and 0 <= s.active_channel_index < len(s.channels):
            draw_active_channel_properties(b, s.channels[s.active_channel_index], s)
            
        row = b.row(align=True)
        row.prop(s, "use_light_map", text="Light Maps", icon='LIGHT_SUN', toggle=True)
        row.prop(s, "use_mesh_map", text="Mesh Maps", icon='MESH_DATA', toggle=True)
        row.prop(s, "use_extension_map", text="Extension (PBR Conv)", icon='NODE_COMPOSITING', toggle=True)

    def draw_saves(self, context, l, bj, s):
        l.prop(bj, "open_saves", text="Save & Export", icon="DISCLOSURE_TRI_DOWN" if bj.open_saves else "DISCLOSURE_TRI_RIGHT", emboss=False)
        if not bj.open_saves: return
        
        b = l.box()
        # --- 1. Naming & Global Toggle ---
        draw_header(b, "Workflows", 'PREFERENCES')
        row = b.row(align=True)
        row.prop(s, "apply_to_scene", text="Apply to Scene", icon='MATERIAL')
        
        # Constraint: Export Mesh requires External Save
        sub = row.row(align=True)
        sub.active = s.use_external_save
        sub.prop(s, "export_model", text="Export Mesh", icon='EXPORT')
        
        if s.export_model:
            row = b.row(align=True)
            row.separator()
            sub = row.row(align=True)
            sub.prop(s, "export_format", expand=True)
            
            row = b.row(align=True)
            row.separator()
            row.prop(s, "export_textures_with_model")
            
        b.separator()
        
        # --- 2. Files & Formats ---
        draw_header(b, "Output Files", 'DISK_DRIVE')
        b.prop(s, "use_external_save", text="External Save", toggle=True)
        
        if s.use_external_save or s.export_model:
            sb = b.box()
            if s.export_model and not s.use_external_save:
                sb.alert = True
                sb.label(text="Warning: External Save recommended for export", icon='ERROR')
            
            draw_file_path(sb, s, "external_save_path", 0)
            
            row = sb.row(align=True)
            row.label(text="Naming:")
            row.prop(s, "name_setting", text="")
            if s.name_setting=='CUSTOM':
                row.prop(s, "custom_name", text="")
                
            draw_image_format_options(sb, s)

            # --- Smart Intelligence (Roadmap 1.1) ---
            sb.separator()
            draw_header(sb, "Smart Intelligence", 'LIGHTPROBE_CUBEMAP')
            box = sb.box()
            box.prop(s, "auto_cage_mode")
            if s.auto_cage_mode == 'PROXIMITY':
                box.prop(s, "auto_cage_margin")
            else:
                box.prop(s, "extrusion")
            
            row = box.row(align=True)
            row.prop(s, "texel_density")
            
            row = box.row(align=True)
            row.prop(s, "auto_switch_vertex_paint")
            box.operator("bake.analyze_cage", text="Analyze Cage Overlap", icon='RAYCAST')
            
            # --- Channel Packing (ORM) ---
            sb.separator()
            sb.prop(s, "use_packing", text="Auto Pack Channels (ORM)", icon='NODE_COMPOSITING')
            if s.use_packing:
                grid = sb.grid_flow(columns=2, align=True)
                grid.prop(s, "pack_r", text="R")
                grid.prop(s, "pack_g", text="G")
                grid.prop(s, "pack_b", text="B")
                grid.prop(s, "pack_a", text="A")
                sb.prop(s, "pack_suffix")
                
                # Roadmap 1.1: Preview Toggle
                row = sb.row()
                row.operator("bake.toggle_preview", 
                             text="Stop Preview" if s.use_preview else "Preview Packing", 
                             icon='RESTRICT_VIEW_OFF' if s.use_preview else 'RESTRICT_VIEW_ON',
                             depress=s.use_preview)

            # --- 3. Animation Sequence ---
            sb.separator()
            sb.prop(s, "bake_motion", text="Bake Image Sequence", icon='RENDER_ANIMATION')

    def draw_others(self, context, l, bj, s):
        l.prop(bj, "open_other", text="Custom Maps", icon="DISCLOSURE_TRI_DOWN" if bj.open_other else "DISCLOSURE_TRI_RIGHT", emboss=False)
        if not bj.open_other: return
        
        b = l.box()
        j = bj.jobs[bj.job_index]
        b.prop(s, "use_custom_map", text="Enable Custom Map Logic", toggle=True)
        
        if s.use_custom_map:
            r = b.row()
            r.template_list("LIST_UL_CustomBakeChannelList", "", j, "custom_bake_channels", j, "custom_bake_channels_index", rows=4)
            draw_template_list_ops(r, "job_custom_channel")
            
            if j.custom_bake_channels and 0 <= j.custom_bake_channels_index < len(j.custom_bake_channels):
                c = j.custom_bake_channels[j.custom_bake_channels_index]
                db = b.box()
                col = db.column(align=True)
                
                col.prop(c, "name")
                col.prop(c, "color_space", text="CS")
                col.prop(c, "bw", text="BW Mode", toggle=True)
                
                r = col.row(align=True)
                r.prop(c, "prefix", text="Pre")
                r.prop(c, "suffix", text="Suf")
                
                channels_to_draw = ['bw'] if c.bw else ['r','g','b','a']
                for char in channels_to_draw:
                    settings = getattr(c, f"{char}_settings")
                    r = db.row(align=True)
                    r.prop(settings, "use_map", text=char.upper(), toggle=True)
                    
                    if settings.use_map:
                        r.prop(settings, "source", text="")
                        r.prop(settings, "invert", text="", icon='ARROW_LEFTRIGHT')
                        r.prop(settings, "sep_col", text="", icon='COLOR')
                        
                        if settings.sep_col:
                            r.prop(settings, "col_chan", text="")

class BAKETOOL_PT_BakedResults(bpy.types.Panel):
    bl_label = "Baked Results"
    bl_idname = "BAKETOOL_PT_baked_results"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Baking"
    bl_parent_id = "BAKE_PT_BakePanel"
    bl_order = 2
    
    def draw(self, context):
        draw_results(context.scene, self.layout, context.scene.BakeJobs)

class BAKETOOL_PT_ImageEditorResults(bpy.types.Panel):
    bl_label = "Baked Results"
    bl_idname = "BAKE_PT_ImageEditorResults"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Baking"
    
    def draw(self, context):
        draw_results(context.scene, self.layout, context.scene.BakeJobs)