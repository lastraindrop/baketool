import bpy
from bpy import props
import os
from pathlib import Path
from .constants import (
    BAKE_TYPES,
    BAKE_MODES,
    BASIC_FORMATS,
    DEVICES,
    DIRECTIONS,
    NORMAL_TYPES,
    NORMAL_CHANNELS,
    COLOR_DEPTHS,
    COLOR_MODES,
    COLOR_SPACES,
    EXR_CODECS,
    TIFF_CODECS,
    DENOISE_METHODS,
    NAMING_MODES,
    CUSTOM_CHANNEL_SEP,
    ATLAS_PACK_METHODS,
    FORMAT_SETTINGS,
)

from .core.common import reset_channels_logic
import logging

logger = logging.getLogger(__name__)

# --- Helper Functions for Properties ---

_LEGACY_DEPTH_MAP = {"0": "8", "1": "16", "2": "32"}
_LEGACY_MODE_MAP = {"0": "RGBA", "1": "RGB", "2": "BW"}
_CANONICAL_DEPTH_KEYS = {"8", "10", "12", "16", "32"}
_CANONICAL_MODE_KEYS = {"RGBA", "RGB", "BW"}


def _as_key_set(values):
    return set(values) if values else set()


def _canonical_depth(value):
    key = str(value) if value is not None else ""
    return _LEGACY_DEPTH_MAP.get(key, key)


def _canonical_mode(value):
    key = str(value) if value is not None else ""
    return _LEGACY_MODE_MAP.get(key, key)


def _canonical_depth_items():
    return [item for item in COLOR_DEPTHS if item[0] in _CANONICAL_DEPTH_KEYS]


def _canonical_mode_items():
    return [item for item in COLOR_MODES if item[0] in _CANONICAL_MODE_KEYS]


def _build_enum_item(item_tuple, idx):
    return (item_tuple[0], item_tuple[1], item_tuple[2], "NONE", idx)


def _pick_first_allowed(valid_keys, ordered_items, preferred):
    if preferred in valid_keys:
        return preferred
    for item in ordered_items:
        key = item[0]
        if key in valid_keys:
            return key
    return None


def _find_item_by_identifier(items, identifier):
    for item in items:
        if item[0] == identifier:
            return item
    return None


def get_channel_source_items(self, context):
    """Safely retrieve available channels for custom source selection."""
    if not context or not getattr(context, "scene", None):
        return [("NONE", "None", "No enabled channels available", "NONE", 0)]

    scene = context.scene
    if not hasattr(scene, "BakeNexusJobs") or not scene.BakeNexusJobs.jobs:
        return [("NONE", "None", "No enabled channels available", "NONE", 0)]

    bj = scene.BakeNexusJobs
    job_index = getattr(bj, "job_index", 0)

    if job_index < 0 or job_index >= len(bj.jobs):
        return [("NONE", "None", "No enabled channels available", "NONE", 0)]

    try:
        job = bj.jobs[job_index]
        setting = job.setting

        items = []
        for i, c in enumerate(setting.channels):
            if c.enabled:
                items.append(
                    (c.id, c.name, f"Use {c.name} result as source", "NONE", i)
                )

        # Prevent self-reference
        current_custom_name = None
        for chan in job.custom_bake_channels:
            if any(getattr(chan, f"{s}_settings") == self for s in ["r", "g", "b", "a", "bw"]):
                current_custom_name = chan.name
                break

        base_len = len(items)
        for i, c in enumerate(job.custom_bake_channels):
            # Self-reference filter
            if current_custom_name and c.name == current_custom_name:
                continue

            identifier = f"BT_CUSTOM_{c.name}"
            items.append(
                (
                    identifier,
                    c.name,
                    f"Use {c.name} (Custom) as source",
                    "NONE",
                    base_len + i,
                )
            )

        return (
            items
            if items
            else [("NONE", "None", "No enabled channels available", "NONE", 0)]
        )
    except Exception as e:
        logger.debug(f"Error getting channel sources: {e}")
        return [("NONE", "None", "No enabled channels available", "NONE", 0)]


