"""Viewport preview material management and baked-result material creation."""
import bpy
import logging
from typing import Any, Dict, Optional
from ..constants import (
    BSDF_COMPATIBILITY_MAP,
    SYSTEM_NAMES,
    CHANNEL_BAKE_INFO,
    APPLY_RESULT_CHANNEL_MAP,
)

logger = logging.getLogger(__name__)

PREVIEW_MAT_NAME = SYSTEM_NAMES["PREVIEW_MAT"]
_NODE_PROPERTY_COPY_SKIP = {
    "rna_type",
    "bl_rna",
    "type",
    "bl_idname",
    "bl_label",
    "bl_description",
    "bl_icon",
    "bl_static_type",
    "inputs",
    "outputs",
    "internal_links",
    "dimensions",
    "name",
    "color",
    "select",
    "show_options",
    "show_preview",
    "show_texture",
    "parent",
    "location",
    "width",
    "height",
}

def create_preview_material(obj, s):
    """Creates or updates a temporary preview material for the object.

    Maps PBR sockets to the packing logic (RGBA) to allow real-time
    viewport visualization of the final channel packing.

    Args:
        obj: The object to apply the preview to.
        s: BakeJobSetting with packing configuration.

    Returns:
        bpy.types.Material: The created or updated preview material.
    """
    if not obj or obj.type != 'MESH':
        return None

    # Get or create preview material
    mat = bpy.data.materials.get(PREVIEW_MAT_NAME)
    if not mat:
        mat = bpy.data.materials.new(name=PREVIEW_MAT_NAME)

    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Create output and principled bsdf for base view
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (600, 0)

    # Create the Packing Logic (Combine RGBA)
    combine = nodes.new('ShaderNodeCombineColor')
    combine.location = (400, 0)

    # HP-5: Emission node between Color output and Shader input
    emission = nodes.new('ShaderNodeEmission')
    emission.location = (550, 0)
    links.new(combine.outputs[0], emission.inputs[0])
    links.new(emission.outputs[0], output.inputs[0])

    # Source mapping
    source_mat = obj.active_material
    if not source_mat or not source_mat.use_nodes:
        # Fallback to simple colors if no source nodes
        return mat

    # Find the main Principled BSDF in the source material to pull data from
    source_bsdf = None
    for n in source_mat.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            source_bsdf = n
            break

    if not source_bsdf:
        return mat

    # Helper to map a channel (R, G, B, A) to a BSDF socket
    def link_channel(pref_attr, combine_input_idx):
        chan_id = getattr(s, pref_attr)
        if chan_id == 'NONE':
            return

        # Get compatible socket names from map
        socket_names = BSDF_COMPATIBILITY_MAP.get(chan_id, [])
        for name in socket_names:
            if name in source_bsdf.inputs:
                socket = source_bsdf.inputs[name]
                # Nodes cannot be linked across material trees. Copy the direct source node
                # when possible; deeper source subtrees intentionally remain out of scope.
                if socket.is_linked:
                    # HP-8: Correctly capture the output socket index from the source
                    from_socket = socket.links[0].from_socket
                    from_node = from_socket.node

                    # Try to find the matching socket index
                    out_idx = 0
                    for i, o_sock in enumerate(from_node.outputs):
                        if o_sock == from_socket:
                            out_idx = i
                            break

                    new_node = nodes.new(from_node.bl_idname)
                    new_node.location = (-200, (1-combine_input_idx)*200)

                    for prop in from_node.bl_rna.properties:
                        if (
                            not prop.is_readonly
                            and prop.identifier not in _NODE_PROPERTY_COPY_SKIP
                        ):
                            try:
                                setattr(new_node, prop.identifier, getattr(from_node, prop.identifier))
                            except (AttributeError, TypeError) as error:
                                logger.debug(
                                    "Could not copy preview node property %s: %s",
                                    prop.identifier,
                                    error,
                                )

                    if out_idx < len(new_node.outputs):
                        links.new(new_node.outputs[out_idx], combine.inputs[combine_input_idx])
                else:
                    # Constant value
                    val_node = nodes.new('ShaderNodeValue')
                    # Use hasattr to handle bpy_prop_array (color/vectors)
                    dv = socket.default_value
                    if hasattr(dv, "__iter__"):
                        val_node.outputs[0].default_value = dv[0]
                    else:
                        val_node.outputs[0].default_value = dv
                    val_node.location = (-200, (1-combine_input_idx)*200)
                    links.new(val_node.outputs[0], combine.inputs[combine_input_idx])

    link_channel('pack_r', 0)
    link_channel('pack_g', 1)
    link_channel('pack_b', 2)
    if len(combine.inputs) > 3:
        link_channel('pack_a', 3)

    return mat

def apply_preview(obj, setting):
    """Apply the ORM preview material to the given object."""
    if obj is None or obj.type != 'MESH':
        return

    # Idempotency: rebuilding from the preview itself would destroy the
    # source node logic captured on the first apply.
    if obj.active_material and obj.active_material.name == PREVIEW_MAT_NAME:
        return

    if not obj.get("_bt_orig_mat_name"):
        if obj.active_material:
            obj["_bt_orig_mat_name"] = obj.active_material.name

    preview_mat = create_preview_material(obj, setting)
    if preview_mat:
        obj.active_material = preview_mat

def remove_preview(obj):
    """Restore original material."""
    if obj is None:
        return
    orig_mat_name = obj.get("_bt_orig_mat_name")
    if orig_mat_name:
        orig_mat = bpy.data.materials.get(orig_mat_name)
        if orig_mat:
            obj.active_material = orig_mat
        del obj["_bt_orig_mat_name"]

    # Cleanup temp material if no one uses it
    mat = bpy.data.materials.get(PREVIEW_MAT_NAME)
    if mat and mat.users == 0:
        bpy.data.materials.remove(mat)


# ---------------------------------------------------------------------------
# Baked-result material creation (migrated from core/common.py per CM.2)
# ---------------------------------------------------------------------------


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
        except (ReferenceError, RuntimeError, AttributeError) as e:
            logger.debug(
                f"BakeNexus: Result collection linkage failed (likely already linked): {e}"
            )

    # 1. Reuse existing baked object if possible to save memory
    target_name = f"{task_base_name}_Baked"
    new_obj = bpy.data.objects.get(target_name)
    if new_obj and not new_obj.get("is_bt_result", False):
        new_obj = None

    if new_obj:
        old_data = new_obj.data
        new_obj.data = original_obj.data.copy()
        if old_data and old_data.users == 0:
            try:
                bpy.data.meshes.remove(old_data, do_unlink=True)
            except (ReferenceError, RuntimeError) as e:
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

    new_obj["is_bt_result"] = True

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

    non_color_channels = {
        k for k, v in CHANNEL_BAKE_INFO.items() if v.get("def_cs") == "Non-Color"
    }

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
