import bpy
import bmesh
import logging
import random
import math
from pathlib import Path
from .constants import FORMAT_SETTINGS

logger = logging.getLogger(__name__)

# --- [重构核心] 退火颜色优化算法 ---

def generate_optimized_colors(count, start_color=(1,0,0,1), use_annealing=True):
    """
    使用简化的退火/互斥算法生成 count 个差异最大的颜色。
    start_color: 用户指定的第一个颜色。
    """
    if count <= 0: return []
    
    # 初始化颜色池，第一个颜色固定为用户指定色
    colors = [list(start_color[:3])] 
    
    if count == 1: return [tuple(colors[0]) + (1.0,)]

    if not use_annealing:
        # 如果不使用优化，使用高对比度色相环步进
        for i in range(1, count):
            random.seed(i)
            colors.append([random.random() for _ in range(3)])
        return [tuple(c) + (1.0,) for c in colors]

    # 模拟退火/迭代排斥逻辑
    # 1. 预填充随机种子点
    for i in range(1, count):
        random.seed(i * 13)
        colors.append([random.random() for _ in range(3)])

    # 2. 迭代优化 ( repulsion )
    # 模拟电荷排斥：点在 RGB 立方体内移动，远离邻居
    iterations = 20
    learning_rate = 0.1
    
    for step in range(iterations):
        temp_rate = learning_rate * (1.0 - step / iterations)
        for i in range(1, count): # 跳过第一个（起始色固定）
            force = [0.0, 0.0, 0.0]
            curr = colors[i]
            
            # 计算来自所有其他点的排斥力
            for j in range(count):
                if i == j: continue
                other = colors[j]
                diff = [curr[k] - other[k] for k in range(3)]
                dist_sq = sum(d*d for d in diff) + 0.001
                
                # 反比力模型 (1/r^2)
                f_mag = 1.0 / dist_sq
                for k in range(3):
                    force[k] += (diff[k] / math.sqrt(dist_sq)) * f_mag
            
            # 更新位置并限制在 [0, 1] 范围内
            for k in range(3):
                colors[i][k] = max(0.0, min(1.0, colors[i][k] + force[k] * temp_rate))

    return [tuple(c) + (1.0,) for c in colors]

def setup_mesh_attribute(obj, id_type='ELEMENT', start_color=(1,0,0,1), use_annealing=True):
    if obj.type != 'MESH': return None
    bm = bmesh.new(); bm.from_mesh(obj.data)
    attr_name = f"BT_ATTR_{id_type}"
    layer = bm.loops.layers.color.get(attr_name) or bm.loops.layers.color.new(attr_name)

    # 1. 预分析数量
    target_ids = [] # 存储孤岛或索引
    if id_type == 'ELEMENT':
        faces = set(bm.faces)
        while faces:
            seed = faces.pop(); queue = [seed]; island = {seed}
            while queue:
                f = queue.pop(0)
                for e in f.edges:
                    for lf in e.link_faces:
                        if lf in faces: faces.remove(lf); queue.append(lf); island.add(lf)
            target_ids.append(island)
    elif id_type == 'MAT':
        mat_indices = {f.material_index for f in bm.faces}
        target_ids = sorted(list(mat_indices))
    elif id_type == 'SEAM':
        target_ids = ['NON_SEAM', 'SEAM']
    elif id_type == 'UVI':
        uv_lay = bm.loops.layers.uv.active
        if uv_lay:
            faces = set(bm.faces)
            while faces:
                seed = faces.pop(); queue = [seed]; island = {seed}
                while queue:
                    curr = queue.pop(0)
                    for edge in curr.edges:
                        for other_f in edge.link_faces:
                            if other_f in faces:
                                is_uv_connected = False
                                for l1 in curr.loops:
                                    if l1.edge == edge:
                                        for l2 in other_f.loops:
                                            if l2.edge == edge:
                                                if (l1[uv_lay].uv - l2[uv_lay].uv).length < 0.0001:
                                                    is_uv_connected = True; break
                                if is_uv_connected: faces.remove(other_f); queue.append(other_f); island.add(other_f)
                target_ids.append(island)

    # 2. 生成最优颜色列表
    optimized_palette = generate_optimized_colors(len(target_ids), start_color, use_annealing)

    # 3. 应用颜色
    if id_type in ('ELEMENT', 'UVI'):
        for i, island in enumerate(target_ids):
            col = optimized_palette[i]
            for f in island:
                for lp in f.loops: lp[layer] = col
    elif id_type == 'MAT':
        # 建立 材质索引 -> 颜色 的映射
        idx_to_col = {idx: optimized_palette[i] for i, idx in enumerate(target_ids)}
        for f in bm.faces:
            col = idx_to_col.get(f.material_index, (0,0,0,1))
            for lp in f.loops: lp[layer] = col
    elif id_type == 'SEAM':
        for f in bm.faces:
            for lp in f.loops:
                lp[layer] = optimized_palette[1] if lp.edge.seam else optimized_palette[0]

    bm.to_mesh(obj.data); bm.free()
    obj.data.update(); obj.data.calc_loop_triangles()
    return attr_name

