"""Shader node graph manipulation and node-based baking for BakeNexus.

This module provides tools to dynamically modify material node trees during
the baking process, such as inserting temporary emission nodes, managing
links, and providing protection for non-active materials.
"""

import bpy
import logging
from typing import Any, Dict, List, Optional, Tuple

from ..constants import BSDF_COMPATIBILITY_MAP, SOCKET_DEFAULT_TYPE, SYSTEM_NAMES
from . import compat

logger = logging.getLogger(__name__)


def bake_node_to_image(
    context: bpy.types.Context,
    material: bpy.types.Material,
    node: bpy.types.Node,
    settings: Any,
) -> Optional[bpy.types.Image]:
    """Bake a specific shader node output to an image datablock.

    Temporarily routes the node's output through an Emission shader and
    triggers a standard Blender bake.

    Args:
        context: Blender context.
        material: Material containing the target node.
        node: The specific node to bake.
        settings: Configuration object with resolution and margin.

    Returns:
        bpy.types.Image: The resulting baked image, or None if failed.
    """
    from .image_manager import set_image, save_image
    from .common import safe_context_override

    if not (material and node):
        logger.warning("bake_node_to_image: Invalid material or node")
        return None

    img = set_image(f"{material.name}_{node.name}", settings.res_x, settings.res_y)

    # Store original engine
    orig_engine = context.scene.render.engine
    context.scene.render.engine = "CYCLES"

    try:
        with safe_context_override(context, context.active_object):
            with NodeGraphHandler([material]) as h:
                tree = material.node_tree
                out = next(
                    (
                        n
                        for n in tree.nodes
                        if n.bl_idname == "ShaderNodeOutputMaterial"
                        and n.is_active_output
                    ),
                    None,
                )
                if out:
                    emi = h._add_node(
                        material,
                        "ShaderNodeEmission",
                        location=(out.location.x - 200, out.location.y),
                    )
                    tree.links.new(node.outputs[0], emi.inputs[0])
                    tree.links.new(emi.outputs[0], out.inputs[0])

                    # Use compatibility layer for bake settings
                    compat.set_bake_type(context.scene, "EMIT")

                    bpy.ops.object.bake(
                        type="EMIT",
                        margin=settings.margin,
                        use_clear=True,
                        target="IMAGE_TEXTURES",
                    )

                    if settings.use_external_save:
                        save_image(
                            img,
                            settings.external_save_path,
                            file_format=settings.image_settings.external_save_format,
                            color_depth=settings.image_settings.color_depth,
                            color_mode=settings.image_settings.color_mode,
                            quality=settings.image_settings.quality,
                            exr_code=settings.image_settings.exr_code,
                            tiff_codec=settings.image_settings.tiff_codec,
                        )
                    else:
                        img.pack()

        return img
    except (AttributeError, KeyError, ReferenceError) as e:
        logger.exception(f"Node baking failed: {e}")
        return None
    except RuntimeError as e:
        logger.error(f"Bake operation failed: {e}")
        return None
    finally:
        context.scene.render.engine = orig_engine


