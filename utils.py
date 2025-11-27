import bpy
import os
import logging
from . import constants

logger = logging.getLogger(__name__)

def report_error(operator, message, status='FINISHED'):
    """
    Report an error message through the operator and return a status.
    This function is used to display error messages in Blender's UI when something goes wrong during
    the baking process. It leverages Blender's operator reporting system to notify the user.
    Args:
        operator (bpy.types.Operator): The operator instance calling this function.
        message (str): The error message to display.
        status (str, optional): The status to return, typically 'FINISHED' or 'CANCELLED'. Defaults to 'FINISHED'.
    Returns:
        dict: A dictionary containing the status, e.g., {'FINISHED'} or {'CANCELLED'}.
    报告错误信息并通过操作符返回状态。
    此函数用于在烘焙过程中出现问题时，通过 Blender 的用户界面显示错误信息。它利用 Blender 的操作符报告系统通知用户。
    参数:
        operator (bpy.types.Operator): 调用此函数的操作符实例。
        message (str): 要显示的错误信息。
        status (str, 可选): 返回的状态，通常为 'FINISHED' 或 'CANCELLED'，默认为 'FINISHED'。
    返回:
        dict: 包含状态的字典，例如 {'FINISHED'} 或 {'CANCELLED'}。
    """
    operator.report({'ERROR'}, message)  # 使用 Blender 的报告机制显示错误
    return {status}  # 返回操作状态

def create_node_link(tree, output_socket, input_socket):
    """
    Create a new link between two nodes in a node tree.
    This utility function establishes a connection between an output socket (output_socket) and an input socket (input_socket)
    within a Blender node tree, facilitating data flow between nodes.
    Args:
        tree (bpy.types.NodeTree): The node tree where the link will be created.
        output_socket (bpy.types.NodeSocket): The output socket of the source node.
        input_socket (bpy.types.NodeSocket): The input socket of the target node.
    Returns:
        bpy.types.NodeLink: The newly created link object.
    在节点树中创建两个节点之间的新链接。
    此实用函数在 Blender 节点树中建立从输出插口 (output_socket) 到输入插口 (input_socket) 的连接，促进节点间的数据流动。
    参数:
        tree (bpy.types.NodeTree): 将要创建链接的节点树。
        output_socket (bpy.types.NodeSocket): 源节点的输出插口。
        input_socket (bpy.types.NodeSocket): 目标节点的输入插口。
    返回:
        bpy.types.NodeLink: 新创建的链接对象。
    """
    link = tree.links.new(output_socket, input_socket)  # 创建并返回新链接
    return link

def create_node_links(tree, socket_pairs):
    """
    Create multiple new links between pairs of nodes in a node tree.
    This function iterates over a list of node socket pairs and creates links between them, useful for
    batch connecting nodes in complex node setups.
    Args:
        tree (bpy.types.NodeTree): The node tree where the links will be created.
        socket_pairs (list): A list of tuples, each containing two sockets (output, input) to connect, e.g., [(out1, in1), (out2, in2)].
    Returns:
        list: A list of newly created bpy.types.NodeLink objects.
    在节点树中为多对节点创建新链接。
    此函数遍历节点插口对列表并在它们之间创建链接，适用于在复杂节点设置中批量连接节点。
    参数:
        tree (bpy.types.NodeTree): 将要创建链接的节点树。
        socket_pairs (list): 包含要连接的插口对的元组列表，例如 [(输出1, 输入1), (输出2, 输入2)]。
    返回:
        list: 新创建的 bpy.types.NodeLink 对象列表。
    """
    links = []
    for pair in socket_pairs:
        link = tree.links.new(pair[0], pair[1])  # 为每对插口创建链接
        links.append(link)
    return links

def make_temnode(material):
    """
    Create a temporary image node in a material's node tree for baking purposes.
    This function generates a small temporary image (64x64) and attaches it to a new ShaderNodeTexImage
    in the material's node tree, setting it as the active node. This is typically used as a placeholder
    during baking operations.
    Args:
        material (bpy.types.Material): The material to which the temporary node will be added.
    Returns:
        list: A list containing [material, image_node, image], where:
            - material: The input material.
            - image_node: The newly created ShaderNodeTexImage.
            - image: The temporary bpy.types.Image object.
    在材质的节点树中创建用于烘焙的临时图像节点。
    此函数生成一个小的临时图像 (64x64)，并将其附加到材质节点树中的新 ShaderNodeTexImage 上，设置为活动节点。通常在烘焙操作中用作占位符。
    参数:
        material (bpy.types.Material): 将要添加临时节点的材质。
    返回:
        list: 包含 [材质, 图像节点, 图像] 的列表，其中：
            - material: 输入的材质。
            - image_node: 新创建的 ShaderNodeTexImage。
            - image: 临时的 bpy.types.Image 对象。
    """
    imagetem = bpy.data.images.new('tem', 64, 64, alpha=False)  # 创建 64x64 无透明度的临时图像
    imagenodetem = material.node_tree.nodes.new("ShaderNodeTexImage")  # 创建新的图像纹理节点
    imagenodetem.image = imagetem  # 将临时图像绑定到节点
    material.node_tree.nodes.active = imagenodetem  # 设置为活动节点
    return [material, imagenodetem, imagetem]  # 返回包含所有相关对象的列表

