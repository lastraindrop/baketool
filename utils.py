import bpy
import os
import logging
from contextlib import contextmanager
from .constants import FORMAT_SETTINGS

logger = logging.getLogger(__name__)

def report_error(operator, message, status='CANCELLED'):
    """
    Report an error message through the operator and return a status.
    """
    operator.report({'ERROR'}, message)
    return {status}

class SceneSettingsContext:
    """
    Context manager to safely apply and restore scene/render settings.
    """
    def __init__(self, category, settings):
        self.category = category
        self.settings = settings
        self.original_settings = {}

    def __enter__(self):
        self.original_settings = manage_scene_settings(self.category, getorset=False)
        manage_scene_settings(self.category, self.settings, getorset=True)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        manage_scene_settings(self.category, self.original_settings, getorset=True)

class MaterialCleanupContext:
    """
    Context manager to track and clean up temporary nodes/images added to materials.
    """
    def __init__(self, materials_info_list):
        self.materials_info_list = materials_info_list

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        for matinfo in self.materials_info_list:
            mat = matinfo['material']
            if not mat or not mat.node_tree:
                continue
            
            # Remove extra nodes created during bake
            for node in matinfo.get('extra_nodes', []):
                if node.name in mat.node_tree.nodes:
                    mat.node_tree.nodes.remove(node)
            matinfo['extra_nodes'].clear()

            # Remove temp images
            if matinfo.get('temp_image'):
                bpy.data.images.remove(matinfo['temp_image'])
                matinfo['temp_image'] = None

            # Restore links (reconnect BSDF to Output if it was disconnected/intercepted)
            if matinfo.get('bsdf_node') and matinfo.get('output_node'):
                try:
                    # If BSDF output is not connected to Output input, reconnect it.
                    # This is a basic check.
                    bsdf_out = matinfo['bsdf_node'].outputs[0]
                    target_in = matinfo['output_node'].inputs[0]
                    
                    is_linked = False
                    for link in bsdf_out.links:
                        if link.to_socket == target_in:
                            is_linked = True
                            break
                    
                    if not is_linked:
                        mat.node_tree.links.new(bsdf_out, target_in)
                except Exception as e:
                    logger.warning(f"Failed to restore links for material {mat.name}: {e}")

def create_matinfo(material, spematerial=None):
    """
    Create a material information dictionary for baking purposes.
    """
    if not material or not material.node_tree:
        return {
            'material': material,
            'output_node': None,
            'bsdf_node': None,
            'extra_nodes': [],
            'is_not_special': False
        }

    output = get_output(material.node_tree.nodes)
    BSDF = None
    if output and output.inputs[0].links:
        from_node = output.inputs[0].links[0].from_node
        if from_node.bl_idname == 'ShaderNodeBsdfPrincipled':
            BSDF = from_node
            
    return {
        'material': material,
        'output_node': output,
        'bsdf_node': BSDF,
        'bake_image_node': None,
        'temp_image': None,
        'extra_nodes': [], 
        'is_not_special': spematerial is not None and material != spematerial
    }

def get_output(nodes):
    for node in nodes:
        if node.bl_idname == 'ShaderNodeOutputMaterial' and node.is_active_output:
            return node
    return None

def manage_scene_settings(category='scene', settings=None, getorset=False):
    config_map = {
        'bake': {
            'margin': {'path': bpy.context.scene.render.bake, 'attr': 'margin', 'default': 8},
            'normal_space': {'path': bpy.context.scene.render.bake, 'attr': 'normal_space', 'default': 'TANGENT'}
        },
        'scene': {
            'res_x': {'path': bpy.context.scene.render, 'attr': 'resolution_x', 'default': 1920},
            'res_y': {'path': bpy.context.scene.render, 'attr': 'resolution_y', 'default': 1080},
            'engine': {'path': bpy.context.scene.render, 'attr': 'engine', 'default': 'BLENDER_EEVEE'},
            'samples': {'path': bpy.context.scene.cycles, 'attr': 'samples', 'default': 128},
            'filepath': {'path': bpy.context.scene.render, 'attr': 'filepath', 'default': ''},
        },
        'image': {
            'file_format': {'path': bpy.context.scene.render.image_settings, 'attr': 'file_format', 'default': 'PNG'},
            'color_depth': {'path': bpy.context.scene.render.image_settings, 'attr': 'color_depth', 'default': '8'},
            'color_mode': {'path': bpy.context.scene.render.image_settings, 'attr': 'color_mode', 'default': 'RGBA'},
            'quality': {'path': bpy.context.scene.render.image_settings, 'attr': 'quality', 'default': 90},
            'exr_codec': {'path': bpy.context.scene.render.image_settings, 'attr': 'exr_codec', 'default': 'ZIP'},
            'tiff_codec': {'path': bpy.context.scene.render.image_settings, 'attr': 'tiff_codec', 'default': 'DEFLATE'}
        }
    }
    
    if category not in config_map:
        raise ValueError(f"Unsupported category: {category}")

    if settings is None:
        settings = {}
        if not getorset:
            for key, config in config_map[category].items():
                try:
                    settings[key] = getattr(config['path'], config['attr'], config['default'])
                except AttributeError:
                    continue
            return settings

    if getorset:
        for key, value in settings.items():
            if key in config_map[category] and value is not None:
                config = config_map[category][key]
                try:
                    setattr(config['path'], config['attr'], value)
                except AttributeError:
                    logger.warning(f"Could not set attribute {config['attr']} on {config['path']}")
            elif key == 'color_depth' and category == 'image':
                 adjust_color_depth(settings)
    
    return settings

