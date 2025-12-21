import bpy
from bpy import props
from .constants import *
from .utils import logger
import logging

def update_debug_mode(self, context):
    """
    根据 debug_mode 更新日志级别。
    注意：self 在这里指的是 BakeJobSetting 的实例
    """
    if self.debug_mode:
        logger.setLevel(logging.DEBUG)
        logger.info("Debug mode enabled: Logging level set to DEBUG")
    else:
        logger.setLevel(logging.INFO)
        logger.info("Debug mode disabled: Logging level set to INFO")

class BakeObject(bpy.types.PropertyGroup):
    bakeobject:props.PointerProperty(name="object", type=bpy.types.Object)
    
class BakeChannel(bpy.types.PropertyGroup):
    """A PropertyGroup to hold all settings for a single, generic bake channel."""
    # --- Identification ---
    name: props.StringProperty(name="Channel Name", description="UI display name for the channel")
    id: props.StringProperty(name="Channel ID", description="Internal ID used for logic")
    
    # --- Common Settings ---
    enabled: props.BoolProperty(name="Enabled", description="Enable this channel for baking", default=False)
    prefix: props.StringProperty(name="Prefix", description="Filename prefix")
    suffix: props.StringProperty(name="Suffix", description="Filename suffix")
    custom_cs: props.EnumProperty(items=color_space, name="Color Space", description="Color space for the baked image")
    
    # --- Channel-Specific Settings (a union of all possible specific settings) ---
    
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
    
    # MESH specific (e.g., Bevel, AO)
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
    save_format:props.EnumProperty(items=basic_format, name='Format', description='Format Used For Saving Image',default="PNG")
    color_depth:props.EnumProperty(items=color_depth, name='Color Depth', description='Color Depth')
    color_mode:props.EnumProperty(items=color_mode, name='Color Mode', description='Color Mode')
    color_space:props.EnumProperty(items=color_space, name='Color Space', description='Color Space')
    quality:props.IntProperty(name='Quality', description='Quality Of Saved Image',default=85,min=0,max=100)
    exr_code:props.EnumProperty(items=exr_code,name='EXR Compression', description='EXR Compression Method',default='ZIP')
    tiff_codec:props.EnumProperty(items=tiff_codec,name='TIFF Compression', description='TIFF Compression Method',default='DEFLATE')
    #RGB通道的基本属性//Basic properties of RGB channels
    r:props.FloatProperty(name='Red', description='Red value for the channel', default=0.0, min=0, max=1)
    g:props.FloatProperty(name='Green', description='Green value for the channel', default=0.0, min=0, max=1)
    b:props.FloatProperty(name='Blue', description='Blue value for the channel', default=0.0, min=0, max=1)
    a:props.FloatProperty(name='Alpha', description='Alpha value for the channel', default=1.0, min=0, max=1)
    r_usemap:props.BoolProperty(name='r usemap',default=False, description='Wheather use map in Red channel')
    r_map_BSDF3:props.EnumProperty(items=basic_channel_BSDF_3, name='', description='Map for the Red channel for the custom channel')
    r_map_BSDF4:props.EnumProperty(items=basic_channel_BSDF_4, name='', description='Map for the Red channel for the custom channel')
    r_map_basic:props.EnumProperty(items=basic_channel_basic_c, name='', description='Map for the Red channel for the custom channel')
    r_invert:props.BoolProperty(name='r invert',default=False, description='Invert Red channel map')
    r_sepcol:props.BoolProperty(name='r sepcol',default=False, description='Red channel seperate color(for color map)')
    r_colchan:props.EnumProperty(items=custom_bake_channel_sep, name='', description='Red channel seperate specificl color(for color map)')
    g_usemap:props.BoolProperty(name='g usemap',default=False, description='Wheather use map in Green channel')
    g_map_BSDF3:props.EnumProperty(items=basic_channel_BSDF_3, name='', description='Map for the Green channel for the custom channel')
    g_map_BSDF4:props.EnumProperty(items=basic_channel_BSDF_4, name='', description='Map for the Green channel for the custom channel')
    g_map_basic:props.EnumProperty(items=basic_channel_basic_c, name='', description='Map for the Green channel for the custom channel')
    g_invert:props.BoolProperty(name='g invert',default=False, description='Invert Green channel map')
    g_sepcol:props.BoolProperty(name='g sepcol',default=False, description='Green channel seperate color(for color map)')
    g_colchan:props.EnumProperty(items=custom_bake_channel_sep, name='', description='Green channel seperate specificl color(for color map)')
    b_usemap:props.BoolProperty(name='b usemap',default=False, description='Wheather use map in Blue channel')
    b_map_BSDF3:props.EnumProperty(items=basic_channel_BSDF_3, name='', description='Map for the Blue channel for the custom channel')
    b_map_BSDF4:props.EnumProperty(items=basic_channel_BSDF_4, name='', description='Map for the Blue channel for the custom channel')
    b_map_basic:props.EnumProperty(items=basic_channel_basic_c, name='', description='Map for the Blue channel for the custom channel')
    b_invert:props.BoolProperty(name='b usemap',default=False, description='Invert Blue channel map')
    b_sepcol:props.BoolProperty(name='b sepcol',default=False, description='Blue channel seperate color(for color map)')
    b_colchan:props.EnumProperty(items=custom_bake_channel_sep, name='', description='Blue channel seperate specificl color(for color map)')
    a_usemap:props.BoolProperty(name='a usemap',default=False, description='Wheather use map in alpha channel')
    a_map_BSDF3:props.EnumProperty(items=basic_channel_BSDF_3, name='', description='Map for the alpha channel for the custom channel')
    a_map_BSDF4:props.EnumProperty(items=basic_channel_BSDF_4, name='', description='Map for the alpha channel for the custom channel')
    a_map_basic:props.EnumProperty(items=basic_channel_basic_c, name='', description='Map for the alpha channel for the custom channel')
    a_invert:props.BoolProperty(name='a invert',default=False, description='Invert Alpha channel map')
    a_sepcol:props.BoolProperty(name='a sepcol',default=False, description='alpha channel seperate color(for color map)')
    a_colchan:props.EnumProperty(items=custom_bake_channel_sep, name='', description='alpha channel seperate specificl color(for color map)')
    #黑白通道的基本属性//Basic properties of black-and-white channels
    bw:props.BoolProperty(name='bw',default=False, description='Use only bw channel')
    bw_map_BSDF3:props.EnumProperty(items=basic_channel_BSDF_3, name='', description='Map for the black-white channel for the custom channel')
    bw_map_BSDF4:props.EnumProperty(items=basic_channel_BSDF_4, name='', description='Map for the black-white channel for the custom channel')
    bw_map_basic:props.EnumProperty(items=basic_channel_basic_c, name='', description='Map for the black-white channel for the custom channel')
    bw_invert:props.BoolProperty(name='a invert',default=False, description='Invert BW channel map')
    bw_sepcol:props.BoolProperty(name='bw sepcol',default=False, description='BW channel seperate color(for color map)')
    bw_colchan:props.EnumProperty(items=custom_bake_channel_sep, name='', description='BW channel seperate specificl color(for color map)')
    #前后缀属性//Prefix or Suffix
    prefix:props.StringProperty(description='Prefix')
    suffix:props.StringProperty(description='Suffix')
    # Added name property for UI list display
    name:props.StringProperty(name='Name', description='Custom Channel Name', default="Custom Channel")
    
