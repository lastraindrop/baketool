"""BVH-based cage overlap analysis for selected-to-active baking."""
import bpy
import bmesh
from mathutils.bvhtree import BVHTree
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class CageAnalyzer:
    """Provides tools for analyzing cage-to-source mesh proximity and quality.

    Uses raycasting to identify areas where a cage extrusion might fail to
    capture high-poly detail or intersect improperly.
    """

    @staticmethod
    def run_raycast_analysis(
        context: bpy.types.Context,
        low_obj: bpy.types.Object,
        high_objects: List[bpy.types.Object],
        extrusion: float = 0.1,
        auto_switch_vp: bool = False,
    ) -> Tuple[bool, str]:
        """Perform visual cage analysis using vertex color heatmaps.

        Highlights vertices on the low poly where rays fail to hit the high poly,
        indicating potential baking artifacts.

        Args:
            context: Blender context.
            low_obj: The low-poly mesh object (target).
            high_objects: List of source mesh objects.
            extrusion: Raycast distance starting from normal-offset positions.
            auto_switch_vp: If True, automatically switches viewport to Vertex Paint.

        Returns:
            Tuple[bool, str]: (Success flag, descriptive status message).
        """
        if not low_obj or low_obj.type != "MESH" or not high_objects:
            return False, "Target or source objects invalid."

        depsgraph = context.evaluated_depsgraph_get()

        # 1. Build BVH Trees for High objects
        # Note: BVHTree.FromBMesh creates an independent tree structure,
        # it does not hold references to the source BMesh, so freeing
        # BMesh after BVHTree creation is safe.
        bvh_trees = []
        for obj in high_objects:
            if obj.type == "MESH" and not obj.hide_render:
                bm = bmesh.new()
                try:
                    bm.from_object(obj, depsgraph)
                    bm.transform(obj.matrix_world)
                    bvh = BVHTree.FromBMesh(bm)
                    bvh_trees.append(bvh)
                except (RuntimeError, ValueError) as e:
                    logger.warning(f"Failed to build BVH for {obj.name}: {e}")
                finally:
                    bm.free()

        if not bvh_trees:
            return False, "No valid high poly geometry found."

        # 2. Iterate low obj vertices and raycast
        low_matrix = low_obj.matrix_world.copy()
        mesh = low_obj.data

        # Ensure working on Object Mode
        if context.object and context.object.mode != "OBJECT":
            try:
                bpy.ops.object.mode_set(mode="OBJECT")
            except (RuntimeError, AttributeError):
                pass

        # Deal with Vertex Colors (Color Attributes in 3.2+)
        vcol_name = "BT_CAGE_ERROR"

        # Compatibility layer: use color_attributes if available (Blender 3.2+)
        if hasattr(mesh, "color_attributes"):
            vcol = mesh.color_attributes.get(vcol_name)
            if not vcol:
                vcol = mesh.color_attributes.new(
                    name=vcol_name, type="BYTE_COLOR", domain="CORNER"
                )
            mesh.color_attributes.active = vcol
            color_data = vcol.data
        else:
            # Fallback for <3.2
            vcol = mesh.vertex_colors.get(vcol_name)
            if not vcol:
                vcol = mesh.vertex_colors.new(name=vcol_name)
            mesh.vertex_colors.active = vcol
            color_data = vcol.data

        error_count = 0
        total_verts = len(mesh.vertices)
        vert_errors = [False] * total_verts

        for v in mesh.vertices:
            world_co = low_matrix @ v.co
            world_no = (low_matrix.to_3x3() @ v.normal).normalized()

            # Cage shoots ray INWARDS (from extrude pos towards original pos)
            ray_origin = world_co + (world_no * extrusion)
            ray_dir = -world_no

            hit_any = False
            for bvh in bvh_trees:
                location, normal, index, distance = bvh.ray_cast(ray_origin, ray_dir)
                # Give some tolerance. The ray travels inwards, typically
                # should hit within extrusion distance, maybe slight penetration (max 2*extrusion)
                if location is not None and distance <= extrusion * 2.5:
                    hit_any = True
                    break

            if not hit_any:
                vert_errors[v.index] = True
                error_count += 1

        # Apply colors to loops
        for poly in mesh.polygons:
            for loop_index in poly.loop_indices:
                v_idx = mesh.loops[loop_index].vertex_index
                if vert_errors[v_idx]:
                    color_data[loop_index].color = (1.0, 0.0, 0.0, 1.0)  # Red
                else:
                    color_data[loop_index].color = (1.0, 1.0, 1.0, 1.0)  # White

        # 3. Viewport Feedback
        if auto_switch_vp:
            prev_act = context.active_object
            prev_mode = prev_act.mode if prev_act else "OBJECT"

            bpy.ops.object.select_all(action="DESELECT")
            low_obj.select_set(True)
            context.view_layer.objects.active = low_obj
            try:
                bpy.ops.object.mode_set(mode="VERTEX_PAINT")
                screen = getattr(context, "screen", None)
                if screen:
                    for area in screen.areas:
                        if area.type == "VIEW_3D":
                            for space in area.spaces:
                                if space.type == "VIEW_3D":
                                    space.shading.type = "SOLID"
                                    space.shading.color_type = "VERTEX"
            except (RuntimeError, AttributeError) as e:
                logger.warning(f"Failed to switch Viewport to Vertex Paint: {e}")
                try:
                    context.view_layer.objects.active = prev_act
                    bpy.ops.object.mode_set(mode=prev_mode)
                except (ReferenceError, RuntimeError, AttributeError):
                    pass

        return (
            True,
            f"Found {error_count} potential baking errors out of {total_verts} vertices.",
        )