def clear_temnode(matinfo):
    """
    Remove a temporary image node and its associated image from a material.
    This function cleans up the temporary resources created by make_temnode, ensuring no residual
    data remains in memory after baking.
    Args:
        matinfo (list): A list containing [material, image_node, image], typically returned by make_temnode.
    Returns:
        None
    从材质中移除临时图像节点及其关联图像。
    此函数清理由 make_temnode 创建的临时资源，确保烘焙后内存中没有残留数据。
    参数:
        matinfo (list): 包含 [材质, 图像节点, 图像] 的列表，通常由 make_temnode 返回。
    返回:
        None
    """
    bpy.data.images.remove(matinfo[2])  # 删除临时图像
    matinfo[0].node_tree.nodes.remove(matinfo[1])  # 从节点树中移除图像节点

def copy_object(obj, clear_material=True):
    """
    Create a duplicate of an object and link it to the current scene.
    This function copies an object, including its data, and optionally clears its materials if it's a mesh.
    The duplicate is linked to the current scene's collection.
    Args:
        obj (bpy.types.Object): The object to duplicate.
        clear_material (bool, optional): If True and the object is a mesh, clear its materials. Defaults to True.
    Returns:
        bpy.types.Object: The duplicated object.
    创建对象的副本并将其链接到当前场景。
    此函数复制对象及其数据，并可选择在对象为网格时清除其材质。副本将被链接到当前场景的集合中。
    参数:
        obj (bpy.types.Object): 要复制的对象。
        clear_material (bool, 可选): 如果为 True 且对象是网格，则清除其材质。默认为 True。
    返回:
        bpy.types.Object: 复制后的对象。
    """
    # 此操作会复制物体的一份副本，并将副本连接至当前场景，可选项：清理所有材质
    new_obj = obj.copy()  # 复制对象
    new_mesh = obj.data.copy()  # 复制对象数据
    new_obj.data = new_mesh  # 将新数据绑定到新对象
    bpy.context.scene.collection.objects.link(new_obj)  # 将新对象链接到场景集合
    if new_obj.type == 'MESH' and clear_material:  # 如果是网格且要求清除材质
        new_mesh.materials.clear()  # 清除材质
    return new_obj

def manage_scene_settings(category='scene', settings=None, getorset=False):
    """
    Manage Blender scene, bake, and image settings generically.
    This function provides a unified way to get or set various Blender settings (scene, bake, image) by mapping
    them to a configuration dictionary. It supports dynamic attribute access and modification, handling errors gracefully.
    Principle (原理):
        - Uses a config_map to define supported settings for each category, including their paths, attributes, and defaults.
        - When getorset=False, it retrieves current settings; when True, it applies provided settings.
        - Handles special cases like color_depth adjustments via a separate helper method.
    Args:
        category (str): Category of settings ('bake', 'scene', 'image'). Defaults to 'scene'.
        settings (dict, optional): Settings to read/write. If None, initializes an empty dict with category keys.
        getorset (bool): False to get current settings, True to set them. Defaults to False.
    Returns:
        dict: Current or updated settings dictionary.
    管理 Blender 场景、烘焙和图像设置的通用函数。
    此函数通过映射到配置字典，提供了一种统一的方式来获取或设置 Blender 的各种设置（场景、烘焙、图像）。它支持动态属性访问和修改，并优雅地处理错误。
    原理:
        - 使用 config_map 定义每个类别支持的设置，包括路径、属性和默认值。
        - 当 getorset=False 时，获取当前设置；当 True 时，应用提供的设置。
        - 通过单独的辅助方法处理特殊情况，如 color_depth 调整。
    参数:
        category (str): 设置类别，可选 'bake', 'scene', 'image'，默认为 'scene'。
        settings (dict, 可选): 要读取或写入的设置字典，默认 None 时初始化为空字典。
        getorset (bool): False 表示记录当前设置，True 表示写入设置，默认为 False。
    返回:
        dict: 当前或更新后的设置字典。
    """
    # 定义各类别支持的设置项及其默认值和访问路径
    config_map = {
        'bake': {
            'margin': {'path': bpy.context.scene.render.bake, 'attr': 'margin', 'default': 8},
            'normal_space': {'path': bpy.context.scene.render.bake, 'attr': 'normal_space', 'default': 'TANGENT'}
        },
        'scene': {
            'res_x': {'path': bpy.context.scene.render, 'attr': 'resolution_x', 'default': None},
            'res_y': {'path': bpy.context.scene.render, 'attr': 'resolution_y', 'default': None},
            'engine': {'path': bpy.context.scene.render, 'attr': 'engine', 'default': None},
            'samples': {'path': bpy.context.scene.cycles, 'attr': 'samples', 'default': None},
            'view_transform': {'path': bpy.context.scene.view_settings, 'attr': 'view_transform', 'default': None},
            'color_management': {'path': bpy.context.scene.render.image_settings, 'attr': 'color_management', 'default': None},
            'filepath': {'path': bpy.context.scene.render, 'attr': 'filepath', 'default': None},
            'device': {'path': bpy.context.scene.cycles, 'attr': 'device', 'default': None}
        },
        'image': {
            'file_format': {'path': bpy.context.scene.render.image_settings, 'attr': 'file_format', 'default': 'PNG'},
            'color_depth': {'path': bpy.context.scene.render.image_settings, 'attr': 'color_depth', 'default': '8'},
            'color_mode': {'path': bpy.context.scene.render.image_settings, 'attr': 'color_mode', 'default': 'RGB'},
            'compression': {'path': bpy.context.scene.render.image_settings, 'attr': 'compression', 'default': 15},
            'quality': {'path': bpy.context.scene.render.image_settings, 'attr': 'quality', 'default': 90},
            'exr_codec': {'path': bpy.context.scene.render.image_settings, 'attr': 'exr_codec', 'default': None}
        }
    }
    # 检查类别是否有效
    if category not in config_map:
        raise ValueError(f"Unsupported category: {category}")  # 抛出异常以提示无效类别
    # 初始化设置字典
    if settings is None:
        settings = {key: None for key in config_map[category]}  # 创建包含所有键的空字典
    try:
        if getorset:  # 写入设置
            for key, value in settings.items():
                if key in config_map[category] and value is not None:
                    config = config_map[category][key]
                    setattr(config['path'], config['attr'], value)  # 设置属性值
                elif key == 'color_depth' and category == 'image':  # 特殊处理 color_depth
                    adjust_color_depth(settings)  # 调用辅助方法调整颜色深度
        else:  # 记录设置
            for key in config_map[category]:
                config = config_map[category][key]
                settings[key] = getattr(config['path'], config['attr'], config['default'])  # 获取属性值或默认值
    except AttributeError as e:
        print(f"Error accessing attribute in {category}: {e}")  # 打印属性访问错误
        logger.error(f"Error accessing attribute in {category}: {e}")
    except Exception as e:
        print(f"Unexpected error in {category}: {e}")  # 打印其他意外错误
        logger.error(f"Unexpected error in {category}: {e}")
    return settings  # 返回设置字典