def update_channels(self, context):
    """When bake settings change, reset and populate the channels collection."""
    # This operator will be defined in ops.py
    bpy.ops.bake.reset_channels('EXEC_DEFAULT')

class BakeJobSetting(bpy.types.PropertyGroup):
    #调试时使用//DEBUG
    debug_mode: bpy.props.BoolProperty(name="Debug Mode",description="Enable debug logging and display detailed information in the UI",default=False,update=lambda self, context: update_debug_mode(self, context))
    #其他//Other settings
    save_and_quit:props.BoolProperty(description='Exit after baking',default=False,name='Save And Quit')
    bake_texture_apply:props.BoolProperty(description='Whether Apply Bake(Only In BSDF)',default=False,name='Apply Bake')
    #物体设置//Object settings
    bake_objects:props.CollectionProperty(type=BakeObject, name='Objects', description='Baking Objects')
    active_object:props.PointerProperty(type=bpy.types.Object, name='Active', description='Active Object')
    cage_object:props.PointerProperty(type=bpy.types.Object, name='Cage', description='Cage For Active Bake')
    #烘焙的基础设定//Basic bake settings
    res_x:props.IntProperty(name='X', description='Bake Map X Resolution', default=1024, min=32,max=65536)
    res_y:props.IntProperty(name='Y', description='Bake Map Y Resolution', default=1024, min=32,max=65536)
    sample:props.IntProperty(name='Sampling', description='Bake Map Sample Count', default=1, min=1,max=32)
    margin:props.IntProperty(name='Margin', description='Bake Map Margin', default=8, min=0, max=64)
    device:props.EnumProperty(name='Device',items=device, description='Use Gpu or Cpu For Bake', default="GPU")
    bake_type:props.EnumProperty(items=bake_type,description='How To Use Bake (Suggest Bsdf If Direct Output Using Bsdf)',name='Bake Type',default="BSDF", update=update_channels)
    bake_mode:props.EnumProperty(items=bake_mode,description='Bake Mode In Use',name='Bake Mode',default="SINGLE_OBJECT")
    special_bake_method:props.EnumProperty(items=special_bake,description='Special Settings (Due To Mutual Exclusion, Written As An Enum Property)',name='Special Settings',default="NO")
    #多级精度烘焙的设定//Settings for multi-resolution baking
    multires_divide:props.IntProperty(name='Multiresolution Subdivision', description='Multiresolution Subdivision Original Data', default=0, min=0,max=32)
    #活动项烘焙的设定//Settings for active item baking
    extrusion:props.FloatProperty(name='Extrude', description='Cage Extrude Distance',min=0,max=1)
    ray_distance:props.FloatProperty(name='Project Distance',description='Distance For Light Project',min=0,max=1)
    #这些是为 Atlas 烘焙准备的//These are for Atlas baking
    atlas_pack_method:props.EnumProperty(items=atlas_pack,description='Method Used For Packing Maps',name='Packing Method',default="ISLAND")
    atlas_margin:props.FloatProperty(description='Packing Margin For Maps',name='Margin',default=0.003,min=0,precision=3)
    #这些是为动画烘焙准备的//These are for animation baking
    bake_motion:props.BoolProperty(description='Whether To Use Animation Bake',default=False,name='Animation Bake')
    bake_motion_use_custom:props.BoolProperty(description='Whether To Use Custom Frame Range',default=False,name='Custom Frames')
    bake_motion_start:props.IntProperty(name='Start', description='Bake Start Frame', default=1, min=0)
    bake_motion_last:props.IntProperty(name='Duration', description='Bake Duration Frames', default=250, min=1,max=10000)
    bake_motion_startindex:props.IntProperty(name='Start Index', description='Start Frame Index', default=0, min=0)
    bake_motion_digit:props.IntProperty(name='Frame Digits', description='Frame Digit Number', default=4, min=1,max=8)
    #这些是为输入准备的//These are for input use
    float32:props.BoolProperty(description='Whether To Use 32 Bit Precision Quality',default=False,name='32 Bit Precision')
    colorspace_setting:props.BoolProperty(description='Custom Color Space',default=False,name='Color Space')
    clearimage:props.BoolProperty(description='Clear Images Before Bake',default=True,name='Clear Image')
    colorbase:props.FloatVectorProperty(name='Color Base', description='Color Base', default=(0.0,0.0,0.0,0.0), step=3, precision=3, subtype='COLOR', size=4,min=0,max=1)
    use_alpha:props.BoolProperty(description='Use Alpha Channels',default=True,name='Use Alpha')
    #这些是为保存准备的//These are for saving
    save_out:props.BoolProperty(description='Whether To Save External File',default=False,name='External Save')
    save_path:props.StringProperty(description='Save Path For Baked Files',subtype='DIR_PATH',name='Save Path')
    use_fake_user:props.BoolProperty(description='Whether To Use Fake Users',default=True,name='Fake User')
    reload:props.BoolProperty(description='Reload Baked Images As Saved External Images',default=False,name='Reload Image')
    save_format:props.EnumProperty(items=basic_format,description='Format Used For Saving Image',name='Format',default="PNG")
    color_depth:props.EnumProperty(items=color_depth, name='Color Depth', description='Color Depth')
    quality:props.IntProperty(name='Quality', description='Quality Of Saved Image',default=85,min=0,max=100)
    exr_code:props.EnumProperty(items=exr_code,name='EXR Compression', description='EXR Compression Method',default='ZIP')
    tiff_codec:props.EnumProperty(items=tiff_codec,name='TIFF Compression', description='TIFF Compression Method',default='DEFLATE')
    create_new_folder:props.BoolProperty(description='Whether To Create New Folder',default=False,name='New Folder')
    new_folder_name_setting:props.EnumProperty(items=basic_name,description='How To Naming New Folder Filename',name='New Folder Name',default="MAT")
    folder_name:props.StringProperty(description='New Folder Custom Name',name='Folder Custom Naming')
    name_setting:props.EnumProperty(items=basic_name,description='How To Use Base Naming',name='Base Name',default="MAT")
    custom_name:props.StringProperty(description='Custom Name',name='Custom Name')
    use_denoise:props.BoolProperty(description='Image Denoising',default=False,name='Denoise')
    denoise_method:props.EnumProperty(items=denoise_method,description='Preprocessing Method Used For Denoising',name='Denoise Preprocessing',default="FAST")
    #这些是为导出模型准备的//These are for export model
    export_model: bpy.props.BoolProperty(name="Export Model",description="Export the baked model after applying textures",default=False)
    export_format: bpy.props.EnumProperty(name="Export Format",description="Format to export the baked model",
        items=[('FBX', 'FBX', 'Export as FBX format', 1),
            ('GLB', 'GLB', 'Export as GLB format', 2),
            ('USD', 'USD', 'Export as USD format', 3)],
        default='FBX')

    # DYNAMIC CHANNELS
    channels: props.CollectionProperty(type=BakeChannel)
    active_channel_index: props.IntProperty(name="Active Channel Index")

    active_object_index: props.IntProperty(name="Active Object Index", default=0)

    #特殊的通道设定
    use_special_map:bpy.props.BoolProperty(description='',default=False,name='Special Map', update=update_channels)
    
    #这些是为自定义通道的设定（具体设定在每个通道中特定）//These are settings for custom channels (specific settings are defined in each channel)
    use_custom_map:props.BoolProperty(description='Whether Use Custom Map',default=False,name='Use Custom Map')
    custom_file_path:props.StringProperty(description='Where Save Custom Map',subtype='DIR_PATH',name='Save Path')
    custom_new_folder:props.BoolProperty(description='Whether Create New Folder',default=False,name='New Folder')
    custom_folder_name_setting:props.EnumProperty(items=basic_name,description='Custom Folder Name Method',name='Folder Name Setting',default="MAT")
    custom_folder_name:props.StringProperty(description='Custom Map Custom Name',name='Name')
    
