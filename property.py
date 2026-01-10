import bpy
from bpy import props
from .constants import *
from .utils import logger, reset_channels_logic
import logging

def get_channel_source_items(self, context):
    fallback = [('NONE', 'None', 'No enabled channels available')]
    if context is None: return fallback
    try:
        scene = context.scene
        if not hasattr(scene, "BakeJobs") or not scene.BakeJobs: return fallback
        idx = scene.BakeJobs.job_index
        if idx < 0 or idx >= len(scene.BakeJobs.jobs): return fallback
        job = scene.BakeJobs.jobs[idx]
        setting = job.setting
        items = []
        for channel in setting.channels:
            if channel.enabled:
                items.append((channel.id, channel.name, f"Use {channel.name} result as source"))
        if not items: return fallback
        return items
    except Exception as e:
        logger.warning(f"Error getting channel sources: {e}")
        return fallback

def get_valid_depths(self, context):
    fmt = getattr(self, "save_format", "PNG")
    if fmt not in FORMAT_SETTINGS: return COLOR_DEPTHS
    valid_depths_keys = FORMAT_SETTINGS[fmt].get("depths", [])
    if not valid_depths_keys: return COLOR_DEPTHS
    return [item for item in COLOR_DEPTHS if item[0] in valid_depths_keys]

def get_valid_modes(self, context):
    fmt = getattr(self, "save_format", "PNG")
    if fmt not in FORMAT_SETTINGS: return COLOR_MODES
    valid_modes = FORMAT_SETTINGS[fmt].get("modes", [])
    if not valid_modes: return COLOR_MODES
    return [item for item in COLOR_MODES if item[0] in valid_modes]

def update_debug_mode(self, context):
    logger.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)

def update_channels(self, context):
    # 重构：直接调用逻辑函数，避免在 Update 中调用 Operator 的风险
    # Refactor: Directly call logic function to avoid Operator risk in Update
    reset_channels_logic(self)

    if self.bake_type == 'BSDF' and self.bake_mode == 'SELECT_ACTIVE':
        self.bake_mode = 'SINGLE_OBJECT'

def get_bake_mode_items(self, context):
    items = []
    for item in BAKE_MODES:
        if self.bake_type == 'BSDF' and item[0] == 'SELECT_ACTIVE': continue
        items.append(item)
    return items

class BakeObject(bpy.types.PropertyGroup):
    bakeobject: props.PointerProperty(name="object", type=bpy.types.Object)
    udim_tile: props.IntProperty(name="UDIM Tile", default=1001, min=1001, max=1099, description="Target UDIM Tile for this object")
    
    # UDIM Resolution Settings
    override_size: props.BoolProperty(name="Override Size", default=False, description="Use custom resolution for this tile instead of global bake resolution")
    udim_width: props.IntProperty(name="Width", default=1024, min=1)
    udim_height: props.IntProperty(name="Height", default=1024, min=1)

class BakeChannelSource(bpy.types.PropertyGroup):
    use_map: props.BoolProperty(name='Use Map', default=False)
    source: props.EnumProperty(items=get_channel_source_items, name='Source')
    invert: props.BoolProperty(name='Invert', default=False)
    sep_col: props.BoolProperty(name='Separate', default=False)
    col_chan: props.EnumProperty(items=CUSTOM_CHANNEL_SEP, name='Channel')

