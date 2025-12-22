import bpy
from bpy import props
from .constants import *
from .utils import logger
import logging

# ==============================================================================
# 动态回调函数 (Dynamic Callbacks)
# ==============================================================================

def get_channel_source_items(self, context):
    """
    动态返回当前 Job 中已启用的通道列表。
    """
    # 默认空选项
    fallback = [('NONE', 'None', 'No enabled channels available')]

    if context is None:
        return fallback

    try:
        # 1. 获取当前 Job 设置
        scene = context.scene
        if not hasattr(scene, "BakeJobs") or not scene.BakeJobs:
            return fallback
            
        idx = scene.BakeJobs.job_index
        if idx < 0 or idx >= len(scene.BakeJobs.jobs):
            return fallback
            
        job = scene.BakeJobs.jobs[idx]
        setting = job.setting
        
        # 2. 构建列表
        items = []
        
        # 遍历动态通道列表 (包含 BSDF, Basic, 和启用的 Special Maps)
        for channel in setting.channels:
            if channel.enabled:
                # 格式: (identifier, name, description)
                # identifier 使用 channel.id (如 'diff', 'rough', 'color')
                items.append((
                    channel.id, 
                    channel.name, 
                    f"Use {channel.name} result as source"
                ))
        
        if not items:
            return fallback
            
        return items

    except Exception as e:
        logger.warning(f"Error getting channel sources: {e}")
        return fallback

def get_valid_depths(self, context):
    """根据选择的文件格式，返回有效的色深选项"""
    # 获取当前的格式属性
    # self 可以是 CustomBakeChannel, BakeJobSetting 或 BakeJobs(Scene)
    # 只要这些类都有 'save_format' (或类似命名的) 属性即可
    
    fmt = "PNG" # 默认
    
    # 检测 self 类型并获取对应的格式属性名
    if hasattr(self, "save_format"):
        fmt = self.save_format
    elif hasattr(self, "node_bake_save_format"):
        fmt = self.node_bake_save_format
    elif hasattr(self, "bake_result_save_format"):
        fmt = self.bake_result_save_format
        
    if fmt not in FORMAT_SETTINGS:
        return color_depth
    
    valid_depths_keys = FORMAT_SETTINGS[fmt].get("depths", [])
    if not valid_depths_keys:
        return color_depth
        
    filtered = [item for item in color_depth if item[0] in valid_depths_keys]
    return filtered

def get_valid_modes(self, context):
    """根据选择的文件格式，返回有效的颜色模式"""
    fmt = "PNG"
    
    if hasattr(self, "save_format"):
        fmt = self.save_format
    elif hasattr(self, "node_bake_save_format"):
        fmt = self.node_bake_save_format
    elif hasattr(self, "bake_result_save_format"):
        fmt = self.bake_result_save_format
        
    if fmt not in FORMAT_SETTINGS:
        return color_mode
    
    valid_modes = FORMAT_SETTINGS[fmt].get("modes", [])
    if not valid_modes:
        return color_mode
        
    filtered = [item for item in color_mode if item[0] in valid_modes]
    return filtered

def update_debug_mode(self, context):
    if self.debug_mode:
        logger.setLevel(logging.DEBUG)
        logger.info("Debug mode enabled")
    else:
        logger.setLevel(logging.INFO)

def update_channels(self, context):
    # 只有在有操作符可用时才调用，防止启动时调用失败
    if hasattr(bpy.ops.bake, "reset_channels"):
        try:
            bpy.ops.bake.reset_channels('EXEC_DEFAULT')
        except:
            pass

# ==============================================================================
# 类定义 (Class Definitions)
# ==============================================================================

class BakeObject(bpy.types.PropertyGroup):
    bakeobject: props.PointerProperty(name="object", type=bpy.types.Object)
    