def adjust_color_depth(settings):
    fmt = settings.get('file_format', 'PNG')
    depth = settings.get('color_depth', '8')
    img_settings = bpy.context.scene.render.image_settings
    
    fmt_settings = FORMAT_SETTINGS.get(fmt, {})
    valid_depths = fmt_settings.get("depths", [])
    
    if valid_depths:
        if depth not in valid_depths:
             # Fallback: prefer 8 if available and current is invalid, otherwise first available
             if '8' in valid_depths: img_settings.color_depth = '8'
             elif '16' in valid_depths: img_settings.color_depth = '16'
             else: img_settings.color_depth = valid_depths[0]
        else:
            img_settings.color_depth = depth

def set_image(name, x, y, alpha=True, full=False, space='sRGB', ncol=False, fake_user=False, basiccolor=(0,0,0,0), clear=True):
    image = bpy.data.images.get(name)
    if image:
        if image.size[0] != x or image.size[1] != y:
            image.scale(x, y)
    else:
        image = bpy.data.images.new(name, x, y, alpha=alpha, float_buffer=full, is_data=ncol)
    
    if not full:
        try:
            image.colorspace_settings.name = space
        except TypeError:
            pass
            
    image.use_fake_user = fake_user
    
    if clear:
        image.generated_color = basiccolor
    
    return image

def save_image(image, path='//', folder=False, folder_name='folder', file_format='PNG', 
               color_depth='16', color_mode='RGBA', quality=100, motion=False, frame=0, 
               exr_codec=None, color_space='sRGB', reload=False, fillnum=4, denoise=False, 
               denoise_method='FAST', save=False):
    
    if not save: return

    if not image:
        logger.error("No image provided to save.")
        return

    if folder:
        directory = os.path.join(path, folder_name)
        if not os.path.exists(bpy.path.abspath(directory)):
            os.makedirs(bpy.path.abspath(directory))
    else:
        directory = path

    file_ext = "." + file_format.lower()
    if file_format in FORMAT_SETTINGS:
        exts = FORMAT_SETTINGS[file_format].get("extensions", [])
        if exts:
            file_ext = exts[0]
    
    name_part = image.name
    if motion:
        name_part += f".{str(frame).zfill(fillnum)}"
    
    filename = f"{name_part}{file_ext}"
    filepath = os.path.join(directory, filename)
    abs_filepath = bpy.path.abspath(filepath)

    # Use render mechanism to save to ensure color management and format settings are respected
    # Current scene settings should be set by manage_scene_settings prior to calling this
    try:
        image.save_render(abs_filepath, scene=bpy.context.scene)
    except Exception as e:
        logger.error(f"Failed to save image {image.name}: {e}")
    
    if reload:
        try:
            image.source = 'FILE'
            image.filepath = filepath
            image.reload()
        except:
            pass

def set_active_and_selected(target_obj, objects):
    bpy.ops.object.select_all(action='DESELECT')
    target_obj.select_set(True)
    bpy.context.view_layer.objects.active = target_obj

def copy_object(obj, clear_material=True):
    new_obj = obj.copy()
    new_mesh = obj.data.copy()
    new_obj.data = new_mesh
    bpy.context.scene.collection.objects.link(new_obj)
    if new_obj.type == 'MESH' and clear_material:
        new_mesh.materials.clear()
    return new_obj

def make_temp_node(material):
    imagetem = bpy.data.images.new('tem', 64, 64, alpha=False)
    imagenodetem = material.node_tree.nodes.new("ShaderNodeTexImage")
    imagenodetem.image = imagetem
    material.node_tree.nodes.active = imagenodetem
    return [material, imagenodetem, imagetem]

def clear_temp_node(matinfo):
    bpy.data.images.remove(matinfo[2])
    matinfo[0].node_tree.nodes.remove(matinfo[1])

def export_baked_model(obj, export_path, export_format, logger):
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    original_selected = bpy.context.selected_objects[:]
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    export_path = bpy.path.abspath(export_path)
    os.makedirs(os.path.dirname(export_path), exist_ok=True)

    def is_addon_enabled(addon):
        return addon in bpy.context.preferences.addons.keys()

    if export_format == 'FBX':
        if not is_addon_enabled("io_scene_fbx"):
            logger.error("FBX export plugin not enabled!")
            return
        try:
            bpy.ops.export_scene.fbx(
                filepath=export_path,
                use_selection=True,
                use_visible=False,
                apply_unit_scale=True,
                bake_space_transform=True,
                path_mode='COPY',
                embed_textures=True,
                object_types={'MESH'},
                use_mesh_modifiers=True
            )
            logger.info(f"Exported FBX to: {export_path}")
        except Exception as e:
            logger.error(f"FBX export failed: {e}")

    elif export_format == 'GLB':
        if not is_addon_enabled("io_scene_gltf2"):
            logger.error("GLTF export plugin not enabled!")
            return
        try:
            bpy.ops.export_scene.gltf(
                filepath=export_path,
                export_format='GLB',
                use_selection=True,
                use_visible=False,
                export_texcoords=True,
                export_normals=True,
                export_materials='EXPORT',
                export_draco_mesh_compression_enable=False
            )
            logger.info(f"Exported GLB to: {export_path}")
        except Exception as e:
            logger.error(f"GLB export failed: {e}")

    elif export_format == 'USD':
        try:
            bpy.ops.wm.usd_export(
                filepath=export_path,
                selected_objects_only=True,
                visible_objects_only=False,
                export_materials=True,
                export_textures=True,
                use_instancing=False
            )
            logger.info(f"Exported USD to: {export_path}")
        except Exception as e:
            logger.error(f"USD export failed: {e}")

    bpy.ops.object.select_all(action='DESELECT')
    for sel_obj in original_selected:
        sel_obj.select_set(True)
