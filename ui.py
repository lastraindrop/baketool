import bpy

from bpy import (
props,
context,
types
)

def draw_file_path(layout, setting, path_prop, location):
    row = layout.row()
    row.prop(setting, path_prop, icon='FILE_FOLDER')
    row.operator("bake.set_save_local", text='', icon='RADIOBUT_ON').save_location = location

def draw_template_list_ops(layout, basic_name):
    
    icons={
    'ADD':'ADD',
    'DELETE':'REMOVE',
    'UP':'TRIA_DOWN',
    'DOWN':'TRIA_UP',
    'CLEAR':'BRUSH_DATA'
    }
    
    for item in ['ADD','DELETE','UP','DOWN','CLEAR']:
        ops=layout.operator("bake.generic_channel_op",text='',icon=icons[item])
        ops.operation=item
        ops.target=basic_name
    '''layout.operator(f"bake.add_{basic_name}", text='',icon='ADD')
    layout.operator(f"bake.delect_{basic_name}", text='',icon='REMOVE')
    layout.operator(f"bake.up_{basic_name}", text='',icon='TRIA_DOWN')
    layout.operator(f"bake.down_{basic_name}", text='',icon='TRIA_UP')
    layout.operator(f"bake.clear_{basic_name}", text='',icon='BRUSH_DATA')'''
# 通用图像格式选项绘制函数
def draw_image_format_options(layout, setting, prefix=""):
    """
    绘制图像格式相关的所有选项：格式、质量、EXR 编码、颜色深度和颜色模式。
    
    Args:
        layout (bpy.types.UILayout): Blender 的布局对象
        setting (bpy.types.PropertyGroup): 包含属性的设置对象
        prefix (str): 属性名前缀，如 "node_bake_" 或 "objectmap_"，默认为空
    """
    format_prop = f"{prefix}save_format"
    quality_prop = f"{prefix}quality"
    exr_prop = f"{prefix}exr_code"
    depth_prop = f"{prefix}color_depth"
    mode_prop = f"{prefix}color_mode"
    space_prop = f"{prefix}color_space"
    
    # 绘制文件格式
    row = layout.row()
    row.prop(setting, format_prop)
    
    # 根据格式绘制 quality 或 exr_code
    format_value = getattr(setting, format_prop)
    if format_value != 'EXR':
        row.prop(setting, quality_prop, slider=True)
    else:
        row.prop(setting, exr_prop)
    
    # 绘制颜色深度
    if format_value in {'PNG', 'EXR'}:
        row = layout.row()
        row.label(text="Color Depth")
        if format_value == 'PNG':
            row.prop_enum(setting, depth_prop, '8')
            row.prop_enum(setting, depth_prop, '16')
        elif format_value == 'EXR':
            row.prop_enum(setting, depth_prop, '16')
            row.prop_enum(setting, depth_prop, '32')
    
    # 绘制颜色模式
    if hasattr(setting, mode_prop):
        row = layout.row()
        row.label(text="Color Mode")
        if format_value in {'BMP', 'JPG', 'HDR'}:
            row.prop_enum(setting, mode_prop, 'BW')
            row.prop_enum(setting, mode_prop, 'RGB')
        else:
            row.prop_enum(setting, mode_prop, 'BW')
            row.prop_enum(setting, mode_prop, 'RGB')
            row.prop_enum(setting, mode_prop, 'RGBA')
        
    # 绘制颜色模式
    if hasattr(setting, space_prop):
        row = layout.row()
        row.label(text="Color Space")
        row.enabled=format_value not in {'HDR', 'EXR'}
        row.prop(setting, space_prop)

def draw_results(scene,layout,bake_jobs):
    # 显示烘焙结果列表
    layout.label(text="Baked Image Results:")
    row = layout.row()
    row.template_list(
        "BAKETOOL_UL_BakedImageResults", "",
        scene, "baked_image_results",
        scene, "baked_image_results_index"
    )

    # 操作按钮
    col = row.column(align=True)
    col.operator("baketool.delete_result", text="", icon="TRASH")
    col.operator("baketool.delete_all_results", text="", icon="X")
    col.operator("baketool.export_result", text="", icon="EXPORT")
    col.operator("baketool.export_all_results", text="", icon="FILE_FOLDER")

    # 导出设置区域
    layout.label(text="Export Settings:")
    box = layout.box()
    box.prop(bake_jobs, "bake_result_save_path", text="Save Path")
    box.prop(bake_jobs, "bake_result_save_format", text="Format")
    box.prop(bake_jobs, "bake_result_color_depth", text="Color Depth")
    box.prop(bake_jobs, "bake_result_color_mode", text="Color Mode")
    box.prop(bake_jobs, "bake_result_color_space", text="Color Space")
    box.prop(bake_jobs, "bake_result_quality", text="Quality")
    if bake_jobs.bake_result_save_format == 'OPEN_EXR':
        box.prop(bake_jobs, "bake_result_exr_code", text="EXR Compression")
    box.prop(bake_jobs, "bake_result_use_denoise", text="Use Denoise")
    if bake_jobs.bake_result_use_denoise:
        box.prop(bake_jobs, "bake_result_denoise_method", text="Denoise Method")

    # 显示选中结果的详细信息
    if scene.baked_image_results_index >= 0 and scene.baked_image_results:
        result = scene.baked_image_results[scene.baked_image_results_index]
        box = layout.box()
        box.label(text="Selected Result Details:")
        box.prop(result, "image", text="Image")
        box.prop(result, "object_name", text="Object")
        box.prop(result, "channel_type", text="Channel")
        box.prop(result, "color_depth", text="Color Depth")
        box.prop(result, "color_space", text="Color Space")
        box.prop(result, "filepath", text="Filepath")

