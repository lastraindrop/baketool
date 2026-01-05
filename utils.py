import bpy
import bmesh
import logging
import random
import math
import colorsys
import numpy as np
from pathlib import Path
from .constants import FORMAT_SETTINGS, BSDF_COMPATIBILITY_MAP, SOCKET_DEFAULT_TYPE, CHANNEL_BAKE_INFO, CHANNEL_DEFINITIONS

logger = logging.getLogger(__name__)

def check_objects_uv(objects):
    no_uv_objs = []
    for obj in objects:
        if obj.type == 'MESH' and not obj.data.uv_layers:
            no_uv_objs.append(obj.name)
    return no_uv_objs

def reset_channels_logic(setting):
    """
    Safely resets channels based on the bake type in the provided setting object.
    Directly modifies the collection property without using Operators.
    """
    defs = []
    # 1. Determine definitions based on Bake Type
    if setting.bake_type == 'BSDF': 
        # Compatibility check for Blender 4.0+
        key = 'BSDF_4' if bpy.app.version >= (4, 0, 0) else 'BSDF_3'
        defs.extend(CHANNEL_DEFINITIONS.get(key, []))
    elif setting.bake_type in CHANNEL_DEFINITIONS: 
        defs.extend(CHANNEL_DEFINITIONS[setting.bake_type])
    
    # 2. Add Optional Maps
    if setting.use_light_map: 
        defs.extend(CHANNEL_DEFINITIONS.get('LIGHT', []))
    if setting.use_mesh_map: 
        defs.extend(CHANNEL_DEFINITIONS.get('MESH', []))
    if setting.use_extension_map:
        defs.extend(CHANNEL_DEFINITIONS.get('EXTENSION', []))
    
    d_ids = {d['id'] for d in defs}
    
    # 3. Remove invalid channels (iterate backwards)
    for i in range(len(setting.channels)-1, -1, -1):
         if setting.channels[i].id not in d_ids: 
             setting.channels.remove(i)
    
    # 4. Add new channels
    existing_ids = {c.id for c in setting.channels}
    for d in defs:
        if d['id'] not in existing_ids:
            new_chan = setting.channels.add()
            new_chan.id = d['id']
            new_chan.name = d['name']
            # Apply defaults
            defaults = d.get('defaults', {})
            for k, v in defaults.items():
                if hasattr(new_chan, k):
                    setattr(new_chan, k, v)