class BakeChannel(bpy.types.PropertyGroup):
    name: props.StringProperty(name="Channel Name")
    id: props.StringProperty(name="Channel ID")
    enabled: props.BoolProperty(name="Enabled", default=False)
    prefix: props.StringProperty(name="Prefix")
    suffix: props.StringProperty(name="Suffix")
    
    override_defaults: props.BoolProperty(name="Override Color Settings", default=False)
    custom_cs: props.EnumProperty(items=COLOR_SPACES, name="Color Space", default='SRGB')
    custom_mode: props.EnumProperty(items=COLOR_MODES, name="Color Mode", default='RGB')
    
    rough_inv: props.BoolProperty(name="Invert")
    
    normal_type: props.EnumProperty(items=NORMAL_TYPES, name="Normal Mode", default='OPENGL')
    normal_X: props.EnumProperty(items=NORMAL_CHANNELS, name="X", default='POS_X')
    normal_Y: props.EnumProperty(items=NORMAL_CHANNELS, name="Y", default='POS_Y')
    normal_Z: props.EnumProperty(items=NORMAL_CHANNELS, name="Z", default='POS_Z')
    normal_obj: props.BoolProperty(name="Object Space")
    
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
    
    bevel_sample: props.IntProperty(name='Samples', default=8, min=2, max=16)
    bevel_rad: props.FloatProperty(name='Radius', default=0.1)
    
    ao_inside: props.BoolProperty(name='Inside', default=False)
    ao_local: props.BoolProperty(name='Only Local', default=False)
    ao_dis: props.FloatProperty(name='Distance', default=1)
    ao_sample: props.IntProperty(name='Samples', default=16)
    
    wireframe_use_pix: props.BoolProperty(name='Use Pixel Size', default=False)
    wireframe_dis: props.FloatProperty(name='Thickness', default=0.01)
    
    bevnor_sample: props.IntProperty(name='Samples', default=8)
    bevnor_rad: props.FloatProperty(name='Radius', default=0.1)
    
    curvature_sample: props.IntProperty(name='Samples', default=6)
    curvature_rad: props.FloatProperty(name='Radius', default=0.05)
    curvature_contrast: props.FloatProperty(name='Contrast', default=1.0)
    
    position_invg: props.BoolProperty(name='Invert G', default=True)
    slope_directions: props.EnumProperty(items=DIRECTIONS, name='Direction', default="Z")
    slope_invert: props.BoolProperty(name='Invert', default=False)
    
    thickness_distance: props.FloatProperty(name='Distance', default=0.5)
    thickness_contrast: props.FloatProperty(name='Contrast', default=0.5)
    
    ID_num: props.IntProperty(name='ID Map Count', default=5)
    
    # PBR Conversion Settings
    pbr_conv_threshold: props.FloatProperty(name='Dielectric Specular', default=0.04, min=0.0, max=1.0, description="Threshold for separating Dielectric from Metallic (F0)")

    # Node Group Settings
    node_group: props.StringProperty(name="Node Group", description="Name of the Shader Node Group to use as bake source")
    node_group_output: props.StringProperty(name="Output Socket", default="", description="Name of the output socket to bake. Leave empty for first output.")

class CustomBakeChannel(bpy.types.PropertyGroup):
    name: props.StringProperty(name='Name', default="Custom Channel")
    color_space: props.EnumProperty(items=COLOR_SPACES, name='Color Space', default='NONCOL')
    
    r: props.FloatProperty(name='Red', default=0.0, min=0, max=1)
    g: props.FloatProperty(name='Green', default=0.0, min=0, max=1)
    b: props.FloatProperty(name='Blue', default=0.0, min=0, max=1)
    a: props.FloatProperty(name='Alpha', default=1.0, min=0, max=1)
    bw: props.BoolProperty(name='bw', default=False)
    
    r_settings: props.PointerProperty(type=BakeChannelSource)
    g_settings: props.PointerProperty(type=BakeChannelSource)
    b_settings: props.PointerProperty(type=BakeChannelSource)
    a_settings: props.PointerProperty(type=BakeChannelSource)
    bw_settings: props.PointerProperty(type=BakeChannelSource)
    
    prefix: props.StringProperty(name='Prefix')
    suffix: props.StringProperty(name='Suffix')
    
