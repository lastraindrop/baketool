import bpy
from .constants import FORMAT_SETTINGS, CAT_MESH, CAT_LIGHT, CAT_DATA, CHANNEL_BAKE_INFO
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
    f_p = f"{prefix}save_format"
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

def _draw_normal(layout, channel):
    col = layout.column(align=True)
    draw_header(col, "Normal Map", 'NORMALS_FACE')
    col.prop(channel, "normal_type", text="Std")
    if channel.normal_type == 'CUSTOM':
        r = col.row(align=True)
        r.prop(channel, "normal_X")
        r.prop(channel, "normal_Y")
        r.prop(channel, "normal_Z")
    col.prop(channel, "normal_obj", text="Object Space")

def _draw_light_path(layout, channel):
    col = layout.column(align=True)
    draw_header(col, "Light Paths", 'LIGHT_SUN')
    r = col.row(align=True)
    r.prop(channel, f"{channel.id}_dir", text="Dir", toggle=True)
    r.prop(channel, f"{channel.id}_ind", text="Ind", toggle=True)
    r.prop(channel, f"{channel.id}_col", text="Col", toggle=True)

def _draw_combine(layout, channel):
    col = layout.column(align=True)
    draw_header(col, "Passes", 'RENDERLAYERS')
    r = col.row(align=True)
    r.prop(channel, "com_dir", text="Dir", toggle=True)
    r.prop(channel, "com_ind", text="Ind", toggle=True)
    col.separator()
    grid = col.grid_flow(columns=2, align=True)
    grid.prop(channel, "com_diff")
    grid.prop(channel, "com_gloss")
    grid.prop(channel, "com_tran")
    grid.prop(channel, "com_emi")

def _draw_ao_bevel(layout, channel):
    col = layout.column(align=True)
    col.prop(channel, f"{channel.id}_sample", text="Samples")
    col.prop(channel, f"{channel.id}_rad" if channel.id!='ao' else "ao_dis", text="Rad/Dist")

def _draw_curvature(layout, channel):
    col = layout.column(align=True)
    col.prop(channel, "curvature_sample", text="Samples")
    col.prop(channel, "curvature_rad", text="Radius")
    col.prop(channel, "curvature_contrast", text="Contrast")

def _draw_wireframe(layout, channel):
    layout.prop(channel, "wireframe_dis", text="Size")
    layout.prop(channel, "wireframe_use_pix")

def _draw_pbr_conv(layout, channel):
    col = layout.column(align=True)
    draw_header(col, "Conversion Logic", 'NODETREE')
    col.prop(channel, "pbr_conv_threshold", text="F0 Threshold")
    col.label(text="Spec < F0 is Dielectric", icon='INFO')
    col.label(text="Spec > F0 becomes Metallic", icon='INFO')

CHANNEL_UI_MAP = {
    'normal': _draw_normal,
    'diff': _draw_light_path,
    'gloss': _draw_light_path,
    'tranb': _draw_light_path,
    'combine': _draw_combine,
    'ao': _draw_ao_bevel,
    'bevel': _draw_ao_bevel,
    'bevnor': _draw_ao_bevel,
    'curvature': _draw_curvature,
    'wireframe': _draw_wireframe,
}

def draw_active_channel_properties(layout, channel, setting):
    if not channel: return
    
    box = layout.box()
    row = box.row()
    row.label(text=f"{channel.name} Settings", icon='PREFERENCES')
    
    col = box.column(align=True)
    row = col.split(factor=0.3)
    row.label(text="Naming:")
    sub = row.row(align=True)
    sub.prop(channel, "prefix", text="Pre")
    sub.prop(channel, "suffix", text="Suf")
    
    box.separator()
    col = box.column()
    col.prop(channel, "override_defaults", toggle=True)
    
    if channel.override_defaults:
        sub = col.box()
        sub.label(text="Advanced Color Override", icon='COLOR')
        sub.prop(channel, "custom_cs", text="Space")
        sub.prop(channel, "custom_mode", text="Export Mode")
        
    box.separator()
    
    if channel.id == 'rough':
        box.prop(channel, "rough_inv", icon='ARROW_LEFTRIGHT')
    elif channel.id.startswith('pbr_conv_'):
        _draw_pbr_conv(box, channel)
    else:
        draw_func = CHANNEL_UI_MAP.get(channel.id)
        if draw_func:
            draw_func(box, channel)

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
    
    box = layout.box()
    draw_header(box, "Export Settings", 'OUTPUT')
    col = box.column(align=True)
    
    col.prop(bj.bake_result_settings, "save_path", text="")
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

class UI_UL_ObjectList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if item.bakeobject:
            layout.label(text=item.bakeobject.name, icon='OBJECT_DATA')
        else:
            layout.label(text="Missing", icon='ERROR')

class BAKETOOL_UL_ChannelList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        info = CHANNEL_BAKE_INFO.get(item.id, {})
        cat = info.get('cat', 'DATA')
        icon_map = {CAT_MESH: 'MESH_DATA', CAT_LIGHT: 'LIGHT_SUN', CAT_DATA: 'MATERIAL'}
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
        row.prop(item, "image", text="", emboss=False, icon='IMAGE_DATA')
        row.label(text=item.channel_type)

