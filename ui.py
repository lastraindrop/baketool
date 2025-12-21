import bpy

from bpy import (
    props,
    context,
    types
)

# --- HELPER FUNCTIONS ---

def draw_header(layout, text, icon='NONE'):
    """绘制带有背景的小标题，用于区分板块"""
    row = layout.row(align=True)
    row.alignment = 'LEFT'
    row.label(text=text, icon=icon)

def draw_file_path(layout, setting, path_prop, location):
    row = layout.row(align=True)
    row.prop(setting, path_prop, text="", icon='FILE_FOLDER')
    # 使用图标按钮来切换保存位置模式
    op = row.operator("bake.set_save_local", text='', icon='HOME')
    op.save_location = location

def draw_template_list_ops(layout, basic_name):
    """绘制列表右侧的操作按钮"""
    col = layout.column(align=True)
    
    icons = {
        'ADD': 'ADD',
        'DELETE': 'REMOVE',
        'UP': 'TRIA_UP',
        'DOWN': 'TRIA_DOWN',
        'CLEAR': 'TRASH'
    }
    
    for item in ['ADD', 'DELETE', 'UP', 'DOWN', 'CLEAR']:
        ops = col.operator("bake.generic_channel_op", text='', icon=icons[item])
        ops.operation = item
        ops.target = basic_name

def draw_image_format_options(layout, setting, prefix=""):
    """根据所选格式动态绘制图像格式选项"""
    format_prop = f"{prefix}save_format"
    quality_prop = f"{prefix}quality"
    exr_prop = f"{prefix}exr_code"
    tiff_prop = f"{prefix}tiff_codec"
    depth_prop = f"{prefix}color_depth"
    mode_prop = f"{prefix}color_mode"
    space_prop = f"{prefix}color_space"
    
    fmt = getattr(setting, format_prop)
    
    # 第一行：格式和主要参数
    row = layout.row(align=True)
    row.prop(setting, format_prop, text="")
    
    if fmt in {'JPEG', 'WEBP', 'JPEG2000'}:
        row.prop(setting, quality_prop, text="Quality", slider=True)
    elif fmt in {'OPEN_EXR', 'OPEN_EXR_MULTILAYER'}:
        row.prop(setting, exr_prop, text="")
    elif fmt == 'TIFF':
        row.prop(setting, tiff_prop, text="")
    
    # 第二行：色深、颜色模式
    row = layout.row(align=True)
    
    # 色深支持验证
    if fmt in {'PNG', 'TIFF', 'DPX', 'JPEG2000'}:
        row.prop(setting, depth_prop, text="")
    elif fmt in {'OPEN_EXR', 'OPEN_EXR_MULTILAYER'}:
        # EXR 仅支持 16/32
        row.prop(setting, depth_prop, text="")
    
    # 颜色模式支持
    if fmt not in {'HDR'}: # HDR 通常固定
        row.prop(setting, mode_prop, text="")
        
    # 第三行：色彩空间
    if hasattr(setting, space_prop):
        row = layout.row(align=True)
        sub = row.row(align=True)
        # HDR/EXR 通常使用 Linear
        sub.enabled = fmt not in {'HDR', 'OPEN_EXR', 'OPEN_EXR_MULTILAYER'}
        sub.prop(setting, space_prop, text="Color Space")