class BakeChannel(bpy.types.PropertyGroup):
    # --- Identification ---
    name: props.StringProperty(name="Channel Name", description="UI display name for the channel")
    id: props.StringProperty(name="Channel ID", description="Internal ID used for logic")
    
    # --- Common Settings ---
    enabled: props.BoolProperty(name="Enabled", description="Enable this channel for baking", default=False)
    prefix: props.StringProperty(name="Prefix", description="Filename prefix")
    suffix: props.StringProperty(name="Suffix", description="Filename suffix")
    custom_cs: props.EnumProperty(items=color_space, name="Color Space", description="Color space for the baked image")
    
    # BSDF specific
    rough_inv: props.BoolProperty(name="Invert", description="Invert Roughness map")

    # Normal specific
    normal_type: props.EnumProperty(items=normal_type, name="Normal Mode", default='OPENGL')
    normal_X: props.EnumProperty(items=normal_channel, name="X", default='POS_X')
    normal_Y: props.EnumProperty(items=normal_channel, name="Y", default='POS_Y')
    normal_Z: props.EnumProperty(items=normal_channel, name="Z", default='POS_Z')
    normal_obj: props.BoolProperty(name="Object Space", description="Bake in object space instead of tangent space")

    # BASIC bake specific
    diff_dir: props.BoolProperty(name="Direct", default=False)
    diff_ind: props.BoolProperty(name="Indirect", default=False)
    diff_col: props.BoolProperty(name="Color", default=True)

    gloss_dir: props.BoolProperty(name="Direct", default=False)
    gloss_ind: props.BoolProperty(name="Indirect", default=False)
    gloss_col: props.BoolProperty(name="Color", default=True)

    tranb_dir: props.BoolProperty(name="Direct", default=False)
    tranb_ind: props.BoolProperty(name="Indirect", default=False)
    tranb_col: props.BoolProperty(name="Color", default=True)

    com_dir: props.BoolProperty(name="Direct", default=True)
    com_ind: props.BoolProperty(name="Indirect", default=True)
    com_diff: props.BoolProperty(name="Diffuse", default=True)
    com_gloss: props.BoolProperty(name="Gloss", default=True)
    com_tran: props.BoolProperty(name="Transmission", default=True)
    com_emi: props.BoolProperty(name="Emission", default=True)
    
    # MESH specific
    bevel_sample: props.IntProperty(name='Samples', default=8, min=2, max=16)
    bevel_rad: props.FloatProperty(name='Radius', default=0.1, min=0, max=1000)
    
    ao_inside: props.BoolProperty(name='Inside', default=False)
    ao_local: props.BoolProperty(name='Only Local', default=False)
    ao_dis: props.FloatProperty(name='Distance', default=1, min=0, max=1000)
    ao_sample: props.IntProperty(name='Samples', default=16, min=1, max=128)

    wireframe_use_pix: props.BoolProperty(name='Use Pixel Size', default=False)
    wireframe_dis: props.FloatProperty(name='Thickness', default=0.01, min=0, max=100)

    bevnor_sample: props.IntProperty(name='Samples', default=8, min=2, max=16)
    bevnor_rad: props.FloatProperty(name='Radius', default=0.1, min=0, max=1000)

    position_invg: props.BoolProperty(name='Invert G', default=True)
    
    slope_directions: props.EnumProperty(items=directions, name='Direction', default="Z")
    slope_invert: props.BoolProperty(name='Invert', default=False)

    thickness_distance: props.FloatProperty(name='Distance', default=0.5)
    thickness_contrast: props.FloatProperty(name='Contrast', default=0.5)

    ID_num: props.IntProperty(name='ID Map Count', default=5, min=2, max=20)