def adjust_color_depth(self, settings):
    """调整图像设置中的 color_depth，确保与 file_format 兼容。"""
    fmt = settings.get('file_format', 'PNG')
    depth = settings.get('color_depth', '8')
    img_settings = bpy.context.scene.render.image_settings
    if fmt == 'OPEN_EXR' or fmt == 'HDR':
        img_settings.color_depth = '32' if depth not in ('16', '32') else depth
    elif fmt == 'PNG':
        img_settings.color_depth = '16' if depth not in ('8', '16') else depth
    elif fmt in ('JPEG', 'BMP', 'TARGA'):
        img_settings.color_depth = '8'
    else:
        img_settings.color_depth = depth

def save_image(image, path='//', folder=False, folder_name='folder', file_format='PNG', 
               color_depth='16', color_mode='RGBA', quality=100, motion=False, frame=0, 
               exr_codec=None, color_space='sRGB', reload=False, fillnum=4, denoise=False, 
               denoise_method='FAST', save=False):
    """
    Save a Blender image with advanced options like path management, color space conversion, and denoising.
    This function handles the saving of a Blender image by setting up a temporary compositing node setup,
    rendering it to a file, and optionally reloading it with a specified color space. It supports animation
    frames and denoising for improved image quality.
    Principle (原理):
        - Temporarily modifies scene settings and creates a compositing node tree to render the image.
        - Uses Blender’s render engine to write the image to disk, supporting various formats and depths.
        - Restores original settings after saving to avoid side effects.
    Args:
        image (bpy.types.Image): The Blender image object to save.
        path (str): Save path, defaults to '//' (relative path).
        folder (bool): Whether to use a subfolder. Defaults to False.
        folder_name (str): Subfolder name. Defaults to 'folder'.
        file_format (str): File format ('PNG', 'JPEG', 'OPEN_EXR', etc.). Defaults to 'PNG'.
        color_depth (str): Color depth ('8', '16', '32'). Defaults to '16'.
        color_mode (str): Color mode ('RGB', 'RGBA', 'BW'). Defaults to 'RGBA'.
        quality (int): Image quality (0-100). Defaults to 100.
        motion (bool): Whether this is an animation frame. Defaults to False.
        frame (int): Current frame number. Defaults to 0.
        exr_codec (str, optional): EXR compression codec. Defaults to None.
        color_space (str): Target color space ('sRGB', 'Linear', 'Non-Color'). Defaults to 'sRGB'.
        reload (bool): Whether to reload the saved image. Defaults to False.
        fillnum (int): Number of digits for frame padding. Defaults to 4.
        denoise (bool): Whether to apply denoising. Defaults to False.
        denoise_method (str): Denoising method ('FAST', 'ACCURATE'). Defaults to 'FAST'.
        save (bool): Whether to perform the save operation. Defaults to False.
    Returns:
        bpy.types.Image or None: The reloaded image if reload=True, otherwise None.
    保存 Blender 图像，支持路径管理、颜色空间转换和降噪等高级选项。
    此函数通过设置临时的合成节点树来保存 Blender 图像，将其渲染到文件中，并可选地以指定颜色空间重新加载。它支持动画帧和降噪以提高图像质量。
    原理:
        - 临时修改场景设置并创建合成节点树以渲染图像。
        - 使用 Blender 的渲染引擎将图像写入磁盘，支持多种格式和深度。
        - 保存后恢复原始设置以避免副作用。
    参数:
        image (bpy.types.Image): 要保存的 Blender 图像对象。
        path (str): 保存路径，默认为 '//'（相对路径）。
        folder (bool): 是否使用子文件夹，默认为 False。
        folder_name (str): 子文件夹名称，默认为 'folder'。
        file_format (str): 文件格式（'PNG', 'JPEG', 'OPEN_EXR' 等），默认为 'PNG'。
        color_depth (str): 颜色深度（'8', '16', '32'），默认为 '16'。
        color_mode (str): 颜色模式（'RGB', 'RGBA', 'BW'），默认为 'RGBA'。
        quality (int): 图像质量（0-100），默认为 100。
        motion (bool): 是否为动画帧，默认为 False。
        frame (int): 当前帧号，默认为 0。
        exr_codec (str, 可选): EXR 压缩编码，默认为 None。
        color_space (str): 目标颜色空间（'sRGB', 'Linear', 'Non-Color'），默认为 'sRGB'。
        reload (bool): 是否重新加载保存的图像，默认为 False。
        fillnum (int): 帧号填充位数，默认为 4。
        denoise (bool): 是否应用降噪，默认为 False。
        denoise_method (str): 降噪方法（'FAST', 'ACCURATE'），默认为 'FAST'。
        save (bool): 是否执行保存操作，默认为 False。
    返回:
        bpy.types.Image 或 None: 如果 reload=True，则返回重新加载的图像，否则返回 None。
    """
    if not image:
        raise ValueError("No image provided for saving")  # 检查图像是否有效
    scene = bpy.context.scene
    has_cam = scene.camera is not None
    if not has_cam:  # 如果场景没有相机，创建临时相机
        camera = bpy.data.cameras.new('tem cam')
        cam_obj = bpy.data.objects.new('tem cam', camera)
        scene.collection.objects.link(cam_obj)
        scene.camera = cam_obj
    # 保存原始设置
    original_scene = manage_scene_settings('scene', getorset=False)
    original_image = manage_scene_settings('image', getorset=False)
    # 计算文件路径
    file_ext = f".{file_format.lower()}"
    frame_str = f".{str(frame).zfill(fillnum)}" if motion else ''
    # 构建相对路径，确保以 '//' 开头
    rel_path = os.path.join(path, folder_name if folder else '', f"{image.name}{frame_str}{file_ext}")
    if not rel_path.startswith('//'):
        rel_path = os.path.join('//', rel_path.lstrip('/\\'))  # 规范化相对路径
    filepath = bpy.path.abspath(rel_path)  # 转换为绝对路径
    # 设置场景和图像参数
    scene_settings = {
        'res_x': image.size[0],
        'res_y': image.size[1],
        'filepath': filepath
    }
    image_settings = {
        'file_format': file_format,
        'color_depth': color_depth,
        'color_mode': color_mode,
        'compression': 100 - quality if file_format == 'PNG' else None,
        'quality': quality if file_format in ('JPEG', 'JPEG2000') else None,
        'exr_codec': exr_codec
    }
    manage_scene_settings('scene', scene_settings, getorset=True)
    manage_scene_settings('image', image_settings, getorset=True)
    # 如果图像未打包，先打包
    if image.is_dirty:
        image.pack()
    # 设置合成节点
    scene.use_nodes = True
    nodes = scene.node_tree.nodes
    links = scene.node_tree.links
    # 查找或创建 Composite 节点
    comp_node = next((n for n in nodes if n.bl_idname == 'CompositorNodeComposite'), None)
    if not comp_node:
        comp_node = nodes.new("CompositorNodeComposite")
    original_link = comp_node.inputs[0].links[0].from_socket if comp_node.inputs[0].links else None
    # 创建图像节点
    image_node = nodes.new("CompositorNodeImage")
    image_node.image = image
    nodes.active = comp_node
    # 处理降噪
    if denoise:
        denoise_node = nodes.new("CompositorNodeDenoise")
        denoise_node.prefilter = denoise_method
        links.new(image_node.outputs[0], denoise_node.inputs[0])
        links.new(denoise_node.outputs[0], comp_node.inputs[0])
    else:
        links.new(image_node.outputs[0], comp_node.inputs[0])
    if save:
        # 执行渲染保存
        bpy.ops.render.render(write_still=True)
    # 清理节点
    nodes.remove(image_node)
    if denoise:
        nodes.remove(denoise_node)
    if original_link:
        links.new(original_link, comp_node.inputs[0])
    # 重新加载图像（可选）
    if reload:
        reloaded_image = bpy.data.images.load(filepath, check_existing=True)
        reloaded_image.colorspace_settings.name = color_space
        bpy.data.images.remove(image)  # 删除原始图像
        image = reloaded_image
    # 恢复原始设置
    manage_scene_settings('scene', original_scene, getorset=True)
    manage_scene_settings('image', original_image, getorset=True)
    if not has_cam:
        bpy.data.objects.remove(cam_obj)
        bpy.data.cameras.remove(camera)
    logger.info(f"Image saved {image.name}")
    return image if reload else None

