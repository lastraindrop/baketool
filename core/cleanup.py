import bpy
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

def log_cleanup_detail(message):
    """Log details to a persistent file in the system temp directory."""
    try:
        # Use system temp directory to avoid permission issues
        log_dir = os.path.join(bpy.app.tempdir, "baketool_logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_path = os.path.join(log_dir, "cleanup_history.log")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        logger.error(f"Failed to write cleanup log: {e}")

class BAKETOOL_OT_EmergencyCleanup(bpy.types.Operator):
    """Clean up temporary data left behind after a crash or interrupted bake."""
    bl_idname = "bake.emergency_cleanup"
    bl_label = "Clean Up Bake Junk"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        count_layers = 0
        count_images = 0
        count_nodes = 0
        
        details = []
        details.append("--- Manual Cleanup Started ---")
        
        # 1. Clean up temporary UV layers
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and hasattr(obj.data, 'uv_layers'):
                for i in range(len(obj.data.uv_layers)-1, -1, -1):
                    uv = obj.data.uv_layers[i]
                    if uv.name == "BT_Bake_Temp_UV":
                        name = obj.name
                        obj.data.uv_layers.remove(uv)
                        count_layers += 1
                        details.append(f"Removed UV Layer 'BT_Bake_Temp_UV' from Object '{name}'")
        
        # 2. Clean up protection nodes in materials
        protection_img = bpy.data.images.get("BT_Protection_Dummy")
        for mat in bpy.data.materials:
            if not mat.use_nodes or not mat.node_tree: continue
            
            nodes_to_remove = []
            for n in mat.node_tree.nodes:
                # Check by Image reference
                if n.bl_idname == 'ShaderNodeTexImage' and protection_img and n.image == protection_img:
                    nodes_to_remove.append(n)
                # Check by Name/Label (Fallback if image is already gone)
                elif n.name == "BT_Protection_Node" or n.label == "BT Protection":
                    nodes_to_remove.append(n)
            
            for n in nodes_to_remove:
                mat_name = mat.name
                try:
                    mat.node_tree.nodes.remove(n)
                    count_nodes += 1
                    details.append(f"Removed Protection Node from Material '{mat_name}'")
                except:
                    pass

        # 3. Clean up protection images and other bake-temp images
        for img in list(bpy.data.images):
            if img.name.startswith("BT_Protection_Dummy") or img.name.startswith("BT_TEMP_"):
                img_name = img.name
                try:
                    bpy.data.images.remove(img)
                    count_images += 1
                    details.append(f"Removed Temp/Protection Image '{img_name}'")
                except:
                    pass

        # 4. Clean up temporary attributes (ID Maps)
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and hasattr(obj.data, 'attributes'):
                for i in range(len(obj.data.attributes)-1, -1, -1):
                    attr = obj.data.attributes[i]
                    if attr.name.startswith("BT_ATTR_"):
                        attr_name = attr.name
                        obj.data.attributes.remove(attr)
                        details.append(f"Removed Attribute '{attr_name}' from Object '{obj.name}'")
                
        # 5. Reset UI States
        context.scene.is_baking = False
        context.scene.bake_status = "Idle"
        context.scene.bake_progress = 0.0
        
        summary = f"Summary: {count_layers} Layers, {count_nodes} Nodes, {count_images} Images cleaned."
        details.append(summary)
        details.append("--- Cleanup Finished ---")
        
        # Write to log file
        for line in details:
            log_cleanup_detail(line)
            
        logger.info(summary)
        self.report({'INFO'}, summary)
        return {'FINISHED'}