def get_valid_depths(self, context):
    """Filter color depths based on current image format technical constraints."""
    try:
        canonical_items = _canonical_depth_items()
        default_items = [
            _build_enum_item(item, i) for i, item in enumerate(canonical_items)
        ]

        if not context or not hasattr(context, "scene"):
            return default_items

        fmt = getattr(self, "external_save_format", "PNG")
        valid_keys = _as_key_set(FORMAT_SETTINGS.get(fmt, {}).get("depths", []))
        raw_current = str(self.get("color_depth", ""))
        current = _canonical_depth(raw_current)

        if not valid_keys:
            return default_items

        filtered = [
            _build_enum_item(item, i)
            for i, item in enumerate(canonical_items)
            if item[0] in valid_keys
        ]

        if current and current not in {item[0] for item in filtered}:
            for item in canonical_items:
                if item[0] == current:
                    filtered.append(_build_enum_item(item, len(filtered)))
                    break
        if raw_current in _LEGACY_DEPTH_MAP:
            legacy_item = _find_item_by_identifier(COLOR_DEPTHS, raw_current)
            if legacy_item:
                filtered.append(_build_enum_item(legacy_item, len(filtered)))

        return filtered if filtered else default_items
    except Exception as e:
        logger.error(f"Error in get_valid_depths: {e}")
        return [("8", "8", "Fallback 8-bit", "NONE", 0)]


def get_valid_modes(self, context):
    """Filter color modes based on current image format technical constraints."""
    try:
        canonical_items = _canonical_mode_items()
        default_items = [
            _build_enum_item(item, i) for i, item in enumerate(canonical_items)
        ]
        if not context or not hasattr(context, "scene"):
            return default_items

        fmt = getattr(self, "external_save_format", "PNG")
        valid_keys = _as_key_set(FORMAT_SETTINGS.get(fmt, {}).get("modes", []))
        raw_current = str(self.get("color_mode", ""))
        current = _canonical_mode(raw_current)

        if not valid_keys:
            return default_items

        filtered = [
            _build_enum_item(item, i)
            for i, item in enumerate(canonical_items)
            if item[0] in valid_keys
        ]

        if current and current not in {item[0] for item in filtered}:
            for item in canonical_items:
                if item[0] == current:
                    filtered.append(_build_enum_item(item, len(filtered)))
                    break
        if raw_current in _LEGACY_MODE_MAP:
            legacy_item = _find_item_by_identifier(COLOR_MODES, raw_current)
            if legacy_item:
                filtered.append(_build_enum_item(legacy_item, len(filtered)))

        return filtered if filtered else default_items
    except Exception as e:
        logger.error(f"Error in get_valid_modes: {e}")
        return [("RGB", "RGB", "Fallback RGB", "NONE", 0)]


def update_format_dependent_enums(self, context):
    """Keep dynamic format-dependent enums in a valid state."""
    fmt = getattr(self, "external_save_format", "PNG")
    fmt_cfg = FORMAT_SETTINGS.get(fmt, {})
    valid_depths = _as_key_set(fmt_cfg.get("depths", []))
    valid_modes = _as_key_set(fmt_cfg.get("modes", []))

    current_depth = _canonical_depth(self.get("color_depth", "8"))
    current_mode = _canonical_mode(self.get("color_mode", "RGBA"))

    if valid_depths and current_depth not in valid_depths:
        next_depth = _pick_first_allowed(valid_depths, _canonical_depth_items(), "8")
        if next_depth:
            self.color_depth = next_depth
    elif current_depth:
        self.color_depth = current_depth

    if valid_modes and current_mode not in valid_modes:
        next_mode = _pick_first_allowed(valid_modes, _canonical_mode_items(), "RGB")
        if next_mode:
            self.color_mode = next_mode
    elif current_mode:
        self.color_mode = current_mode


