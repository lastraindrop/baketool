import bpy
import logging
import traceback
from collections import namedtuple
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple
from ..constants import (
    BAKE_CHANNEL_INFO,
    BSDF_COMPATIBILITY_MAP,
    SOCKET_DEFAULT_TYPE,
    APPLY_RESULT_CHANNEL_MAP,
    SYSTEM_NAMES,
)

logger = logging.getLogger(__name__)

ValidationResult = namedtuple("ValidationResult", ["success", "message", "job_name"])


def log_error(
    context: bpy.types.Context,
    message: str,
    state_mgr: Optional[Any] = None,
    include_traceback: bool = False,
) -> None:
    """Log error to multiple channels: Python logger, scene UI, and state file.

    Args:
        context: Blender context for scene access.
        message: Error message to log.
        state_mgr: Optional state manager for crash recovery.
        include_traceback: Whether to include full Python traceback.
    """
    technical_msg = message
    if include_traceback:
        technical_msg = f"{message}\n{traceback.format_exc()}"

    logger.error(technical_msg)

    if context and hasattr(context, "scene"):
        context.scene.bake_error_log += f"{message}\n"

    if state_mgr:
        try:
            state_mgr.log_error(technical_msg)
        except (IOError, OSError) as e:
            logger.debug(f"Failed to persist state error: {e}")


def get_safe_base_name(
    setting: Any,
    obj: bpy.types.Object,
    mat: Optional[bpy.types.Material] = None,
    is_batch: bool = False,
) -> str:
    """Generate a safe base name for baked textures based on naming settings.

    Args:
        setting: BakeJobSetting with naming configuration.
        obj: Target object being baked.
        mat: Material being baked (for material split modes).
        is_batch: Whether this is part of a batch bake.

    Returns:
        Clean base name suitable for file/image naming.
    """
    mode = setting.bake_mode
    m = setting.name_setting
    base = "Bake"

    if m == "CUSTOM":
        base = setting.custom_name
        if is_batch:
            suffix = f"_{obj.name}"
            if mode == "SPLIT_MATERIAL" and mat:
                suffix += f"_{mat.name}"
            base += suffix
    elif m == "OBJECT":
        base = obj.name
        if mode == "SPLIT_MATERIAL" and mat:
            base = f"{base}_{mat.name}"
    elif m == "MAT":
        base = mat.name if mat else "NoMat"
        if (is_batch or mode == "SPLIT_MATERIAL") and obj:
            base = f"{obj.name}_{base}"
    elif m == "OBJ_MAT":
        base = f"{obj.name}_{mat.name if mat else 'NoMat'}"

    return bpy.path.clean_name(base)


def check_objects_uv(objects: List[bpy.types.Object]) -> List[str]:
    """Return a list of object names that are missing UV layers.

    Args:
        objects: List of Blender objects to check.

    Returns:
        List of object names without UV layers.
    """
    return [
        obj.name for obj in objects if obj.type == "MESH" and not obj.data.uv_layers
    ]


def reset_channels_logic(setting: Any) -> None:
    """Reset channels to default configuration based on bake type.

    Syncs the channel collection with BAKE_CHANNEL_INFO definitions,
    removing invalid channels and adding missing ones.

    Args:
        setting: BakeJobSetting with channels collection.
    """
    defs = []
    b_type = setting.bake_type

    from . import compat

    is_v4 = compat.is_blender_4() or compat.is_blender_5()
    key = ("BSDF_4" if is_v4 else "BSDF_3") if b_type == "BSDF" else b_type
    defs.extend(BAKE_CHANNEL_INFO.get(key, []))

    if setting.use_light_map:
        defs.extend(BAKE_CHANNEL_INFO.get("LIGHT", []))
    if setting.use_mesh_map:
        defs.extend(BAKE_CHANNEL_INFO.get("MESH", []))
    if setting.use_extension_map:
        defs.extend(BAKE_CHANNEL_INFO.get("EXTENSION", []))

    target_ids = {d["id"]: d for d in defs}

    # 1. Update existing and remove invalid (destructive sync for lean property data)
    for i in range(len(setting.channels) - 1, -1, -1):
        c = setting.channels[i]
        if c.id in target_ids:
            c.valid_for_mode = True
            c.name = target_ids[c.id]["name"]
        else:
            setting.channels.remove(i)

    # 2. Build map AFTER destructive sync to correctly detect missing channels
    existing_map = {c.id: c for c in setting.channels}

    # 3. Add missing
    for d in defs:
        d_id = d["id"]
        if d_id not in existing_map:
            new_chan = setting.channels.add()
            new_chan.id = d_id
            new_chan.name = d["name"]
            new_chan.valid_for_mode = True
            defaults = d.get("defaults", {})
            for k, v in defaults.items():
                if hasattr(new_chan, k):
                    setattr(new_chan, k, v)


