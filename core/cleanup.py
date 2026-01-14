import bpy
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

def log_cleanup_detail(message):
    """Log details to a persistent file in the addon directory."""
    try:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
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
        if protection_img:
            for mat in bpy.data.materials:
                if not mat.use_nodes or not mat.node_tree: continue
                nodes_to_remove = [n for n in mat.node_tree.nodes 
                                  if n.bl_idname == 'ShaderNodeTexImage' and n.image == protection_img]
                for n in nodes_to_remove:
                    mat_name = mat.name
                    mat.node_tree.nodes.remove(n)
                    count_nodes += 1
                    details.append(f"Removed Protection Node from Material '{mat_name}'")

        # 3. Clean up protection images
        for img in list(bpy.data.images):
            if img.name.startswith("BT_Protection_Dummy"):
                img_name = img.name
                bpy.data.images.remove(img)
                count_images += 1
                details.append(f"Removed Protection Image '{img_name}'")
                
        # 4. Reset UI States
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