def update_debug_mode(self, context):
    """Update global logger level based on debug setting."""
    pkg_name = __package__.split(".")[0] if "." in __package__ else __package__
    logging.getLogger(pkg_name).setLevel(
        logging.DEBUG if self.debug_mode else logging.INFO
    )


def update_channels(self, context):
    """Trigger channel sync when map categories are toggled."""
    reset_channels_logic(self)


def update_preview(self, context):
    """Trigger real-time viewport preview when toggled."""
    from .core import shading

    # 'self' here is the BakeJobSetting group
    objs = [o.bakeobject for o in self.bake_objects if o.bakeobject]

    for obj in objs:
        if self.use_preview:
            shading.apply_preview(obj, self)
        else:
            shading.remove_preview(obj)

    if context and context.screen:
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


# --- Sub-Setting Groups ---


class BakeNormalSettings(bpy.types.PropertyGroup):
    type: props.EnumProperty(items=NORMAL_TYPES, name="Normal Mode", default="OPENGL")
    X: props.EnumProperty(items=NORMAL_CHANNELS, name="X", default="POS_X")
    Y: props.EnumProperty(items=NORMAL_CHANNELS, name="Y", default="POS_Y")
    Z: props.EnumProperty(items=NORMAL_CHANNELS, name="Z", default="POS_Z")
    object_space: props.BoolProperty(name="Object Space", default=False)


class BakePassSettings(bpy.types.PropertyGroup):
    """Generic settings for Render Passes (Diffuse, Glossy, etc.)"""

    use_direct: props.BoolProperty(name="Direct", default=False)
    use_indirect: props.BoolProperty(name="Indirect", default=False)
    use_color: props.BoolProperty(name="Color", default=True)


class BakeCombineSettings(bpy.types.PropertyGroup):
    """Settings specifically for Combined pass"""

    use_direct: props.BoolProperty(name="Direct", default=True)
    use_indirect: props.BoolProperty(name="Indirect", default=True)
    use_diffuse: props.BoolProperty(name="Diffuse", default=True)
    use_glossy: props.BoolProperty(name="Glossy", default=True)
    use_transmission: props.BoolProperty(name="Transmission", default=True)
    use_emission: props.BoolProperty(name="Emission", default=True)


class BakeMeshSettings(bpy.types.PropertyGroup):
    """Generic settings for Mesh Analysis maps (AO, Bevel, Curvature, etc.)"""

    samples: props.IntProperty(name="Samples", default=8, min=1, max=128)
    radius: props.FloatProperty(name="Radius", default=0.1)
    distance: props.FloatProperty(name="Distance", default=1.0)
    contrast: props.FloatProperty(name="Contrast", default=1.0)
    inside: props.BoolProperty(name="Inside", default=False)
    local_only: props.BoolProperty(name="Only Local", default=False)
    use_pixel_size: props.BoolProperty(name="Use Pixel Size", default=False)
    invert_g: props.BoolProperty(name="Invert G", default=True)
    direction: props.EnumProperty(items=DIRECTIONS, name="Direction", default="Z")
    invert: props.BoolProperty(name="Invert", default=False)
    id_count: props.IntProperty(name="ID Map Count", default=5)


class BakeExtensionSettings(bpy.types.PropertyGroup):
    """Settings for PBR Conversion and Custom Node Groups"""

    threshold: props.FloatProperty(name="Threshold", default=0.04, min=0.0, max=1.0)
    node_group: props.StringProperty(name="Node Group")
    output_name: props.StringProperty(name="Output Socket", default="")


# --- Property Group Classes ---