def manage_objects_logic(
    s: Any,
    action: str,
    sel: List[bpy.types.Object],
    act: Optional[bpy.types.Object] = None,
) -> None:
    """Manage bake object list with various actions.

    Args:
        s: BakeJobSetting with bake_objects collection.
        action: Operation to perform (SET, ADD, REMOVE, CLEAR, SET_ACTIVE, SMART_SET).
        sel: Selected objects for the operation.
        act: Active object (for SELECT_ACTIVE mode). Defaults to None.
    """

    def add(o):
        if not any(i.bakeobject == o for i in s.bake_objects):
            from .uv_manager import detect_object_udim_tile

            new = s.bake_objects.add()
            new.bakeobject = o
            new.udim_tile = detect_object_udim_tile(o)

    if action == "SET":
        s.bake_objects.clear()
        targets = sel
        if s.bake_mode == "SELECT_ACTIVE" and act and act in targets:
            s.active_object = act
            targets = [o for o in targets if o != act]
        for o in targets:
            add(o)
    elif action == "ADD":
        for o in sel:
            if s.bake_mode == "SELECT_ACTIVE" and o == s.active_object:
                continue
            add(o)
    elif action == "REMOVE":
        rem = set(sel)
        for i in range(len(s.bake_objects) - 1, -1, -1):
            if s.bake_objects[i].bakeobject in rem:
                s.bake_objects.remove(i)
    elif action == "CLEAR":
        s.bake_objects.clear()
    elif action == "SET_ACTIVE":
        if act:
            s.active_object = act
    elif action == "SMART_SET":
        if act:
            s.active_object = act
        s.bake_objects.clear()
        for o in sel:
            if o != act:
                add(o)


def manage_channels_logic(
    target: str, action_type: str, bj: Any
) -> Tuple[bool, str]:
    """Manage generic collection items (jobs, channels, objects).

    Args:
        target: Collection type (jobs_channel, job_custom_channel, bake_objects).
        action_type: Operation (ADD, DELETE, CLEAR, UP, DOWN).
        bj: BakeJobs manager object.

    Returns:
        Tuple of (success: bool, error_message: str).
    """
    job_index = bj.job_index if bj.jobs else -1
    if job_index < 0 or job_index >= len(bj.jobs):
        job_index = 0 if bj.jobs else -1
        # M-05: Update the actual property to stay in sync
        bj.job_index = job_index
    job = bj.jobs[job_index] if 0 <= job_index < len(bj.jobs) else None

    dispatch = {
        "jobs_channel": (bj.jobs, "job_index", bj),
        "job_custom_channel": (
            job.custom_bake_channels,
            "custom_bake_channels_index",
            job,
        )
        if job
        else None,
        "bake_objects": (job.setting.bake_objects, "active_object_index", job.setting)
        if job
        else None,
    }

    entry = dispatch.get(target)
    if not entry:
        return False, f"Invalid target: {target}"

    coll, attr, parent = entry
    if parent is None:
        return False, "Action unavailable: Parent data missing"

    idx = getattr(parent, attr)

    if action_type == "ADD":
        success, item = manage_collection_item(coll, "ADD", idx)
        if success and target == "jobs_channel":
            item.name = f"Job {len(coll)}"
            s = item.setting
            s.bake_type = "BSDF"
            s.bake_mode = "SINGLE_OBJECT"
            reset_channels_logic(s)
            for c in s.channels:
                if c.id in {"color", "combine", "normal"}:
                    c.enabled = True
    else:
        success, _ = manage_collection_item(coll, action_type, idx, parent, attr)

    return success, ""


def manage_collection_item(
    collection: Any,
    action: str,
    index: int,
    parent_obj: Optional[Any] = None,
    index_prop: str = "",
) -> Tuple[bool, Optional[Any]]:
    """Generic helper to manage items in a Blender CollectionProperty.

    Args:
        collection: Blender CollectionProperty to modify.
        action: Operation (ADD, DELETE, CLEAR, UP, DOWN).
        index: Current selected index.
        parent_obj: Parent object with index property (for auto-update).
        index_prop: Name of index property on parent.

    Returns:
        Tuple of (success, item_or_None).
    """
    if action == "ADD":
        return True, collection.add()
    elif action == "DELETE":
        if len(collection) > 0 and 0 <= index < len(collection):
            collection.remove(index)
            if parent_obj and index_prop:
                setattr(parent_obj, index_prop, max(0, index - 1))
            return True, None
    elif action == "CLEAR":
        collection.clear()
        if parent_obj and index_prop:
            setattr(parent_obj, index_prop, 0)
        return True, None
    elif action in {"UP", "DOWN"}:
        if action == "UP" and index > 0:
            target_idx = index - 1
        elif action == "DOWN" and index < len(collection) - 1:
            target_idx = index + 1
        else:
            return False, None
        collection.move(index, target_idx)
        if parent_obj and index_prop:
            setattr(parent_obj, index_prop, target_idx)
        return True, None
    return False, None