def draw_active_channel_properties(layout, channel):
    """绘制当前选中通道的详细属性"""
    if not channel:
        layout.label(text="No channel selected.", icon='INFO')
        return

    box = layout.box()
    row = box.row()
    row.label(text=f"{channel.name} Settings", icon='PREFERENCES')
    
    # 通用属性
    col = box.column(align=True)
    split = col.split(factor=0.3)
    split.label(text="Naming:")
    row = split.row(align=True)
    row.prop(channel, "prefix", text="Prefix")
    row.prop(channel, "suffix", text="Suffix")
    
    bake_jobs = bpy.context.scene.BakeJobs
    if bake_jobs.jobs and bake_jobs.job_index >= 0:
        current_job_setting = bake_jobs.jobs[bake_jobs.job_index].setting
        if current_job_setting.colorspace_setting:
            col.separator()
            col.prop(channel, "custom_cs", text="Color Space", icon='COLOR')

    # 特定属性
    box.separator()
    if channel.id == 'rough':
        box.prop(channel, "rough_inv", icon='ARROW_LEFTRIGHT')
    elif channel.id == 'normal':
        col = box.column(align=True)
        draw_header(col, "Normal Map", 'NORMALS_FACE')
        col.prop(channel, "normal_type", text="Standard")
        if channel.normal_type == 'CUSTOM':
            row = col.row(align=True)
            row.prop(channel, "normal_X", text="X")
            row.prop(channel, "normal_Y", text="Y")
            row.prop(channel, "normal_Z", text="Z")
        col.prop(channel, "normal_obj", text="Object Space")
    elif channel.id in {'diff', 'gloss', 'tranb'}:
        col = box.column(align=True)
        draw_header(col, "Light Paths", 'LIGHT_SUN')
        row = col.row(align=True)
        row.prop(channel, f"{channel.id}_dir", text="Direct", toggle=True)
        row.prop(channel, f"{channel.id}_ind", text="Indirect", toggle=True)
        row.prop(channel, f"{channel.id}_col", text="Color", toggle=True)
    elif channel.id == 'combine':
        col = box.column(align=True)
        draw_header(col, "Passes", 'RENDERLAYERS')
        row = col.row(align=True)
        row.prop(channel, "com_dir", text="Direct", toggle=True)
        row.prop(channel, "com_ind", text="Indirect", toggle=True)
        col.separator()
        grid = col.grid_flow(columns=2, align=True)
        grid.prop(channel, "com_diff", text="Diffuse")
        grid.prop(channel, "com_gloss", text="Glossy")
        grid.prop(channel, "com_tran", text="Transmission")
        grid.prop(channel, "com_emi", text="Emission")
    elif channel.id == 'bevel':
        col = box.column(align=True)
        col.prop(channel, "bevel_sample", text="Samples")
        col.prop(channel, "bevel_rad", text="Radius")
    elif channel.id == 'ao':
        col = box.column(align=True)
        col.prop(channel, "ao_sample", text="Samples")
        col.prop(channel, "ao_dis", text="Distance")
        row = col.row(align=True)
        row.prop(channel, "ao_inside", toggle=True)
        row.prop(channel, "ao_local", toggle=True)
    elif channel.id == 'wireframe':
        col = box.column(align=True)
        col.prop(channel, "wireframe_dis", text="Thickness")
        col.prop(channel, "wireframe_use_pix", text="Pixel Size")
    elif channel.id == 'bevnor':
        col = box.column(align=True)
        col.prop(channel, "bevnor_sample", text="Samples")
        col.prop(channel, "bevnor_rad", text="Radius")
    elif channel.id == 'position':
        box.prop(channel, "position_invg", text="Invert Green", toggle=True)
    elif channel.id == 'slope':
        col = box.column(align=True)
        col.prop(channel, "slope_directions", text="Axis")
        col.prop(channel, "slope_invert", text="Invert", toggle=True)
    elif channel.id == 'thickness':
        col = box.column(align=True)
        col.prop(channel, "thickness_distance", text="Distance")
        col.prop(channel, "thickness_contrast", text="Contrast")
    elif channel.id in ('ID_mat', 'ID_ele', 'ID_UVI', 'ID_seam'):
        box.prop(channel, "ID_num", text="Color Count")

def draw_results(scene, layout, bake_jobs):
    # 结果列表
    layout.label(text="Baked Results", icon='IMAGE_DATA')
    
    row = layout.row()
    row.template_list(
        "BAKETOOL_UL_BakedImageResults", "",
        scene, "baked_image_results",
        scene, "baked_image_results_index",
        rows=5
    )
    
    # 侧边操作栏
    col = row.column(align=True)
    col.operator("baketool.delete_result", text="", icon="TRASH")
    col.operator("baketool.delete_all_results", text="", icon="X")
    col.separator()
    col.operator("baketool.export_result", text="", icon="EXPORT")
    col.operator("baketool.export_all_results", text="", icon="FILE_FOLDER")

    # 导出设置
    box = layout.box()
    draw_header(box, "Export Configuration", 'OUTPUT')
    
    col = box.column(align=True)
    col.prop(bake_jobs, "bake_result_save_path", text="")
    
    draw_image_format_options(col, bake_jobs, prefix="bake_result_")
    
    row = col.row(align=True)
    row.prop(bake_jobs, "bake_result_use_denoise", text="Denoise", toggle=True, icon='BRUSH_BLUR')
    if bake_jobs.bake_result_use_denoise:
        row.prop(bake_jobs, "bake_result_denoise_method", text="")

    # 详细信息
    if scene.baked_image_results_index >= 0 and scene.baked_image_results:
        result = scene.baked_image_results[scene.baked_image_results_index]
        box = layout.box()
        draw_header(box, "Details", 'INFO')
        col = box.column(align=True)
        col.label(text=f"Image: {result.image.name if result.image else 'None'}", icon='IMAGE_DATA')
        col.label(text=f"Object: {result.object_name}", icon='OBJECT_DATA')
        col.label(text=f"Type: {result.channel_type}", icon='SHADING_TEXTURE')