class BakeJobSetting(bpy.types.PropertyGroup):
    save_and_quit: props.BoolProperty(default=False, name='Save And Quit')
    bake_texture_apply: props.BoolProperty(default=False, name='Apply Bake')
    
    bake_objects: props.CollectionProperty(type=BakeObject, name='Objects')
    active_object: props.PointerProperty(type=bpy.types.Object, name='Active')
    cage_object: props.PointerProperty(type=bpy.types.Object, name='Cage')
    
    res_x: props.IntProperty(name='X', default=1024, min=32)
    res_y: props.IntProperty(name='Y', default=1024, min=32)
    sample: props.IntProperty(name='Sampling', default=1, min=1)
    margin: props.IntProperty(name='Margin', default=8, min=0)
    device: props.EnumProperty(name='Device', items=DEVICES, default="GPU") 
    
    bake_type: props.EnumProperty(items=BAKE_TYPES, name='Bake Type', default="BSDF", update=update_channels)
    bake_mode: props.EnumProperty(items=get_bake_mode_items, name='Bake Mode')
    
    extrusion: props.FloatProperty(name='Extrude', min=0)
    
    atlas_pack_method: props.EnumProperty(items=ATLAS_PACK_METHODS, name='Packing', default="ISLAND") 
    atlas_margin: props.FloatProperty(name='Margin', default=0.003, precision=3) 
    
    bake_motion: props.BoolProperty(default=False, name='Animation')
    bake_motion_use_custom: props.BoolProperty(default=False, name='Custom Frames')
    bake_motion_start: props.IntProperty(name='Start', default=1)
    bake_motion_last: props.IntProperty(name='Duration', default=250)
    bake_motion_startindex: props.IntProperty(name='Start Index', default=0)
    bake_motion_digit: props.IntProperty(name='Frame Digits', default=4)
    bake_motion_separator: props.StringProperty(name='Separator', default='_')
    
    float32: props.BoolProperty(default=False, name='32 Bit')
    clearimage: props.BoolProperty(default=True, name='Clear')
    colorbase: props.FloatVectorProperty(name='Color Base', default=(0,0,0,0), subtype='COLOR', size=4)
    use_alpha: props.BoolProperty(default=True, name='Use Alpha')
    
    save_out: props.BoolProperty(default=False, name='External Save')
    save_path: props.StringProperty(subtype='DIR_PATH', name='Save Path')
    
    save_format: props.EnumProperty(items=BASIC_FORMATS, name='Format', default="PNG")
    color_depth: props.EnumProperty(items=get_valid_depths, name='Color Depth')
    
    color_mode: props.EnumProperty(items=get_valid_modes, name='Color Mode')
    
    quality: props.IntProperty(name='Quality', default=85)
    exr_code: props.EnumProperty(items=EXR_CODECS, name='EXR Codec', default='ZIP')
    tiff_codec: props.EnumProperty(items=TIFF_CODECS, name='TIFF Codec', default='DEFLATE')
    
    create_new_folder: props.BoolProperty(default=False, name='New Folder')
    new_folder_name_setting: props.EnumProperty(items=NAMING_MODES, name='Folder Naming', default="MAT") 
    folder_name: props.StringProperty(name='Custom Folder Name') 
    name_setting: props.EnumProperty(items=NAMING_MODES, name='Base Name', default="MAT")
    custom_name: props.StringProperty(name='Custom Name')
    
    use_denoise: props.BoolProperty(default=False, name='Denoise') 
    denoise_method: props.EnumProperty(items=DENOISE_METHODS, name='Denoise Method', default="FAST") 
    
    export_model: bpy.props.BoolProperty(name="Export Model", default=False)
    export_format: bpy.props.EnumProperty(items=[('FBX','FBX','',1),('GLB','GLB','',2),('USD','USD','',3)], default='FBX')
    
    channels: props.CollectionProperty(type=BakeChannel)
    active_channel_index: props.IntProperty(name="Active Channel Index")
    active_object_index: props.IntProperty(name="Active Object Index", default=0)
    
    use_light_map: bpy.props.BoolProperty(default=False, name='Light Maps', update=update_channels)
    use_mesh_map: bpy.props.BoolProperty(default=False, name='Mesh Maps', update=update_channels)
    use_extension_map: bpy.props.BoolProperty(default=False, name='Extension Maps', update=update_channels)
    
    use_custom_map: props.BoolProperty(default=False, name='Use Custom Map')

    # --- Smart UV Settings ---
    use_auto_uv: props.BoolProperty(name="Auto Smart UV", default=False, description="Automatically create and unwrap a new UV map for baking")
    auto_uv_name: props.StringProperty(name="UV Name", default="Smart_UV")
    auto_uv_angle: props.FloatProperty(name="Angle Limit", default=66.0, min=1.0, max=89.0, subtype='ANGLE')
    auto_uv_margin: props.FloatProperty(name="Island Margin", default=0.001, min=0.0, max=1.0, precision=4)
    auto_uv_keep_active: props.BoolProperty(name="Keep as Active", default=False, description="Keep the new UV as active after baking")

    # --- UDIM Settings ---
    # use_udim is deprecated, replaced by bake_mode='UDIM'
    udim_mode: props.EnumProperty(
        name="UDIM Mode",
        items=[
            ('DETECT', 'Use Existing UVs', 'Trust current UV positions (e.g. 1002, 1011). Bake assumes UVs are already laid out.'),
            ('REPACK', 'Auto Repack 0-1', 'Keep existing UDIM UVs, but automatically move 0-1 UVs to new empty tiles.'),
            ('CUSTOM', 'Custom List', 'Force UVs to the specific tiles defined in the object list below.'),
        ],
        default='DETECT'
    )
    # For Manual/List mode
    udim_start_tile: props.IntProperty(name="Start Tile", default=1001, min=1001, max=1099)
    udim_count: props.IntProperty(name="Tile Count", default=1, min=1, max=99)
    # Simple Manual Grid (e.g. 2x2)
    udim_grid_u: props.IntProperty(name="Grid U", default=2, min=1)
    udim_grid_v: props.IntProperty(name="Grid V", default=1, min=1)

    id_manual_start_color: props.BoolProperty(name='Manual Start Color', default=True)
    id_start_color: props.FloatVectorProperty(name='ID Start Color', default=(1.0, 0.0, 0.0, 1.0), subtype='COLOR', size=4)
    id_iterations: props.IntProperty(name='Quality (Iterations)', default=50, min=1, max=1000)
    id_seed: props.IntProperty(name='Random Seed', default=0, min=0)

