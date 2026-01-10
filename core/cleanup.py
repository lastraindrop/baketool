import bpy
import logging

logger = logging.getLogger(__name__)

class BAKETOOL_OT_EmergencyCleanup(bpy.types.Operator):
    """Clean up temporary data left behind after a crash or interrupted bake."""
    bl_idname = "bake.emergency_cleanup"
    bl_label = "Clean Up Bake Junk"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        count_layers = 0
        count_images = 0
        count_nodes = 0
        
        # 1. Clean up temporary UV layers
        # These are usually named "BT_Bake_Temp_UV"
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and hasattr(obj.data, 'uv_layers'):
                # Iterate in reverse to safely remove
                for i in range(len(obj.data.uv_layers)-1, -1, -1):
                    uv = obj.data.uv_layers[i]
                    if uv.name == "BT_Bake_Temp_UV":
                        obj.data.uv_layers.remove(uv)
                        count_layers += 1
        
        # 2. Clean up protection images
        # These are named "BT_Protection_Dummy"
        for img in bpy.data.images:
            if img.name.startswith("BT_Protection_Dummy"):
                bpy.data.images.remove(img)
                count_images += 1
                
        # 3. Clean up node groups if we created temp ones (future proofing)
        # Currently NodeGraphHandler cleans up mostly, but if we had temp groups:
        # for ng in bpy.data.node_groups:
        #     if ng.name.startswith("BT_Temp"): ...
        
        msg = f"Cleaned: {count_layers} UV Layers, {count_images} Images."
        logger.info(msg)
        self.report({'INFO'}, msg)
        return {'FINISHED'}
