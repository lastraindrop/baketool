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
        layout = self.layout
        scene = context.scene
        bj = scene.BakeJobs
        
        # --- 1. Top Dashboard (Crash Recover & Dev Zone) ---
        draw_crash_report(layout)
        
        # Dev Zone - More subtle UI
        if bj.debug_mode:
            col = layout.column(align=True)
            box = col.box()
            row = box.row(align=True)
            row.label(text="DEV MODE", icon='CONSOLE')
            row.operator("bake.run_dev_tests", text="Run Safety Audit", icon='CHECKBOX_HLT')
            
            if scene.last_test_info:
                sub = box.row()
                sub.scale_y = 0.8
                sub.alert = not scene.test_pass
                sub.label(text=scene.last_test_info, icon='INFO' if scene.test_pass else 'ERROR')
            layout.separator()

        # --- 2. Preset & Quick Actions ---
        col = layout.column(align=True)
        row = col.row(align=True)
        row.scale_y = 1.2
        row.template_icon_view(bj, "library_preset", show_labels=True)
        
        sub = row.column(align=True)
        sub.operator("bake.refresh_presets", text="", icon='FILE_REFRESH')
        sub.operator("bake.one_click_pbr", text="", icon='MATERIAL')
        sub.prop(bj, "debug_mode", text="", icon='CONSOLE', toggle=True)
        
        layout.separator(factor=0.5)

        # --- 3. Job Manager Sub-Panel ---
        main_box = layout.box()
        row = main_box.row()
        row.label(text="JOB MANAGER", icon='PREFERENCES')
        
        row = main_box.row(align=True)
        row.template_list("LIST_UL_JobsList", "", bj, "jobs", bj, "job_index", rows=2)
        
        side_col = row.column(align=True)
        draw_template_list_ops(side_col, "jobs_channel")
        
        footer = main_box.row(align=True)
        footer.operator("bake.save_setting", text="Export", icon='EXPORT')
        footer.operator("bake.load_setting", text="Import", icon='IMPORT')

        if not bj.jobs:
            layout.label(text="Create a job to define bake parameters", icon='INFO')
            return
            
        # --- 4. Detailed Configuration (Active Job) ---
        job = bj.jobs[bj.job_index]
        s = job.setting
        
        # Env Status Warnings
        draw_env_status(layout, s)
        
        # Active Job Config
        col = layout.column(align=True)
        col.prop(job, "name", text="Config Name", icon='SYNCHRONIZED')
        
        self.draw_inputs(context, col, bj, s)
        self.draw_channels(context, col, bj, s)
        self.draw_saves(context, col, bj, s)
        self.draw_others(context, col, bj, s)
        
        # --- 5. Main Execution ---
        layout.separator(factor=1.5)
        
        if scene.is_baking:
            status_box = layout.box()
            col = status_box.column(align=True)
            col.label(text=scene.bake_status, icon='RENDER_STILL')
            col.prop(scene, "bake_progress", text="", slider=True)
        else:
            row = layout.row()
            row.scale_y = 2.0
            row.operator("bake.bake_operator", text="START BAKE PIPELINE", icon='PLAY')

    def draw_inputs(self, context, l, bj, s):
        row = l.row(align=True)
        row.prop(bj, "open_inputs", text="1. SETUP & TARGETS", icon="DISCLOSURE_TRI_DOWN" if bj.open_inputs else "DISCLOSURE_TRI_RIGHT", emboss=False)
        if not bj.open_inputs: return
        
        col = l.column(align=True)
        # resolution & bit depth
        r = col.row(align=True)
        r.prop(s, "res_x", text="X")
        r.prop(s, "res_y", text="Y")
        r.prop(s, "use_float32", text="HDR", toggle=True)
        
        r = col.row(align=True)
        r.prop(s, "bake_type", text="")
        r.prop(s, "bake_mode", text="")
        
        # Targets Area
        sub = col.box()
        r = sub.row()
        r.label(text="Bake Objects", icon='OUTLINER_OB_MESH')
        if len(s.bake_objects) == 0:
            r.label(text="(Empty)", icon='ERROR')
            
        r = sub.row(align=True)
        r.template_list("UI_UL_ObjectList", "", s, "bake_objects", s, "active_object_index", rows=3)
        
        c = r.column(align=True)
        c.operator("bake.manage_objects", icon='ADD', text="").action = 'ADD'
        c.operator("bake.manage_objects", icon='REMOVE', text="").action = 'REMOVE'
        c.operator("bake.manage_objects", icon='TRASH', text="").action = 'CLEAR'
        
        # Smart UV & UDIM Logic
        if s.use_auto_uv or s.bake_mode == 'UDIM':
            grid = col.grid_flow(columns=2, align=True)
            grid.prop(s, "use_auto_uv", text="Auto UV", toggle=True)
            if s.bake_mode == 'UDIM':
                grid.prop(s, "udim_mode", text="")
            
            if s.use_auto_uv:
                r = col.row(align=True)
                r.prop(s, "auto_uv_angle", text="Angle")
                r.prop(s, "auto_uv_margin", text="Margin")
            
            if s.bake_mode == 'UDIM':
                col.operator("bake.refresh_udim_locations", icon='FILE_REFRESH', text="Sync UDIM Tiles")

        if s.bake_mode == 'SELECT_ACTIVE':
            sub = col.box()
            r = sub.row(align=True)
            r.prop(s, "active_object", text="Target")
            r.operator("bake.manage_objects", icon='EYEDROPPER', text="").action = 'SET_ACTIVE'
            sub.operator("bake.manage_objects", text="Smart Match (High -> Low)", icon='PIVOT_ACTIVE').action = 'SMART_SET'

    def draw_channels(self, context, l, bj, s):
        row = l.row(align=True)
        row.prop(bj, "open_channels", text="2. BAKE CHANNELS", icon="DISCLOSURE_TRI_DOWN" if bj.open_channels else "DISCLOSURE_TRI_RIGHT", emboss=False)
        if not bj.open_channels: return
        
        col = l.column(align=True)
        r = col.row(align=True)
        r.template_list("BAKETOOL_UL_ChannelList", "", s, "channels", s, "active_channel_index", rows=4)
        r.column(align=True).operator("bake.reset_channels", icon='FILE_REFRESH', text="")
        
        if s.channels and 0 <= s.active_channel_index < len(s.channels):
            draw_active_channel_properties(col, s.channels[s.active_channel_index], s)
            
        r = col.row(align=True)
        r.scale_y = 0.8
        r.prop(s, "use_light_map", text="Light", toggle=True)
        r.prop(s, "use_mesh_map", text="Mesh", toggle=True)
        r.prop(s, "use_extension_map", text="PBR", toggle=True)

    def draw_saves(self, context, l, bj, s):
        row = l.row(align=True)
        row.prop(bj, "open_saves", text="3. OUTPUT & EXPORT", icon="DISCLOSURE_TRI_DOWN" if bj.open_saves else "DISCLOSURE_TRI_RIGHT", emboss=False)
        if not bj.open_saves: return
        
        col = l.column(align=True)
        r = col.row(align=True)
        r.prop(s, "apply_to_scene", text="Auto-Apply", icon='MATERIAL', toggle=True)
        r.prop(s, "use_external_save", text="To Disk", icon='DISK_DRIVE', toggle=True)
        
        if s.use_external_save:
            sub = col.box()
            draw_file_path(sub, s, "external_save_path", 0)
            
            r = sub.row(align=True)
            r.prop(s, "name_setting", text="Naming")
            if s.name_setting == 'CUSTOM':
                r.prop(s, "custom_name", text="")
            
            draw_image_format_options(sub, s)
            
            # ORM & Pack
            sub.separator()
            sub.prop(s, "use_packing", text="ORM Packing (R+G+B+A)", icon='NODE_COMPOSITING')
            if s.use_packing:
                grid = sub.grid_flow(columns=4, align=True)
                grid.prop(s, "pack_r", text="R")
                grid.prop(s, "pack_g", text="G")
                grid.prop(s, "pack_b", text="B")
                grid.prop(s, "pack_a", text="A")
                
        if s.use_external_save:
            r = col.row(align=True)
            r.prop(s, "export_model", text="Export Mesh", icon='EXPORT', toggle=True)
            if s.export_model:
                r.prop(s, "export_format", text="")

        # Smart Intelligence
        sub = col.box()
        r = sub.row()
        r.label(text="Smart Intelligence", icon='LIGHTPROBE_CUBEMAP')
        
        row = sub.row(align=True)
        row.prop(s, "auto_cage_mode", text="Cage")
        if s.auto_cage_mode == 'PROXIMITY':
            row.prop(s, "auto_cage_margin", text="Margin")
        else:
            row.prop(s, "extrusion", text="Ext")
            
        row = sub.row(align=True)
        row.prop(s, "texel_density", text="Texel")
        row.prop(s, "auto_switch_vertex_paint", text="Auto-VP", toggle=True)
        
        sub.operator("bake.analyze_cage", text="Analyze Overlap", icon='RAYCAST')

    def draw_others(self, context, l, bj, s):
        row = l.row(align=True)
        row.prop(bj, "open_other", text="4. CUSTOM MAPS", icon="DISCLOSURE_TRI_DOWN" if bj.open_other else "DISCLOSURE_TRI_RIGHT", emboss=False)
        if not bj.open_other: return
        
        col = l.column(align=True)
        j = bj.jobs[bj.job_index]
        
        col.prop(s, "use_custom_map", text="Enable Custom Map Logic", icon='NODE_COMPOSITING', toggle=True)
        
        if s.use_custom_map:
            sub = col.box()
            r = sub.row()
            r.template_list("LIST_UL_CustomBakeChannelList", "", j, "custom_bake_channels", j, "custom_bake_channels_index", rows=3)
            draw_template_list_ops(r.column(align=True), "job_custom_channel")
            
            if j.custom_bake_channels and 0 <= j.custom_bake_channels_index < len(j.custom_bake_channels):
                c = j.custom_bake_channels[j.custom_bake_channels_index]
                cfg = sub.column(align=True)
                cfg.prop(c, "name")
                
                r = cfg.row(align=True)
                r.prop(c, "color_space", text="CS")
                r.prop(c, "bw", text="B&W", toggle=True)
                
                r = cfg.row(align=True)
                r.prop(c, "prefix", text="Pre")
                r.prop(c, "suffix", text="Suf")
                
                # Channel mapping logic
                cfg.separator()
                channels_to_draw = ['bw'] if c.bw else ['r','g','b','a']
                for char in channels_to_draw:
                    chan_settings = getattr(c, f"{char}_settings")
                    r = cfg.row(align=True)
                    r.prop(chan_settings, "use_map", text=char.upper(), toggle=True)
                    if chan_settings.use_map:
                        r.prop(chan_settings, "source", text="")
                        r.prop(chan_settings, "invert", text="", icon='ARROW_LEFTRIGHT', toggle=True)
                        r.prop(chan_settings, "sep_col", text="", icon='COLOR', toggle=True)
                        if chan_settings.sep_col:
                            r.prop(chan_settings, "col_chan", text="")

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