class CustomBakeChannel(bpy.types.PropertyGroup):
    name: props.StringProperty(name='Name', description='Custom Channel Name', default="Custom Channel")
    
    # --- 动态格式设置 ---
    # 静态列表可以用 default string
    save_format: props.EnumProperty(items=basic_format, name='Format', description='Format Used For Saving Image', default="PNG")
    
    # 动态列表不能用 string default。
    # color_depth 列表第一项是 8 Bits，所以默认就是 8 Bits
    color_depth: props.EnumProperty(items=get_valid_depths, name='Color Depth', description='Color Depth')
    
    # color_mode 列表第一项是 RGBA，所以默认就是 RGBA
    color_mode: props.EnumProperty(items=get_valid_modes, name='Color Mode', description='Color Mode')
    
    color_space: props.EnumProperty(items=color_space, name='Color Space', description='Color Space')
    quality: props.IntProperty(name='Quality', description='Quality Of Saved Image', default=85, min=0, max=100)
    exr_code: props.EnumProperty(items=exr_code, name='EXR Compression', description='EXR Compression Method', default='ZIP')
    tiff_codec: props.EnumProperty(items=tiff_codec, name='TIFF Compression', description='TIFF Compression Method', default='DEFLATE')

    # --- 动态通道源 ---
    # 所有 *_source 都使用动态 items，移除 default
    
    # Red
    r: props.FloatProperty(name='Red', description='Red value', default=0.0, min=0, max=1)
    r_usemap: props.BoolProperty(name='Use Map', default=False)
    r_source: props.EnumProperty(items=get_channel_source_items, name='Source', description='Map source for Red channel')
    r_invert: props.BoolProperty(name='Invert', default=False)
    r_sepcol: props.BoolProperty(name='Separate', default=False)
    r_colchan: props.EnumProperty(items=custom_bake_channel_sep, name='Channel')

    # Green
    g: props.FloatProperty(name='Green', description='Green value', default=0.0, min=0, max=1)
    g_usemap: props.BoolProperty(name='Use Map', default=False)
    g_source: props.EnumProperty(items=get_channel_source_items, name='Source', description='Map source for Green channel')
    g_invert: props.BoolProperty(name='Invert', default=False)
    g_sepcol: props.BoolProperty(name='Separate', default=False)
    g_colchan: props.EnumProperty(items=custom_bake_channel_sep, name='Channel')

    # Blue
    b: props.FloatProperty(name='Blue', description='Blue value', default=0.0, min=0, max=1)
    b_usemap: props.BoolProperty(name='Use Map', default=False)
    b_source: props.EnumProperty(items=get_channel_source_items, name='Source', description='Map source for Blue channel')
    b_invert: props.BoolProperty(name='Invert', default=False)
    b_sepcol: props.BoolProperty(name='Separate', default=False)
    b_colchan: props.EnumProperty(items=custom_bake_channel_sep, name='Channel')

    # Alpha
    a: props.FloatProperty(name='Alpha', description='Alpha value', default=1.0, min=0, max=1)
    a_usemap: props.BoolProperty(name='Use Map', default=False)
    a_source: props.EnumProperty(items=get_channel_source_items, name='Source', description='Map source for Alpha channel')
    a_invert: props.BoolProperty(name='Invert', default=False)
    a_sepcol: props.BoolProperty(name='Separate', default=False)
    a_colchan: props.EnumProperty(items=custom_bake_channel_sep, name='Channel')

    # BW
    bw: props.BoolProperty(name='bw', default=False, description='Use only bw channel')
    bw_source: props.EnumProperty(items=get_channel_source_items, name='Source', description='Map source for BW channel')
    bw_invert: props.BoolProperty(name='Invert', default=False)
    bw_sepcol: props.BoolProperty(name='Separate', default=False)
    bw_colchan: props.EnumProperty(items=custom_bake_channel_sep, name='Channel')

    prefix: props.StringProperty(description='Prefix')
    suffix: props.StringProperty(description='Suffix')
    
