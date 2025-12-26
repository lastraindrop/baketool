import bpy
from bpy import props
from .constants import *
from .utils import logger
import logging

# ... (保持动态回调 get_channel_source_items, get_valid_depths 等不变)
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
    fmt = "PNG" 
    if hasattr(self, "save_format"): fmt = self.save_format
    elif hasattr(self, "node_bake_save_format"): fmt = self.node_bake_save_format
    elif hasattr(self, "bake_result_save_format"): fmt = self.bake_result_save_format
    if fmt not in FORMAT_SETTINGS: return color_depth
    valid_depths_keys = FORMAT_SETTINGS[fmt].get("depths", [])
    if not valid_depths_keys: return color_depth
    return [item for item in color_depth if item[0] in valid_depths_keys]

def get_valid_modes(self, context):
    fmt = "PNG"
    if hasattr(self, "save_format"): fmt = self.save_format
    elif hasattr(self, "node_bake_save_format"): fmt = self.node_bake_save_format
    elif hasattr(self, "bake_result_save_format"): fmt = self.bake_result_save_format
    if fmt not in FORMAT_SETTINGS: return color_mode
    valid_modes = FORMAT_SETTINGS[fmt].get("modes", [])
    if not valid_modes: return color_mode
    return [item for item in color_mode if item[0] in valid_modes]

def update_debug_mode(self, context):
    if self.debug_mode:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

def update_channels(self, context):
    if hasattr(bpy.ops.bake, "reset_channels"):
        try: bpy.ops.bake.reset_channels('EXEC_DEFAULT')
        except: pass

class BakeObject(bpy.types.PropertyGroup):
    bakeobject: props.PointerProperty(name="object", type=bpy.types.Object)
    
class BakeChannel(bpy.types.PropertyGroup):
    name: props.StringProperty(name="Channel Name"); id: props.StringProperty(name="Channel ID")
    enabled: props.BoolProperty(name="Enabled", default=False); prefix: props.StringProperty(name="Prefix")
    suffix: props.StringProperty(name="Suffix"); custom_cs: props.EnumProperty(items=color_space, name="Color Space")
    rough_inv: props.BoolProperty(name="Invert"); normal_type: props.EnumProperty(items=normal_type, name="Normal Mode", default='OPENGL')
    normal_X: props.EnumProperty(items=normal_channel, name="X", default='POS_X'); normal_Y: props.EnumProperty(items=normal_channel, name="Y", default='POS_Y')
    normal_Z: props.EnumProperty(items=normal_channel, name="Z", default='POS_Z'); normal_obj: props.BoolProperty(name="Object Space")
    diff_dir: props.BoolProperty(name="Direct", default=False); diff_ind: props.BoolProperty(name="Indirect", default=False); diff_col: props.BoolProperty(name="Color", default=True)
    gloss_dir: props.BoolProperty(name="Direct", default=False); gloss_ind: props.BoolProperty(name="Indirect", default=False); gloss_col: props.BoolProperty(name="Color", default=True)
    tranb_dir: props.BoolProperty(name="Direct", default=False); tranb_ind: props.BoolProperty(name="Indirect", default=False); tranb_col: props.BoolProperty(name="Color", default=True)
    com_dir: props.BoolProperty(name="Direct", default=True); com_ind: props.BoolProperty(name="Indirect", default=True); com_diff: props.BoolProperty(name="Diffuse", default=True)
    com_gloss: props.BoolProperty(name="Gloss", default=True); com_tran: props.BoolProperty(name="Transmission", default=True); com_emi: props.BoolProperty(name="Emission", default=True)
    bevel_sample: props.IntProperty(name='Samples', default=8, min=2, max=16); bevel_rad: props.FloatProperty(name='Radius', default=0.1)
    ao_inside: props.BoolProperty(name='Inside', default=False); ao_local: props.BoolProperty(name='Only Local', default=False); ao_dis: props.FloatProperty(name='Distance', default=1); ao_sample: props.IntProperty(name='Samples', default=16)
    wireframe_use_pix: props.BoolProperty(name='Use Pixel Size', default=False); wireframe_dis: props.FloatProperty(name='Thickness', default=0.01)
    bevnor_sample: props.IntProperty(name='Samples', default=8); bevnor_rad: props.FloatProperty(name='Radius', default=0.1)
    position_invg: props.BoolProperty(name='Invert G', default=True); slope_directions: props.EnumProperty(items=directions, name='Direction', default="Z")
    slope_invert: props.BoolProperty(name='Invert', default=False); thickness_distance: props.FloatProperty(name='Distance', default=0.5)
    thickness_contrast: props.FloatProperty(name='Contrast', default=0.5); ID_num: props.IntProperty(name='ID Map Count', default=5)

