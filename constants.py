# 修复拼写错误，完善扩展名映射
job_type=[
('S','Simple','Simple Jobs Setting',1),
('A','Accurate','Accurate Jobs Setting',2),
]
custom_bake_channel_sep=[
('R','Red','Use Red channel',1),
('G','Green','Use Green channel',2),
('B','Blue','Use Blue channel',3),
('A','Alpha','Use Alpha channel',4)
]
bake_type=[
("BASIC","Basic Bake","Blender Default Baking",1),
("BSDF","BSDF Bake","Use BSDF Baking(need a BSDF node connect to output)",2)
]
bake_mode=[
("SINGLE_OBJECT","Single Object Bake","Bake single object ",1),
("COMBINE_OBJECT","Multi Objects Bake","Bake multi objects",2),
("SELECT_ACTIVE","Active Bake","Bake selected to active",3),
("SPLIT_MATERIAL","Split Material Bake","Bake each split material",4)
]
basic_format=[
    ("BMP", "BMP", "Output image in bitmap format", 1),
    ("IRIS", "Iris", "Output image in SGI IRIS format", 2),
    ("PNG", "PNG", "Output image in PNG format", 3),
    ("JPEG", "JPEG", "Output image in JPEG format", 4),
    ("JPEG2000", "JPEG 2000", "Output image in JPEG 2000 format", 5),
    ("TARGA", "Targa", "Output image in Targa format", 6),
    ("TARGA_RAW", "Targa Raw", "Output image in uncompressed Targa format", 7),
    ("CINEON", "Cineon", "Output image in Cineon format", 8),
    ("DPX", "DPX", "Output image in DPX format", 9),
    ("OPEN_EXR_MULTILAYER", "OpenEXR MultiLayer", "Output image in multilayer OpenEXR format", 10),
    ("OPEN_EXR", "OpenEXR", "Output image in OpenEXR format", 11),
    ("HDR", "Radiance HDR", "Output image in Radiance HDR format", 12),
    ("TIFF", "TIFF", "Output image in TIFF format", 13),
    ("WEBP", "WebP", "Output image in WebP format", 14),
]

# 通用颜色空间和设备定义
device=[('GPU','GPU','Use GPU'),('CPU','CPU','Use CPU')]
atlas_pack=[('REPACK','Smart Project','Use Smart UV Project repack UV'),('ISLAND','Pack Island','Pack UV island for current UV')]
directions=[('X','X','X'),('Y','Y','Y'),('Z','Z','Z')]
normal_type=[('OPENGL','OPENGL','Use OPENGL Standard'),('DIRECTX','DIRECTX','Use DIRECTX Standard'),('CUSTOM','Custom','Use Custom Standard')]
normal_channel=[('POS_X','+X','+X'),('POS_Y','+Y','+Y'),('POS_Z','+Z','+Z'),('NEG_X','-X','-X'),('NEG_Y','-Y','-Y'),('NEG_Z','-Z','-Z')]

color_depth=[('8','8','8 Bits'),('10','10','10 Bits'),('12','12','12 Bits'),('16','16','16 Bits'),('32','32','32 Bits')]
color_mode=[('RGBA','RGBA','RGB and Alpha channel'),('RGB','RGB','RGB channel'),('BW','BW','BW channel')]
color_space=[('NONCOL','Non-Color','Non-Color'),('SRGB','sRGB','sRGB'),('LINEAR','Linear','Linear')]
color_space2=color_space+[('DEFAULT','Default','Default')]

tiff_codec=[('NONE', 'None', 'No compression'),('DEFLATE', 'Deflate', 'Deflate compression'),('LZW', 'LZW', 'LZW compression'),('PACKBITS', 'Packbits', 'Packbits compression')]
exr_code = [('NONE', 'None', 'No compression'),('PXR24', 'Pxr24', 'Lossy'),('ZIP', 'ZIP', 'Lossless'),('PIZ', 'PIZ', 'Lossless'),('RLE', 'RLE', 'Lossless'),('ZIPS', 'ZIPS', 'Lossless'),('B44', 'B44', 'Lossy'),('B44A', 'B44A', 'Lossy'),('DWAA', 'DWAA', 'Lossy'),('DWAB', 'DWAB', 'Lossy')]
denoise_method=[("NONE","No","No Prefilter"),("FAST","Fast","Fast"),("ACCURATE","Accurate","Accurate")]
basic_name=[("OBJECT","Object","Object"),("MAT","Material","Material"),("OBJ_MAT","Object-Material","Obj-Mat"),("CUSTOM","Custom","Custom")]