class BakeJob(bpy.types.PropertyGroup):
    name: props.StringProperty(name="Job Name", default="New Job")
    setting:props.PointerProperty(type=BakeJobSetting)
    Custombakechannels:props.CollectionProperty(type=CustomBakeChannel)
    Custombakechannels_index:props.IntProperty(name='Index', description='Custom channel Index',default=0,min=0)
    
class BakeJobs(bpy.types.PropertyGroup):
    #节点烘焙//Node baking
    node_bake_res_x:props.IntProperty(name='X', description='X Resolution', default=1024, min=32)
    node_bake_res_y:props.IntProperty(name='Y', description='Y Resolution', default=1024, min=32)
    node_bake_sample:props.IntProperty(name='Sample', description='Sample', default=1, min=1)
    node_bake_margin:props.IntProperty(name='Margin', description='Margin', default=4, min=0)
    node_bake_float32:props.BoolProperty(description='Whether To Use 32 Bit Precision Quality',default=False,name='32 Bit Precision')
    node_bake_socket_index:props.IntProperty(name='Output Socket', description='Output Socket Index', default=0, min=0,max=10)
    node_bake_save_outside:props.BoolProperty(description='Save External',default=False,name='Save External')
    node_bake_save_path:props.StringProperty(description='Save Path',subtype='DIR_PATH',name='Path')
    node_bake_save_format:props.EnumProperty(items=basic_format, name='Format', description='Save Format')
    node_bake_color_depth:props.EnumProperty(items=color_depth, name='Color Depth', description='Color Depth')
    node_bake_color_mode:props.EnumProperty(items=color_mode, name='Color Mode', description='Color Mode')
    node_bake_color_space:props.EnumProperty(items=color_space, name='Color Space', description='Color Space',default='SRGB')
    node_bake_quality:props.IntProperty(name='Quality', description='Save Quality',default=100,min=0,max=100)
    node_bake_exr_code:props.EnumProperty(items=exr_code,name='Compression', description='EXR Compression',default='ZIP')
    node_bake_tiff_codec:props.EnumProperty(items=tiff_codec,name='TIFF Compression', description='TIFF Compression Method',default='DEFLATE')
    node_bake_reload:props.BoolProperty(description='Whether Reload Image',default=False,name='Reload Image')
    node_bake_delete_node:props.BoolProperty(description='Delect Image Node After Baking',default=False,name='Delect Node')
    node_bake_auto_find_socket:props.BoolProperty(description='Auto Find Output Socket',default=False,name='Auto Socket')
    #物体烘焙，保存//Object baking and saving
    bake_result_save_path:props.StringProperty(description='Map Save Path',subtype='DIR_PATH',name='Path')
    bake_result_save_format:props.EnumProperty(items=basic_format, name='Format', description='Save Format')
    bake_result_color_depth:props.EnumProperty(items=color_depth, name='Color Depth', description='Color Depth')
    bake_result_color_mode:props.EnumProperty(items=color_mode, name='Color Mode', description='Color Mode')
    bake_result_color_space:props.EnumProperty(items=color_space2, name='Color Space', description='Color Space',default='DEFAULT')
    bake_result_quality:props.IntProperty(name='Quality', description='Save Quality)',default=100,min=0,max=100)
    bake_result_exr_code:props.EnumProperty(items=exr_code,name='Compression', description='EXR Compression',default='ZIP')
    bake_result_tiff_codec:props.EnumProperty(items=tiff_codec,name='TIFF Compression', description='TIFF Compression Method',default='DEFLATE')
    bake_result_use_denoise:props.BoolProperty(description='Image Denoise',default=False,name='Denoise')
    bake_result_denoise_method:props.EnumProperty(items=denoise_method,description='Denoise Method',name='Denoise Method',default="FAST")
    #展开设定//Expand settings
    open_inputs:props.BoolProperty(description='Expand Input Settings',default=False,name='Input Settings')
    open_channels:props.BoolProperty(description='Expand Channel Settings',default=False,name='Channel Settings')
    open_saves:props.BoolProperty(description='Expand Save Settings',default=False,name='Save Settings')
    open_other:props.BoolProperty(description='Expand Other Settings',default=False,name='Other Settings')
    copy_job:props.BoolProperty(description='Copy Current Job',default=False,name='Copy Job')
    #工作设定//Jobs settings
    jobs:props.CollectionProperty(type=BakeJob)
    job_index:props.IntProperty(name='Job index', description='Index of index',default=0,min=0)
    
# 定义单个烘焙结果的属性类
class BakedImageResult(bpy.types.PropertyGroup):
    image: props.PointerProperty(
        type=bpy.types.Image,
        name="Image",
        description="The baked image data block"
    )
    color_depth: props.StringProperty(
        name="Color Depth",
        description="Color depth of the baked image (e.g., '8', '16', '32')",
        default=""
    )
    color_space: props.StringProperty(
        name="Color Space",
        description="Color space of the baked image (e.g., 'sRGB', 'Non-Color')",
        default=""
    )
    filepath: props.StringProperty(
        name="Filepath",
        description="Absolute filepath if the image is saved externally",
        default=""
    )
    object_name: props.StringProperty(
        name="Object Name",
        description="Name of the object this image was baked from",
        default=""
    )
    channel_type: props.StringProperty(
        name="Channel Type",
        description="Type of the baked channel (e.g., 'NORMAL', 'COLOR')",
        default=""
    )