def set_image(name, x, y, alpha=True, full=False, space='sRGB', ncol=False, fake_user=False, basiccolor=(0,0,0,0), clear=True):
    """
    Create a new Blender image with specified properties.
    This function generates a new image in Blender with customizable dimensions, color mode, and other attributes.
    It can be used to initialize images for baking or rendering purposes.
    Args:
        name (str): The name of the new image.
        x (int): Width of the image in pixels.
        y (int): Height of the image in pixels.
        alpha (bool): Whether the image has an alpha channel. Defaults to True.
        full (bool): Whether to use a float buffer (32-bit). Defaults to False.
        space (str): Color space ('sRGB', 'Linear', etc.). Defaults to 'sRGB'.
        ncol (bool): Whether the image is non-color data. Defaults to False.
        fake_user (bool): Whether to assign a fake user to prevent deletion. Defaults to False.
        basiccolor (tuple): Default color as (R, G, B, A) tuple, used if clear=False. Defaults to (0, 0, 0, 0).
        clear (bool): Whether to clear the image with the basiccolor. Defaults to True.
    Returns:
        bpy.types.Image: The newly created image object.
    创建具有指定属性的新 Blender 图像。
    此函数在 Blender 中生成一个新图像，具有可自定义的尺寸、颜色模式和其他属性。可用于初始化烘焙或渲染所需的图像。
    参数:
        name (str): 新图像的名称。
        x (int): 图像宽度（像素）。
        y (int): 图像高度（像素）。
        alpha (bool): 图像是否具有 alpha 通道，默认为 True。
        full (bool): 是否使用浮点缓冲区（32 位），默认为 False。
        space (str): 颜色空间（'sRGB', 'Linear' 等），默认为 'sRGB'。
        ncol (bool): 图像是否为非颜色数据，默认为 False。
        fake_user (bool): 是否分配假用户以防止删除，默认为 False。
        basiccolor (tuple): 默认颜色，以 (R, G, B, A) 元组形式，若 clear=False 则使用，默认为 (0, 0, 0, 0)。
        clear (bool): 是否用 basiccolor 清除图像，默认为 True。
    返回:
        bpy.types.Image: 新创建的图像对象。
    """
    image = bpy.data.images.new(name, x, y, alpha=alpha, float_buffer=full, is_data=ncol)  # 创建新图像
    if full == False:
        image.colorspace_settings.name = space  # 设置颜色空间（仅非浮点图像）
    image.use_fake_user = fake_user  # 设置假用户状态
    if not clear:
        image.generated_color = basiccolor  # 如果不清空，则设置默认颜色
    return image

