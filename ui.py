import bpy
from .constants import FORMAT_SETTINGS

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
    m_p = f"{prefix}color_mode"
    
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
        row.prop(setting, d_p, text="")
    if "modes" in fs and len(fs["modes"]) > 0:
        row.prop(setting, m_p, text="")

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
    
    if setting.colorspace_setting:
        col.prop(channel, "custom_cs", text="Color Space", icon='COLOR')
        
    box.separator()
    
    if channel.id == 'rough':
        box.prop(channel, "rough_inv", icon='ARROW_LEFTRIGHT')
        
    elif channel.id == 'normal':
        col = box.column(align=True)
        draw_header(col, "Normal Map", 'NORMALS_FACE')
        col.prop(channel, "normal_type", text="Std")
        
        if channel.normal_type == 'CUSTOM':
            r = col.row(align=True)
            r.prop(channel, "normal_X")
            r.prop(channel, "normal_Y")
            r.prop(channel, "normal_Z")
        col.prop(channel, "normal_obj", text="Object Space")
        
    elif channel.id in {'diff', 'gloss', 'tranb'}:
        col = box.column(align=True)
        draw_header(col, "Light Paths", 'LIGHT_SUN')
        r = col.row(align=True)
        r.prop(channel, f"{channel.id}_dir", text="Dir", toggle=True)
        r.prop(channel, f"{channel.id}_ind", text="Ind", toggle=True)
        r.prop(channel, f"{channel.id}_col", text="Col", toggle=True)
        
    elif channel.id == 'combine':
        col = box.column(align=True)
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
        
    elif channel.id in ('ao', 'bevel', 'bevnor'):
        col = box.column(align=True)
        col.prop(channel, f"{channel.id}_sample", text="Samples")
        col.prop(channel, f"{channel.id}_rad" if channel.id!='ao' else "ao_dis", text="Rad/Dist")
        
    elif channel.id == 'wireframe':
        box.prop(channel, "wireframe_dis", text="Size")
        box.prop(channel, "wireframe_use_pix")

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
    col.prop(bj, "bake_result_save_path", text="")
    draw_image_format_options(col, bj, "bake_result_")

class UI_UL_ObjectList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if item.bakeobject:
            layout.label(text=item.bakeobject.name, icon='OBJECT_DATA')
        else:
            layout.label(text="Missing", icon='ERROR')

class BAKETOOL_UL_ChannelList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "enabled", text="")
        row.label(text=item.name, icon='TEXTURE' if item.enabled else 'SHADING_SOLID')

class LIST_UL_JobsList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.label(text=item.name or f"Job {index}", icon='PREFERENCES')

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
    bl_category = 'Baking'
    
    @classmethod
    def poll(cls, context): 
        return context.space_data.tree_type == 'ShaderNodeTree'
        
    def draw(self, context):
        l = self.layout
        bj = context.scene.BakeJobs
        b = l.box()
        draw_header(b, "Res & Save", 'PREFERENCES')
        
        r = b.row(align=True)
        r.prop(bj, "node_bake_res_x", text="X")
        r.prop(bj, "node_bake_res_y", text="Y")
        
        b.prop(bj, "node_bake_save_outside", text="To Disk", icon='DISK_DRIVE')
        if bj.node_bake_save_outside:
            draw_file_path(b, bj, "node_bake_save_path", 2)
            draw_image_format_options(b, bj, "node_bake_")
            
        l.operator("bake.selected_node_bake", text="Bake Node", icon='RENDER_STILL')

class BAKE_PT_BakePanel(bpy.types.Panel):
    bl_label = "Baking Tool"
    bl_idname = "BAKE_PT_BakePanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Baking'
    
    def draw(self, context):
        l = self.layout
        bj = context.scene.BakeJobs
        b = l.box()
        r = b.row()
        
        r.template_list("LIST_UL_JobsList", "", bj, "jobs", bj, "job_index", rows=3)
        draw_template_list_ops(r, "jobs_channel")
        
        if not bj.jobs:
            b.label(text="Add job to start", icon='INFO')
            return
            
        j = bj.jobs[bj.job_index]
        s = j.setting
        b.prop(j, "name", text="")
        
        self.draw_inputs(l, bj, s)
        self.draw_channels(l, bj, s)
        self.draw_saves(l, bj, s)
        self.draw_others(l, bj, s)
        
        l.separator()
        r = l.row()
        r.scale_y = 2.0
        r.operator("bake.bake_operator", text="START BAKE", icon='RENDER_STILL')

    def draw_inputs(self, l, bj, s):
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
        r = b.row()
        r.template_list("UI_UL_ObjectList", "", s, "bake_objects", s, "active_object_index", rows=3)
        
        c = r.column(align=True)
        c.operator("bake.record_objects", icon='ADD').objecttype=0
        c.operator("bake.generic_channel_op", icon='TRASH').target="bake_objects"
        
        # [新增] ID 贴图高级设置
        if any(c.id.startswith('ID_') for c in s.channels if c.enabled):
            sb = b.box(); draw_header(sb, "ID Map Optimization", 'COLOR')
            
            sb.prop(s, "id_manual_start_color")
            if s.id_manual_start_color:
                sb.prop(s, "id_start_color", text="")
                
            sb.prop(s, "id_iterations", slider=True)

        if s.bake_mode == 'SELECT_ACTIVE':
            sb = b.box()
            c = sb.column(align=True)
            r = c.row(align=True)
            r.prop(s, "active_object")
            r.operator("bake.record_objects", icon='EYEDROPPER').objecttype=1

    def draw_channels(self, l, bj, s):
        l.prop(bj, "open_channels", text="Channels", icon="DISCLOSURE_TRI_DOWN" if bj.open_channels else "DISCLOSURE_TRI_RIGHT", emboss=False)
        if not bj.open_channels: return
        
        b = l.box()
        r = b.row()
        r.template_list("BAKETOOL_UL_ChannelList", "", s, "channels", s, "active_channel_index", rows=5)
        r.column().operator("bake.reset_channels", icon='FILE_REFRESH', text="")
        
        if s.channels and 0 <= s.active_channel_index < len(s.channels):
            draw_active_channel_properties(b, s.channels[s.active_channel_index], s)
            
        b.prop(s, "use_special_map", text="Mesh Maps", icon='MOD_MASK', toggle=True)

    def draw_saves(self, l, bj, s):
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
            
            # [改进] Export 依赖于 Save Out，移入内部
            sb.separator()
            sb.prop(s, "export_model", text="Export Mesh", icon='EXPORT', toggle=True)
            
            if s.export_model:
                r = sb.row(align=True)
                r.prop(s, "export_format", expand=True)

    def draw_others(self, l, bj, s):
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
                
                # Loop through appropriate channels including Alpha
                channels_to_draw = ['bw'] if c.bw else ['r','g','b','a']
                
                for char in channels_to_draw:
                    # Get the sub-property settings object
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