class BakeJobSetting(bpy.types.PropertyGroup):
    debug_mode: bpy.props.BoolProperty(name="Debug Mode", description="Enable debug logging", default=False, update=update_debug_mode)
    save_and_quit: props.BoolProperty(description='Exit after baking', default=False, name='Save And Quit')
    bake_texture_apply: props.BoolProperty(description='Whether Apply Bake(Only In BSDF)', default=False, name='Apply Bake')
    
    bake_objects: props.CollectionProperty(type=BakeObject, name='Objects')
    active_object: props.PointerProperty(type=bpy.types.Object, name='Active')
    cage_object: props.PointerProperty(type=bpy.types.Object, name='Cage')
    
    res_x: props.IntProperty(name='X', default=1024, min=32, max=65536)
    res_y: props.IntProperty(name='Y', default=1024, min=32, max=65536)
    sample: props.IntProperty(name='Sampling', default=1, min=1, max=32)
    margin: props.IntProperty(name='Margin', default=8, min=0, max=64)
    device: props.EnumProperty(name='Device', items=device, default="GPU")
    
    # Bake Type update
    bake_type: props.EnumProperty(items=bake_type, name='Bake Type', default="BSDF", update=update_channels)
    
    bake_mode: props.EnumProperty(items=bake_mode, name='Bake Mode', default="SINGLE_OBJECT")
    special_bake_method: props.EnumProperty(items=special_bake, name='Special Settings', default="NO")
    
    multires_divide: props.IntProperty(name='Multiresolution Subdivision', default=0, min=0, max=32)
    extrusion: props.FloatProperty(name='Extrude', min=0, max=1)
    ray_distance: props.FloatProperty(name='Project Distance', min=0, max=1)
    
    atlas_pack_method: props.EnumProperty(items=atlas_pack, name='Packing Method', default="ISLAND")
    atlas_margin: props.FloatProperty(name='Margin', default=0.003, min=0, precision=3)
    
    bake_motion: props.BoolProperty(default=False, name='Animation Bake')
    bake_motion_use_custom: props.BoolProperty(default=False, name='Custom Frames')
    bake_motion_start: props.IntProperty(name='Start', default=1, min=0)
    bake_motion_last: props.IntProperty(name='Duration', default=250, min=1, max=10000)
    bake_motion_startindex: props.IntProperty(name='Start Index', default=0, min=0)
    bake_motion_digit: props.IntProperty(name='Frame Digits', default=4, min=1, max=8)
    
    float32: props.BoolProperty(default=False, name='32 Bit Precision')
    colorspace_setting: props.BoolProperty(default=False, name='Color Space')
    clearimage: props.BoolProperty(default=True, name='Clear Image')
    colorbase: props.FloatVectorProperty(name='Color Base', default=(0.0,0.0,0.0,0.0), step=3, precision=3, subtype='COLOR', size=4, min=0, max=1)
    use_alpha: props.BoolProperty(default=True, name='Use Alpha')
    
    save_out: props.BoolProperty(default=False, name='External Save')
    save_path: props.StringProperty(subtype='DIR_PATH', name='Save Path')
    use_fake_user: props.BoolProperty(default=True, name='Fake User')
    reload: props.BoolProperty(default=False, name='Reload Image')
    
    # --- 动态格式设置 (Dynamic Format Settings) ---
    save_format: props.EnumProperty(items=basic_format, name='Format', default="PNG")
    
    # 移除 default='...' 
    color_depth: props.EnumProperty(items=get_valid_depths, name='Color Depth')
    color_mode: props.EnumProperty(items=get_valid_modes, name='Color Mode')
    
    quality: props.IntProperty(name='Quality', default=85, min=0, max=100)
    exr_code: props.EnumProperty(items=exr_code, name='EXR Compression', default='ZIP')
    tiff_codec: props.EnumProperty(items=tiff_codec, name='TIFF Compression', default='DEFLATE')
    
    create_new_folder: props.BoolProperty(default=False, name='New Folder')
    new_folder_name_setting: props.EnumProperty(items=basic_name, name='New Folder Name', default="MAT")
    folder_name: props.StringProperty(name='Folder Custom Naming')
    name_setting: props.EnumProperty(items=basic_name, name='Base Name', default="MAT")
    custom_name: props.StringProperty(name='Custom Name')
    use_denoise: props.BoolProperty(default=False, name='Denoise')
    denoise_method: props.EnumProperty(items=denoise_method, name='Denoise Preprocessing', default="FAST")
    
    export_model: bpy.props.BoolProperty(name="Export Model", default=False)
    export_format: bpy.props.EnumProperty(name="Export Format",
        items=[('FBX', 'FBX', '', 1), ('GLB', 'GLB', '', 2), ('USD', 'USD', '', 3)], default='FBX')

    channels: props.CollectionProperty(type=BakeChannel)
    active_channel_index: props.IntProperty(name="Active Channel Index")
    active_object_index: props.IntProperty(name="Active Object Index", default=0)

    use_special_map: bpy.props.BoolProperty(default=False, name='Special Map', update=update_channels)
    
    use_custom_map: props.BoolProperty(default=False, name='Use Custom Map')
    custom_file_path: props.StringProperty(subtype='DIR_PATH', name='Save Path')
    custom_new_folder: props.BoolProperty(default=False, name='New Folder')
    custom_folder_name_setting: props.EnumProperty(items=basic_name, name='Folder Name Setting', default="MAT")
    custom_folder_name: props.StringProperty(name='Name')
    