def reload_image(image, filepath, change_cs=False, cs='sRGB', reload_inside=False):
    """
    Reload an image from a file path and optionally update its color space or pack it.
    This function reloads an existing Blender image from a specified file path, optionally changing its
    color space and/or packing it into the .blend file. It ensures the image is updated in memory.
    Args:
        image (bpy.types.Image): The Blender image object to reload.
        filepath (str): The file path to reload the image from.
        change_cs (bool): Whether to change the image’s color space. Defaults to False.
        cs (str): The target color space ('sRGB', 'Linear', etc.) if change_cs is True. Defaults to 'sRGB'.
        reload_inside (bool): Whether to pack the reloaded image into the .blend file. Defaults to False.
    Returns:
        bpy.types.Image: The reloaded and updated image object.
    从文件路径重新加载图像，并可选地更新其颜色空间或打包。
    此函数从指定文件路径重新加载现有的 Blender 图像，可选地更改其颜色空间和/或将其打包到 .blend 文件中，确保图像在内存中更新。
    参数:
        image (bpy.types.Image): 要重新加载的 Blender 图像对象。
        filepath (str): 重新加载图像的文件路径。
        change_cs (bool): 是否更改图像的颜色空间，默认为 False。
        cs (str): 如果 change_cs 为 True，则为目标颜色空间（'sRGB', 'Linear' 等），默认为 'sRGB'。
        reload_inside (bool): 是否将重新加载的图像打包到 .blend 文件中，默认为 False。
    返回:
        bpy.types.Image: 重新加载并更新的图像对象。
    """
    if os.path.exists(filepath):  # 检查文件路径是否存在
        image.unpack(method='REMOVE')  # 解包现有图像数据
        image.filepath = filepath  # 设置新的文件路径
        image.filepath_raw = filepath  # 设置原始文件路径
        image.reload()  # 重新加载图像
        if change_cs:
            image.colorspace_settings.name = cs  # 更新颜色空间
        if reload_inside:
            image.pack()  # 将图像打包到 .blend 文件
            os.remove(filepath)  # 删除原始文件
    return image

def get_output(nodes):
    """
    Retrieve the active output node from a node collection.
    This function searches through a collection of nodes to find the active ShaderNodeOutputMaterial,
    which is the primary output node used for rendering or baking in a material’s node tree.
    Args:
        nodes (bpy.types.NodeTree.nodes): The collection of nodes to search through.
    Returns:
        bpy.types.Node or None: The active ShaderNodeOutputMaterial node if found, otherwise None.
    从节点集合中检索活动的输出节点。
    此函数在节点集合中搜索，找到活动的 ShaderNodeOutputMaterial 节点，这是材质节点树中用于渲染或烘焙的主要输出节点。
    参数:
        nodes (bpy.types.NodeTree.nodes): 要搜索的节点集合。
    返回:
        bpy.types.Node 或 None: 如果找到活动的 ShaderNodeOutputMaterial 节点，则返回该节点，否则返回 None。
    """
    output = None
    for node in nodes:
        if node.bl_idname == 'ShaderNodeOutputMaterial' and node.is_active_output == True:
            output = node
            break  # 找到活动输出节点后退出循环
    return output  