# --- UI LISTS ---

class UI_UL_ObjectList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        obj = item.bakeobject
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if obj:
                layout.label(text=obj.name, icon='OBJECT_DATA')
            else:
                layout.label(text="Missing Object", icon='ERROR')
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='OBJECT_DATA')

class BAKETOOL_UL_ChannelList(bpy.types.UIList):
    """UIList for dynamic bake channels. Simplified icons to avoid errors."""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # 使用统一的安全图标，避免 'BRUSH_ROUGHEN' 等图标在不同 Blender 版本中缺失导致的崩溃
        # Use safe icons: TEXTURE when enabled, SHADING_SOLID when disabled
        
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "enabled", text="")
            row.label(text=item.name, icon='TEXTURE' if item.enabled else 'SHADING_SOLID')
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.prop(item, "enabled", text="", icon='TEXTURE' if item.enabled else 'SHADING_SOLID')

class LIST_UL_JobsList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        custom_icon = 'PREFERENCES'
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name if item.name else f"Job {index}", icon=custom_icon)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon=custom_icon)

class LIST_UL_CustomBakeChannelList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        custom_icon = 'NODE_COMPOSITING'
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name if item.name else f"Channel {index}", icon=custom_icon)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon=custom_icon)

class BAKETOOL_UL_BakedImageResults(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "image", text="", emboss=False, icon='IMAGE_DATA')
            row.label(text=item.channel_type)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=item.image.name if item.image else "No Image")

# --- PANELS ---

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
        layout = self.layout
        setting = context.scene.BakeJobs
        
        layout.label(text="Bake selected nodes to image", icon='NODE_SEL')
        layout.separator()
        
        # 基础设置
        box = layout.box()
        draw_header(box, "Resolution & Quality", 'PREFERENCES')
        
        row = box.row(align=True)
        row.prop(setting, "node_bake_res_x", text="X")
        row.prop(setting, "node_bake_res_y", text="Y")
        
        row = box.row(align=True)
        row.prop(setting, "node_bake_sample", text="Samples")
        row.prop(setting, "node_bake_margin", text="Margin")
        
        row = box.row(align=True)
        row.prop(setting, "node_bake_float32", text="32-Bit Float", toggle=True)
        row.prop(setting, "node_bake_delete_node", text="Del Node", toggle=True)
        
        # 端口选择
        box = layout.box()
        draw_header(box, "Output Socket", 'NODE_OUTPUT_MATERIAL')
        row = box.row(align=True)
        row.prop(setting, "node_bake_auto_find_socket", text="Auto Detect", toggle=True)
        if not setting.node_bake_auto_find_socket:
            row.prop(setting, "node_bake_socket_index", text="Index")

        # 保存设置
        box = layout.box()
        draw_header(box, "Save Options", 'FILE_TICK')
        box.prop(setting, "node_bake_save_outside", text="Save to Disk", icon='DISK_DRIVE')
        
        if setting.node_bake_save_outside:
            col = box.column(align=True)
            draw_file_path(col, setting, "node_bake_save_path", 2)
            draw_image_format_options(col, setting, prefix="node_bake_")
            col.prop(setting, "node_bake_reload", text="Reload Image", toggle=True, icon='FILE_REFRESH')
        
        layout.separator()
        row = layout.row()
        row.scale_y = 1.5
        row.operator("bake.selected_node_bake", text="Bake Node", icon='RENDER_STILL')
       