class NodeGraphHandler:
    """Context manager for shader node graph manipulation during baking.

    Handles temporary node insertion, link management, and automatic cleanup.
    Protects non-active materials to prevent the baker from using wrong nodes.

    Example:
        with NodeGraphHandler([material]) as handler:
            handler.setup_protection(objects, active_materials)
            handler.setup_for_pass("EMIT", "color", image)
            # Baking happens here
        # All temporary nodes and links are restored automatically

    Attributes:
        materials (List[bpy.types.Material]): Active materials being managed.
        session_nodes (Dict): Temporary texture and emission nodes per material.
        temp_logic_nodes (Dict): List of other temporary logic nodes per material.
        temp_attributes (List): Temporary vertex attributes created for ID maps.
        original_links (Dict): Snapshot of node links before modification.
    """

    def __init__(self, materials: List[bpy.types.Material]):
        """Initialize node graph handler.

        Args:
            materials: List of materials to manage during baking.
        """
        self.materials = [
            m for m in materials if m and hasattr(m, "use_nodes") and m.use_nodes
        ]
        self.session_nodes = {}
        self.temp_logic_nodes = {}
        self.temp_attributes = []
        self.original_links = {}

    def __enter__(self):
        for mat in self.materials:
            tree = mat.node_tree
            links_data = []  # List of (from_socket, to_socket) pairs
            for l in tree.links:
                links_data.append((l.from_socket, l.to_socket))
            self.original_links[mat] = links_data

        self._prepare_session_nodes()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False

    def _prepare_session_nodes(self):
        """Create base texture and emission nodes used for most bake passes."""
        for mat in self.materials:
            tree = mat.node_tree
            tex_n = tree.nodes.new("ShaderNodeTexImage")
            emi_n = tree.nodes.new("ShaderNodeEmission")
            tex_n["is_bt_temp"] = True
            emi_n["is_bt_temp"] = True

            self.session_nodes[mat] = {"tex": tex_n, "emi": emi_n}
            self.session_nodes[mat]["tex"].location = (-800, 500)
            self.session_nodes[mat]["emi"].location = (600, 0)
            self.temp_logic_nodes[mat] = []

    def cleanup(self) -> None:
        """Physically remove all temporary nodes and restore original links."""
        # 1. Clean up all materials that had nodes added
        for mat in list(self.temp_logic_nodes.keys()):
            if not mat or not hasattr(mat, "node_tree") or not mat.node_tree:
                continue
            tree = mat.node_tree

            if mat in self.session_nodes:
                for n in self.session_nodes[mat].values():
                    try:
                        tree.nodes.remove(n)
                    except (ReferenceError, KeyError):
                        pass

            if mat in self.temp_logic_nodes:
                nodes = self.temp_logic_nodes[mat]
                for n in reversed(nodes):
                    try:
                        if n.name in tree.nodes:
                            tree.nodes.remove(n)
                    except (ReferenceError, KeyError):
                        pass
                self.temp_logic_nodes[mat] = []

        # 2. Restore original links
        for mat, links_data in self.original_links.items():
            if not mat or not hasattr(mat, "node_tree") or not mat.node_tree:
                continue
            tree = mat.node_tree

            # HI-08: Surgical link restoration instead of full clear if possible, 
            # but for simplicity and reliability of BSDF redirection, we use clear with protection.
            try:
                tree.links.clear()
            except (ReferenceError, RuntimeError):
                continue

            for from_sock, to_sock in links_data:
                try:
                    # Verify both sockets and their nodes still exist
                    if (from_sock and from_sock.node and from_sock.node.name in tree.nodes and
                        to_sock and to_sock.node and to_sock.node.name in tree.nodes):
                        tree.links.new(from_sock, to_sock)
                except (ReferenceError, KeyError, AttributeError, RuntimeError):
                    # Individual link failure shouldn't stop others
                    pass

        # 3. Clean up temp attributes
        for obj, attr in self.temp_attributes:
            try:
                if attr in obj.data.attributes:
                    obj.data.attributes.remove(obj.data.attributes[attr])
            except (KeyError, AttributeError, ReferenceError):
                pass

        # 4. Explicitly remove the protection dummy image
        d = bpy.data.images.get(SYSTEM_NAMES["DUMMY_IMG"])
        if d and d.users == 0:
            try:
                bpy.data.images.remove(d)
            except (ReferenceError, RuntimeError):
                pass

    def setup_protection(
        self,
        objects: Optional[List[bpy.types.Object]] = None,
        active_materials: Optional[List[bpy.types.Material]] = None,
    ) -> None:
        """Ensure non-active materials have an active texture node.

        Prevents Blender's baker from using nodes in materials not intended
        for the current bake pass.

        Args:
            objects: List of objects to protect.
            active_materials: Materials that should NOT be protected.
        """
        if not objects:
            return
        if active_materials is None:
            active_materials = self.materials

        active_set = set(active_materials)
        d = bpy.data.images.get(SYSTEM_NAMES["DUMMY_IMG"]) or bpy.data.images.new(
            SYSTEM_NAMES["DUMMY_IMG"], 32, 32, alpha=True
        )
        d.use_fake_user = False

        for obj in objects:
            if obj.type != "MESH":
                continue
            for s in obj.material_slots:
                m = s.material
                if m and m.use_nodes and m not in active_set:
                    if m.library:
                        continue
                    self._add_node(
                        m,
                        "ShaderNodeTexImage",
                        image=d,
                        name=SYSTEM_NAMES["PROTECTION_NODE"],
                        label=SYSTEM_NAMES["PROTECTION_LABEL"],
                    )

    def setup_for_pass(
        self,
        bake_pass: str,
        socket_name: str,
        image: bpy.types.Image,
        mesh_type: Optional[str] = None,
        attr_name: Optional[str] = None,
        channel_settings: Any = None,
    ) -> None:
        """Configure node trees for a specific bake pass.

        Args:
            bake_pass: pass type (EMIT, DIFFUSE, etc.).
            socket_name: channel identifier.
            image: target image datablock.
            mesh_type: mesh map category if applicable.
            attr_name: attribute name for ID maps.
            channel_settings: configuration for the current channel.
        """
        for mat in self.materials:
            tree = mat.node_tree
            out_n = self._find_output(tree)
            if not out_n or mat not in self.session_nodes:
                continue

            for n in self.temp_logic_nodes[mat]:
                try:
                    tree.nodes.remove(n)
                except (ReferenceError, KeyError):
                    pass
            self.temp_logic_nodes[mat] = []

            s_nodes = self.session_nodes[mat]
            tex_n, emi_n = s_nodes["tex"], s_nodes["emi"]

            tex_n.image = image
            tree.nodes.active = tex_n

            needs_emit = (
                bake_pass == "EMIT"
                or mesh_type
                or socket_name.startswith("pbr_conv")
                or socket_name == "node_group"
            )

            if needs_emit:
                tree.links.new(emi_n.outputs[0], out_n.inputs[0])
                src = None
                if mesh_type:
                    src = self._create_mesh_map_logic(
                        mat, mesh_type, attr_name, channel_settings
                    )
                elif socket_name.startswith("pbr_conv"):
                    src = self._create_extension_logic(
                        mat, socket_name, channel_settings
                    )
                elif socket_name == "node_group":
                    src = self._create_node_group_logic(mat, channel_settings)
                else:
                    src = self._find_socket_source(mat, socket_name, channel_settings)

                if src:
                    tree.links.new(src, emi_n.inputs[0])

    def _create_node_group_logic(self, mat: bpy.types.Material, s: Any) -> Optional[bpy.types.NodeSocket]:
        es = getattr(s, "extension_settings", None)
        if not es or not es.node_group:
            return None
        ng_data = bpy.data.node_groups.get(es.node_group)
        if not ng_data:
            return None
        grp = self._add_node(mat, "ShaderNodeGroup")
        grp.node_tree = ng_data
        return (
            grp.outputs.get(es.output_name)
            if es.output_name
            else (grp.outputs[0] if grp.outputs else None)
        )

    def _add_node(self, mat: bpy.types.Material, node_type: str, **kwargs) -> bpy.types.Node:
        """Add a temporary node to a material's node tree.

        Nodes added via this method are tracked and automatically
        removed during cleanup.

        Args:
            mat: Material to add node to.
            node_type: Blender node type identifier.
            **kwargs: Properties to set on the new node.

        Returns:
            The created node.
        """
        n = mat.node_tree.nodes.new(node_type)
        n["is_bt_temp"] = True
        for k, v in kwargs.items():
            if hasattr(n, k):
                setattr(n, k, v)
        if mat not in self.temp_logic_nodes:
            self.temp_logic_nodes[mat] = []
        self.temp_logic_nodes[mat].append(n)
        return n

    def _find_output(self, tree: bpy.types.NodeTree) -> Optional[bpy.types.Node]:
        """Find the active material output node."""
        for n in tree.nodes:
            if n.bl_idname == "ShaderNodeOutputMaterial" and n.is_active_output:
                return n
        return next(
            (n for n in tree.nodes if n.bl_idname == "ShaderNodeOutputMaterial"), None
        )

    def _find_socket_source(
        self, mat: bpy.types.Material, socket_name: str, settings: Any
    ) -> Optional[bpy.types.NodeSocket]:
        """Find the node socket that serves as the source for a PBR channel."""
        tree = mat.node_tree
        bsdf = next(
            (n for n in tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None
        )
        found = None
        if bsdf:
            for cand in BSDF_COMPATIBILITY_MAP.get(socket_name, [socket_name]):
                if cand in bsdf.inputs:
                    found = bsdf.inputs[cand]
                    break

        if not found and socket_name in {"color", "emi"}:
            emi = next(
                (n for n in tree.nodes if n.bl_idname == "ShaderNodeEmission"), None
            )
            if emi:
                found = emi.inputs["Color"]

        src = None
        if found and found.is_linked:
            src = found.links[0].from_socket
        else:
            val = (
                found.default_value
                if found
                else SOCKET_DEFAULT_TYPE.get(socket_name, (0, 0, 0, 1))
            )
            rgb = self._add_node(mat, "ShaderNodeRGB")
            if hasattr(val, "__len__") and len(val) >= 3:
                v = (val[0], val[1], val[2], 1.0)
            else:
                v = (val, val, val, 1.0)
            rgb.outputs[0].default_value = v
            src = rgb.outputs[0]

        if settings and socket_name == "rough" and settings.rough_inv:
            inv = self._add_node(mat, "ShaderNodeInvert")
            inv.inputs[0].default_value = 1.0
            tree.links.new(src, inv.inputs[1])
            src = inv.outputs[0]
        return src

    def _create_mesh_map_logic(
        self, mat: bpy.types.Material, mtype: str, attr: Optional[str], s: Any
    ) -> Optional[bpy.types.NodeSocket]:
        """Inject shader nodes to generate mesh analysis maps."""
        ms = getattr(s, "mesh_settings", None)
        if mtype == "ID":
            return self._add_node(
                mat, "ShaderNodeAttribute", attribute_name=attr
            ).outputs["Color"]
        elif mtype == "AO":
            n = self._add_node(mat, "ShaderNodeAmbientOcclusion")
            n.samples = ms.samples if ms else 16
            n.inputs["Distance"].default_value = ms.distance if ms else 1.0
            n.inside = ms.inside if ms else False
            return n.outputs["Color"]
        elif mtype == "POS":
            return self._add_node(mat, "ShaderNodeNewGeometry").outputs["Position"]
        elif mtype == "UV":
            return self._add_node(mat, "ShaderNodeUVMap").outputs["UV"]
        elif mtype == "WF":
            n = self._add_node(mat, "ShaderNodeWireframe")
            n.use_pixel_size = ms.use_pixel_size if ms else False
            n.inputs[0].default_value = ms.distance if ms else 0.01
            return n.outputs[0]
        elif mtype == "BEVEL":
            n = self._add_node(mat, "ShaderNodeBevel")
            n.samples = ms.samples if ms else 8
            n.inputs["Radius"].default_value = ms.radius if ms else 0.05
            return n.outputs[0]
        return None

    def _create_extension_logic(
        self, mat: bpy.types.Material, socket_name: str, settings: Any
    ) -> Optional[bpy.types.NodeSocket]:
        """Inject math nodes for custom PBR conversion logic."""
        es = getattr(settings, "extension_settings", None)
        threshold = es.threshold if es else 0.04
        tree = mat.node_tree
        spec_src = self._find_socket_source(mat, "specular", None)
        sep = self._add_node(mat, "ShaderNodeSeparateColor")
        tree.links.new(spec_src, sep.inputs[0])
        math1 = self._add_node(mat, "ShaderNodeMath", operation="MAXIMUM")
        tree.links.new(sep.outputs[0], math1.inputs[0])
        tree.links.new(sep.outputs[1], math1.inputs[1])
        math2 = self._add_node(mat, "ShaderNodeMath", operation="MAXIMUM")
        tree.links.new(math1.outputs[0], math2.inputs[0])
        tree.links.new(sep.outputs[2], math2.inputs[1])
        sub = self._add_node(mat, "ShaderNodeMath", operation="SUBTRACT")
        tree.links.new(math2.outputs[0], sub.inputs[0])
        sub.inputs[1].default_value = threshold
        div = self._add_node(mat, "ShaderNodeMath", operation="DIVIDE")
        tree.links.new(sub.outputs[0], div.inputs[0])
        div.inputs[1].default_value = max(1e-5, 1.0 - threshold)
        clamp = self._add_node(mat, "ShaderNodeClamp")
        tree.links.new(div.outputs[0], clamp.inputs[0])
        metallic_out = clamp.outputs[0]

        if socket_name == "pbr_conv_metal":
            return metallic_out
        elif socket_name == "pbr_conv_base":
            diff_src = self._find_socket_source(mat, "color", None)
            if compat.is_blender_4() or compat.is_blender_5():
                mix = self._add_node(mat, "ShaderNodeMix")
                mix.data_type = "RGBA"
                tree.links.new(metallic_out, mix.inputs[0])
                sock_a = mix.inputs.get("A") or next(
                    (s for s in mix.inputs if s.type == "RGBA" and s != mix.inputs[0]),
                    None,
                )
                sock_b = mix.inputs.get("B") or next(
                    (
                        s
                        for i, s in enumerate(mix.inputs)
                        if s.type == "RGBA" and s != sock_a and i > 0
                    ),
                    None,
                )
            else:
                mix = self._add_node(mat, "ShaderNodeMixRGB")
                tree.links.new(metallic_out, mix.inputs[0])
                sock_a = mix.inputs.get(
                    "Color1", mix.inputs[1] if len(mix.inputs) > 1 else None
                )
                sock_b = mix.inputs.get(
                    "Color2", mix.inputs[2] if len(mix.inputs) > 2 else None
                )

            if sock_a is None or sock_b is None:
                logger.warning("PBR Conv: Mix node socket not found.")
                return None

            tree.links.new(diff_src, sock_a)
            tree.links.new(spec_src, sock_b)
            result_output = (
                mix.outputs[2]
                if (compat.is_blender_4() or compat.is_blender_5())
                else mix.outputs[0]
            )
            return result_output
        return None