format_map={f[0]: f[0] for f in basic_format}

FORMAT_SETTINGS = {
    "BMP": {
        "modes": {'BW', 'RGB'},
        "depths": {'8'},
        "quality": False,
        "extensions": ['.bmp']
    },
    "IRIS": {
        "modes": {'BW', 'RGB', 'RGBA'},
        "depths": {'8'},
        "quality": False,
        "extensions": ['.rgb']
    },
    "PNG": {
        "modes": {'BW', 'RGB', 'RGBA'},
        "depths": {'8', '16'},
        "compression": True,
        "extensions": ['.png']
    },
    "JPEG": {
        "modes": {'BW', 'RGB'},
        "depths": {'8'},
        "quality": True,
        "extensions": ['.jpg', '.jpeg']
    },
    "JPEG2000": {
        "modes": {'BW', 'RGB', 'RGBA'},
        "depths": {'8', '12', '16'},
        "quality": True,
        "extensions": ['.jp2']
    },
    "TARGA": {
        "modes": {'BW', 'RGB', 'RGBA'},
        "depths": {'8'},
        "quality": False,
        "extensions": ['.tga']
    },
    "TARGA_RAW": {
        "modes": {'BW', 'RGB', 'RGBA'},
        "depths": {'8'},
        "quality": False,
        "extensions": ['.tga']
    },
    "CINEON": {
        "modes": {'BW', 'RGB'},
        "depths": {'10'},
        "quality": False,
        "extensions": ['.cin']
    },
    "DPX": {
        "modes": {'BW', 'RGB', 'RGBA'},
        "depths": {'8', '10', '12', '16'},
        "quality": False,
        "extensions": ['.dpx']
    },
    "OPEN_EXR_MULTILAYER": {
        "modes": {'RGBA'},
        "depths": {'16', '32'},
        "codec": True,
        "extensions": ['.exr']
    },
    "OPEN_EXR": {
        "modes": {'BW', 'RGB', 'RGBA'},
        "depths": {'16', '32'},
        "codec": True,
        "extensions": ['.exr']
    },
    "HDR": {
        "modes": {'BW', 'RGB'},
        "depths": {'32'},
        "quality": False,
        "extensions": ['.hdr']
    },
    "TIFF": {
        "modes": {'BW', 'RGB', 'RGBA'},
        "depths": {'8', '16'},
        "tiff_codec": True,
        "extensions": ['.tif', '.tiff']
    },
    "WEBP": {
        "modes": {'BW', 'RGB', 'RGBA'},
        "depths": {'8'},
        "quality": True,
        "extensions": ['.webp']
    },
}

# --- 核心：通道分类与默认值定义 ---
CAT_DATA = 'DATA'   # PBR 固有属性
CAT_LIGHT = 'LIGHT' # 光照/渲染结果
CAT_MESH = 'MESH'   # 几何/拓扑数据
CAT_EXTENSION = 'EXTENSION' # 拓展/转换贴图