class BakeObject(bpy.types.PropertyGroup):
    bakeobject: props.PointerProperty(name="object", type=bpy.types.Object)
    udim_tile: props.IntProperty(
        name="UDIM Tile",
        default=1001,
        min=1001,
        max=1099,
        description="Target UDIM Tile for this object",
    )

    override_size: props.BoolProperty(
        name="Override Size",
        default=False,
        description="Use custom resolution for this tile",
    )
    udim_width: props.IntProperty(name="Width", default=1024, min=1)
    udim_height: props.IntProperty(name="Height", default=1024, min=1)


class BakeChannelSource(bpy.types.PropertyGroup):
    use_map: props.BoolProperty(name="Use Map", default=False)
    source: props.EnumProperty(items=get_channel_source_items, name="Source")
    invert: props.BoolProperty(name="Invert", default=False)
    sep_col: props.BoolProperty(name="Separate", default=False)
    col_chan: props.EnumProperty(items=CUSTOM_CHANNEL_SEP, name="Channel")
    default_value: props.FloatProperty(name="Default Value", default=0.0, min=0.0, max=1.0)


class BakeChannel(bpy.types.PropertyGroup):
    valid_for_mode: props.BoolProperty(default=True)
    name: props.StringProperty(name="Channel Name")
    id: props.StringProperty(name="Channel ID")
    enabled: props.BoolProperty(name="Enabled", default=False)
    prefix: props.StringProperty(name="Prefix")
    suffix: props.StringProperty(name="Suffix")

    override_defaults: props.BoolProperty(
        name="Override Global Color Settings",
        default=False,
        description="Use specific color space and depth for this channel instead of job defaults",
    )
    custom_cs: props.EnumProperty(
        items=COLOR_SPACES, name="Color Space", default="SRGB"
    )
    custom_mode: props.EnumProperty(items=COLOR_MODES, name="Color Mode", default="RGB")

    rough_inv: props.BoolProperty(name="Invert")

    # Sub-Settings
    normal_settings: props.PointerProperty(type=BakeNormalSettings)
    pass_settings: props.PointerProperty(type=BakePassSettings)
    combine_settings: props.PointerProperty(type=BakeCombineSettings)
    mesh_settings: props.PointerProperty(type=BakeMeshSettings)
    extension_settings: props.PointerProperty(type=BakeExtensionSettings)


class CustomBakeChannel(bpy.types.PropertyGroup):
    name: props.StringProperty(name="Name", default="Custom Channel")
    color_space: props.EnumProperty(
        items=COLOR_SPACES, name="Color Space", default="NONCOL"
    )
    bw: props.BoolProperty(name="bw", default=False)

    r_settings: props.PointerProperty(type=BakeChannelSource)
    g_settings: props.PointerProperty(type=BakeChannelSource)
    b_settings: props.PointerProperty(type=BakeChannelSource)
    a_settings: props.PointerProperty(type=BakeChannelSource)
    bw_settings: props.PointerProperty(type=BakeChannelSource)

    prefix: props.StringProperty(name="Prefix")
    suffix: props.StringProperty(name="Suffix")


class BakedImageResult(bpy.types.PropertyGroup):
    image: props.PointerProperty(type=bpy.types.Image)
    filepath: props.StringProperty()
    object_name: props.StringProperty()
    channel_type: props.StringProperty()

    # --- Metadata Fields ---
    res_x: props.IntProperty(name="Width")
    res_y: props.IntProperty(name="Height")
    samples: props.IntProperty(name="Samples")
    duration: props.FloatProperty(name="Duration", precision=2)
    bake_time: props.FloatProperty(name="Bake Time", precision=2)
    save_time: props.FloatProperty(name="Save Time", precision=2)
    bake_type: props.StringProperty(name="Method")
    device: props.StringProperty(name="Device")
    file_size: props.StringProperty(name="File Size")  # Formatted e.g. "1.2 MB"