class BAKE_PT_NodePanel(bpy.types.Panel):
    bl_label = "Node Bake"
    bl_idname = "BAKE_PT_NodePanel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Bake'
    
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
        
        b.prop(nbs, "save_outside", text="To Disk", icon='DISK_DRIVE')
        if nbs.save_outside:
            draw_file_path(b, nbs, "save_path", 2)
            draw_image_format_options(b, nbs.image_settings, "")
            
        l.operator("bake.selected_node_bake", text="Bake Node", icon='RENDER_STILL')

class BAKE_PT_BakePanel(bpy.types.Panel):
    bl_label = "Baking Tool"
    bl_idname = "BAKE_PT_BakePanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Bake'
    
    def draw(self, context):
        l = self.layout
        draw_crash_report(l)
        
        scene = context.scene
        bj = scene.BakeJobs
        
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
            if l.operator("wm.context_set_string", text="Clear Errors", icon='TRASH'):
                pass

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
        
        # --- Smart UV UI ---
        sb = b.box()
        draw_header(sb, "Smart UV", 'GROUP_UVS')
        sb.prop(s, "use_auto_uv", toggle=True)
        if s.use_auto_uv:
            col = sb.column(align=True)
            col.prop(s, "auto_uv_name", text="Name")
            
            row = col.row(align=True)
            row.prop(s, "auto_uv_angle")
            row.prop(s, "auto_uv_margin")
            
            col.prop(s, "auto_uv_keep_active")

        # --- UDIM UI ---
        if s.bake_mode == 'UDIM':
            sb = b.box()
            draw_header(sb, "UDIM Tiling", 'FILE_IMAGE')
            
            col = sb.column(align=True)
            col.prop(s, "udim_mode", text="Method")
            
            if s.udim_mode == 'MANUAL':
                col.prop(s, "udim_start_tile", text="Start")
                r = col.row(align=True)
                r.prop(s, "udim_grid_u", text="Grid U")
                r.prop(s, "udim_grid_v", text="Grid V")
            elif s.udim_mode == 'SEQUENCE':
                col.prop(s, "udim_start_tile", text="Start")
                col.label(text="1 Tile per Object", icon='SORTALPHA')
            elif s.udim_mode == 'AUTO':
                col.label(text="Detects from Active UV", icon='INFO')

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
        draw_header(b, "Naming", 'SORTALPHA')
        r = b.row(align=True)
        r.prop(s, "name_setting", text="")
        
        if s.name_setting=='CUSTOM':
            r.prop(s, "custom_name", text="")
            
        b.separator()
        b.prop(s, "save_out", icon='DISK_DRIVE', toggle=True)
        
        if s.save_out:
            sb = b.box()
            draw_file_path(sb, s, "save_path", 0)
            draw_image_format_options(sb, s)
            
            sb.separator()
            row = sb.row(align=True)
            row.prop(s, "bake_motion", text="Bake Image Sequence", icon='RENDER_ANIMATION')
            
            if s.bake_motion:
                if s.use_mesh_map:
                    sb.label(text="Mesh Maps + Animation might be redundant", icon='INFO')
                if s.bake_texture_apply:
                    sb.label(text="Auto-Apply is disabled for sequences", icon='INFO')
                
                col = sb.column(align=True)
                r = col.row(align=True)
                r.prop(s, "bake_motion_use_custom", text="Custom Frames", toggle=True)
                
                if s.bake_motion_use_custom:
                    r = col.row(align=True)
                    r.prop(s, "bake_motion_start", text="Start")
                    r.prop(s, "bake_motion_last", text="Duration")
                else:
                    col.label(text=f"Sync Scene: {context.scene.frame_start}-{context.scene.frame_end}", icon='TIME')
                
                row = col.row(align=True)
                row.prop(s, "bake_motion_separator", text="Sep")
                row.prop(s, "bake_motion_startindex", text="Start#")
                row.prop(s, "bake_motion_digit", text="Pad")

            sb.separator()
            sb.prop(s, "export_model", text="Export Mesh", icon='EXPORT', toggle=True)
            
            if s.export_model:
                r = sb.row(align=True)
                r.prop(s, "export_format", expand=True)

    def draw_others(self, context, l, bj, s):
        l.prop(bj, "open_other", text="Custom Maps", icon="DISCLOSURE_TRI_DOWN" if bj.open_other else "DISCLOSURE_TRI_RIGHT", emboss=False)
        if not bj.open_other: return
        
        b = l.box()
        j = bj.jobs[bj.job_index]
        b.prop(s, "use_custom_map", text="Enable Custom Map Logic", toggle=True)
        
        if s.use_custom_map:
            r = b.row()
            r.template_list("LIST_UL_CustomBakeChannelList", "", j, "Custombakechannels", j, "Custombakechannels_index", rows=4)
            draw_template_list_ops(r, "job_custom_channel")
            
            if j.Custombakechannels and 0 <= j.Custombakechannels_index < len(j.Custombakechannels):
                c = j.Custombakechannels[j.Custombakechannels_index]
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