CHANNEL_BAKE_INFO = {
    # --- PBR Data ---
    'color': {'bake_pass': 'EMIT', 'node_socket': 'Base Color', 'cat': CAT_DATA, 'def_cs': 'sRGB', 'def_mode': 'RGB'},
    'metal': {'bake_pass': 'EMIT', 'node_socket': 'Metallic', 'cat': CAT_DATA, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'rough': {'bake_pass': 'EMIT', 'node_socket': 'Roughness', 'cat': CAT_DATA, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'specular': {'bake_pass': 'EMIT', 'node_socket': 'Specular IOR Level', 'cat': CAT_DATA, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'specular_tint': {'bake_pass': 'EMIT', 'node_socket': 'Specular Tint', 'cat': CAT_DATA, 'def_cs': 'Non-Color', 'def_mode': 'RGB'},
    'anisotropic': {'bake_pass': 'EMIT', 'node_socket': 'Anisotropic', 'cat': CAT_DATA, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'anisotropic_rot': {'bake_pass': 'EMIT', 'node_socket': 'Anisotropic Rotation', 'cat': CAT_DATA, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'sheen': {'bake_pass': 'EMIT', 'node_socket': 'Sheen Weight', 'cat': CAT_DATA, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'sheen_tint': {'bake_pass': 'EMIT', 'node_socket': 'Sheen Tint', 'cat': CAT_DATA, 'def_cs': 'Non-Color', 'def_mode': 'RGB'},
    'sheen_rough': {'bake_pass': 'EMIT', 'node_socket': 'Sheen Roughness', 'cat': CAT_DATA, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'clearcoat': {'bake_pass': 'EMIT', 'node_socket': 'Coat Weight', 'cat': CAT_DATA, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'clearcoat_rough': {'bake_pass': 'EMIT', 'node_socket': 'Coat Roughness', 'cat': CAT_DATA, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'clearcoat_tint': {'bake_pass': 'EMIT', 'node_socket': 'Coat Tint', 'cat': CAT_DATA, 'def_cs': 'Non-Color', 'def_mode': 'RGB'},
    'tran': {'bake_pass': 'EMIT', 'node_socket': 'Transmission Weight', 'cat': CAT_DATA, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'tran_rou': {'bake_pass': 'EMIT', 'node_socket': 'Transmission Roughness', 'cat': CAT_DATA, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'emi': {'bake_pass': 'EMIT', 'node_socket': 'Emission Color', 'cat': CAT_DATA, 'def_cs': 'sRGB', 'def_mode': 'RGB'},
    'emi_str': {'bake_pass': 'EMIT', 'node_socket': 'Emission Strength', 'cat': CAT_DATA, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'alpha': {'bake_pass': 'EMIT', 'node_socket': 'Alpha', 'cat': CAT_DATA, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'normal': {'bake_pass': 'NORMAL', 'node_socket': 'Normal', 'cat': CAT_DATA, 'def_cs': 'Non-Color', 'def_mode': 'RGB'},
    
    'subface': {'bake_pass': 'EMIT', 'node_socket': 'Subsurface Weight', 'cat': CAT_DATA, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'subface_col': {'bake_pass': 'EMIT', 'node_socket': 'Subsurface Color', 'cat': CAT_DATA, 'def_cs': 'sRGB', 'def_mode': 'RGB'},
    'subface_ani': {'bake_pass': 'EMIT', 'node_socket': 'Subsurface Anisotropy', 'cat': CAT_DATA, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    
    # --- Light / Render Result ---
    'diff': {'bake_pass': 'DIFFUSE', 'cat': CAT_LIGHT, 'def_cs': 'sRGB', 'def_mode': 'RGB'},
    'gloss': {'bake_pass': 'GLOSSY', 'cat': CAT_LIGHT, 'def_cs': 'sRGB', 'def_mode': 'RGB'},
    'tranb': {'bake_pass': 'TRANSMISSION', 'cat': CAT_LIGHT, 'def_cs': 'sRGB', 'def_mode': 'RGB'},
    'combine': {'bake_pass': 'COMBINED', 'cat': CAT_LIGHT, 'def_cs': 'sRGB', 'def_mode': 'RGB'},
    'shadow': {'bake_pass': 'SHADOW', 'cat': CAT_LIGHT, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'env': {'bake_pass': 'ENVIRONMENT', 'cat': CAT_LIGHT, 'def_cs': 'sRGB', 'def_mode': 'RGB'},
    'ao': {'bake_pass': 'EMIT', 'cat': CAT_LIGHT, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    
    # --- Mesh / Topology ---
    'height': {'bake_pass': 'DISPLACEMENT', 'cat': CAT_MESH, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'vertex': {'bake_pass': 'EMIT', 'cat': CAT_MESH, 'def_cs': 'sRGB', 'def_mode': 'RGB'},
    'bevel': {'bake_pass': 'EMIT', 'cat': CAT_MESH, 'def_cs': 'Non-Color', 'def_mode': 'BW'}, # Normal map actually
    'bevnor': {'bake_pass': 'NORMAL', 'cat': CAT_MESH, 'def_cs': 'Non-Color', 'def_mode': 'RGB'},
    'UV': {'bake_pass': 'EMIT', 'cat': CAT_MESH, 'def_cs': 'Non-Color', 'def_mode': 'RGB'},
    'wireframe': {'bake_pass': 'EMIT', 'cat': CAT_MESH, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'position': {'bake_pass': 'EMIT', 'cat': CAT_MESH, 'def_cs': 'Non-Color', 'def_mode': 'RGB'},
    'slope': {'bake_pass': 'EMIT', 'cat': CAT_MESH, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'thickness': {'bake_pass': 'EMIT', 'cat': CAT_MESH, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'ID_mat': {'bake_pass': 'EMIT', 'cat': CAT_MESH, 'def_cs': 'Non-Color', 'def_mode': 'RGB'},
    'ID_ele': {'bake_pass': 'EMIT', 'cat': CAT_MESH, 'def_cs': 'Non-Color', 'def_mode': 'RGB'},
    'ID_UVI': {'bake_pass': 'EMIT', 'cat': CAT_MESH, 'def_cs': 'Non-Color', 'def_mode': 'RGB'},
    'ID_seam': {'bake_pass': 'EMIT', 'cat': CAT_MESH, 'def_cs': 'Non-Color', 'def_mode': 'RGB'},
    'select': {'bake_pass': 'EMIT', 'cat': CAT_MESH, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    'curvature': {'bake_pass': 'EMIT', 'cat': CAT_MESH, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
    
    # --- Extension / Conversion ---
    'pbr_conv_base': {'bake_pass': 'EMIT', 'cat': CAT_EXTENSION, 'def_cs': 'sRGB', 'def_mode': 'RGB'},
    'pbr_conv_metal': {'bake_pass': 'EMIT', 'cat': CAT_EXTENSION, 'def_cs': 'Non-Color', 'def_mode': 'BW'},
}

# 核心：导出属性白名单
CHANNEL_EXPORT_WHITELIST = {
    'rough': {'rough_inv'},
    'normal': {'normal_type', 'normal_X', 'normal_Y', 'normal_Z', 'normal_obj'},
    'diff': {'diff_dir', 'diff_ind', 'diff_col'},
    'gloss': {'gloss_dir', 'gloss_ind', 'gloss_col'},
    'tranb': {'tranb_dir', 'tranb_ind', 'tranb_col'},
    'combine': {'com_dir', 'com_ind', 'com_diff', 'com_gloss', 'com_tran', 'com_emi'},
    'ao': {'ao_inside', 'ao_local', 'ao_dis', 'ao_sample'},
    'bevel': {'bevel_sample', 'bevel_rad'},
    'bevnor': {'bevnor_sample', 'bevnor_rad'},
    'curvature': {'curvature_rad', 'curvature_sample', 'curvature_contrast'},
    'wireframe': {'wireframe_use_pix', 'wireframe_dis'},
    'position': {'position_invg'},
    'slope': {'slope_directions', 'slope_invert'},
    'thickness': {'thickness_distance', 'thickness_contrast'},
    'ID_mat': {'ID_num'},
    'ID_ele': {'ID_num'},
    'ID_UVI': {'ID_num'},
    'ID_seam': {'ID_num'},
}

BSDF_COMPATIBILITY_MAP = {
    # --- 基础通道 ---
    'color':    ['Base Color', 'Diffuse'],
    'alpha':    ['Alpha'],
    'normal':   ['Normal'],
    'emi':      ['Emission Color', 'Emission'],
    'emi_str':  ['Emission Strength'],

    # --- 高光/金属流 ---
    'metal':    ['Metallic'],
    'specular': ['Specular IOR Level', 'Specular'], 
    'specular_tint': ['Specular Tint'], 
    'rough':    ['Roughness'],
    
    # --- 次表面流 ---
    'subface':  ['Subsurface Weight', 'Subsurface'],
    'subface_col': ['Subsurface Radius', 'Subsurface Color'], 
    'subface_ani': ['Subsurface Anisotropy'],

    # --- 透射流 ---
    'tran':     ['Transmission Weight', 'Transmission'],
    'tran_rou': ['Transmission Roughness'], 

    # --- 光泽/清漆流 ---
    'clearcoat':       ['Coat Weight', 'Coat', 'Clearcoat'],
    'clearcoat_rough': ['Coat Roughness', 'Clearcoat Roughness'],
    'clearcoat_tint':  ['Coat Tint', 'Clearcoat Tint'],
    
    'sheen':       ['Sheen Weight', 'Sheen'],
    'sheen_rough': ['Sheen Roughness'],
    'sheen_tint':  ['Sheen Tint'],
    
    'anisotropic': ['Anisotropic'],
    'anisotropic_rot': ['Anisotropic Rotation'],
}

SOCKET_DEFAULT_TYPE = {
    'color': (0.8, 0.8, 0.8, 1.0),
    'normal': (0.5, 0.5, 1.0, 1.0),
    'rough': 0.5,
    'metal': 0.0,
    'alpha': 1.0,
    'emi': (0.0, 0.0, 0.0, 1.0),
    'emi_str': 0.0,
}

CHANNEL_DEFINITIONS = {
    'BSDF_3': [
        {'id': 'color', 'name': 'Base Color', 'defaults': {'enabled': True, 'suffix': '_color'}},
        {'id': 'subface', 'name': 'SSS', 'defaults': {'suffix': '_subface'}},
        {'id': 'subface_col', 'name': 'SSS Base Color', 'defaults': {'suffix': '_subfacecol'}},
        {'id': 'subface_ani', 'name': 'SSS Anisotropy', 'defaults': {'suffix': '_subfaceani'}},
        {'id': 'metal', 'name': 'Metalness', 'defaults': {'suffix': '_metal'}},
        {'id': 'specular', 'name': 'Specular', 'defaults': {'suffix': '_spe'}},
        {'id': 'specular_tint', 'name': 'Specular Tint', 'defaults': {'suffix': '_spet'}},
        {'id': 'rough', 'name': 'Roughness', 'defaults': {'enabled': True, 'suffix': '_rough'}},
        {'id': 'anisotropic', 'name': 'Anisotropy', 'defaults': {'suffix': '_aniso'}},
        {'id': 'anisotropic_rot', 'name': 'Anisotropy Rotating', 'defaults': {'suffix': '_anisorot'}},
        {'id': 'sheen', 'name': 'Sheen', 'defaults': {'suffix': '_sheen'}},
        {'id': 'sheen_tint', 'name': 'Sheen Tint', 'defaults': {'suffix': '_sheentint'}},
        {'id': 'clearcoat', 'name': 'Clearcoat', 'defaults': {'suffix': '_cc'}},
        {'id': 'clearcoat_rough', 'name': 'Clearcoat Roughness', 'defaults': {'suffix': '_ccr'}},
        {'id': 'tran', 'name': 'Transmission', 'defaults': {'suffix': '_tran'}},
        {'id': 'tran_rou', 'name': 'Transmission Roughness', 'defaults': {'suffix': '_tranr'}},
        {'id': 'emi', 'name': 'Emission', 'defaults': {'suffix': '_emi'}},
        {'id': 'emi_str', 'name': 'Emission Strength', 'defaults': {'suffix': '_emistr'}},
        {'id': 'alpha', 'name': 'Alpha', 'defaults': {'suffix': '_alpha'}},
        {'id': 'normal', 'name': 'Normal', 'defaults': {'enabled': True, 'suffix': '_nor'}},
    ],
    'BSDF_4': [
        {'id': 'color', 'name': 'Base Color', 'defaults': {'enabled': True, 'suffix': '_color'}},
        {'id': 'subface', 'name': 'SSS', 'defaults': {'suffix': '_subface'}},
        {'id': 'subface_ani', 'name': 'SSS Anisotropy', 'defaults': {'suffix': '_subfaceani'}},
        {'id': 'metal', 'name': 'Metalness', 'defaults': {'suffix': '_metal'}},
        {'id': 'specular', 'name': 'Specular', 'defaults': {'suffix': '_spe'}},
        {'id': 'specular_tint', 'name': 'Specular Tint', 'defaults': {'suffix': '_spet'}},
        {'id': 'rough', 'name': 'Roughness', 'defaults': {'enabled': True, 'suffix': '_rough'}},
        {'id': 'anisotropic', 'name': 'Anisotropy', 'defaults': {'suffix': '_aniso'}},
        {'id': 'anisotropic_rot', 'name': 'Anisotropy Rotating', 'defaults': {'suffix': '_anisorot'}},
        {'id': 'sheen', 'name': 'Sheen', 'defaults': {'suffix': '_sheen'}},
        {'id': 'sheen_tint', 'name': 'Sheen Tint', 'defaults': {'suffix': '_sheentint'}},
        {'id': 'sheen_rough', 'name': 'Sheen Roughness', 'defaults': {'suffix': '_sheenrough'}},
        {'id': 'clearcoat', 'name': 'Clearcoat', 'defaults': {'suffix': '_cc'}},
        {'id': 'clearcoat_rough', 'name': 'Clearcoat Roughness', 'defaults': {'suffix': '_ccr'}},
        {'id': 'clearcoat_tint', 'name': 'Clearcoat Tint', 'defaults': {'suffix': '_cct'}},
        {'id': 'tran', 'name': 'Transmission', 'defaults': {'suffix': '_tran'}},
        {'id': 'emi', 'name': 'Emission', 'defaults': {'suffix': '_emi'}},
        {'id': 'emi_str', 'name': 'Emission Strength', 'defaults': {'suffix': '_emistr'}},
        {'id': 'alpha', 'name': 'Alpha', 'defaults': {'suffix': '_alpha'}},
        {'id': 'normal', 'name': 'Normal', 'defaults': {'enabled': True, 'suffix': '_nor'}},
    ],
    'BASIC': [
        {'id': 'diff', 'name': 'Diffuse', 'defaults': {'enabled': True, 'suffix': '_diff'}},
        {'id': 'gloss', 'name': 'Gloss', 'defaults': {'suffix': '_gloss'}},
        {'id': 'tranb', 'name': 'Transmission', 'defaults': {'suffix': '_tran'}},
        {'id': 'normal', 'name': 'Normal', 'defaults': {'enabled': True, 'suffix': '_nor'}},
        {'id': 'combine', 'name': 'Combine', 'defaults': {'suffix': '_com'}},
        {'id': 'emi', 'name': 'Emission', 'defaults': {'suffix': '_emi'}},
        {'id': 'rough', 'name': 'Roughness', 'defaults': {'enabled': True, 'suffix': '_rough'}},
    ],
    'LIGHT': [
        {'id': 'ao', 'name': 'Ambient Occlusion', 'defaults': {'suffix': '_ao'}},
        {'id': 'shadow', 'name': 'Shadow', 'defaults': {'suffix': '_sha'}},
        {'id': 'env', 'name': 'Environment', 'defaults': {'suffix': '_env'}},
    ],
    'MESH': [
        {'id': 'vertex', 'name': 'Vertex Color', 'defaults': {'suffix': '_vertex'}},
        {'id': 'bevel', 'name': 'Bevel', 'defaults': {'suffix': '_bv'}},
        {'id': 'curvature', 'name': 'Curvature', 'defaults': {'suffix': '_curv'}},
        {'id': 'UV', 'name': 'UV', 'defaults': {'suffix': '_UV'}},
        {'id': 'wireframe', 'name': 'Wireframe', 'defaults': {'suffix': '_wf'}},
        {'id': 'bevnor', 'name': 'Bevel Normal', 'defaults': {'suffix': '_bn'}},
        {'id': 'position', 'name': 'Position', 'defaults': {'suffix': '_pos'}},
        {'id': 'slope', 'name': 'Slope', 'defaults': {'suffix': '_slope'}},
        {'id': 'thickness', 'name': 'Thickness', 'defaults': {'suffix': '_thick'}},
        {'id': 'ID_mat', 'name': 'Material ID', 'defaults': {'suffix': '_idmat'}},
        {'id': 'ID_ele', 'name': 'Element ID', 'defaults': {'suffix': '_idele'}},
        {'id': 'ID_UVI', 'name': 'UV ID', 'defaults': {'suffix': '_idUVI'}},
        {'id': 'ID_seam', 'name': 'Seam ID', 'defaults': {'suffix': '_idseam'}},
        {'id': 'select', 'name': 'Select', 'defaults': {'suffix': '_select'}},
    ],
    'EXTENSION': [
        {'id': 'pbr_conv_base', 'name': 'Conv: Base Color', 'defaults': {'suffix': '_base_conv'}},
        {'id': 'pbr_conv_metal', 'name': 'Conv: Metallic', 'defaults': {'suffix': '_metal_conv'}},
    ]
}