class BakeJobSetting(bpy.types.PropertyGroup):
    save_and_quit: props.BoolProperty(default=False, name="Save And Quit")
    apply_to_scene: props.BoolProperty(default=False, name="Apply Bake")

    # Global / Backward compatibility toggles
    use_direct: props.BoolProperty(name="Direct", default=True)
    use_indirect: props.BoolProperty(name="Indirect", default=True)
    use_color: props.BoolProperty(name="Color", default=True)

    bake_objects: props.CollectionProperty(type=BakeObject, name="Objects")
    active_object: props.PointerProperty(type=bpy.types.Object, name="Active")
    cage_object: props.PointerProperty(type=bpy.types.Object, name="Cage")

    res_x: props.IntProperty(name="X", default=1024, min=32)
    res_y: props.IntProperty(name="Y", default=1024, min=32)
    sample: props.IntProperty(name="Sampling", default=1, min=1)
    margin: props.IntProperty(name="Margin", default=8, min=0)
    device: props.EnumProperty(name="Device", items=DEVICES, default="GPU")

    bake_type: props.EnumProperty(
        items=BAKE_TYPES, name="Bake Type", default="BSDF", update=update_channels
    )
    bake_mode: props.EnumProperty(
        items=BAKE_MODES, name="Bake Mode", default="SINGLE_OBJECT"
    )

    extrusion: props.FloatProperty(name="Uniform Extrude", min=0, default=0.01)

    # Auto-Cage 2.0
    auto_cage_mode: props.EnumProperty(
        name="Cage Mode",
        items=[
            ("UNIFORM", "Uniform", "Standard normal offset"),
            ("PROXIMITY", "Proximity", "Ray-cast based smart offset"),
        ],
        default="UNIFORM",
    )
    auto_cage_margin: props.FloatProperty(name="Safety Margin", default=0.1, min=0.0)
    use_float32: props.BoolProperty(default=False, name="32 Bit")
    use_denoise: props.BoolProperty(default=False, name="Denoise (OIDN)")
    use_clear_image: props.BoolProperty(default=True, name="Clear")
    color_base: props.FloatVectorProperty(
        name="Color Base", default=(0, 0, 0, 0), subtype="COLOR", size=4
    )
    use_alpha: props.BoolProperty(default=True, name="Use Alpha")

    use_external_save: props.BoolProperty(default=False, name="External Save")
    external_save_path: props.StringProperty(subtype="DIR_PATH", name="Save Path")
    external_save_format: props.EnumProperty(
        items=BASIC_FORMATS,
        name="Format",
        default="PNG",
        update=update_format_dependent_enums,
    )
    color_depth: props.EnumProperty(
        items=get_valid_depths, name="Color Depth", default=0
    )
    color_mode: props.EnumProperty(
        items=get_valid_modes, name="Color Mode", default=0
    )
    quality: props.IntProperty(name="Quality", default=85)
    exr_code: props.EnumProperty(items=EXR_CODECS, name="EXR Codec", default="ZIP")
    tiff_codec: props.EnumProperty(
        items=TIFF_CODECS, name="TIFF Codec", default="DEFLATE"
    )

    create_new_folder: props.BoolProperty(default=False, name="New Folder")
    folder_name: props.StringProperty(name="Custom Folder Name")
    name_setting: props.EnumProperty(
        items=NAMING_MODES, name="Base Name", default="MAT"
    )
    custom_name: props.StringProperty(name="Custom Name")

    bake_motion: props.BoolProperty(default=False, name="Animation")
    bake_motion_use_custom: props.BoolProperty(default=False, name="Custom Frames")
    bake_motion_start: props.IntProperty(name="Start", default=1)
    bake_motion_last: props.IntProperty(name="Duration", default=250)
    bake_motion_startindex: props.IntProperty(name="Start Index", default=1)
    bake_motion_digit: props.IntProperty(name="Frame Digits", default=4)
    bake_motion_separator: props.StringProperty(name="Separator", default="_")

    export_model: props.BoolProperty(name="Export Model", default=False)
    export_format: props.EnumProperty(
        items=[("FBX", "FBX", "", 1), ("GLB", "GLB", "", 2), ("USD", "USD", "", 3)],
        default="FBX",
    )
    export_textures_with_model: props.BoolProperty(
        name="Export with Textures",
        default=True,
        description="Automatically bind baked textures to exported model",
    )
    auto_switch_vertex_paint: props.BoolProperty(
        default=False,
        name="Auto Switch to Vertex Paint",
        description="Automatically switch viewport to Vertex Paint mode after cage analysis",
    )

    path_valid: props.BoolProperty(
        name="Path Valid",
        default=True,
        options={"SKIP_SAVE"},
        description="Internal cache for export path validity",
    )

    # Channel Packing (ORM etc)
    use_packing: props.BoolProperty(name="Auto Pack Channels", default=False)
    pack_r: props.EnumProperty(items=get_channel_source_items, name="Red (R)")
    pack_g: props.EnumProperty(items=get_channel_source_items, name="Green (G)")
    pack_b: props.EnumProperty(items=get_channel_source_items, name="Blue (B)")
    pack_a: props.EnumProperty(items=get_channel_source_items, name="Alpha (A)")
    pack_suffix: props.StringProperty(name="Suffix", default="_ORM")

    # Roadmap 1.1: Interactive Preview
    use_preview: props.BoolProperty(
        name="Interactive Preview",
        default=False,
        description="Show real-time channel packing preview in viewport",
        update=update_preview,
    )

    channels: props.CollectionProperty(type=BakeChannel)
    active_channel_index: props.IntProperty(name="Active Channel Index")
    active_object_index: props.IntProperty(name="Active Object Index", default=0)

    use_light_map: props.BoolProperty(
        default=False, name="Light Maps", update=update_channels
    )
    use_mesh_map: props.BoolProperty(
        default=False, name="Mesh Maps", update=update_channels
    )
    use_extension_map: props.BoolProperty(
        default=False, name="Extension Maps", update=update_channels
    )
    use_custom_map: props.BoolProperty(default=False, name="Use Custom Map")

    use_auto_uv: props.BoolProperty(name="Auto Smart UV", default=False)
    auto_uv_name: props.StringProperty(name="UV Name", default="Smart_UV")
    auto_uv_angle: props.FloatProperty(
        name="Angle Limit",
        default=1.15192,
        min=0.0175,
        max=1.5533,
        subtype="ANGLE",
        description="Angle limit for Smart UV projection (66° default)",
    )
    auto_uv_margin: props.FloatProperty(
        name="Island Margin", default=0.001, min=0.0, max=1.0, precision=4
    )

    udim_mode: props.EnumProperty(
        name="UDIM Mode",
        items=[
            ("DETECT", "Use Existing UVs", ""),
            ("REPACK", "Auto Repack", ""),
            ("CUSTOM", "Custom List", ""),
        ],
        default="DETECT",
    )

    id_manual_start_color: props.BoolProperty(name="Manual Start Color", default=True)
    id_start_color: props.FloatVectorProperty(
        name="ID Start Color", default=(1.0, 0.0, 0.0, 1.0), subtype="COLOR", size=4
    )
    # Quality settings
    use_antialiasing: props.BoolProperty(name="Anti-Aliasing", default=True)
    id_seed: props.IntProperty(name="Random Seed", default=0, min=0)

    # Texel Density
    texel_density: props.FloatProperty(
        name="Target Density",
        default=10.24,
        min=0.01,
        description="Target texel density in px/unit",
    )