def get_imagemaps(setting, bake_type):
    """
    Generate a list of channel configuration dictionaries based on the bake type.
    This function defines and returns a list of dictionaries representing texture channels (e.g., Normal, Base Color)
    supported by a given bake type (BSDF, BASIC, MULTIRES, MESH). Each dictionary includes settings like enable state,
    prefixes, and color modes, derived from the provided setting object.
    Principle (原理):
        - Uses predefined channel configuration templates for different bake types and Blender versions (3.x vs 4.x for BSDF).
        - Dynamically constructs channel configurations using list comprehension, pulling attributes from the setting object.
        - Supports customization through prefixes, suffixes, and custom color spaces.
    Args:
        setting: A settings object containing enable states, prefixes, suffixes, and other bake-related properties.
        bake_type (str): The type of baking ('BSDF', 'BASIC', 'MULTIRES', 'MESH').
    Returns:
        list: A list of dictionaries, each representing a channel configuration with keys:
            - 'type': Channel type (e.g., 'NORMAL', 'COLOR').
            - 'enabled': Boolean indicating if the channel is active.
            - 'prefix': Prefix for the channel name.
            - 'suffix': Suffix for the channel name.
            - 'node_name': Internal node name for BSDF baking.
            - 'color_mode': Color mode ('RGB', 'RGBA', 'BW').
            - 'default_cs': Default color space ('sRGB', 'Non-Color', etc.).
            - 'custom_cs': Custom color space from settings.
            - 'image': Placeholder for the image (initially None).
    根据烘焙类型生成通道配置字典列表。
    此函数定义并返回一个字典列表，表示给定烘焙类型（BSDF、BASIC、MULTIRES、MESH）支持的纹理通道（例如 Normal、Base Color）。每个字典包含启用状态、前缀、颜色模式等设置，从提供的设置对象中派生。
    原理:
        - 使用针对不同烘焙类型和 Blender 版本（BSDF 的 3.x 与 4.x）的预定义通道配置模板。
        - 使用列表推导式动态构建通道配置，从设置对象中提取属性。
        - 支持通过前缀、后缀和自定义颜色空间进行定制。
    参数:
        setting: 包含启用状态、前缀、后缀等烘焙相关属性的设置对象。
        bake_type (str): 烘焙类型（'BSDF', 'BASIC', 'MULTIRES', 'MESH'）。
    返回:
        list: 包含通道配置的字典列表，每个字典的键包括：
            - 'type': 通道类型（例如 'NORMAL', 'COLOR'）。
            - 'enabled': 布尔值，表示通道是否启用。
            - 'prefix': 通道名称的前缀。
            - 'suffix': 通道名称的后缀。
            - 'node_name': 用于 BSDF 烘焙的内部节点名称。
            - 'color_mode': 颜色模式（'RGB', 'RGBA', 'BW'）。
            - 'default_cs': 默认颜色空间（'sRGB', 'Non-Color' 等）。
            - 'custom_cs': 来自设置的自定义颜色空间。
            - 'image': 图像占位符（初始为 None）。
    """
    # 定义通道配置模板
    channel_configs = {
        'BSDF_3': [
            ('NORMAL', 'Normal', 'RGB', 'Non-Color', 'normal'),
            ('COLOR', 'Base Color', 'RGB', 'sRGB', 'color'),
            ('SUBFACECOL', 'Subsurface Color', 'RGB', 'sRGB', 'subface_col'),
            ('SUBFACE', 'Subsurface', 'BW', 'Non-Color', 'subface'),
            ('SUBFACEANI', 'Subsurface Anisotropy', 'RGB', 'Non-Color', 'subface_ani'),
            ('METAL', 'Metallic', 'BW', 'Non-Color', 'metal'),
            ('SPECULAR', 'Specular', 'BW', 'Non-Color', 'specular'),
            ('SPECULARTINT', 'Specular Tint', 'BW', 'Non-Color', 'specular_tint'),
            ('ROUGH', 'Roughness', 'BW', 'Non-Color', 'rough'),
            ('ANISOTROPIC', 'Anisotropic', 'BW', 'Non-Color', 'anisotropic'),
            ('ANISOTROPICROT', 'Anisotropic Rotation', 'BW', 'Non-Color', 'anisotropic_rot'),
            ('SHEEN', 'Sheen', 'BW', 'Non-Color', 'sheen'),
            ('SHEENTINT', 'Sheen Tint', 'BW', 'Non-Color', 'sheen_tint'),
            ('CLEARCOAT', 'Clearcoat', 'BW', 'Non-Color', 'clearcoat'),
            ('CLEARCOATROU', 'Clearcoat Roughness', 'BW', 'Non-Color', 'clearcoat_rough'),
            ('TRAN', 'Transmission', 'BW', 'Non-Color', 'tran'),
            ('TRANROU', 'Transmission Roughness', 'BW', 'Non-Color', 'tran_rou'),
            ('EMI', 'Emission', 'RGB', 'sRGB', 'emi'),
            ('EMISTR', 'Emission Strength', 'BW', 'Non-Color', 'emi_str'),
            ('ALPHA', 'Alpha', 'BW', 'Non-Color', 'alpha'),
        ],
        'BSDF_4': [
            ('NORMAL', 'Normal', 'RGB', 'Non-Color', 'normal'),
            ('COLOR', 'Base Color', 'RGB', 'sRGB', 'color'),
            ('SUBFACE', 'Subsurface Weight', 'BW', 'Non-Color', 'subface'),
            ('SUBFACEANI', 'Subsurface Anisotropy', 'RGB', 'Non-Color', 'subface_ani'),
            ('METAL', 'Metallic', 'BW', 'Non-Color', 'metal'),
            ('SPECULAR', 'Specular IOR Level', 'BW', 'Non-Color', 'specular'),
            ('SPECULARTINT', 'Specular Tint', 'RGB', 'sRGB', 'specular_tint'),
            ('ROUGH', 'Roughness', 'BW', 'Non-Color', 'rough'),
            ('ANISOTROPIC', 'Anisotropic', 'BW', 'Non-Color', 'anisotropic'),
            ('ANISOTROPICROT', 'Anisotropic Rotation', 'BW', 'Non-Color', 'anisotropic_rot'),
            ('SHEEN', 'Sheen Weight', 'BW', 'Non-Color', 'sheen'),
            ('SHEENTINT', 'Sheen Tint', 'RGB', 'sRGB', 'sheen_tint'),
            ('SHEENROUGH', 'Sheen Roughness', 'RGB', 'sRGB', 'sheen_rough'),
            ('CLEARCOAT', 'Coat Weight', 'BW', 'Non-Color', 'clearcoat'),
            ('CLEARCOATROUGH', 'Coat Roughness', 'BW', 'Non-Color', 'clearcoat_rough'),
            ('CLEARCOATTINT', 'Coat Tint', 'RGB', 'sRGB', 'clearcoat_tint'),
            ('TRAN', 'Transmission Weight', 'BW', 'Non-Color', 'tran'),
            ('EMI', 'Emission Color', 'RGB', 'sRGB', 'emi'),
            ('EMISTR', 'Emission Strength', 'BW', 'Non-Color', 'emi_str'),
            ('ALPHA', 'Alpha', 'BW', 'Non-Color', 'alpha'),
        ],
        'BASIC': [
            ('NORMAL', 'NORMAL', 'RGB', 'Non-Color', 'normal'),
            ('DIFF', 'DIFFUSE', 'RGBA', 'sRGB', 'diff'),
            ('ROUGH', 'ROUGHNESS', 'BW', 'Non-Color', 'rough'),
            ('TRANB', 'TRANSMISSION', 'RGBA', 'Non-Color', 'tranb'),
            ('EMI', 'EMIT', 'RGB', 'sRGB', 'emi'),
            ('GLO', 'GLOSSY', 'RGBA', 'sRGB', 'gloss'),
            ('COM', 'COMBINED', 'RGBA', 'sRGB', 'combine'),
        ],
        'MULTIRES': [
            ('NORMAL', 'NORMALS', 'RGB', 'Non-Color', 'normal'),
            ('HEIGHT', 'DISPLACEMENT', 'RGB', 'Non-Color', 'height'),
        ],
        'MESH': [
            ('SHADOW', '', 'RGB', 'sRGB', 'shadow'),
            ('ENVIRONMENT', '', 'RGB', 'sRGB', 'env'),
            ('VERTEX', '', 'RGB', 'sRGB', 'vertex'),
            ('BEVEL', '', 'BW', 'Non-Color', 'bevel'),
            ('AO', '', 'BW', 'Non-Color', 'ao'),
            ('UV', '', 'RGB', 'Non-Color', 'UV'),
            ('WIREFRAME', '', 'BW', 'Non-Color', 'wireframe'),
            ('BEVNOR', '', 'RGB', 'Non-Color', 'bevnor'),
            ('POSITION', '', 'RGB', 'Non-Color', 'position'),
            ('SLOPE', '', 'RGB', 'Non-Color', 'slope'),
            ('THICKNESS', '', 'BW', 'Non-Color', 'thickness'),
            ('IDMAT', '', 'RGB', 'Non-Color', 'ID_mat'),
            ('SELECT', '', 'BW', 'Non-Color', 'select'),
            ('IDELE', '', 'RGB', 'Non-Color', 'ID_ele'),
            ('IDUVI', '', 'RGB', 'Non-Color', 'ID_UVI'),
            ('IDSEAM', '', 'RGB', 'Non-Color', 'ID_seam'),
        ]
    }
    # 根据烘焙类型选择配置
    if bake_type == 'BSDF':
        config_key = 'BSDF_3' if bpy.app.version < (4, 0, 0) else 'BSDF_4'  # 根据 Blender 版本选择 BSDF 配置
    elif bake_type in channel_configs:
        config_key = bake_type
    else:
        return []  # 如果类型无效，返回空列表
    # 使用列表推导式生成通道配置
    selected_maps = [
        {
            'type': type_name,
            'enabled': getattr(setting, attr),  # 从设置对象获取通道启用状态
            'prefix': getattr(setting, f'{attr}_pre'),  # 获取前缀
            'suffix': getattr(setting, f'{attr}_suf'),  # 获取后缀
            'node_name': node_name,
            'color_mode': color_mode,
            'default_cs': default_cs,
            'custom_cs': getattr(setting, f'{attr}_cs'),  # 获取自定义颜色空间
            'image': None
        }
        for type_name, node_name, color_mode, default_cs, attr in channel_configs[config_key]
    ]
    return selected_maps