class BAKE_PT_nodepanel(bpy.types.Panel):
    bl_label = "Node Bake"
    bl_idname = "BAKE_PT_nodepanel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Baking'
    
    # 绘制节点烘焙面板的 UI。
    # Draw the UI for the node baking panel.
    
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'ShaderNodeTree'
    
    def draw(self, context):
        layout = self.layout
        setting = context.scene.BakeJobs
        
        layout.label(text="Shader nodes are not supported currently", icon='INFO')
        layout.separator()
        
        # 分辨率和采样分组
        box = layout.box()
        box.label(text="Bake Settings", icon='RENDER_STILL')
        grid = box.grid_flow(columns=2, align=True)
        grid.prop(setting, "node_bake_res_x", text="X", icon='MESH_PLANE')
        grid.prop(setting, "node_bake_res_y", text="Y", icon='MESH_PLANE')
        grid.prop(setting, "node_bake_sample", text="Samples", icon='RENDER_RESULT')
        grid.prop(setting, "node_bake_margin", text="Margin", icon='OUTLINER_OB_EMPTY')
        
        # 其他选项
        box.prop(setting, "node_bake_delect_node", icon='NODETREE')
        box.prop(setting, "node_bake_float32", expand=True, icon='IMAGE_RGB')
        
        row = box.row()
        row.enabled = not setting.node_bake_float32 or (setting.node_bake_save_outside and setting.node_bake_reload)
        row.prop(setting, "node_bake_color_space", icon='COLOR')
        
        # 保存设置分组
        box = layout.box()
        box.label(text="Save Options", icon='FILE_TICK')
        box.prop(setting, "node_bake_save_outside", text="Save Externally", icon='FILE_TICK')
        if setting.node_bake_save_outside:
            draw_file_path(box, setting, "node_bake_save_path", 2)
            draw_image_format_options(box, setting, prefix="node_bake_")
            box.prop(setting, "node_bake_reload", icon='FILE_REFRESH')
        
        layout.prop(setting, "node_bake_auto_find_socket", icon='NODE')
        if not setting.node_bake_auto_find_socket:
            layout.prop(setting, "node_bake_socket_index", icon='NODE')
        
        # 操作按钮
        layout.separator()
        row = layout.row(align=True)
        row.scale_y = 2.0
        row.operator("bake.selected_node_bake", text="Bake Selected Node", icon='RENDER_STILL')
        
       