class BakeJob(bpy.types.PropertyGroup):
    name: props.StringProperty(name="Job Name", default="New Job")
    setting: props.PointerProperty(type=BakeJobSetting)
    Custombakechannels: props.CollectionProperty(type=CustomBakeChannel)
    Custombakechannels_index: props.IntProperty(name='Index', default=0, min=0)
    
class BakeJobs(bpy.types.PropertyGroup):
    # Node baking
    node_bake_res_x: props.IntProperty(name='X', default=1024, min=32)
    node_bake_res_y: props.IntProperty(name='Y', default=1024, min=32)
    node_bake_sample: props.IntProperty(name='Sample', default=1, min=1)
    node_bake_margin: props.IntProperty(name='Margin', default=4, min=0)
    node_bake_float32: props.BoolProperty(default=False, name='32 Bit Precision')
    node_bake_socket_index: props.IntProperty(name='Output Socket', default=0, min=0, max=10)
    node_bake_save_outside: props.BoolProperty(default=False, name='Save External')
    node_bake_save_path: props.StringProperty(subtype='DIR_PATH', name='Path')
    
    node_bake_save_format: props.EnumProperty(items=basic_format, name='Format', default="PNG")
    # 动态属性：移除 default
    node_bake_color_depth: props.EnumProperty(items=get_valid_depths, name='Color Depth')
    node_bake_color_mode: props.EnumProperty(items=get_valid_modes, name='Color Mode')
    
    node_bake_color_space: props.EnumProperty(items=color_space, name='Color Space', default='SRGB')
    node_bake_quality: props.IntProperty(name='Quality', default=100, min=0, max=100)
    node_bake_exr_code: props.EnumProperty(items=exr_code, name='Compression', default='ZIP')
    node_bake_tiff_codec: props.EnumProperty(items=tiff_codec, name='TIFF Compression', default='DEFLATE')
    node_bake_reload: props.BoolProperty(default=False, name='Reload Image')
    node_bake_delete_node: props.BoolProperty(default=False, name='Delect Node')
    node_bake_auto_find_socket: props.BoolProperty(default=False, name='Auto Socket')
    
    # Object baking results
    bake_result_save_path: props.StringProperty(subtype='DIR_PATH', name='Path')
    bake_result_save_format: props.EnumProperty(items=basic_format, name='Format', default="PNG")
    # 动态属性：移除 default
    bake_result_color_depth: props.EnumProperty(items=get_valid_depths, name='Color Depth')
    bake_result_color_mode: props.EnumProperty(items=get_valid_modes, name='Color Mode')
    
    bake_result_color_space: props.EnumProperty(items=color_space2, name='Color Space', default='DEFAULT')
    bake_result_quality: props.IntProperty(name='Quality', default=100, min=0, max=100)
    bake_result_exr_code: props.EnumProperty(items=exr_code, name='Compression', default='ZIP')
    bake_result_tiff_codec: props.EnumProperty(items=tiff_codec, name='TIFF Compression', default='DEFLATE')
    bake_result_use_denoise: props.BoolProperty(default=False, name='Denoise')
    bake_result_denoise_method: props.EnumProperty(items=denoise_method, name='Denoise Method', default="FAST")
    
    open_inputs: props.BoolProperty(default=False, name='Input Settings')
    open_channels: props.BoolProperty(default=False, name='Channel Settings')
    open_saves: props.BoolProperty(default=False, name='Save Settings')
    open_other: props.BoolProperty(default=False, name='Other Settings')
    copy_job: props.BoolProperty(default=False, name='Copy Job')
    
    jobs: props.CollectionProperty(type=BakeJob)
    job_index: props.IntProperty(name='Job index', default=0, min=0)
    
class BakedImageResult(bpy.types.PropertyGroup):
    image: props.PointerProperty(type=bpy.types.Image, name="Image")
    color_depth: props.StringProperty(name="Color Depth", default="")
    color_space: props.StringProperty(name="Color Space", default="")
    filepath: props.StringProperty(name="Filepath", default="")
    object_name: props.StringProperty(name="Object Name", default="")
    channel_type: props.StringProperty(name="Channel Type", default="")