@contextmanager
def safe_context_override(
    context: bpy.types.Context,
    active_object: Optional[bpy.types.Object] = None,
    selected_objects: Optional[List[bpy.types.Object]] = None,
):
    """Context manager for safe temporary context override.

    Args:
        context: Base Blender context.
        active_object: Object to set as active.
        selected_objects: Objects to set as selected.

    Yields:
        The overridden context.
    """
    kw = {}
    if active_object:
        kw["active_object"] = active_object
        kw["object"] = active_object
    if selected_objects:
        selected_objects = list(selected_objects)
        if active_object and active_object not in selected_objects:
            selected_objects.append(active_object)
        kw["selected_objects"] = selected_objects
        kw["selected_editable_objects"] = selected_objects

    with context.temp_override(**kw):
        yield


class SceneSettingsContext:
    """Context manager for temporary scene/render setting changes.

    Saves current values and restores them on exit, handling errors gracefully.

    Example:
        with SceneSettingsContext("cycles", {"samples": 128, "device": "GPU"}):
            # Render with custom settings
            bpy.ops.render.render()
        # Original settings restored
    """

    def __init__(
        self,
        category: str,
        settings: Dict[str, Any],
        scene: Optional[bpy.types.Scene] = None,
    ):
        """Initialize settings context manager.

        Args:
            category: Settings category (scene, cycles, image, cm, bake).
            settings: Dict of property names to values.
            scene: Target scene. Uses bpy.context.scene if None.
        """
        import bpy

        self.category = category
        self.settings = settings
        self.scene = scene
        self.original = {}
        self.attr_map = {
            "scene": {
                "res_x": "resolution_x",
                "res_y": "resolution_y",
                "res_pct": "resolution_percentage",
            },
        }

    def _get_target(self):
        import bpy

        scene = self.scene
        if not scene:
            scene = bpy.context.scene
        if not scene:
            return None
        if self.category == "scene":
            return scene.render
        if self.category == "cycles":
            return scene.cycles
        if self.category == "image":
            return scene.render.image_settings
        if self.category == "cm":
            return scene.view_settings
        if self.category == "bake":
            from . import compat

            if compat.is_blender_5() and hasattr(scene.render, "bake"):
                return scene.render.bake
            return scene.render
        return None

    def __enter__(self):
        target = self._get_target()
        if not target or not self.settings:
            return self

        mapping = self.attr_map.get(self.category, {})
        for k, v in self.settings.items():
            real_key = mapping.get(k, k)
            if hasattr(target, real_key):
                self.original[real_key] = getattr(target, real_key)
                # Skip empty strings for Enum properties to prevent "enum '' not found" errors
                if v is not None and v != "":
                    try:
                        setattr(target, real_key, v)
                    except Exception as e:
                        logger.warning(
                            f"Failed to set {self.category}.{real_key} to '{v}': {e}"
                        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        target = self._get_target()
        if not target:
            return
        for k, v in self.original.items():
            try:
                setattr(target, k, v)
            except (AttributeError, TypeError, ValueError, RuntimeError) as e:
                logger.debug(f"Restore failed for {k}: {e}")


def apply_baked_result(
    context: bpy.types.Context,
    original_obj: bpy.types.Object,
    task_images: Dict[str, bpy.types.Image],
    setting: Any,
    task_base_name: str,
) -> Optional[bpy.types.Object]:
    """Create or update a baked result object with applied textures.

    Creates a new object with baked materials applied, reusing existing
    result objects when possible to save memory.

    Args:
        context: Blender context.
        original_obj: Source object that was baked.
        task_images: Dict mapping channel IDs to baked images.
        setting: BakeJobSetting with apply configuration.
        task_base_name: Base name for the result object.

    Returns:
        The created or updated result object, or None on failure.
    """
    if not task_images:
        logger.warning("apply_baked_result: No images found to apply.")
        return None
    scene = context.scene
    col = bpy.data.collections.get(
        SYSTEM_NAMES["RESULT_COLLECTION"]
    ) or bpy.data.collections.new(SYSTEM_NAMES["RESULT_COLLECTION"])
    if col.name not in scene.collection.children:
        try:
            scene.collection.children.link(col)
        except Exception as e:
            logger.debug(
                f"BakeNexus: Result collection linkage failed (likely already linked): {e}"
            )

    # 1. Reuse existing baked object if possible to save memory
    target_name = f"{task_base_name}_Baked"
    new_obj = bpy.data.objects.get(target_name)

    if new_obj:
        old_data = new_obj.data
        new_obj.data = original_obj.data.copy()
        if old_data and old_data.users == 0:
            try:
                bpy.data.meshes.remove(old_data, do_unlink=True)
            except Exception as e:
                logger.debug(
                    f"BakeNexus: Failed to remove old baked mesh data {old_data.name}: {e}"
                )
        if col and new_obj.name not in {o.name for o in col.objects}:
            for c in new_obj.users_collection:
                c.objects.unlink(new_obj)
            col.objects.link(new_obj)
    else:
        new_obj = original_obj.copy()
        new_obj.data = original_obj.data.copy()
        new_obj.name = target_name
        for c in new_obj.users_collection:
            c.objects.unlink(new_obj)
        col.objects.link(new_obj)

    first_val = next(iter(task_images.values()))
    if isinstance(first_val, dict):
        orig_mats = [s.material for s in original_obj.material_slots if s.material]
        new_obj.data.materials.clear()
        for i, om in enumerate(orig_mats):
            mat_textures = {}
            for chan_id, mat_dict in task_images.items():
                if om.name in mat_dict:
                    mat_textures[chan_id] = mat_dict[om.name]
            mat = create_simple_baked_material(
                f"{task_base_name}_{om.name}_Baked", mat_textures
            )
            new_obj.data.materials.append(mat)
    else:
        mat = create_simple_baked_material(f"{task_base_name}_Mat", task_images)
        new_obj.data.materials.clear()
        new_obj.data.materials.append(mat)
    return new_obj


def create_simple_baked_material(
    name: str, texture_map: Dict[str, bpy.types.Image]
) -> bpy.types.Material:
    """Create a simple PBR material from baked texture maps.

    Args:
        name: Base name for the material.
        texture_map: Dict mapping channel IDs to image textures.

    Returns:
        Created Principled BSDF material with applied textures.
    """
    import uuid

    unique_name = f"{name}_{uuid.uuid4().hex[:8]}"
    mat = bpy.data.materials.new(name=unique_name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    out.location = (300, 0)
    tree.links.new(bsdf.outputs[0], out.inputs[0])
    y_pos = 0

    # Extended mapping supports standard vs specific IDs
    for chan_id, image in texture_map.items():
        if not image:
            continue
        target_socket = None
        compat_key = APPLY_RESULT_CHANNEL_MAP.get(chan_id)
        if compat_key:
            for p_name in BSDF_COMPATIBILITY_MAP.get(compat_key, []):
                if p_name in bsdf.inputs:
                    target_socket = bsdf.inputs[p_name]
                    break

        if not target_socket and not (chan_id == "normal"):
            continue

        tex = tree.nodes.new("ShaderNodeTexImage")
        tex.image = image
        tex.location = (-600 if chan_id == "normal" else -300, y_pos)
        y_pos -= 280

        # M-15: Derive non-color channels from CHANNEL_BAKE_INFO metadata
        from ..constants import CHANNEL_BAKE_INFO

        non_color_channels = {
            k for k, v in CHANNEL_BAKE_INFO.items() if v.get("def_cs") == "Non-Color"
        }

        if chan_id in non_color_channels:
            try:
                tex.image.colorspace_settings.name = "Non-Color"
            except (AttributeError, RuntimeError) as e:
                logger.debug(
                    f"BakeNexus: Failed to set non-color space on {tex.image.name}: {e}"
                )

        if chan_id == "normal":
            nor = tree.nodes.new("ShaderNodeNormalMap")
            nor.location = (-300, tex.location.y)
            tree.links.new(tex.outputs[0], nor.inputs["Color"])
            if "Normal" in bsdf.inputs:
                tree.links.new(nor.outputs["Normal"], bsdf.inputs["Normal"])
        elif chan_id == "gloss":
            # Invert Gloss to Roughness proxy
            inv = tree.nodes.new("ShaderNodeInvert")
            inv.location = (-150, tex.location.y)
            tree.links.new(tex.outputs[0], inv.inputs[1])
            if target_socket:
                tree.links.new(inv.outputs[0], target_socket)
        elif target_socket:
            tree.links.new(tex.outputs[0], target_socket)

        if chan_id == "alpha" and hasattr(mat, "blend_method"):
            mat.blend_method = "BLEND"
    return mat