class BakeJob(bpy.types.PropertyGroup):
    name: props.StringProperty(name="Job Name", default="New Job")
    enabled: props.BoolProperty(name="Enabled", default=True)
    setting: props.PointerProperty(type=BakeJobSetting)
    custom_bake_channels: props.CollectionProperty(type=CustomBakeChannel)
    custom_bake_channels_index: props.IntProperty(name='Index', default=0)

class BakeImageSettings(bpy.types.PropertyGroup):
    save_format: props.EnumProperty(items=BASIC_FORMATS, default="PNG")
    color_depth: props.EnumProperty(items=get_valid_depths)
    color_mode: props.EnumProperty(items=get_valid_modes)
    quality: props.IntProperty(name='Quality', default=100)
    exr_code: props.EnumProperty(items=EXR_CODECS, default='ZIP')
    tiff_codec: props.EnumProperty(items=TIFF_CODECS, default='DEFLATE')

class BakeNodeSettings(bpy.types.PropertyGroup):
    res_x: props.IntProperty(name='X', default=1024)
    res_y: props.IntProperty(name='Y', default=1024)
    sample: props.IntProperty(name='Sample', default=1)
    margin: props.IntProperty(name='Margin', default=4)
    float32: props.BoolProperty(default=False, name='32 Bit')
    save_outside: props.BoolProperty(default=False, name='Save External')
    save_path: props.StringProperty(subtype='DIR_PATH', name='Path')
    image_settings: props.PointerProperty(type=BakeImageSettings)

class BakeResultSettings(bpy.types.PropertyGroup):
    save_path: props.StringProperty(subtype='DIR_PATH')
    use_denoise: props.BoolProperty(default=False) 
    denoise_method: props.EnumProperty(items=DENOISE_METHODS, default="FAST")
    image_settings: props.PointerProperty(type=BakeImageSettings)
    
class BakeJobs(bpy.types.PropertyGroup):
    debug_mode: bpy.props.BoolProperty(name="Debug Mode", default=False, update=update_debug_mode)
    jobs: props.CollectionProperty(type=BakeJob)
    job_index: props.IntProperty(name='Index', default=0)
    node_bake_settings: props.PointerProperty(type=BakeNodeSettings)
    bake_result_settings: props.PointerProperty(type=BakeResultSettings)
    
    open_inputs: props.BoolProperty(default=False)
    open_channels: props.BoolProperty(default=False)
    open_saves: props.BoolProperty(default=False)
    open_other: props.BoolProperty(default=False)

class BakedImageResult(bpy.types.PropertyGroup):
    image: props.PointerProperty(type=bpy.types.Image)
    color_depth: props.StringProperty()
    color_space: props.StringProperty()
    filepath: props.StringProperty()
    object_name: props.StringProperty()
    channel_type: props.StringProperty()