# --- [基础辅助类保持不变] ---

def report_error(operator, message, status='CANCELLED'):
    if operator: operator.report({'ERROR'}, message)
    logger.error(message)
    return {status}

class SceneSettingsContext:
    def __init__(self, category, settings):
        self.category = category; self.settings = settings; self.original = {}
    def __enter__(self):
        self.original = manage_scene_settings(self.category, getorset=False)
        manage_scene_settings(self.category, self.settings, getorset=True); return self
    def __exit__(self, t, v, tb):
        manage_scene_settings(self.category, self.original, getorset=True)

class NodeGraphHandler:
    def __init__(self, materials):
        self.materials = materials; self.history = {}; self.temp_nodes = {}; self.temp_attributes = []

    def setup_for_pass(self, bake_pass, socket_name, image, mesh_type=None, attr_name=None):
        for mat in self.materials:
            if not mat or not mat.use_nodes: continue
            tree = mat.node_tree; nodes = tree.nodes; links = tree.links
            if mat not in self.temp_nodes: self.temp_nodes[mat] = []
            img_node = nodes.new('ShaderNodeTexImage'); img_node.image = image; nodes.active = img_node; self.temp_nodes[mat].append(img_node)
            if bake_pass != 'EMIT' and not mesh_type: continue
            output = self._get_output_node(tree)
            if not output: continue
            surf_in = output.inputs[0]
            if mat not in self.history:
                self.history[mat] = {'sock': surf_in, 'src': surf_in.links[0].from_socket if surf_in.is_linked else None}
            emi = nodes.new('ShaderNodeEmission'); self.temp_nodes[mat].append(emi)
            source = None
            if mesh_type:
                if mesh_type == 'ID':
                    attr = nodes.new('ShaderNodeAttribute'); attr.attribute_name = attr_name
                    self.temp_nodes[mat].append(attr); source = attr.outputs['Color']
                elif mesh_type == 'POS':
                    geom = nodes.new('ShaderNodeNewGeometry'); self.temp_nodes[mat].append(geom); source = geom.outputs['Position']
                elif mesh_type == 'UV':
                    uvm = nodes.new('ShaderNodeUVMap'); self.temp_nodes[mat].append(uvm); source = uvm.outputs['UV']
                elif mesh_type == 'WF':
                    wf = nodes.new('ShaderNodeWireframe'); self.temp_nodes[mat].append(wf); source = wf.outputs[0]
            else:
                target = self._find_socket(tree, socket_name)
                if target:
                    if target.is_linked: source = target.links[0].from_socket
                    else:
                        rgb = nodes.new('ShaderNodeRGB'); v = target.default_value
                        rgb.outputs[0].default_value = (v[0],v[1],v[2],1) if hasattr(v,'__len__') else (v,v,v,1)
                        self.temp_nodes[mat].append(rgb); source = rgb.outputs[0]
                else:
                    rgb = nodes.new('ShaderNodeRGB'); rgb.outputs[0].default_value = (0,0,0,1); self.temp_nodes[mat].append(rgb); source = rgb.outputs[0]
            if final_source := source: links.new(final_source, emi.inputs[0])
            links.new(emi.outputs[0], surf_in)

    def cleanup(self):
        for mat, data in self.history.items():
            if mat and mat.node_tree:
                try:
                    target = data['sock']; source = data['src']
                    if source: mat.node_tree.links.new(source, target)
                    else:
                        for l in list(target.links): mat.node_tree.links.remove(l)
                except: pass
        self.history.clear()
        for mat, nodes in self.temp_nodes.items():
            if mat and mat.node_tree:
                for n in nodes:
                    try: mat.node_tree.nodes.remove(n)
                    except: pass
        self.temp_nodes.clear()
        for obj, attr in self.temp_attributes:
            if obj and obj.data and attr in obj.data.attributes:
                obj.data.attributes.remove(obj.data.attributes[attr])
        self.temp_attributes.clear()

    def _get_output_node(self, tree):
        for n in tree.nodes:
            if n.bl_idname == 'ShaderNodeOutputMaterial' and n.is_active_output: return n
        return next((n for n in tree.nodes if n.bl_idname == 'ShaderNodeOutputMaterial'), None)

    def _find_socket(self, tree, name):
        if not name: return None
        bsdf = next((n for n in tree.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled'), None)
        return bsdf.inputs.get(name) if bsdf else None

def manage_scene_settings(category='scene', settings=None, getorset=False):
    config_map = {
        'bake': {'margin': {'path': bpy.context.scene.render.bake, 'attr': 'margin', 'default': 8}, 'normal_space': {'path': bpy.context.scene.render.bake, 'attr': 'normal_space', 'default': 'TANGENT'}},
        'scene': {'res_x': {'path': bpy.context.scene.render, 'attr': 'resolution_x', 'default': 1920}, 'res_y': {'path': bpy.context.scene.render, 'attr': 'resolution_y', 'default': 1080}, 'engine': {'path': bpy.context.scene.render, 'attr': 'engine', 'default': 'CYCLES'}, 'samples': {'path': bpy.context.scene.cycles, 'attr': 'samples', 'default': 128}},
        'image': {'file_format': {'path': bpy.context.scene.render.image_settings, 'attr': 'file_format', 'default': 'PNG'}, 'color_depth': {'path': bpy.context.scene.render.image_settings, 'attr': 'color_depth', 'default': '8'}, 'color_mode': {'path': bpy.context.scene.render.image_settings, 'attr': 'color_mode', 'default': 'RGBA'}, 'quality': {'path': bpy.context.scene.render.image_settings, 'attr': 'quality', 'default': 90}, 'exr_codec': {'path': bpy.context.scene.render.image_settings, 'attr': 'exr_codec', 'default': 'ZIP'}, 'tiff_codec': {'path': bpy.context.scene.render.image_settings, 'attr': 'tiff_codec', 'default': 'DEFLATE'}},
        'cm': {'view_transform': {'path': bpy.context.scene.view_settings, 'attr': 'view_transform', 'default': 'Standard'}, 'look': {'path': bpy.context.scene.view_settings, 'attr': 'look', 'default': 'None'}}
    }
    if not getorset:
        backup = {}
        if category not in config_map: return backup
        for k, v in config_map[category].items():
            try: backup[k] = getattr(v['path'], v['attr'], v['default'])
            except: continue
        return backup
    if category == 'image' and 'file_format' in settings:
        try: setattr(config_map['image']['file_format']['path'], 'file_format', settings['file_format'])
        except: pass
    for k, v in settings.items():
        if category == 'image' and k in ('color_mode', 'color_depth'):
            if k == 'color_mode': adjust_color_mode(settings)
            else: adjust_color_depth(settings)
            continue
        if category in config_map and k in config_map[category] and v is not None:
            try: setattr(config_map[category][k]['path'], config_map[category][k]['attr'], v)
            except: pass
    return settings

def adjust_color_mode(settings):
    fmt = settings.get('file_format', 'PNG'); mode = settings.get('color_mode', 'RGBA')
    cap = FORMAT_SETTINGS.get(fmt, {}); modes = cap.get('modes', {'RGB'})
    target = mode if modes and mode in modes else ('RGBA' if 'RGBA' in modes else list(modes)[0] if modes else mode)
    try: bpy.context.scene.render.image_settings.color_mode = target
    except: pass

def adjust_color_depth(settings):
    fmt = settings.get('file_format', 'PNG'); depth = settings.get('color_depth', '8')
    cap = FORMAT_SETTINGS.get(fmt, {}); depths = cap.get('depths', {'8'})
    target = depth if depths and depth in depths else ('16' if '16' in depths else list(depths)[0] if depths else depth)
    try: bpy.context.scene.render.image_settings.color_depth = target
    except: pass

def set_image(name, x, y, alpha=True, full=False, space='sRGB', ncol=False, fake_user=False, basiccolor=(0,0,0,0), clear=True):
    image = bpy.data.images.get(name)
    if image:
        if image.size[0] != x or image.size[1] != y: image.scale(x, y)
    else: image = bpy.data.images.new(name, x, y, alpha=alpha, float_buffer=full, is_data=ncol)
    if not full:
        try: image.colorspace_settings.name = space
        except: pass
    image.use_fake_user = fake_user
    if alpha: image.alpha_mode = 'STRAIGHT'
    if clear: image.generated_color = basiccolor
    return image

def save_image(image, path='//', folder=False, folder_name='folder', file_format='PNG', motion=False, frame=0, reload=False, fillnum=4, save=True):
    if not save or not image: return
    base_dir = Path(bpy.path.abspath(path))
    directory = base_dir / folder_name if folder else base_dir
    try: directory.mkdir(parents=True, exist_ok=True)
    except: return
    fmt_info = FORMAT_SETTINGS.get(file_format, {})
    ext = fmt_info.get("extensions", ["." + file_format.lower()])[0]
    name = f"{image.name}.{str(frame).zfill(fillnum)}{ext}" if motion else f"{image.name}{ext}"
    filepath = directory / name
    try: image.save_render(str(filepath.resolve()), scene=bpy.context.scene)
    except: pass
    if reload:
        try: image.source = 'FILE'; image.filepath = str(filepath); image.reload()
        except: pass

def export_baked_model(obj, export_path, export_format):
    if bpy.context.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    original_selected = bpy.context.selected_objects[:]
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active = obj
    path_obj = Path(bpy.path.abspath(export_path))
    try: path_obj.parent.mkdir(parents=True, exist_ok=True)
    except: pass
    try:
        if export_format == 'FBX': bpy.ops.export_scene.fbx(filepath=str(path_obj), use_selection=True, object_types={'MESH'})
        elif export_format == 'GLB': bpy.ops.export_scene.gltf(filepath=str(path_obj), export_format='GLB', use_selection=True)
        elif export_format == 'USD': bpy.ops.wm.usd_export(filepath=str(path_obj), selected_objects_only=True)
    except Exception as e: logger.error(f"Export fail: {e}")
    finally:
        bpy.ops.object.select_all(action='DESELECT')
        for s in original_selected:
            try: s.select_set(True)
            except: pass