class CustomBakeChannel(bpy.types.PropertyGroup):
    name: props.StringProperty(name='Name', default="Custom Channel")
    color_space: props.EnumProperty(items=color_space, name='Color Space', default='NONCOL')
    r: props.FloatProperty(name='Red', default=0.0, min=0, max=1); r_usemap: props.BoolProperty(name='Use Map', default=False); r_source: props.EnumProperty(items=get_channel_source_items, name='Source'); r_invert: props.BoolProperty(name='Invert', default=False); r_sepcol: props.BoolProperty(name='Separate', default=False); r_colchan: props.EnumProperty(items=custom_bake_channel_sep, name='Channel')
    g: props.FloatProperty(name='Green', default=0.0, min=0, max=1); g_usemap: props.BoolProperty(name='Use Map', default=False); g_source: props.EnumProperty(items=get_channel_source_items, name='Source'); g_invert: props.BoolProperty(name='Invert', default=False); g_sepcol: props.BoolProperty(name='Separate', default=False); g_colchan: props.EnumProperty(items=custom_bake_channel_sep, name='Channel')
    b: props.FloatProperty(name='Blue', default=0.0, min=0, max=1); b_usemap: props.BoolProperty(name='Use Map', default=False); b_source: props.EnumProperty(items=get_channel_source_items, name='Source'); b_invert: props.BoolProperty(name='Invert', default=False); b_sepcol: props.BoolProperty(name='Separate', default=False); b_colchan: props.EnumProperty(items=custom_bake_channel_sep, name='Channel')
    a: props.FloatProperty(name='Alpha', default=1.0, min=0, max=1); a_usemap: props.BoolProperty(name='Use Map', default=False); a_source: props.EnumProperty(items=get_channel_source_items, name='Source'); a_invert: props.BoolProperty(name='Invert', default=False); a_sepcol: props.BoolProperty(name='Separate', default=False); a_colchan: props.EnumProperty(items=custom_bake_channel_sep, name='Channel')
    bw: props.BoolProperty(name='bw', default=False); bw_source: props.EnumProperty(items=get_channel_source_items, name='Source'); bw_invert: props.BoolProperty(name='Invert', default=False); bw_sepcol: props.BoolProperty(name='Separate', default=False); bw_colchan: props.EnumProperty(items=custom_bake_channel_sep, name='Channel')
    prefix: props.StringProperty(name='Prefix'); suffix: props.StringProperty(name='Suffix')
    
class BakeJobSetting(bpy.types.PropertyGroup):
    debug_mode: bpy.props.BoolProperty(name="Debug Mode", default=False, update=update_debug_mode)
    save_and_quit: props.BoolProperty(default=False, name='Save And Quit')
    bake_texture_apply: props.BoolProperty(default=False, name='Apply Bake')
    bake_objects: props.CollectionProperty(type=BakeObject, name='Objects')
    active_object: props.PointerProperty(type=bpy.types.Object, name='Active')
    cage_object: props.PointerProperty(type=bpy.types.Object, name='Cage')
    res_x: props.IntProperty(name='X', default=1024, min=32); res_y: props.IntProperty(name='Y', default=1024, min=32)
    sample: props.IntProperty(name='Sampling', default=1, min=1); margin: props.IntProperty(name='Margin', default=8, min=0)
    device: props.EnumProperty(name='Device', items=device, default="GPU"); bake_type: props.EnumProperty(items=bake_type, name='Bake Type', default="BSDF", update=update_channels)
    bake_mode: props.EnumProperty(items=bake_mode, name='Bake Mode', default="SINGLE_OBJECT"); special_bake_method: props.EnumProperty(items=special_bake, name='Special Settings', default="NO")
    multires_divide: props.IntProperty(name='Multires Level', default=0); extrusion: props.FloatProperty(name='Extrude', min=0); ray_distance: props.FloatProperty(name='Ray Dist', min=0)
    atlas_pack_method: props.EnumProperty(items=atlas_pack, name='Packing', default="ISLAND"); atlas_margin: props.FloatProperty(name='Margin', default=0.003, precision=3)
    bake_motion: props.BoolProperty(default=False, name='Animation'); bake_motion_use_custom: props.BoolProperty(default=False, name='Custom Frames')
    bake_motion_start: props.IntProperty(name='Start', default=1); bake_motion_last: props.IntProperty(name='Duration', default=250)
    bake_motion_startindex: props.IntProperty(name='Start Index', default=0); bake_motion_digit: props.IntProperty(name='Frame Digits', default=4)
    float32: props.BoolProperty(default=False, name='32 Bit'); colorspace_setting: props.BoolProperty(default=False, name='Color Space')
    clearimage: props.BoolProperty(default=True, name='Clear'); colorbase: props.FloatVectorProperty(name='Color Base', default=(0,0,0,0), subtype='COLOR', size=4)
    use_alpha: props.BoolProperty(default=True, name='Use Alpha'); save_out: props.BoolProperty(default=False, name='External Save')
    save_path: props.StringProperty(subtype='DIR_PATH', name='Save Path'); use_fake_user: props.BoolProperty(default=True, name='Fake User')
    reload: props.BoolProperty(default=False, name='Reload Image'); save_format: props.EnumProperty(items=basic_format, name='Format', default="PNG")
    color_depth: props.EnumProperty(items=get_valid_depths, name='Color Depth'); color_mode: props.EnumProperty(items=get_valid_modes, name='Color Mode')
    quality: props.IntProperty(name='Quality', default=85); exr_code: props.EnumProperty(items=exr_code, name='EXR Codec', default='ZIP')
    tiff_codec: props.EnumProperty(items=tiff_codec, name='TIFF Codec', default='DEFLATE'); create_new_folder: props.BoolProperty(default=False, name='New Folder')
    new_folder_name_setting: props.EnumProperty(items=basic_name, name='Folder Naming', default="MAT"); folder_name: props.StringProperty(name='Custom Folder Name')
    name_setting: props.EnumProperty(items=basic_name, name='Base Name', default="MAT"); custom_name: props.StringProperty(name='Custom Name')
    use_denoise: props.BoolProperty(default=False, name='Denoise'); denoise_method: props.EnumProperty(items=denoise_method, name='Denoise Method', default="FAST")
    export_model: bpy.props.BoolProperty(name="Export Model", default=False); export_format: bpy.props.EnumProperty(items=[('FBX','FBX','',1),('GLB','GLB','',2),('USD','USD','',3)], default='FBX')
    channels: props.CollectionProperty(type=BakeChannel); active_channel_index: props.IntProperty(name="Active Channel Index"); active_object_index: props.IntProperty(name="Active Object Index", default=0)
    use_special_map: bpy.props.BoolProperty(default=False, name='Special Map', update=update_channels); use_custom_map: props.BoolProperty(default=False, name='Use Custom Map')
    
    # [新增] ID 贴图优化设置
    id_start_color: props.FloatVectorProperty(name='ID Start Color', default=(1.0, 0.0, 0.0, 1.0), subtype='COLOR', size=4, description="First color used for ID generation")
    id_use_annealing: props.BoolProperty(name='Maximize Difference', default=True, description="Use Simulated Annealing to maximize visual difference between ID colors")