class BAKE_PT_BakePanel(bpy.types.Panel):
    bl_label = "Baking Tool"
    bl_idname = "BAKE_PT_BakePanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Baking'

    def draw_rgba_channel(self, layout, item, channel, setting, is_bw=False):
        """绘制自定义通道的RGBA/BW设置"""
        prefix = channel + "_"
        
        row = layout.row(align=True)
        # 标签和启用开关
        label = channel.upper() if not is_bw else "BW"
        row.prop(item, prefix + "usemap", text=label, toggle=True)
        
        if getattr(item, prefix + "usemap"):
            # 如果启用了贴图，显示贴图选择和选项
            sub = row.row(align=True)
            if setting.bake_type == 'BSDF':
                if bpy.app.version < (4, 0, 0):
                    sub.prop(item, prefix + "map_BSDF3", text="")
                else:
                    sub.prop(item, prefix + "map_BSDF4", text="")
            else:
                sub.prop(item, prefix + "map_basic", text="")
            
            sub.prop(item, prefix + "invert", text="", icon='ARROW_LEFTRIGHT')
            sub.prop(item, prefix + "sepcol", text="", icon='COLOR')
            
            if getattr(item, prefix + "sepcol"):
                sub.prop(item, prefix + "colchan", text="")
        else:
            # 如果未启用贴图，显示数值滑块
            if not is_bw:
                row.prop(item, channel, text="")

    def draw_inputs(self, layout, jobs, setting):
        # 标题栏带折叠图标
        icon = "DISCLOSURE_TRI_DOWN" if jobs.open_inputs else "DISCLOSURE_TRI_RIGHT"
        layout.prop(jobs, "open_inputs", text="Input Settings", icon=icon, emboss=False)
        
        if not jobs.open_inputs: return
        
        # 使用 Box 包裹内容
        box = layout.box()
        
        # 1. 基础参数 (分辨率/采样)
        col = box.column(align=True)
        draw_header(col, "Dimensions & Quality", 'TEXTURE')
        
        row = col.row(align=True)
        row.enabled = setting.special_bake_method != 'VERTEXCOLOR'
        row.prop(setting, "res_x", text="X")
        row.prop(setting, "res_y", text="Y")
        
        row = col.row(align=True)
        row.prop(setting, "sample", text="Samples")
        row.prop(setting, "margin", text="Margin")
        
        col.separator()
        
        # 2. 烘焙方式
        draw_header(col, "Method", 'SHADING_RENDERED')
        row = col.row(align=True)
        row.prop(setting, "device", expand=True)
        
        col.prop(setting, "bake_type", text="Type")
        
        if setting.bake_type in {"BASIC", "BSDF"}:
            col.prop(setting, "special_bake_method", text="Special")
            
        col.prop(setting, "bake_mode", text="Mode")
        
        col.separator()

        # 3. 物体列表
        draw_header(col, "Target Objects", 'OUTLINER_OB_MESH')
        row = col.row()
        row.template_list("UI_UL_list", "bake_objects_list", setting, "bake_objects", setting, "active_object_index", rows=3)
        
        # 物体列表操作
        sub = row.column(align=True)
        sub.operator("bake.record_objects", text="", icon='ADD').objecttype = 0
        sub.operator("bake.record_objects", text="", icon='TRASH').objecttype = 0 # 需要在ops中实现清除逻辑，这里暂时复用
        
        # 4. 模式特定设置 (Selected to Active)
        if setting.bake_mode == "SELECT_ACTIVE":
            subbox = box.box()
            draw_header(subbox, "Selected to Active", 'PIVOT_ACTIVE')
            
            col = subbox.column(align=True)
            
            row = col.row(align=True)
            row.prop(setting, "active_object", text="Active")
            row.operator("bake.record_objects", text="", icon='EYEDROPPER').objecttype = 1
            
            row = col.row(align=True)
            row.prop(setting, "cage_object", text="Cage")
            row.operator("bake.record_objects", text="", icon='EYEDROPPER').objecttype = 2
            
            row = col.row(align=True)
            row.prop(setting, "extrusion", text="Extrusion")
            row.prop(setting, "ray_distance", text="Ray Dist")

        # 5. Atlas 设置
        if setting.special_bake_method == 'AUTOATLAS':
            subbox = box.box()
            draw_header(subbox, "Atlas Settings", 'UV_DATA')
            col = subbox.column(align=True)
            col.prop(setting, "atlas_pack_method", text="Pack")
            col.prop(setting, "atlas_margin", text="Margin")

        # 6. Multires 设置
        if setting.bake_type == 'MULTIRES':
            subbox = box.box()
            draw_header(subbox, "Multires", 'MOD_MULTIRES')
            subbox.prop(setting, "multires_divide", text="Subdivision Level")
        
        # 7. 动画设置
        box.separator()
        row = box.row(align=True)
        row.prop(setting, "bake_motion", text="Animation Bake", icon='TIME', toggle=True)
        
        if setting.bake_motion:
            subbox = box.box()
            col = subbox.column(align=True)
            col.prop(setting, "bake_motion_use_custom", text="Custom Range", toggle=True)
            
            if setting.bake_motion_use_custom:
                row = col.row(align=True)
                row.prop(setting, "bake_motion_start", text="Start")
                row.prop(setting, "bake_motion_last", text="Count")
            
            row = col.row(align=True)
            row.prop(setting, "bake_motion_startindex", text="Start Index")
            row.prop(setting, "bake_motion_digit", text="Digits")

        # 8. 杂项设置 (颜色空间等)
        col = box.column(align=True)
        col.separator()
        row = col.row(align=True)
        row.prop(setting, "float32", text="Float 32", toggle=True)
        row.prop(setting, "use_alpha", text="Alpha", toggle=True)
        
        row = col.row(align=True)
        row.prop(setting, "colorspace_setting", text="Custom ColorSpace", toggle=True)
        row.prop(setting, "clearimage", text="Clear Image", toggle=True)
        
        if not setting.clearimage:
            col.prop(setting, "colorbase", text="Base Color")


    def draw_channels(self, layout, jobs, setting):
        icon = "DISCLOSURE_TRI_DOWN" if jobs.open_channels else "DISCLOSURE_TRI_RIGHT"
        layout.prop(jobs, "open_channels", text="Channel Settings", icon=icon, emboss=False)
        
        if not jobs.open_channels: return
        
        box = layout.box()
        
        # 通道列表和操作
        row = box.row()
        row.template_list("BAKETOOL_UL_ChannelList", "channels", setting, "channels", setting, "active_channel_index", rows=5)
        
        col = row.column(align=True)
        col.operator("bake.reset_channels", text="", icon='FILE_REFRESH')
        
        # 选中通道的属性
        if setting.channels and setting.active_channel_index >= 0 and setting.active_channel_index < len(setting.channels):
            active_channel = setting.channels[setting.active_channel_index]
            draw_active_channel_properties(box, active_channel)

        box.separator()
        box.prop(setting, "use_special_map", text="Enable Special Maps", icon='MOD_MASK', toggle=True)

    def draw_saves(self, layout, jobs, setting):
        icon = "DISCLOSURE_TRI_DOWN" if jobs.open_saves else "DISCLOSURE_TRI_RIGHT"
        layout.prop(jobs, "open_saves", text="Save Settings", icon=icon, emboss=False)
        
        if not jobs.open_saves: return
        
        box = layout.box()
        
        # 命名规则
        draw_header(box, "Naming Convention", 'SORTALPHA')
        row = box.row(align=True)
        row.prop(setting, "name_setting", text="")
        if setting.name_setting == "CUSTOM":
            row.prop(setting, "custom_name", text="")
            
        # 外部保存
        if setting.special_bake_method != 'VERTEXCOLOR':
            box.separator()
            box.prop(setting, "save_out", text="Save to Disk", icon='DISK_DRIVE', toggle=True)
            
            if setting.save_out or setting.bake_motion:
                subbox = box.box()
                col = subbox.column(align=True)
                
                draw_file_path(col, setting, "save_path", 0)
                col.separator()
                draw_image_format_options(col, setting)
                
                col.separator()
                col.prop(setting, "create_new_folder", text="Create Subfolder", toggle=True)
                if setting.create_new_folder:
                    row = col.row(align=True)
                    row.prop(setting, "new_folder_name_setting", text="")
                    if setting.new_folder_name_setting == 'CUSTOM':
                        row.prop(setting, "folder_name", text="")
    
    def draw_others(self, layout, jobs, setting):
        job = jobs.jobs[jobs.job_index]
        icon = "DISCLOSURE_TRI_DOWN" if jobs.open_other else "DISCLOSURE_TRI_RIGHT"
        layout.prop(jobs, "open_other", text="Advanced Settings", icon=icon, emboss=False)
        
        if not jobs.open_other: return
        
        box = layout.box()
        col = box.column(align=True)
        
        # 行为设置
        draw_header(col, "Post-Bake Actions", 'CHECKMARK')
        col.prop(setting, "save_and_quit", text="Save & Quit Blender", toggle=True)
        
        row = col.row(align=True)
        row.enabled = setting.bake_type == 'BSDF' and not setting.bake_motion and setting.bake_mode != 'SPLIT_MATERIAL'
        row.prop(setting, "bake_texture_apply", text="Apply to Material", toggle=True)
        
        # 自定义通道 (Custom Maps)
        col.separator()
        row = col.row(align=True)
        row.enabled = setting.special_bake_method != 'VERTEXCOLOR' and not setting.bake_motion and setting.bake_type != 'MULTIRES'
        row.prop(setting, "use_custom_map", text="Custom Maps", icon='NODE_COMPOSITING', toggle=True)
        
        if setting.use_custom_map and row.enabled:
            subbox = box.box()
            col = subbox.column(align=True)
            
            # 自定义路径
            draw_file_path(col, setting, "custom_file_path", 1)
            
            col.prop(setting, "custom_new_folder", text="Subfolder", toggle=True)
            if setting.custom_new_folder:
                row = col.row(align=True)
                row.prop(setting, "custom_folder_name_setting", text="")
                if setting.custom_folder_name_setting == 'CUSTOM':
                    row.prop(setting, "custom_folder_name", text="")
            
            col.separator()
            col.label(text="Channels", icon='TEXTURE')
            
            # 自定义通道列表
            row = col.row()
            row.template_list("LIST_UL_CustomBakeChannelList", "bake_channel_list", job, "Custombakechannels", job, "Custombakechannels_index", rows=4)
            draw_template_list_ops(row, "job_custom_channel")
            
            # 自定义通道详情
            if len(job.Custombakechannels) > 0 and job.Custombakechannels_index < len(job.Custombakechannels):
                item = job.Custombakechannels[job.Custombakechannels_index]
                
                detail_box = subbox.box()
                draw_header(detail_box, "Channel Details", 'EDITMODE_HLT')
                
                dcol = detail_box.column(align=True)
                dcol.prop(item, "name", text="Name", icon='SORTALPHA')
                dcol.separator()
                draw_image_format_options(dcol, item)
                
                dcol.separator()
                dcol.prop(item, "bw", text="Black & White Mode", toggle=True)
                
                dcol.separator()
                if item.bw:
                    self.draw_rgba_channel(dcol, item, 'bw', setting, True)
                else:
                    for channel_char in ['r', 'g', 'b', 'a']:
                        self.draw_rgba_channel(dcol, item, channel_char, setting)
                
                dcol.separator()
                row = dcol.row(align=True)
                row.prop(item, "prefix", text="Prefix")
                row.prop(item, "suffix", text="Suffix")
    
    def draw(self, context):
        layout = self.layout
        jobs = context.scene.BakeJobs

        # 顶部：Job 管理
        box = layout.box()
        row = box.row()
        row.template_list("LIST_UL_JobsList", "jobs_list", jobs, "jobs", jobs, "job_index", rows=3)
        draw_template_list_ops(row, "jobs_channel")
        
        if not jobs.jobs:
            box.label(text="Add a job to start", icon='INFO')
            return
        
        job = jobs.jobs[jobs.job_index]
        setting = job.setting
        
        # Job 名称
        row = box.row(align=True)
        row.prop(job, "name", text="", icon='PREFERENCES')

        layout.separator()

        # 各个板块
        self.draw_inputs(layout, jobs, setting)
        self.draw_channels(layout, jobs, setting)
        self.draw_saves(layout, jobs, setting)
        self.draw_others(layout, jobs, setting)

        # 底部：开始按钮
        layout.separator()
        row = layout.row()
        row.scale_y = 2.0
        # 使用大图标和醒目的文字
        row.operator("bake.bake_operator", text="START BAKE", icon='RENDER_STILL')

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
    bl_idname = "BAKETOOL_PT_image_editor_results"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Baking"

    def draw(self, context):
        scene = context.scene
        draw_results(scene, self.layout, scene.BakeJobs)
        if scene.baked_image_results_index >= 0 and scene.baked_image_results:
            result = scene.baked_image_results[scene.baked_image_results_index]
            if result.image and context.space_data.image != result.image:
                context.space_data.image = result.image