class BAKE_PT_bakepanel(bpy.types.Panel):
    bl_label = "Baking Tool"
    bl_idname = "BAKE_PT_bakepanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Baking'

    # 绘制主烘焙工具面板的 UI。
    # Draw the UI for the main baking tool panel.
    # 通道定义字典，支持 BSDF（分版本）、BASIC 和 MULTIRES 类型
    CHANNELS = {
        "BSDF": {
            "pre_4_0": [  # Blender 4.0 之前的通道
                {"name": "color", "extra": []},
                {"name": "subface", "extra": []},
                {"name": "subface_col", "extra": []},
                {"name": "subface_ani", "extra": []},
                {"name": "metal", "extra": []},
                {"name": "specular", "extra": []},
                {"name": "specular_tint", "extra": []},
                {"name": "rough", "extra": ["rough_inv"]},
                {"name": "anisotropic", "extra": []},
                {"name": "anisotropic_rot", "extra": []},
                {"name": "sheen", "extra": []},
                {"name": "sheen_tint", "extra": []},
                {"name": "clearcoat", "extra": []},
                {"name": "clearcoat_rough", "extra": []},
                {"name": "tran", "extra": []},
                {"name": "tran_rou", "extra": []},
                {"name": "emi", "extra": []},
                {"name": "emi_str", "extra": []},
                {"name": "alpha", "extra": []},
                {"name": "normal", "extra": []},
            ],
            "post_4_0": [  # Blender 4.0 及之后的通道
                {"name": "color", "extra": []},
                {"name": "subface", "extra": []},
                {"name": "subface_ani", "extra": []},
                {"name": "metal", "extra": []},
                {"name": "specular", "extra": []},
                {"name": "specular_tint", "extra": []},
                {"name": "rough", "extra": ["rough_inv"]},
                {"name": "anisotropic", "extra": []},
                {"name": "anisotropic_rot", "extra": []},
                {"name": "sheen", "extra": []},
                {"name": "sheen_tint", "extra": []},
                {"name": "sheen_rough", "extra": []},
                {"name": "clearcoat", "extra": []},
                {"name": "clearcoat_rough", "extra": []},
                {"name": "clearcoat_tint", "extra": []},  # 4.0 新增
                {"name": "tran", "extra": []},
                {"name": "emi", "extra": []},
                {"name": "emi_str", "extra": []},
                {"name": "alpha", "extra": []},
                {"name": "normal", "extra": []},
            ]
        },
        "BASIC": {
            "channels": [
                {"name": "diff", "extra": ["diff_dir", "diff_ind", "diff_col"]},
                {"name": "rough", "extra": []},
                {"name": "emi", "extra": []},
                {"name": "gloss", "extra": ["gloss_dir", "gloss_ind", "gloss_col"]},
                {"name": "tranb", "extra": ["tranb_dir", "tranb_ind", "tranb_col"]},
                {"name": "combine", "extra": ["com_dir", "com_ind", "com_diff", "com_gloss", "com_tran", "com_emi"]},
                {"name": "normal", "extra": []},
            ]
        },
        "MULTIRES": {
            "channels": [
                {"name": "height", "extra": []},
                {"name": "normal", "extra": []},
            ]
        },
        "SPECIAL_MAPS": {  # 特殊贴图通道
            "lighting": [
                {"name": "shadow", "extra": []},
                {"name": "env", "extra": []},
            ],
            "mesh": [
                {"name": "bevel", "extra": ["bevel_sample", "bevel_rad"]},
                {"name": "ao", "extra": ["ao_inside", "ao_local", "ao_dis", "ao_sample"]},
                {"name": "UV", "extra": []},
                {"name": "wireframe", "extra": ["wireframe_use_pix", "wireframe_dis"]},
                {"name": "bevnor", "extra": ["bevnor_sample", "bevnor_rad"]},
                {"name": "position", "extra": ["position_invg"]},
                {"name": "slope", "extra": ["slope_directions", "slope_invert"]},
                {"name": "thickness", "extra": ["thickness_distance", "thickness_contrast"]},
                {"name": "select", "extra": []},
            ],
            "id": [
                {"name": "ID_mat", "extra": []},
                {"name": "ID_ele", "extra": []},
                {"name": "ID_UVI", "extra": []},
                {"name": "ID_seam", "extra": []},
            ],
            "other": [
                {"name": "vertex", "extra": []},
            ]
        }
    }
    # 烘焙类型、方法和模式的映射表
    BAKE_TYPE_MAPPING = {
        "BASIC": {
            "NO": {
                "available_modes": ["SINGLE_OBJECT", "COMBINE_OBJECT", "SELECT_ACTIVE", "SPILT_MATERIAL"],
                "description": "标准烘焙，支持单个物体、组合物体、选中到活动物体和按材质分割"
            },
            "VERTEXCOLOR": {
                "available_modes": ["SINGLE_OBJECT", "COMBINE_OBJECT", "SELECT_ACTIVE", "SPILT_MATERIAL"],
                "description": "将结果烘焙到顶点色，支持所有模式"
            },
            "AUTOATLAS": {
                "available_modes": ["SINGLE_OBJECT", "SELECT_ACTIVE"],
                "description": "制作合并贴图，仅支持单个物体和选中到活动物体"
            }
        },
        "BSDF": {
            "NO": {
                "available_modes": ["SINGLE_OBJECT", "COMBINE_OBJECT", "SPILT_MATERIAL"],
                "description": "BSDF 正常烘焙，支持单个物体、组合物体和按材质分割"
            },
            "VERTEXCOLOR": {
                "available_modes": ["SINGLE_OBJECT", "COMBINE_OBJECT", "SPILT_MATERIAL"],
                "description": "BSDF 顶点色烘焙，支持单个物体、组合物体和按材质分割"
            },
            "AUTOATLAS": {
                "available_modes": [],
                "description": "BSDF 不支持自动图集模式"
            }
        },
        "MULTIRES": {
            "NO": {
                "available_modes": ["SINGLE_OBJECT", "COMBINE_OBJECT"],
                "description": "多级精度烘焙，仅支持单个物体和组合物体"
            },
            "VERTEXCOLOR": {
                "available_modes": [],
                "description": "多级精度烘焙不支持顶点色模式"
            },
            "AUTOATLAS": {
                "available_modes": [],
                "description": "多级精度烘焙不支持自动图集模式"
            }
        }
    }
    
    def draw_channel(self, layout, setting, channel_name, extra_props=None):
        """绘制单个通道的 UI，包括开关、前缀、后缀和可选的额外属性 (Draw UI for a single channel, including toggle, prefix, suffix, and optional extra properties)"""
        row = layout.row(align=True)
        row.prop(setting, channel_name, toggle=True)  # 通道开关 (Channel toggle)
        row.prop(setting, f"{channel_name}_pre")  # 前缀 (Prefix)
        row.prop(setting, f"{channel_name}_suf")  # 后缀 (Suffix)
        if setting.colorspace_setting and not setting.float32:
            row.prop(setting, f"{channel_name}_cs")  # 颜色空间 (Color space)
        if extra_props and getattr(setting, channel_name):
            col = layout.column(align=True)
            for prop in extra_props:
                col.prop(setting, prop)  # 额外属性 (Extra property)

    def draw_rgba_channel(self, layout, item, channel, setting, bw=False):
        """绘制单个 RGBA 通道的 UI，包括开关、反转和映射选择 (Draw UI for a single RGBA channel, including toggle, invert, and map selection)"""
        row = layout.row()
        if not bw: 
            usemap_prop = f"{channel}_usemap"
            row.prop(item, usemap_prop, text=f"{channel.upper()} Channel Use Map")  # 使用贴图开关 (Use map toggle)
        split = row.split(factor=1, align=False)
        split.enabled = bw or getattr(item, usemap_prop)
        split.scale_x = 0.6
        split.prop(item, f"{channel}_invert", text="Invert")  # 反转 (Invert)
        split = row.split(factor=1, align=False)
        split.enabled = bw or getattr(item, usemap_prop)
        split.scale_x = 0.75
        if setting.bake_type == 'BSDF' and bpy.app.version < (4, 0, 0):
            split.prop(item, f"{channel}_map_BSDF3")  # BSDF 3.x 映射 (BSDF 3.x mapping)
        elif setting.bake_type == 'BSDF' and bpy.app.version >= (4, 0, 0):
            split.prop(item, f"{channel}_map_BSDF4")  # BSDF 4.x 映射 (BSDF 4.x mapping)
        else:
            split.prop(item, f"{channel}_map_basic")  # 基本映射 (Basic mapping)
        if bw or getattr(item, usemap_prop):
            row = layout.row()
            row.scale_x = 0.8
            row.prop(item, f"{channel}_sepcol", text="Separate Colors")  # 分离颜色 (Separate colors)
            if getattr(item, f"{channel}_sepcol"):
                row.prop(item, f"{channel}_colchan", text="Channel")  # 颜色通道 (Color channel)

    def draw_inputs(self, layout, jobs, setting):
        """绘制输入设置面板，优化排版和图标 (Draw input settings panel, optimize layout and icons)"""
        layout.prop(jobs, "open_inputs", icon="DISCLOSURE_TRI_DOWN" if jobs.open_inputs else "DISCLOSURE_TRI_RIGHT", text="Inputs")  # 输入面板开关 (Input panel toggle)
        if not jobs.open_inputs:
            return

        box = layout.box()
        box.label(text="Bake Inputs", icon='RENDER_STILL')  # 烘焙输入标题 (Bake inputs title)

        # 分辨率和采样（网格布局）(Resolution and sampling [grid layout])
        grid = box.grid_flow(columns=2, align=True)
        grid.enabled = setting.special_bake_method != 'VERTEXCOLOR'  # VERTEXCOLOR 时禁用 (Disabled when VERTEXCOLOR)
        grid.prop(setting, "res_x", text="Width", icon='MESH_PLANE')  # 宽度 (Width)
        grid.prop(setting, "res_y", text="Height", icon='MESH_PLANE')  # 高度 (Height)
        grid.prop(setting, "sample", text="Samples", icon='RENDER_RESULT')  # 采样数 (Samples)
        grid.prop(setting, "margin", text="Margin", icon='OUTLINER_OB_EMPTY')  # 边缘距离 (Margin)

        # 设备和烘焙类型 (Device and bake type)
        col = box.column(align=True)
        col.prop(setting, "device", icon='SYSTEM', text="Device")  # 设备选择 (Device selection)
        col.prop(setting, "bake_type", icon='SHADING_TEXTURE', text="Bake Type")  # 烘焙类型 (Bake type)

        # Special Setting（仅 BASIC 和 BSDF）(Special Setting [only BASIC and BSDF])
        if setting.bake_type in {"BASIC", "BSDF"}:
            box.separator()  # 分隔符 (Separator)
            col = box.column(align=True)
            col.label(text="Special Settings", icon='MODIFIER')  # 特殊设置标题 (Special settings title)
            row = col.row(align=True)
            row.prop_enum(setting, "special_bake_method", "NO", text="None", icon='NONE')  # 无特殊方法 (No special method)
            row.prop_enum(setting, "special_bake_method", "VERTEXCOLOR", text="Vertex Color", icon='VPAINT_HLT')  # 顶点色 (Vertex color)
            row.prop_enum(setting, "special_bake_method", "AUTOATLAS", text="Auto Atlas", icon='UV')  # 自动图集 (Auto atlas)

        # Baking Method（动态选项）(Baking Method [dynamic options])
        available_modes = self.BAKE_TYPE_MAPPING.get(setting.bake_type, {}).get(setting.special_bake_method, {}).get("available_modes", [])
        if available_modes:
            box.separator()
            col = box.column(align=True)
            col.label(text="Baking Method", icon='OBJECT_DATA')  # 烘焙方法标题 (Baking method title)
            row = col.row(align=True)
            for mode in available_modes:
                row.prop_enum(setting, "bake_mode", mode, translate=True, icon='NONE')  # 动态烘焙模式 (Dynamic bake mode)

        # Baking Objects (烘焙对象)
        box.separator()
        col = box.column(align=True)
        col.label(text="Baking Objects", icon='OUTLINER_OB_MESH')  # 烘焙对象标题 (Baking objects title)
        for obj in setting.bake_objects:
            if obj.bakeobject:
                col.label(text=obj.bakeobject.name, icon='OBJECT_DATA')  # 对象名称 (Object name)
        row = col.row(align=True)
        row.prop(setting, "bake_objects", text="")  # 对象列表 (Object list)
        row.operator("bake.record_objects", text="Record", icon='ADD').objecttype = 0  # 记录对象 (Record objects)

        # SELECT_ACTIVE 模式额外设置 (SELECT_ACTIVE mode extra settings)
        if setting.bake_mode == "SELECT_ACTIVE" and setting.bake_type == "BASIC":
            box.separator()
            col = box.column(align=True)
            col.label(text="Active Object Settings", icon='PIVOT_ACTIVE')  # 活动对象设置标题 (Active object settings title)
            row = col.row(align=True)
            row.prop(setting, "active_object", text="Active")  # 活动对象 (Active object)
            row.operator("bake.record_objects", text="", icon='EYEDROPPER').objecttype = 1  # 记录活动对象 (Record active object)
            row = col.row(align=True)
            row.prop(setting, "cage_object", text="Cage")  # 罩体对象 (Cage object)
            row.operator("bake.record_objects", text="", icon='EYEDROPPER').objecttype = 2  # 记录罩体对象 (Record cage object)
            row = col.row(align=True)
            row.prop(setting, "extrusion", text="Extrusion")  # 挤出距离 (Extrusion distance)
            row.prop(setting, "ray_distance", text="Ray Distance")  # 光线距离 (Ray distance)

        # AUTOATLAS 模式额外设置 (AUTOATLAS mode extra settings)
        if setting.special_bake_method == 'AUTOATLAS':
            box.separator()
            col = box.column(align=True)
            col.label(text="Atlas Settings", icon='UV_DATA')  # 图集设置标题 (Atlas settings title)
            col.prop(setting, "altas_pack_method", expand=True)  # 图集打包方法 (Atlas packing method)
            col.prop(setting, "altas_margin", text="Margin")  # 图集边距 (Atlas margin)

        # MULTIRES 模式额外设置 (MULTIRES mode extra settings)
        if setting.bake_type == 'MULTIRES':
            box.separator()
            col = box.column(align=True)
            col.label(text="Multires Settings", icon='MOD_MULTIRES')  # 多级精度设置标题 (Multires settings title)
            col.prop(setting, "mutlires_divide", text="Subdivision")  # 细分级别 (Subdivision level)

        # 动画烘焙选项 (Animation baking options)
        box.separator()
        col = box.column(align=True)
        row = col.row(align=True)
        row.enabled = setting.special_bake_method != 'VERTEXCOLOR' and setting.bake_type != 'MULTIRES'  # 禁用条件 (Disable condition)
        row.prop(setting, "bake_motion", icon='ANIM', text="Bake Animation")  # 动画烘焙开关 (Animation baking toggle)
        if setting.bake_motion:
            col = box.column(align=True)
            col.label(text="Animation Range", icon='TIME')  # 动画范围标题 (Animation range title)
            row = col.row(align=True)
            row.prop(setting, "bake_motion_startindex", text="Start Index")  # 开始索引 (Start index)
            row.prop(setting, "bake_motion_digit", text="Digits")  # 位数 (Digits)
            col.prop(setting, "bake_motion_use_custom", text="Custom Range", icon='PRESET')  # 自定义范围 (Custom range)
            if setting.bake_motion_use_custom:
                row = col.row(align=True)
                row.prop(setting, "bake_motion_start", text="Start Frame")  # 开始帧 (Start frame)
                row.prop(setting, "bake_motion_last", text="End Frame")  # 结束帧 (End frame)

        # 精度和颜色设置 (Precision and color settings)
        box.separator()
        col = box.column(align=True)
        col.prop(setting, "float32", icon='IMAGE_RGB', text="32-bit Float")  # 32位浮点开关 (32-bit float toggle)
        if setting.special_bake_method != 'VERTEXCOLOR':
            row = col.row(align=True)
            row.enabled = not setting.float32 or (setting.reload and setting.save_out or setting.bake_motion)  # 启用条件 (Enable condition)
            row.prop(setting, "colorspace_setting", icon='COLOR', text="Color Space")  # 颜色空间 (Color space)
            col.prop(setting, "use_alpha", icon='IMAGE_ALPHA', text="Use Alpha")  # 使用Alpha (Use Alpha)
            col.prop(setting, "clearimage", icon='BRUSH_DATA', text="Clear Image")  # 清除图像 (Clear image)
            if not setting.clearimage:
                col.prop(setting, "colorbase", icon='COLOR', text="Base Color")  # 基底颜色 (Base color)

    def draw_channels(self, layout, jobs, setting):
        """绘制通道设置面板，优化排版和图标 (Draw channels settings panel, optimize layout and icons)"""
        layout.prop(jobs, "open_channels", icon="DISCLOSURE_TRI_DOWN" if jobs.open_channels else "DISCLOSURE_TRI_RIGHT", text="Channels")  # 通道面板开关 (Channels panel toggle)
        if not jobs.open_channels:
            return

        box = layout.box()
        box.label(text="Bake Channels", icon='TEXTURE')  # 烘焙通道标题 (Bake channels title)

        # 主通道 (Main channels)
        if setting.bake_type == "BSDF":
            channels = self.CHANNELS["BSDF"]["post_4_0" if bpy.app.version >= (4, 0, 0) else "pre_4_0"]  # BSDF通道版本 (BSDF channel version)
        else:
            channels = self.CHANNELS.get(setting.bake_type, {}).get("channels", [])  # 其他类型通道 (Other type channels)
        col = box.column(align=True)
        for channel in channels:
            self.draw_channel(col, setting, channel["name"], channel.get("extra", []))  # 绘制主通道 (Draw main channel)

        # 法线设置 (Normal settings)
        if setting.normal:
            box.separator()
            col = box.column(align=True)
            col.label(text="Normal Settings", icon='NORMALS_FACE')  # 法线设置标题 (Normal settings title)
            col.prop(setting, "normal_type", text="Type")  # 法线类型 (Normal type)
            if setting.normal_type == 'CUSTOM':
                row = col.row(align=True)
                row.prop(setting, "normal_X", text="X")  # X轴法线 (X-axis normal)
                row.prop(setting, "normal_Y", text="Y")  # Y轴法线 (Y-axis normal)
                row.prop(setting, "normal_Z", text="Z")  # Z轴法线 (Z-axis normal)
            col.prop(setting, "normal_obj", text="Object")  # 法线对象 (Normal object)

        # 特殊贴图 (Special maps)
        box.separator()
        col = box.column(align=True)
        col.prop(setting, "use_special_map", icon='TEXTURE_DATA', text="Special Maps")  # 特殊贴图开关 (Special maps toggle)
        if setting.use_special_map:
            # Lighting Maps (光照贴图)
            sub_box = box.box()
            sub_box.label(text="Lighting Maps", icon='LIGHT')  # 光照贴图标题 (Lighting maps title)
            col = sub_box.column(align=True)
            for channel in self.CHANNELS["SPECIAL_MAPS"]["lighting"]:
                self.draw_channel(col, setting, channel["name"], channel.get("extra", []))  # 绘制光照贴图 (Draw lighting map)
            
            enabled=not (setting.bake_mode == 'SELECT_ACTIVE' and setting.bake_type == 'BASIC') and \
                          setting.special_bake_method != 'VERTEXCOLOR' and \
                          setting.bake_mode != 'SPILT_MATERIAL' and \
                          not setting.bake_motion  # 启用条件 (Enable condition)
            # Mesh Maps (网格贴图)
            sub_box = box.box()
            sub_box.label(text="Mesh Maps", icon='MESH_DATA')  # 网格贴图标题 (Mesh maps title)
            col = sub_box.column(align=True)
            col.enabled = enabled
            for channel in self.CHANNELS["SPECIAL_MAPS"]["mesh"]:
                self.draw_channel(col, setting, channel["name"], channel.get("extra", []))  # 绘制网格贴图 (Draw mesh map)

            # ID Maps (ID贴图)
            sub_box = box.box()
            sub_box.label(text="ID Maps", icon='TEXT')  # ID贴图标题 (ID maps title)
            col = sub_box.column(align=True)
            col.enabled = enabled
            for channel in self.CHANNELS["SPECIAL_MAPS"]["id"]:
                self.draw_channel(col, setting, channel["name"], channel.get("extra", []))  # 绘制ID贴图 (Draw ID map)
            col = sub_box.column(align=True)
            col.prop(setting,"ID_num",text='ID nums')

            # Other Maps (其他贴图)
            sub_box = box.box()
            sub_box.label(text="Other Maps", icon='GROUP_VERTEX')  # 其他贴图标题 (Other maps title)
            col = sub_box.column(align=True)
            col.enabled = enabled
            for channel in self.CHANNELS["SPECIAL_MAPS"]["other"]:
                self.draw_channel(col, setting, channel["name"], channel.get("extra", []))  # 绘制其他贴图 (Draw other map)

    def draw_saves(self, layout, jobs, setting):
        """绘制保存设置面板，优化排版和图标 (Draw save settings panel, optimize layout and icons)"""
        layout.prop(jobs, "open_saves", icon="DISCLOSURE_TRI_DOWN" if jobs.open_saves else "DISCLOSURE_TRI_RIGHT", text="Saves")  # 保存面板开关 (Saves panel toggle)
        if not jobs.open_saves:
            return

        box = layout.box()
        box.label(text="Save Options", icon='FILE_TICK')  # 保存选项标题 (Save options title)

        col = box.column(align=True)
        col.prop(setting, "name_setting", icon='SORTALPHA', text="Naming")  # 命名设置 (Naming settings)
        row = col.row(align=True)
        row.enabled = setting.name_setting == "CUSTOM"  # 启用自定义命名 (Enable custom naming)
        row.prop(setting, "custom_name", icon='FONT_DATA', text="Custom Name")  # 自定义名称 (Custom name)

        if setting.special_bake_method != 'VERTEXCOLOR':
            col.prop(setting, "use_fake_user", icon='FAKE_USER_ON', text="Use Fake User")  # 使用伪用户 (Use fake user)
            col.prop(setting, "object_image_map", icon='IMAGE_DATA', text="Object Image Map")  # 对象图像贴图 (Object image map)
            row = col.row(align=True)
            row.enabled = not setting.bake_motion  # 非动画时启用 (Enabled when not baking motion)
            row.prop(setting, "save_out", icon='EXPORT', text="Save Externally")  # 外部保存 (Save externally)
            if setting.save_out or setting.bake_motion:
                col.prop(setting, "use_denoise", icon='MODIFIER', text="Denoise")  # 使用降噪 (Use denoise)
                if setting.use_denoise:
                    col.prop(setting, "denoise_method", text="Method")  # 降噪方法 (Denoise method)
                sub_col = col.column(align=True)
                if setting.bake_type == 'BASIC':
                    sub_col.label(text="Tip: Use PNG/EXR for transparency", icon='INFO')  # 提示：透明度用PNG/EXR (Tip: Use PNG/EXR for transparency)
                if setting.float32:
                    sub_col.label(text="Tip: Use 16/32-bit formats", icon='INFO')  # 提示：使用16/32位格式 (Tip: Use 16/32-bit formats)
                draw_file_path(sub_col, setting, "save_path", 0)  # 保存路径 (Save path)
                sub_col.prop(setting, "reload", icon='FILE_REFRESH', text="Reload")  # 重新加载 (Reload)
                draw_image_format_options(box, setting)  # 图像格式选项 (Image format options)
                col.prop(setting, "create_new_folder", icon='NEWFOLDER', text="Create New Folder")  # 创建新文件夹 (Create new folder)
                if setting.create_new_folder:
                    row = col.row(align=True)
                    row.prop(setting, "new_folder_name_setting", text="Folder Naming")  # 文件夹命名 (Folder naming)
                    split = row.split()
                    split.enabled = setting.new_folder_name_setting == 'CUSTOM'  # 启用自定义文件夹名 (Enable custom folder name)
                    split.prop(setting, "folder_name", icon='FILE_FOLDER', text="Name")  # 文件夹名称 (Folder name)

    def draw_others(self, layout, jobs, setting):
        """绘制其他设置面板，优化排版和图标 (Draw other settings panel, optimize layout and icons)"""
        job = jobs.jobs[jobs.job_index]
        layout.prop(jobs, "open_other", icon="DISCLOSURE_TRI_DOWN" if jobs.open_other else "DISCLOSURE_TRI_RIGHT", text="Others")  # 其他面板开关 (Others panel toggle)
        if not jobs.open_other:
            return

        box = layout.box()
        box.label(text="Other Options", icon='PREFERENCES')  # 其他选项标题 (Other options title)

        col = box.column(align=True)
        col.prop(setting, "save_and_quit", icon='QUIT', text="Save and Quit")  # 保存并退出 (Save and quit)
        row = col.row(align=True)
        row.enabled = setting.bake_type == 'BSDF' and not setting.bake_motion and setting.bake_mode != 'SPILT_MATERIAL'  # 启用条件 (Enable condition)
        row.prop(setting, "bake_texture_apply", icon='TEXTURE', text="Apply Texture")  # 应用纹理 (Apply texture)
        row = col.row(align=True)
        row.enabled = setting.special_bake_method != 'VERTEXCOLOR' and not setting.bake_motion and setting.bake_type != 'MULTIRES'  # 启用条件 (Enable condition)
        row.prop(setting, "use_custom_map", icon='TEXTURE_DATA', text="Custom Map")  # 自定义贴图 (Custom map)
        if setting.use_custom_map and row.enabled:
            draw_file_path(box, setting, "custom_file_path", 1)  # 自定义文件路径 (Custom file path)
            col.prop(setting, "custom_new_folder", icon='NEWFOLDER', text="New Folder")  # 新文件夹 (New folder)
            if setting.custom_new_folder:
                row = col.row(align=True)
                row.prop(setting, "custom_folder_name_setting", text="Folder Naming")  # 文件夹命名 (Folder naming)
                split = row.split()
                split.enabled = setting.custom_folder_name_setting == 'CUSTOM'  # 启用自定义文件夹名 (Enable custom folder name)
                split.prop(setting, "custom_folder_name", icon='FILE_FOLDER', text="Name")  # 文件夹名称 (Folder name)
            col.label(text="Custom Map Channels", icon='TEXTURE')  # 自定义贴图通道标题 (Custom map channels title)
            col.template_list("LIST_UL_Custombakechannellist", "bake_channel_list", job, "Custombakechannels", job, "Custombakechannels_index")  # 通道列表 (Channel list)
            row = col.row(align=True)
            row = col.row(align=True)
            row.label(text=f"Total: {len(job.Custombakechannels)}", icon='INFO')  # 通道总数 (Total channels)
            row.label(text=f"Active: {job.Custombakechannels_index}", icon='PIVOT_ACTIVE')  # 活动通道 (Active channel)
            row = col.row(align=True)
            row.scale_x = 3
            draw_template_list_ops(row, "job_custom_channel")  # 通道操作模板 (Channel operation template)
            if len(job.Custombakechannels) > 0:
                item = job.Custombakechannels[job.Custombakechannels_index]
                col.separator()
                col.label(text="Channel Details", icon='SHADING_TEXTURE')  # 通道详情标题 (Channel details title)
                col.prop(item, "name", text="Name", icon='FONT_DATA')  # 通道名称 (Channel name)
                draw_image_format_options(col, item)  # 图像格式选项 (Image format options)
                col.prop(item, "bw", text="BW Map Only", icon='IMAGE_RGB')  # 仅黑白贴图 (BW map only)
                if item.bw:
                    self.draw_rgba_channel(col, item, 'bw', setting, True)  # 绘制黑白通道 (Draw BW channel)
                else:
                    for channel in ['r', 'g', 'b', 'a']:
                        self.draw_rgba_channel(col, item, channel, setting)  # 绘制RGBA通道 (Draw RGBA channel)
                col.prop(item, "prefix", text="Prefix", icon='SORTALPHA')  # 前缀 (Prefix)
                col.prop(item, "suffix", text="Suffix", icon='SORTALPHA')  # 后缀 (Suffix)

        col.separator()
        row = col.row(align=True)
        #row.operator("bake.save_bake_setting", text="Save Settings", icon='FILE_TICK')  # 保存设置 (Save settings)
        #row.operator("bake.load_bake_setting", text="Load Settings", icon='FILE_REFRESH')  # 加载设置 (Load settings)
    
    def draw(self, context):
        layout = self.layout
        jobs = context.scene.BakeJobs

        # Jobs 列表 (Jobs list)
        box = layout.box()
        box.label(text="Jobs List", icon='RENDERLAYERS')  # 任务列表标题 (Jobs list title)
        box.template_list("LIST_UL_Jobslist", "jobs_list", jobs, "jobs", jobs, "job_index")  # 任务列表 (Jobs list)
        row = box.row(align=True)
        row.scale_x = 3
        draw_template_list_ops(row, "jobs_channel")  # 任务操作模板 (Jobs operation template)
        if jobs.jobs:
            row = box.row(align=True)
            row.prop(jobs.jobs[jobs.job_index], "name", text="Job Name", icon='FONT_DATA')  # 任务名称 (Job name)
        else:
            layout.label(text="Add a job to continue", icon='INFO')  # 添加任务提示 (Add job prompt)
            return

        job = jobs.jobs[jobs.job_index]
        setting = job.setting

        # 绘制各部分 (Draw each section)
        self.draw_inputs(layout, jobs, setting)
        self.draw_channels(layout, jobs, setting)
        self.draw_saves(layout, jobs, setting)
        self.draw_others(layout, jobs, setting)


        # 开始烘焙按钮 (Start baking button)
        layout.separator()
        row = layout.row(align=True)
        row.scale_y = 2.0
        row.operator("bake.bake_operator", text="Start Baking", icon='RENDER_STILL')  # 开始烘焙 (Start baking)
        