class BakeJob(bpy.types.PropertyGroup):
    name: props.StringProperty(name="Job Name", default="New Job")
    enabled: props.BoolProperty(name="Enabled", default=True)
    setting: props.PointerProperty(type=BakeJobSetting)
    custom_bake_channels: props.CollectionProperty(type=CustomBakeChannel)
    custom_bake_channels_index: props.IntProperty(name="Index", default=0)


# NOTE: Image format props intentionally duplicated from BakeJobSetting.
# Blender PropertyGroup does not support inheritance-based reuse,
# and these serve different contexts (Job Save vs Node/Result Save).
class BakeImageSettings(bpy.types.PropertyGroup):
    external_save_format: props.EnumProperty(
        items=BASIC_FORMATS,
        default="PNG",
        update=update_format_dependent_enums,
    )
    color_depth: props.EnumProperty(items=get_valid_depths, default=0)
    color_mode: props.EnumProperty(items=get_valid_modes, default=0)
    quality: props.IntProperty(name="Quality", default=100)
    exr_code: props.EnumProperty(items=EXR_CODECS, default="ZIP")
    tiff_codec: props.EnumProperty(items=TIFF_CODECS, default="DEFLATE")


class BakeNodeSettings(bpy.types.PropertyGroup):
    res_x: props.IntProperty(name="X", default=1024)
    res_y: props.IntProperty(name="Y", default=1024)
    sample: props.IntProperty(name="Sample", default=1)
    margin: props.IntProperty(name="Margin", default=4)
    use_external_save: props.BoolProperty(default=False, name="Save External")
    external_save_path: props.StringProperty(subtype="DIR_PATH", name="Path")
    image_settings: props.PointerProperty(type=BakeImageSettings)