class BakeJob(bpy.types.PropertyGroup):
    name: props.StringProperty(name="Job Name", default="New Job")
    setting: props.PointerProperty(type=BakeJobSetting)
    Custombakechannels: props.CollectionProperty(type=CustomBakeChannel); Custombakechannels_index: props.IntProperty(name='Index', default=0)
    
class BakeJobs(bpy.types.PropertyGroup):
    node_bake_res_x: props.IntProperty(name='X', default=1024); node_bake_res_y: props.IntProperty(name='Y', default=1024); node_bake_sample: props.IntProperty(name='Sample', default=1); node_bake_margin: props.IntProperty(name='Margin', default=4); node_bake_float32: props.BoolProperty(default=False, name='32 Bit'); node_bake_socket_index: props.IntProperty(name='Socket', default=0); node_bake_save_outside: props.BoolProperty(default=False, name='Save External'); node_bake_save_path: props.StringProperty(subtype='DIR_PATH', name='Path'); node_bake_save_format: props.EnumProperty(items=basic_format, default="PNG"); node_bake_color_depth: props.EnumProperty(items=get_valid_depths); node_bake_color_mode: props.EnumProperty(items=get_valid_modes); node_bake_color_space: props.EnumProperty(items=color_space, default='SRGB'); node_bake_quality: props.IntProperty(name='Quality', default=100); node_bake_exr_code: props.EnumProperty(items=exr_code, default='ZIP'); node_bake_tiff_codec: props.EnumProperty(items=tiff_codec, default='DEFLATE'); node_bake_reload: props.BoolProperty(default=False); node_bake_delete_node: props.BoolProperty(default=False); node_bake_auto_find_socket: props.BoolProperty(default=False); bake_result_save_path: props.StringProperty(subtype='DIR_PATH'); bake_result_save_format: props.EnumProperty(items=basic_format, default="PNG"); bake_result_color_depth: props.EnumProperty(items=get_valid_depths); bake_result_color_mode: props.EnumProperty(items=get_valid_modes); bake_result_color_space: props.EnumProperty(items=color_space2, default='DEFAULT'); bake_result_quality: props.IntProperty(default=100); bake_result_exr_code: props.EnumProperty(items=exr_code, default='ZIP'); bake_result_tiff_codec: props.EnumProperty(items=tiff_codec, default='DEFLATE'); bake_result_use_denoise: props.BoolProperty(default=False); bake_result_denoise_method: props.EnumProperty(items=denoise_method, default="FAST"); open_inputs: props.BoolProperty(default=False); open_channels: props.BoolProperty(default=False); open_saves: props.BoolProperty(default=False); open_other: props.BoolProperty(default=False); copy_job: props.BoolProperty(default=False); jobs: props.CollectionProperty(type=BakeJob); job_index: props.IntProperty(default=0)
    
class BakedImageResult(bpy.types.PropertyGroup):
    image: props.PointerProperty(type=bpy.types.Image); color_depth: props.StringProperty(); color_space: props.StringProperty(); filepath: props.StringProperty(); object_name: props.StringProperty(); channel_type: props.StringProperty()