def create_matinfo(material, spematerial=None):
    """
    Create a material information dictionary for baking purposes.
    This function constructs a dictionary containing key information about a Blender material, such as its
    output node and Principled BSDF node (if present), to facilitate baking operations. It also determines
    whether the material is special based on a comparison with spematerial.
    Args:
        material (bpy.types.Material): The Blender material object to analyze.
        spematerial (bpy.types.Material, optional): A specific material to compare against, used to identify
            if the input material is not special. Defaults to None.
    Returns:
        dict: A dictionary containing material information with the following keys:
            - 'material': The input material.
            - 'output_node': The active ShaderNodeOutputMaterial, or None if not found.
            - 'bsdf_node': The Principled BSDF node connected to the output, or None if not present.
            - 'bake_image_node': Placeholder for an image node used in baking (initially None).
            - 'temp_image': Placeholder for a temporary image (initially None).
            - 'temp_image_node': Placeholder for a temporary image node (initially None).
            - 'extra_nodes': List of additional nodes created during baking (initially empty).
            - 'is_not_special': Boolean indicating if the material differs from spematerial.
    创建用于烘焙的材质信息字典。
    此函数构建一个包含 Blender 材质关键信息的字典，例如输出节点和 Principled BSDF 节点（如果存在），以便于烘焙操作。它还通过与 spematerial 比较来确定材质是否为特殊材质。
    参数:
        material (bpy.types.Material): 要分析的 Blender 材质对象。
        spematerial (bpy.types.Material, 可选): 用于比较的特定材质，用于判断输入材质是否非特殊材质。默认为 None。
    返回:
        dict: 包含材质信息的字典，键包括：
            - 'material': 输入的材质。
            - 'output_node': 活动的 ShaderNodeOutputMaterial 节点，若未找到则为 None。
            - 'bsdf_node': 连接到输出的 Principled BSDF 节点，若不存在则为 None。
            - 'bake_image_node': 用于烘焙的图像节点占位符（初始为 None）。
            - 'temp_image': 临时图像占位符（初始为 None）。
            - 'temp_image_node': 临时图像节点占位符（初始为 None）。
            - 'extra_nodes': 烘焙期间创建的额外节点列表（初始为空）。
            - 'is_not_special': 布尔值，指示材质是否与 spematerial 不同。
    """
    output = get_output(material.node_tree.nodes)  # 获取材质的活动输出节点
    BSDF = None
    if output and output.inputs[0].links and output.inputs[0].links[0].from_node.bl_idname == 'ShaderNodeBsdfPrincipled':
        BSDF = output.inputs[0].links[0].from_node  # 如果输出连接到 Principled BSDF，则记录该节点
    return {
        'material': material,
        'output_node': output,
        'bsdf_node': BSDF,
        'bake_image_node': None,
        'temp_image': None,
        'temp_image_node': None,
        'extra_nodes': [],
        'is_not_special': spematerial is not None and material != spematerial  # 判断材质是否非特殊材质
    }