# 主面板中的烘焙结果显示
class BAKETOOL_PT_BakedResults(bpy.types.Panel):
    bl_label = "Baked Results"
    bl_idname = "BAKETOOL_PT_baked_results"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BakeTool"
    bl_parent_id = "BAKE_PT_bakepanel"

    def draw(self, context):

        draw_results(context.scene,self.layout,context.scene.BakeJobs)

# 图像编辑器中的烘焙结果显示
class BAKETOOL_PT_ImageEditorResults(bpy.types.Panel):
    bl_label = "Baked Results"
    bl_idname = "BAKETOOL_PT_image_editor_results"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "BakeTool"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        draw_results(scene,layout,scene.BakeJobs)

        # 在图像编辑器中显示预览
        if scene.baked_image_results_index >= 0 and scene.baked_image_results:
            result = scene.baked_image_results[scene.baked_image_results_index]
            if result.image and context.space_data.image != result.image:
                context.space_data.image = result.image  # 设置图像编辑器显示选中的图像

class LIST_UL_Jobslist(bpy.types.UIList):
    #借用了sinestesia的模板
    def draw_item(self, context, layout, data, item, icon, active_data,active_propname, index):
        custom_icon = 'SHADING_TEXTURE'
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, icon = custom_icon)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon = custom_icon)

class LIST_UL_Basicbakechannellist(bpy.types.UIList):
    #借用了sinestesia的模板
    def draw_item(self, context, layout, data, item, icon, active_data,active_propname, index):
        custom_icon = 'SHADING_TEXTURE'
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, icon = custom_icon)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon = custom_icon)

class LIST_UL_Custombakechannellist(bpy.types.UIList):
    #借用了sinestesia的模板
    def draw_item(self, context, layout, data, item, icon, active_data,active_propname, index):
        custom_icon = 'SHADING_TEXTURE'
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, icon = custom_icon)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon = custom_icon)

# 定义 UIList 来显示烘焙结果
class BAKETOOL_UL_BakedImageResults(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "image", text="", emboss=False)  # 显示图像名称
            row.prop(item, "object_name", text="", emboss=False)  # 显示对象名称
            row.prop(item, "channel_type", text="", emboss=False)  # 显示通道类型
            row.label(text=f"Depth: {item.color_depth}")  # 显示色深
            row.label(text=f"Space: {item.color_space}")  # 显示色彩空间
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=item.image.name if item.image else "No Image")