import bpy
import logging
from datetime import datetime
from pathlib import Path
from ..constants import SYSTEM_NAMES

logger = logging.getLogger(__name__)

def log_cleanup_detail(message):
    """Log details to a persistent file in the system temp directory."""
    try:
        # Use system temp directory to avoid permission issues
        log_dir = Path(bpy.app.tempdir) / "baketool_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "cleanup_history.log"
        
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
                    if uv.name == SYSTEM_NAMES['TEMP_UV']:
                        name = obj.name
                        obj.data.uv_layers.remove(uv)
                        count_layers += 1
                        details.append(f"Removed UV Layer '{SYSTEM_NAMES['TEMP_UV']}' from Object '{name}'")
        
        # 2. Clean up protection nodes in materials
        protection_img = bpy.data.images.get(SYSTEM_NAMES['DUMMY_IMG'])
        for mat in bpy.data.materials:
            if not mat.use_nodes or not mat.node_tree: continue
            
            nodes_to_remove = []
            for n in mat.node_tree.nodes:
                # 1. Primary safety check: GUID/Tag injected by our tool
                is_tagged = n.get("is_bt_temp", False)
                
                # 2. Check by Image reference or name prefix
                has_prot_img = False
                if n.bl_idname == 'ShaderNodeTexImage' and n.image:
                    img_name = n.image.name
                    if protection_img and n.image == protection_img:
                        has_prot_img = True
                    elif img_name.startswith(SYSTEM_NAMES['TEMP_IMG_PREFIX']):
                        has_prot_img = True
                
                # 3. Check by Name/Label (Fallback if image is already gone or legacy)
                has_prot_name = n.name == SYSTEM_NAMES['PROTECTION_NODE'] or n.label == SYSTEM_NAMES['PROTECTION_LABEL']
                
                # 4. Heuristic for session nodes: Orphaned Emission nodes with no label but specific structure
                
                if is_tagged or has_prot_img or has_prot_name:
                    nodes_to_remove.append(n)
            
            for n in nodes_to_remove:
                mat_name = mat.name
                try:
                    mat.node_tree.nodes.remove(n)
                    count_nodes += 1
                    details.append(f"Removed Protection Node from Material '{mat_name}'")
                except Exception:
                    pass

        # 3. Clean up protection images and other bake-temp images
        for img in list(bpy.data.images):
            if img.name.startswith(SYSTEM_NAMES['DUMMY_IMG']) or img.name.startswith(SYSTEM_NAMES['TEMP_IMG_PREFIX']):
                img_name = img.name
                try:
                    bpy.data.images.remove(img)
                    count_images += 1
                    details.append(f"Removed Temp/Protection Image '{img_name}'")
                except Exception:
                    pass

        # 4. Clean up temporary attributes (ID Maps)
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and hasattr(obj.data, 'attributes'):
                for i in range(len(obj.data.attributes)-1, -1, -1):
                    attr = obj.data.attributes[i]
                    if attr.name.startswith(SYSTEM_NAMES['ATTR_PREFIX']):
                        attr_name = attr.name
                        obj.data.attributes.remove(attr)
                        details.append(f"Removed Attribute '{attr_name}' from Object '{obj.name}'")
                
        # 5. Reset UI States using central manager
        from ..state_manager import BakeStateManager
        BakeStateManager().reset_ui_state(context)
        
        summary = f"Summary: {count_layers} Layers, {count_nodes} Nodes, {count_images} Images cleaned."
        details.append(summary)
        details.append("--- Cleanup Finished ---")
        
        # Write to log file
        for line in details:
            log_cleanup_detail(line)
            
        logger.info(summary)
        self.report({'INFO'}, summary)
        return {'FINISHED'}