def set_active_and_selected(target_obj, objects):
    """
    Set the target object as active and exclusively selected among a list of objects.
    This function iterates through a list of Blender objects, setting the selection state such that only the
    target object is selected, and then assigns it as the active object in the current view layer. This is
    useful for operations requiring a single active object, such as baking.
    Args:
        target_obj (bpy.types.Object): The object to set as active and selected.
        objects (list): A list of bpy.types.Object instances to manage selection for.
    Returns:
        None
    将目标对象设置为活动对象并在对象列表中独占选择状态。
    此函数遍历 Blender 对象列表，设置选择状态，使仅目标对象被选中，然后将其指定为当前视图层中的活动对象。这对于需要单一活动对象的操作（如烘焙）非常有用。
    参数:
        target_obj (bpy.types.Object): 要设置为活动和选中的对象。
        objects (list): 要管理选择状态的 bpy.types.Object 实例列表。
    返回:
        None
    """
    for obj in objects:
        obj.select_set(obj == target_obj)  # 仅当对象是目标对象时设置为选中状态，否则取消选中
    bpy.context.view_layer.objects.active = target_obj  # 将目标对象设置为当前视图层的活动对象
    
def is_addon_enabled(addon_name):
    """检查指定插件是否启用"""
    return addon_name in bpy.context.preferences.addons.keys()

def export_baked_model(obj, export_path, export_format, logger):
    """导出烘焙后的模型到指定路径和格式"""
    # 确保在对象模式下操作
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # 保存当前选择状态并仅选择目标对象
    original_selected = bpy.context.selected_objects[:]
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # 应用变换
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # 根据格式导出
    export_path = bpy.path.abspath(export_path)
    os.makedirs(os.path.dirname(export_path), exist_ok=True)

    if export_format == 'FBX':
        if not is_addon_enabled("io_scene_fbx"):
            logger.error("FBX export plugin not enabled! Enable 'Import-Export: FBX' in preferences.")
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
            logger.error("GLTF export plugin not enabled! Enable 'Import-Export: glTF 2.0' in preferences.")
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

    # 恢复选择状态
    bpy.ops.object.select_all(action='DESELECT')
    for sel_obj in original_selected:
        sel_obj.select_set(True)