class ContextOverride:
    def __init__(self, context, active_object=None, selected_objects=None):
        self.context = context
        self.target_active = active_object
        self.target_selected = selected_objects or ([active_object] if active_object else [])
        self.original_active = None
        self.original_selected = []

    def __enter__(self):
        try:
            self.original_active = self.context.view_layer.objects.active
            self.original_selected = self.context.selected_objects[:]
        except: pass
        
        bpy.ops.object.select_all(action='DESELECT')
        if self.target_active:
            self.context.view_layer.objects.active = self.target_active
        for obj in self.target_selected:
            if obj: obj.select_set(True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            bpy.ops.object.select_all(action='DESELECT')
            if self.original_active:
                self.context.view_layer.objects.active = self.original_active
            for obj in self.original_selected:
                if obj: obj.select_set(True)
        except: pass

def generate_optimized_colors(count, start_color=(1,0,0,1), iterations=0, manual_start=True, seed=0):
    if count <= 0: return np.zeros((0, 4), dtype=np.float32)
    
    # 黄金分割步进
    golden_ratio = 0.618033988749895
    
    # 构建基础 Hue 数组
    indices = np.arange(count, dtype=np.float64)
    
    if manual_start:
        h_start, _, _ = colorsys.rgb_to_hsv(start_color[0], start_color[1], start_color[2])
        # h[0] = h_start, h[1] = h_start + gr, ...
        # 注意：这里如果 manual_start=True，第一个颜色是固定的，后面遵循序列
        # 为了保持逻辑简单，我们生成 count 个，然后手动覆盖第一个
        hues = (h_start + indices * golden_ratio) % 1.0
    else:
        rng = np.random.default_rng(seed)
        start_hue = rng.random()
        hues = (start_hue + indices * golden_ratio) % 1.0

    # 使用 Numpy 生成随机的 S 和 V
    # 为了确定性，我们需要一个基于索引的伪随机，或者使用 numpy 的 random generator
    rng = np.random.default_rng(seed)
    
    # S: 0.5 ~ 0.8
    sats = 0.5 + rng.random(count) * 0.3
    # V: 0.8 ~ 1.0
    vals = 0.8 + rng.random(count) * 0.2
    
    # HSV to RGB (Vectorized)
    # Numpy 没有直接的 hsv_to_rgb 向量化函数，但我们可以简单实现或列表推导
    # 列表推导在几十个颜色时比引入 skimage 依赖更轻量且足够快
    colors = np.array([colorsys.hsv_to_rgb(h, s, v) for h, s, v in zip(hues, sats, vals)], dtype=np.float32)
    
    # 添加 Alpha 通道
    colors = np.column_stack((colors, np.ones(count, dtype=np.float32)))
    
    if manual_start:
        colors[0] = list(start_color)
        
    return colors

def setup_mesh_attribute(obj, id_type='ELEMENT', start_color=(1,0,0,1), iterations=0, manual_start=True, seed=0):
    if obj.type != 'MESH': return None
    if id_type == 'ELE': id_type = 'ELEMENT'
    
    attr_name = f"BT_ATTR_{id_type}"
    if attr_name in obj.data.attributes:
        return attr_name

    current_mode = obj.mode
    if current_mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.ensure_lookup_table()
        
        # 1. Topology Analysis (Find Islands)
        # face_index -> island_index mapping
        # Initialize with -1
        face_island_map = np.full(len(bm.faces), -1, dtype=np.int32)
        island_count = 0
        
        if id_type == 'MAT':
            for f in bm.faces:
                face_island_map[f.index] = f.material_index
            island_count = np.max(face_island_map) + 1
            
        elif id_type in ('ELEMENT', 'SEAM', 'UVI'):
            faces_set = set(bm.faces)
            uv_lay = bm.loops.layers.uv.active if id_type == 'UVI' else None
            
            while faces_set:
                seed_face = faces_set.pop()
                stack = [seed_face]
                # Assign current island index to seed
                face_island_map[seed_face.index] = island_count
                
                while stack:
                    curr = stack.pop()
                    for edge in curr.edges:
                        if id_type == 'SEAM' and edge.seam: continue
                        for other_f in edge.link_faces:
                            if other_f is curr or other_f not in faces_set: continue
                            
                            should_join = True
                            if id_type == 'UVI' and uv_lay:
                                loops_curr = {l.vert: l[uv_lay].uv for l in curr.loops}
                                loops_other = {l.vert: l[uv_lay].uv for l in other_f.loops}
                                match = 0
                                for v in edge.verts:
                                    if v in loops_curr and v in loops_other:
                                        if (loops_curr[v]-loops_other[v]).length_squared < 1e-5: match += 1
                                if match < 2: should_join = False
                            
                            if should_join:
                                faces_set.remove(other_f)
                                face_island_map[other_f.index] = island_count
                                stack.append(other_f)
                island_count += 1

        # 2. Color Generation
        # Generate enough colors for all islands
        # If finding islands failed or empty, count might be 0
        if island_count == 0: island_count = 1
        
        palette = generate_optimized_colors(island_count, start_color, iterations, manual_start, seed)
        
        # 3. Data Writing (Numpy Accelerated)
        # Create Attribute
        if not obj.data.attributes.get(attr_name):
            obj.data.attributes.new(name=attr_name, type='BYTE_COLOR', domain='CORNER')
        attr = obj.data.attributes[attr_name]
        
        # Map faces to colors
        # face_island_map contains index into palette for each face
        # Handle cases where map might be -1 (shouldn't happen with correct logic, but for safety)
        face_island_map[face_island_map == -1] = 0
        
        # Determine sorting/randomization if needed? 
        # The original code sorted islands by size to optimize color distribution (largest gets best colors).
        # To replicate "largest island gets first color":
        # We need to re-map the island indices based on frequency.
        
        unique, counts = np.unique(face_island_map, return_counts=True)
        # Sort indices by count (descending)
        sorted_indices = np.argsort(-counts) 
        # Map original island ID to new sorted ID
        # Create a lookup table
        remap_table = np.zeros(island_count, dtype=np.int32)
        # sorted_indices[0] is the island ID with most faces. We want it to map to color 0.
        # But wait, unique[sorted_indices[0]] is the island ID.
        for i, idx in enumerate(sorted_indices):
            original_island_id = unique[idx]
            remap_table[original_island_id] = i
            
        # Apply remapping
        remapped_island_indices = remap_table[face_island_map]
        
        # Get face colors (NumFaces, 4)
        face_colors = palette[remapped_island_indices]
        
        # Expand to Loops (NumLoops, 4)
        loop_totals = np.zeros(len(obj.data.polygons), dtype=np.int32)
        obj.data.polygons.foreach_get("loop_total", loop_totals)
        
        # Repeat face colors for each loop vertex
        loop_colors = np.repeat(face_colors, loop_totals, axis=0)
        
        # Flatten and Write
        attr.data.foreach_set("color", loop_colors.flatten())
        
    except Exception as e:
        logger.error(f"ID Map Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        attr_name = None
    finally:
        bm.free()
    
    if current_mode != 'OBJECT':
        try: bpy.ops.object.mode_set(mode=current_mode)
        except: pass
    return attr_name

def process_pbr_numpy(target_img, spec_img, diff_img, map_id, threshold=0.04):
    """
    使用 Numpy 加速 PBR 转换计算
    target_img: 目标图像对象 (写入)
    spec_img: 来源 Specular 图像 (读取)
    diff_img: 来源 Diffuse/Color 图像 (读取)
    map_id: 'pbr_conv_metal' 或 'pbr_conv_base'
    threshold: Dielectric F0 阈值
    """
    try:
        # 1. 验证尺寸
        count = len(target_img.pixels)
        if len(spec_img.pixels) != count or (diff_img and len(diff_img.pixels) != count):
            logger.warning(f"Numpy PBR: Resolution mismatch. Target: {target_img.size[:]}")
            return False

        # 2. 读取数据 (Foreach Get)
        # 始终是 RGBA float 数组
        spec_arr = np.empty(count, dtype=np.float32)
        spec_img.pixels.foreach_get(spec_arr)
        
        # Reshape to (PixelCount, 4)
        spec_arr = spec_arr.reshape(-1, 4)
        
        # 3. 计算 Metallic
        # Metal = (Max(R,G,B) - Threshold) / (1 - Threshold)
        # 取 RGB 最大值
        spec_max = np.max(spec_arr[:, :3], axis=1)
        
        denom = 1.0 - threshold
        if denom < 1e-5: denom = 1e-5
        
        metal_arr = np.clip((spec_max - threshold) / denom, 0.0, 1.0)
        
        # 4. 根据类型生成结果
        result_arr = np.zeros_like(spec_arr)
        result_arr[:, 3] = 1.0 # Alpha default
        
        if map_id == 'pbr_conv_metal':
            # BW map: R=G=B=Metal
            result_arr[:, 0] = metal_arr
            result_arr[:, 1] = metal_arr
            result_arr[:, 2] = metal_arr
            
        elif map_id == 'pbr_conv_base':
            if not diff_img: return False
            
            diff_arr = np.empty(count, dtype=np.float32)
            diff_img.pixels.foreach_get(diff_arr)
            diff_arr = diff_arr.reshape(-1, 4)
            
            # Base Color = Mix(Diff, Spec, Factor=Metal)
            # Vectorized Mix
            # shape metal to (N, 1) for broadcasting
            m = metal_arr[:, np.newaxis]
            
            # RGB Mix
            result_arr[:, :3] = diff_arr[:, :3] * (1.0 - m) + spec_arr[:, :3] * m
            
            # Alpha handling (Keep diffuse alpha?)
            result_arr[:, 3] = diff_arr[:, 3]

        # 5. 写入数据
        target_img.pixels.foreach_set(result_arr.flatten())
        return True
        
    except Exception as e:
        logger.error(f"Numpy Calc Error: {e}")
        return False

def apply_baked_result(original_obj, task_images, setting, task_base_name):
    if not task_images: return None
    col_name = "Baked_Results"
    target_col = bpy.data.collections.get(col_name) or bpy.data.collections.new(col_name)
    if col_name not in bpy.context.scene.collection.children:
        try: bpy.context.scene.collection.children.link(target_col)
        except: pass

    target_name = f"{task_base_name}_Baked"
    new_obj = bpy.data.objects.get(target_name)
    if new_obj:
        new_obj.data.materials.clear()
    else:
        new_obj = original_obj.copy()
        new_obj.data = original_obj.data.copy()
        new_obj.name = target_name
        for col in new_obj.users_collection: col.objects.unlink(new_obj)
        target_col.objects.link(new_obj)

    first_val = next(iter(task_images.values()))
    is_split = isinstance(first_val, dict)
    
    if is_split:
        orig_mat_names = [s.material.name for s in original_obj.material_slots if s.material]
        while len(new_obj.material_slots) < len(orig_mat_names): new_obj.data.materials.append(None)
        for i, orig_name in enumerate(orig_mat_names):
            mat_name = f"{task_base_name}_{orig_name}_Baked"
            mat = _get_or_create_mat(mat_name)
            new_obj.material_slots[i].material = mat
            mat_textures = {}
            for chan_id, mat_dict in task_images.items():
                if orig_name in mat_dict: mat_textures[chan_id] = mat_dict[orig_name]
            _setup_baked_material(mat, mat_textures)
    else:
        mat_name = f"{task_base_name}_Mat"
        mat = _get_or_create_mat(mat_name)
        new_obj.data.materials.clear()
        new_obj.data.materials.append(mat)
        _setup_baked_material(mat, task_images)
    return new_obj

def _get_or_create_mat(name):
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
    return mat

def _setup_baked_material(mat, texture_map):
    tree = mat.node_tree
    nodes = tree.nodes; links = tree.links
    nodes.clear()
    
    output = nodes.new('ShaderNodeOutputMaterial'); output.location = (300, 0)
    bsdf = nodes.new('ShaderNodeBsdfPrincipled'); bsdf.location = (0, 0)
    links.new(bsdf.outputs[0], output.inputs[0])

    y_pos = 0
    socket_map = {
        'color': ('Base Color', False, False), 'metal': ('Metallic', True, False),
        'rough': ('Roughness', True, False), 'normal': ('Normal', True, True),
        'specular': ('Specular IOR Level', True, False), 'emi': ('Emission Color', False, False),
        'alpha': ('Alpha', True, False), 'ao': ('Base Color', True, False),
        'combine': ('Base Color', False, False)
    }
    
    for chan_id, image in texture_map.items():
        if chan_id not in socket_map: continue
        target_name, is_non_color, is_normal = socket_map[chan_id]
        
        target_socket = None
        candidates = [target_name]
        if target_name == 'Specular IOR Level': candidates.append('Specular')
        if target_name == 'Emission Color': candidates.append('Emission')
        for n in candidates:
            if n in bsdf.inputs: target_socket = bsdf.inputs[n]; break
            
        if not target_socket and not is_normal: continue
        
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = image
        tex.location = (-600 if is_normal else -300, y_pos)
        y_pos -= 280
        
        if is_non_color:
            try: tex.image.colorspace_settings.name = 'Non-Color'
            except: pass
            
        if is_normal:
            nor = nodes.new('ShaderNodeNormalMap')
            nor.location = (-300, tex.location.y)
            links.new(tex.outputs[0], nor.inputs['Color'])
            if 'Normal' in bsdf.inputs: links.new(nor.outputs['Normal'], bsdf.inputs['Normal'])
        elif target_socket:
            links.new(tex.outputs[0], target_socket)
            
        if chan_id == 'emi' and 'Emission Strength' in bsdf.inputs:
            bsdf.inputs['Emission Strength'].default_value = 1.0
        if chan_id == 'alpha' and 'Alpha' in bsdf.inputs:
            mat.blend_method = 'BLEND'

def report_error(operator, message):
    if operator: operator.report({'ERROR'}, message)
    logger.error(message)

class SceneSettingsContext:
    def __init__(self, category, settings):
        self.category = category; self.settings = settings; self.original = {}
    def __enter__(self):
        self.original = self._manage(self.category, get_only=True)
        self._manage(self.category, self.settings)
        return self
    def __exit__(self, t, v, tb):
        self._manage(self.category, self.original)
    
    def _manage(self, category, settings=None, get_only=False):
        scene = bpy.context.scene
        targets = {'scene': scene.render, 'cycles': scene.cycles, 'image': scene.render.image_settings, 'cm': scene.view_settings}
        attr_map = {'scene': {'res_x': 'resolution_x', 'res_y': 'resolution_y'}}
        
        target = targets.get(category)
        if not target: return {}
        
        if get_only: return {} # Simplified
        if not settings: return {}
        
        for k, v in settings.items():
            real = attr_map.get(category, {}).get(k, k)
            if hasattr(target, real) and v is not None:
                try: setattr(target, real, v)
                except: pass
        return {}

def set_image(name, x, y, alpha=True, full=False, space='sRGB', ncol=False, basiccolor=(0,0,0,0), clear=True):
    image = bpy.data.images.get(name)
    if image:
        if image.size[0] != x or image.size[1] != y: image.scale(x, y)
    else: 
        image = bpy.data.images.new(name, width=x, height=y, alpha=alpha, float_buffer=full)
    
    image.file_format = 'PNG' 
    image.use_fake_user = True
    
    if not full:
        try: image.colorspace_settings.name = space
        except: pass
    
    if alpha: image.alpha_mode = 'STRAIGHT'
    if clear: image.generated_color = basiccolor
    return image

def save_image(image, path='//', folder=False, folder_name='folder', file_format='PNG', motion=False, frame=0, reload=False, fillnum=4, save=True, separator="_", color_mode='RGB'):
    if not save or not image: return None
    
    base = Path(bpy.path.abspath(path))
    if str(base) == '.': base = Path(bpy.data.filepath).parent 
    directory = base / folder_name if folder else base
    
    try: directory.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {e}")
        return None
    
    info = FORMAT_SETTINGS.get(file_format, {})
    ext = info.get("extensions", ["." + file_format.lower()])[0]
    
    fname = f"{image.name}{separator}{str(frame).zfill(fillnum)}{ext}" if motion else f"{image.name}{ext}"
    filepath = directory / fname
    abs_path = str(filepath.resolve())
    
    old_path = image.filepath_raw
    old_fmt = image.file_format
    
    try:
        image.filepath_raw = abs_path
        image.file_format = file_format
        image.save()
    except Exception as e:
        logger.error(f"Image save failed: {e}")
        image.filepath_raw = old_path
        image.file_format = old_fmt
        return None
        
    if not motion and reload:
        try: 
            image.source = 'FILE'
            image.reload()
        except: pass
        
    return abs_path

class NodeGraphHandler:
    def __init__(self, materials):
        self.materials = [m for m in materials if m and m.use_nodes]
        self.history = {}       
        self.active_nodes = {}  
        self.temp_attributes = [] 

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): self.cleanup(); return False

    def setup_for_pass(self, bake_pass, socket_name, image, mesh_type=None, attr_name=None, specific_material=None, channel_settings=None):
        targets = [specific_material] if specific_material else self.materials
        for mat in targets:
            if not mat or not mat.use_nodes: continue
            
            # Clean up previous pass for this material
            self._clean_material_temp_nodes(mat)
            
            tree = mat.node_tree; nodes = tree.nodes; links = tree.links
            if mat not in self.active_nodes: self.active_nodes[mat] = []
            
            out_n = next((n for n in nodes if n.bl_idname=='ShaderNodeOutputMaterial' and n.is_active_output), None)
            if not out_n: out_n = next((n for n in nodes if n.bl_idname=='ShaderNodeOutputMaterial'), None)
            if not out_n: continue
            
            surf = out_n.inputs[0]
            if mat not in self.history:
                self.history[mat] = {'sock': surf, 'src': surf.links[0].from_socket if surf.is_linked else None}
            
            # Target Image
            img_n = nodes.new('ShaderNodeTexImage')
            img_n.image = image
            img_n.location=(-300,400)
            img_n.select=True; nodes.active=img_n
            self.active_nodes[mat].append(img_n)
            
            if bake_pass != 'EMIT' and not mesh_type and channel_settings.id not in {'pbr_conv_base', 'pbr_conv_metal'}: continue
            
            emi = nodes.new('ShaderNodeEmission')
            emi.location = (out_n.location.x-200, out_n.location.y)
            self.active_nodes[mat].append(emi)
            
            src = None
            if mesh_type: 
                src = self._create_mesh_map(nodes, mat, mesh_type, attr_name, channel_settings)
            elif channel_settings.id.startswith('pbr_conv_'):
                src = self._create_extension_map(nodes, tree, mat, channel_settings)
            else: 
                src = self._find_socket(tree, nodes, mat, socket_name, channel_settings)
            
            if src: links.new(src, emi.inputs[0])
            links.new(emi.outputs[0], surf)

    def _clean_material_temp_nodes(self, mat):
        if mat in self.active_nodes:
            tree = mat.node_tree
            if tree:
                for n in self.active_nodes[mat]:
                    try: tree.nodes.remove(n)
                    except: pass
            self.active_nodes[mat] = []

    def _create_extension_map(self, nodes, tree, mat, settings):
        map_id = settings.id
        threshold = settings.pbr_conv_threshold
        
        # 寻找源 Socket：Specular 和 Base Color/Diffuse
        spec_src = self._find_socket(tree, nodes, mat, 'specular', None)
        diff_src = self._find_socket(tree, nodes, mat, 'color', None) # color map usually means diffuse here
        
        # 构建计算 Metallic 的节点链
        # Metallic = (Max(Spec) - Threshold) / (1.0 - Threshold) -> Clamp
        
        # 1. Separate RGB (或者用 Vector Math -> Length 也可以，但 Max 更符合 PBR 逻辑)
        sep = nodes.new('ShaderNodeSeparateColor')
        tree.links.new(spec_src, sep.inputs[0])
        self.active_nodes[mat].append(sep)
        
        # 2. Max(R, G)
        math1 = nodes.new('ShaderNodeMath'); math1.operation = 'MAXIMUM'
        tree.links.new(sep.outputs[0], math1.inputs[0])
        tree.links.new(sep.outputs[1], math1.inputs[1])
        self.active_nodes[mat].append(math1)
        
        # 3. Max(Max(R,G), B)
        math2 = nodes.new('ShaderNodeMath'); math2.operation = 'MAXIMUM'
        tree.links.new(math1.outputs[0], math2.inputs[0])
        tree.links.new(sep.outputs[2], math2.inputs[1])
        self.active_nodes[mat].append(math2)
        
        # 4. Subtract Threshold
        sub = nodes.new('ShaderNodeMath'); sub.operation = 'SUBTRACT'
        tree.links.new(math2.outputs[0], sub.inputs[0])
        sub.inputs[1].default_value = threshold
        self.active_nodes[mat].append(sub)
        
        # 5. Divide by (1.0 - Threshold)
        div = nodes.new('ShaderNodeMath'); div.operation = 'DIVIDE'
        tree.links.new(sub.outputs[0], div.inputs[0])
        # 避免除以0
        denom = 1.0 - threshold
        if abs(denom) < 1e-5: denom = 1e-5
        div.inputs[1].default_value = denom
        self.active_nodes[mat].append(div)
        
        # 6. Clamp
        clamp = nodes.new('ShaderNodeClamp')
        tree.links.new(div.outputs[0], clamp.inputs[0])
        self.active_nodes[mat].append(clamp)
        
        metallic_out = clamp.outputs[0]
        
        if map_id == 'pbr_conv_metal':
            return metallic_out
            
        elif map_id == 'pbr_conv_base':
            # Base Color = Mix(Diff, Spec, Factor=Metallic)
            mix = nodes.new('ShaderNodeMix')
            mix.data_type = 'RGBA'
            tree.links.new(metallic_out, mix.inputs[0]) # Factor
            tree.links.new(diff_src, mix.inputs[6]) # A (Diffuse)
            tree.links.new(spec_src, mix.inputs[7]) # B (Specular)
            self.active_nodes[mat].append(mix)
            return mix.outputs[2] # Result
            
        return None

    def _find_socket(self, tree, nodes, mat, socket_name, settings):
        bsdf = next((n for n in tree.nodes if n.bl_idname=='ShaderNodeBsdfPrincipled'), None)
        found = None
        if bsdf:
            for cand in BSDF_COMPATIBILITY_MAP.get(socket_name, [socket_name]):
                if cand in bsdf.inputs: found = bsdf.inputs[cand]; break
        
        src = None
        if found:
            if found.is_linked: src = found.links[0].from_socket
            else: src = self._const(nodes, mat, found.default_value)
        else:
            src = self._const(nodes, mat, SOCKET_DEFAULT_TYPE.get(socket_name, (0,0,0,1)))
            
        if settings and socket_name == 'rough' and getattr(settings, 'rough_inv', False):
            inv = nodes.new('ShaderNodeInvert'); inv.inputs[0].default_value=1.0
            self.active_nodes[mat].append(inv)
            tree.links.new(src, inv.inputs[1])
            src = inv.outputs[0]
        return src

    def _create_mesh_map(self, nodes, mat, type, attr, set):
        n = None; out = None
        if type == 'ID': n=nodes.new('ShaderNodeAttribute'); n.attribute_name=attr; out=n.outputs['Color']
        elif type == 'POS': n=nodes.new('ShaderNodeNewGeometry'); out=n.outputs['Position']
        elif type == 'UV': n=nodes.new('ShaderNodeUVMap'); out=n.outputs['UV']
        elif type == 'WF': 
            n=nodes.new('ShaderNodeWireframe'); n.use_pixel_size=getattr(set,'wireframe_use_pix',False)
            n.inputs[0].default_value=getattr(set,'wireframe_dis',0.01); out=n.outputs[0]
        elif type == 'AO':
            n=nodes.new('ShaderNodeAmbientOcclusion'); n.samples=getattr(set,'ao_sample',16)
            n.inside=getattr(set,'ao_inside',False); n.inputs['Distance'].default_value=getattr(set,'ao_dis',1.0); out=n.outputs['Color']
        elif type == 'BEVEL':
            n=nodes.new('ShaderNodeBevel'); n.samples=getattr(set,'bevel_sample',8)
            n.inputs['Radius'].default_value=getattr(set,'bevel_rad',0.05); out=n.outputs[0]
        elif type == 'CURVATURE':
            # 1. Bevel Normal
            bev = nodes.new('ShaderNodeBevel')
            bev.samples = getattr(set, 'curvature_sample', 6)
            bev.inputs['Radius'].default_value = getattr(set, 'curvature_rad', 0.05)
            self.active_nodes[mat].append(bev)
            
            # 2. Geometry Normal (Standard)
            geo = nodes.new('ShaderNodeNewGeometry')
            self.active_nodes[mat].append(geo)
            
            # 3. Dot Product
            dot = nodes.new('ShaderNodeVectorMath')
            dot.operation = 'DOT_PRODUCT'
            mat.node_tree.links.new(bev.outputs['Normal'], dot.inputs[0])
            mat.node_tree.links.new(geo.outputs['Normal'], dot.inputs[1])
            self.active_nodes[mat].append(dot)
            
            # 4. Invert (1 - Dot) to get edges as white
            sub = nodes.new('ShaderNodeMath')
            sub.operation = 'SUBTRACT'
            sub.inputs[0].default_value = 1.0
            mat.node_tree.links.new(dot.outputs['Value'], sub.inputs[1])
            self.active_nodes[mat].append(sub)
            
            # 5. Contrast/Boost
            mult = nodes.new('ShaderNodeMath')
            mult.operation = 'MULTIPLY'
            mult.inputs[1].default_value = getattr(set, 'curvature_contrast', 1.0) * 10.0 # Multiply by 10 to make UI value (1.0) feel more natural
            mat.node_tree.links.new(sub.outputs[0], mult.inputs[0])
            self.active_nodes[mat].append(mult)
            
            # 6. Clamp
            clamp = nodes.new('ShaderNodeClamp')
            mat.node_tree.links.new(mult.outputs[0], clamp.inputs[0])
            self.active_nodes[mat].append(clamp)
            
            out = clamp.outputs[0]
            
        elif type == 'SLOPE':
            n=nodes.new('ShaderNodeVectorMath'); n.operation='DOT_PRODUCT'
            geo=nodes.new('ShaderNodeNewGeometry')
            self.active_nodes[mat].append(geo)
            
            d = getattr(set, 'slope_directions', 'Z')
            vec = (0,0,1)
            if d == 'X': vec = (1,0,0)
            elif d == 'Y': vec = (0,1,0)
            n.inputs[1].default_value = vec
            mat.node_tree.links.new(geo.outputs['Normal'], n.inputs[0])
            out = n.outputs['Value']
            
            if getattr(set, 'slope_invert', False):
                inv = nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
                mat.node_tree.links.new(out, inv.inputs[1])
                self.active_nodes[mat].append(inv)
                out = inv.outputs[0]
        
        if n: self.active_nodes[mat].append(n)
        return out

    def _const(self, nodes, mat, val):
        rgb = nodes.new('ShaderNodeRGB')
        v = (val[0],val[1],val[2],1) if hasattr(val,"__len__") and len(val)>=3 else (val,val,val,1)
        rgb.outputs[0].default_value = v
        self.active_nodes[mat].append(rgb)
        return rgb.outputs[0]

    def cleanup(self):
        for mat, d in self.history.items():
            if not mat.node_tree: continue
            sock = d['sock']
            if sock.is_linked:
                for l in list(sock.links): mat.node_tree.links.remove(l)
            if d['src']: 
                try: mat.node_tree.links.new(d['src'], sock)
                except: pass
        self.history.clear()
        
        for mat, ns in self.active_nodes.items():
            if not mat.node_tree: continue
            for n in ns: 
                try: mat.node_tree.nodes.remove(n)
                except: pass
        self.active_nodes.clear()
        
        for obj, attr in self.temp_attributes:
            try: obj.data.attributes.remove(obj.data.attributes[attr])
            except: pass
        self.temp_attributes.clear()
        
        d = bpy.data.images.get("BT_Protection_Dummy")
        if d: bpy.data.images.remove(d)
    
    def setup_protection(self, objects, active_materials):
        active_set = set(active_materials)
        d = bpy.data.images.get("BT_Protection_Dummy")
        if not d: d = bpy.data.images.new("BT_Protection_Dummy", 32, 32, alpha=True); d.use_fake_user=True
        for obj in objects:
            if obj.type!='MESH': continue
            for s in obj.material_slots:
                m = s.material
                if m and m.use_nodes and m not in active_set:
                    if m not in self.active_nodes: self.active_nodes[m]=[]
                    n = m.node_tree.nodes.new('ShaderNodeTexImage'); n.image=d; n.select=True
                    m.node_tree.nodes.active=n; self.active_nodes[m].append(n)