class BakeResultSettings(bpy.types.PropertyGroup):
    external_save_path: props.StringProperty(subtype="DIR_PATH")
    image_settings: props.PointerProperty(type=BakeImageSettings)


def update_library_preset(self, context):
    """Load the selected preset from the library."""
    if self.library_preset == "NONE":
        return

    path = bpy.path.abspath(self.library_preset)
    if os.path.exists(path):
        import json
        from . import preset_handler

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not preset_handler.load_preset_into_jobs_manager(self, data):
                raise ValueError("Unsupported preset schema")
        except Exception as e:
            logger.error(f"Failed to load preset from library: {e}")
        finally:
            # Allow retrying the same preset after either success or failure.
            self.library_preset = "NONE"


def get_library_preset_items(self, context):
    """Scan library path and return items with icons for the UI gallery."""
    items = [("NONE", "No Presets", "Select a folder in preferences", 0)]
    if not context:
        return items

    package_name = __package__.split(".")[0] if "." in __package__ else __package__
    prefs = context.preferences.addons.get(package_name)
    if not prefs or not prefs.preferences.library_path:
        return items

    library_path = Path(prefs.preferences.library_path)
    if not library_path.exists():
        return items

    from .core import thumbnail_manager

    thumbnail_manager.get_preview_collection("presets")

    found_items = []
    # Find all .json files
    for f in library_path.glob("*.json"):
        name = f.stem
        # Icon ID from thumbnail manager (0 if no matching png)
        icon_id = thumbnail_manager.get_icon_id(name)
        found_items.append(
            (str(f.resolve()), name, f"Load {name}", icon_id, len(found_items))
        )

    return found_items if found_items else items


class BakeJobs(bpy.types.PropertyGroup):
    debug_mode: props.BoolProperty(
        name="Debug Mode", default=False, update=update_debug_mode
    )

    # Roadmap 2.3: Visual Preset Library
    library_preset: props.EnumProperty(
        name="Library",
        items=get_library_preset_items,
        update=update_library_preset,
        description="Visual Preset Gallery",
    )

    jobs: props.CollectionProperty(type=BakeJob)
    job_index: props.IntProperty(name="Index", default=0)
    node_bake_settings: props.PointerProperty(type=BakeNodeSettings)
    bake_result_settings: props.PointerProperty(type=BakeResultSettings)

    open_inputs: props.BoolProperty(default=False)
    open_channels: props.BoolProperty(default=False)
    open_saves: props.BoolProperty(default=False)
    open_other: props.BoolProperty(default=False)
