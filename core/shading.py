import bpy
import logging
from ..constants import BSDF_COMPATIBILITY_MAP

logger = logging.getLogger(__name__)

PREVIEW_MAT_NAME = "BT_Packing_Preview"

def create_preview_material(obj, s):
    """
    Creates or updates a temporary preview material for the object.
    Maps PBR sockets to the packing logic (RGBA).
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
    links.new(combine.outputs[0], output.inputs[0])
    
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
                # If connected, copy the node over or use a proxy
                # For simplicity in this preview, we create a proxy node that pulls the value
                # or we literally copy the subtree (more complex).
                # KISS: We'll just use the default value or Attribute if needed.
                # In a real implementation, we would traverse the tree.
                # For this roadmap demo, we'll use a specialized 'Value' or 'Attribute' node.
                
                # Actually, in Blender UI preview, we want to see the effect of the PACKING.
                # If 'Roughness' is packed into 'Green', we should see the roughness map as green.
                
                # To be robust, we'd need to link the same input nodes to our new material.
                # Since we can't easily link across materials, we duplicate the input node.
                if socket.is_linked:
                    from_node = socket.links[0].from_node
                    new_node = nodes.new(from_node.bl_idname)
                    new_node.location = (-200, (1-combine_input_idx)*200)
                    # 安全属性复制：仅复制已知安全的用户可编辑属性
                    safe_skip = {'rna_type', 'bl_rna', 'type', 'bl_idname', 'bl_label', 
                                 'bl_description', 'bl_icon', 'bl_static_type',
                                 'inputs', 'outputs', 'internal_links', 'dimensions',
                                 'name', 'color', 'select', 'show_options', 'show_preview',
                                 'show_texture', 'parent', 'location', 'width', 'height'}
                    for prop in from_node.bl_rna.properties:
                        if not prop.is_readonly and prop.identifier not in safe_skip:
                            try:
                                setattr(new_node, prop.identifier, getattr(from_node, prop.identifier))
                            except Exception:
                                pass
                    links.new(new_node.outputs[0], combine.inputs[combine_input_idx])
                else:
                    # Constant value
                    val_node = nodes.new('ShaderNodeValue')
                    val_node.outputs[0].default_value = socket.default_value if not isinstance(socket.default_value, (list, tuple)) else socket.default_value[0]
                    val_node.location = (-200, (1-combine_input_idx)*200)
                    links.new(val_node.outputs[0], combine.inputs[combine_input_idx])

    link_channel('pack_r', 0)
    link_channel('pack_g', 1)
    link_channel('pack_b', 2)
    link_channel('pack_a', 3)
    
    return mat

def apply_preview(obj, setting):
    """Apply the ORM preview material to the given object."""
    if obj is None or obj.type != 'MESH':
        return
        
    if not obj.get("_bt_orig_mat_name"):
        if obj.active_material:
            obj["_bt_orig_mat_name"] = obj.active_material.name
    
    preview_mat = create_preview_material(obj, setting)
    if preview_mat:
        obj.active_material = preview_mat

def remove_preview(obj):
    """Restore original material."""
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
