import bpy

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
("BSDF","BSDF Bake","Use BSDF Baking(need a BSDF node connect to output)",2),
("MULTIRES","Multires Bake","Multires Baking",3)
]
bake_mode=[
("SINGLE_OBJECT","Single Object Bake","Bake single object ",1),
("COMBINE_OBJECT","Multi Objects Bake","Bake multi objects",2),
("SELECT_ACTIVE","Active Bake","Bake selected to active",3),
("SPLIT_MATERIAL","Split Material Bake","Bake each split material",4)
]
special_bake=[
('NO','No','Normal bake'),
('VERTEXCOLOR','Vertex Color','Bake result to vertex color'),
('AUTOATLAS','ATLAS','Make ATLAS texture')
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
color_space=[('NONCOL','non-color','Non-Color'),('SRGB','sRGB','sRGB'),('LINEAR','linear','Linear')]
color_space2=color_space+[('DEFAULT','default','Default')]

tiff_codec=[('NONE', 'None', 'No compression'),('DEFLATE', 'Deflate', 'Deflate compression'),('LZW', 'LZW', 'LZW compression'),('PACKBITS', 'Packbits', 'Packbits compression')]
exr_code = [('NONE', 'None', 'No compression'),('PXR24', 'Pxr24', 'Lossy'),('ZIP', 'ZIP', 'Lossless'),('PIZ', 'PIZ', 'Lossless'),('RLE', 'RLE', 'Lossless'),('ZIPS', 'ZIPS', 'Lossless'),('B44', 'B44', 'Lossy'),('B44A', 'B44A', 'Lossy'),('DWAA', 'DWAA', 'Lossy'),('DWAB', 'DWAB', 'Lossy')]
denoise_method=[("NONE","No","No Prefilter"),("FAST","Fast","Fast"),("ACCURATE","Accurate","Accurate")]
basic_name=[("OBJECT","Object","Object"),("MAT","Material","Material"),("OBJ_MAT","Object-Material","Obj-Mat"),("CUSTOM","Custom","Custom")]

format_map={f[0]: f[0] for f in basic_format}

# 核心：根据 @image_type.txt 完善格式设置矩阵
# [改进] 添加 extensions 字段以确保正确的文件后缀
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

CHANNEL_BAKE_INFO = {
    'color': {'bake_pass': 'EMIT', 'node_socket': 'Base Color'},
    'subface': {'bake_pass': 'EMIT', 'node_socket': 'Subsurface Weight'},
    'subface_col': {'bake_pass': 'EMIT', 'node_socket': 'Subsurface Color'},
    'subface_ani': {'bake_pass': 'EMIT', 'node_socket': 'Subsurface Anisotropy'},
    'metal': {'bake_pass': 'EMIT', 'node_socket': 'Metallic'},
    'specular': {'bake_pass': 'EMIT', 'node_socket': 'Specular IOR Level'},
    'specular_tint': {'bake_pass': 'EMIT', 'node_socket': 'Specular Tint'},
    'rough': {'bake_pass': 'EMIT', 'node_socket': 'Roughness'},
    'anisotropic': {'bake_pass': 'EMIT', 'node_socket': 'Anisotropic'},
    'anisotropic_rot': {'bake_pass': 'EMIT', 'node_socket': 'Anisotropic Rotation'},
    'sheen': {'bake_pass': 'EMIT', 'node_socket': 'Sheen Weight'},
    'sheen_tint': {'bake_pass': 'EMIT', 'node_socket': 'Sheen Tint'},
    'sheen_rough': {'bake_pass': 'EMIT', 'node_socket': 'Sheen Roughness'},
    'clearcoat': {'bake_pass': 'EMIT', 'node_socket': 'Coat Weight'},
    'clearcoat_rough': {'bake_pass': 'EMIT', 'node_socket': 'Coat Roughness'},
    'clearcoat_tint': {'bake_pass': 'EMIT', 'node_socket': 'Coat Tint'},
    'tran': {'bake_pass': 'EMIT', 'node_socket': 'Transmission Weight'},
    'tran_rou': {'bake_pass': 'EMIT', 'node_socket': 'Transmission Roughness'},
    'emi': {'bake_pass': 'EMIT', 'node_socket': 'Emission Color'},
    'emi_str': {'bake_pass': 'EMIT', 'node_socket': 'Emission Strength'},
    'alpha': {'bake_pass': 'EMIT', 'node_socket': 'Alpha'},
    'normal': {'bake_pass': 'NORMAL', 'node_socket': 'Normal'},
    'diff': {'bake_pass': 'DIFFUSE'},
    'gloss': {'bake_pass': 'GLOSSY'},
    'tranb': {'bake_pass': 'TRANSMISSION'},
    'combine': {'bake_pass': 'COMBINED'},
    'height': {'bake_pass': 'DISPLACEMENT'},
    'shadow': {'bake_pass': 'SHADOW'},
    'env': {'bake_pass': 'ENVIRONMENT'},
    'vertex': {'bake_pass': 'EMIT'},
    'bevel': {'bake_pass': 'EMIT'},
    'ao': {'bake_pass': 'EMIT'},
    'UV': {'bake_pass': 'EMIT'},
    'wireframe': {'bake_pass': 'EMIT'},
    'bevnor': {'bake_pass': 'NORMAL'},
    'position': {'bake_pass': 'EMIT'},
    'slope': {'bake_pass': 'EMIT'},
    'thickness': {'bake_pass': 'EMIT'},
    'ID_mat': {'bake_pass': 'EMIT'},
    'ID_ele': {'bake_pass': 'EMIT'},
    'ID_UVI': {'bake_pass': 'EMIT'},
    'ID_seam': {'bake_pass': 'EMIT'},
    'select': {'bake_pass': 'EMIT'},
}

CHANNEL_DEFINITIONS = {
    'BSDF_3': [
        {'id': 'color', 'name': 'Base Color', 'defaults': {'enabled': True, 'suffix': '_color', 'custom_cs': 'SRGB'}},
        {'id': 'subface', 'name': 'SSS', 'defaults': {'suffix': '_subface', 'custom_cs': 'NONCOL'}},
        {'id': 'subface_col', 'name': 'SSS Base Color', 'defaults': {'suffix': '_subfacecol', 'custom_cs': 'SRGB'}},
        {'id': 'subface_ani', 'name': 'SSS Anisotropy', 'defaults': {'suffix': '_subfaceani', 'custom_cs': 'NONCOL'}},
        {'id': 'metal', 'name': 'Metalness', 'defaults': {'suffix': '_metal', 'custom_cs': 'NONCOL'}},
        {'id': 'specular', 'name': 'Specular', 'defaults': {'suffix': '_spe', 'custom_cs': 'NONCOL'}},
        {'id': 'specular_tint', 'name': 'Specular Tint', 'defaults': {'suffix': '_spet', 'custom_cs': 'NONCOL'}},
        {'id': 'rough', 'name': 'Roughness', 'defaults': {'enabled': True, 'suffix': '_rough', 'custom_cs': 'NONCOL'}},
        {'id': 'anisotropic', 'name': 'Anisotropy', 'defaults': {'suffix': '_aniso', 'custom_cs': 'NONCOL'}},
        {'id': 'anisotropic_rot', 'name': 'Anisotropy Rotating', 'defaults': {'suffix': '_anisorot', 'custom_cs': 'NONCOL'}},
        {'id': 'sheen', 'name': 'Sheen', 'defaults': {'suffix': '_sheen', 'custom_cs': 'NONCOL'}},
        {'id': 'sheen_tint', 'name': 'Sheen Tint', 'defaults': {'suffix': '_sheentint', 'custom_cs': 'NONCOL'}},
        {'id': 'clearcoat', 'name': 'Clearcoat', 'defaults': {'suffix': '_cc', 'custom_cs': 'NONCOL'}},
        {'id': 'clearcoat_rough', 'name': 'Clearcoat Roughness', 'defaults': {'suffix': '_ccr', 'custom_cs': 'NONCOL'}},
        {'id': 'tran', 'name': 'Transmission', 'defaults': {'suffix': '_tran', 'custom_cs': 'NONCOL'}},
        {'id': 'tran_rou', 'name': 'Transmission Roughness', 'defaults': {'suffix': '_tranr', 'custom_cs': 'NONCOL'}},
        {'id': 'emi', 'name': 'Emission', 'defaults': {'suffix': '_emi', 'custom_cs': 'SRGB'}},
        {'id': 'emi_str', 'name': 'Emission Strength', 'defaults': {'suffix': '_emistr', 'custom_cs': 'NONCOL'}},
        {'id': 'alpha', 'name': 'Alpha', 'defaults': {'suffix': '_alpha', 'custom_cs': 'NONCOL'}},
        {'id': 'normal', 'name': 'Normal', 'defaults': {'enabled': True, 'suffix': '_nor', 'custom_cs': 'NONCOL'}},
    ],
    'BSDF_4': [
        {'id': 'color', 'name': 'Base Color', 'defaults': {'enabled': True, 'suffix': '_color', 'custom_cs': 'SRGB'}},
        {'id': 'subface', 'name': 'SSS', 'defaults': {'suffix': '_subface', 'custom_cs': 'NONCOL'}},
        {'id': 'subface_ani', 'name': 'SSS Anisotropy', 'defaults': {'suffix': '_subfaceani', 'custom_cs': 'NONCOL'}},
        {'id': 'metal', 'name': 'Metalness', 'defaults': {'suffix': '_metal', 'custom_cs': 'NONCOL'}},
        {'id': 'specular', 'name': 'Specular', 'defaults': {'suffix': '_spe', 'custom_cs': 'NONCOL'}},
        {'id': 'specular_tint', 'name': 'Specular Tint', 'defaults': {'suffix': '_spet', 'custom_cs': 'NONCOL'}},
        {'id': 'rough', 'name': 'Roughness', 'defaults': {'enabled': True, 'suffix': '_rough', 'custom_cs': 'NONCOL'}},
        {'id': 'anisotropic', 'name': 'Anisotropy', 'defaults': {'suffix': '_aniso', 'custom_cs': 'NONCOL'}},
        {'id': 'anisotropic_rot', 'name': 'Anisotropy Rotating', 'defaults': {'suffix': '_anisorot', 'custom_cs': 'NONCOL'}},
        {'id': 'sheen', 'name': 'Sheen', 'defaults': {'suffix': '_sheen', 'custom_cs': 'NONCOL'}},
        {'id': 'sheen_tint', 'name': 'Sheen Tint', 'defaults': {'suffix': '_sheentint', 'custom_cs': 'NONCOL'}},
        {'id': 'sheen_rough', 'name': 'Sheen Roughness', 'defaults': {'suffix': '_sheenrough', 'custom_cs': 'NONCOL'}},
        {'id': 'clearcoat', 'name': 'Clearcoat', 'defaults': {'suffix': '_cc', 'custom_cs': 'NONCOL'}},
        {'id': 'clearcoat_rough', 'name': 'Clearcoat Roughness', 'defaults': {'suffix': '_ccr', 'custom_cs': 'NONCOL'}},
        {'id': 'clearcoat_tint', 'name': 'Clearcoat Tint', 'defaults': {'suffix': '_cct', 'custom_cs': 'NONCOL'}},
        {'id': 'tran', 'name': 'Transmission', 'defaults': {'suffix': '_tran', 'custom_cs': 'NONCOL'}},
        {'id': 'emi', 'name': 'Emission', 'defaults': {'suffix': '_emi', 'custom_cs': 'SRGB'}},
        {'id': 'emi_str', 'name': 'Emission Strength', 'defaults': {'suffix': '_emistr', 'custom_cs': 'NONCOL'}},
        {'id': 'alpha', 'name': 'Alpha', 'defaults': {'suffix': '_alpha', 'custom_cs': 'NONCOL'}},
        {'id': 'normal', 'name': 'Normal', 'defaults': {'enabled': True, 'suffix': '_nor', 'custom_cs': 'NONCOL'}},
    ],
    'BASIC': [
        {'id': 'diff', 'name': 'Diffuse', 'defaults': {'enabled': True, 'suffix': '_diff', 'custom_cs': 'SRGB'}},
        {'id': 'gloss', 'name': 'Gloss', 'defaults': {'suffix': '_gloss', 'custom_cs': 'NONCOL'}},
        {'id': 'tranb', 'name': 'Transmission', 'defaults': {'suffix': '_tran', 'custom_cs': 'NONCOL'}},
        {'id': 'normal', 'name': 'Normal', 'defaults': {'enabled': True, 'suffix': '_nor', 'custom_cs': 'NONCOL'}},
        {'id': 'combine', 'name': 'Combine', 'defaults': {'suffix': '_com', 'custom_cs': 'SRGB'}},
        {'id': 'emi', 'name': 'Emission', 'defaults': {'suffix': '_emi', 'custom_cs': 'SRGB'}},
        {'id': 'rough', 'name': 'Roughness', 'defaults': {'enabled': True, 'suffix': '_rough', 'custom_cs': 'NONCOL'}},
    ],
    'MULTIRES': [
        {'id': 'height', 'name': 'Height', 'defaults': {'suffix': '_height', 'custom_cs': 'NONCOL'}},
        {'id': 'normal', 'name': 'Normal', 'defaults': {'enabled': True, 'suffix': '_nor', 'custom_cs': 'NONCOL'}},
    ],
    'MESH': [
        {'id': 'shadow', 'name': 'Shadow', 'defaults': {'suffix': '_sha', 'custom_cs': 'NONCOL'}},
        {'id': 'env', 'name': 'Environment', 'defaults': {'suffix': '_env', 'custom_cs': 'SRGB'}},
        {'id': 'vertex', 'name': 'Vertex Color', 'defaults': {'suffix': '_vertex', 'custom_cs': 'NONCOL'}},
        {'id': 'bevel', 'name': 'Bevel', 'defaults': {'suffix': '_bv', 'custom_cs': 'NONCOL'}},
        {'id': 'ao', 'name': 'Ambient Occlusion', 'defaults': {'suffix': '_ao', 'custom_cs': 'NONCOL'}},
        {'id': 'UV', 'name': 'UV', 'defaults': {'suffix': '_UV', 'custom_cs': 'NONCOL'}},
        {'id': 'wireframe', 'name': 'Wireframe', 'defaults': {'suffix': '_wf', 'custom_cs': 'NONCOL'}},
        {'id': 'bevnor', 'name': 'Bevel Normal', 'defaults': {'suffix': '_bn', 'custom_cs': 'NONCOL'}},
        {'id': 'position', 'name': 'Position', 'defaults': {'suffix': '_pos', 'custom_cs': 'NONCOL'}},
        {'id': 'slope', 'name': 'Slope', 'defaults': {'suffix': '_slope', 'custom_cs': 'NONCOL'}},
        {'id': 'thickness', 'name': 'Thickness', 'defaults': {'suffix': '_thick', 'custom_cs': 'NONCOL'}},
        {'id': 'ID_mat', 'name': 'Material ID', 'defaults': {'suffix': '_idmat', 'custom_cs': 'NONCOL'}},
        {'id': 'ID_ele', 'name': 'Element ID', 'defaults': {'suffix': '_idele', 'custom_cs': 'NONCOL'}},
        {'id': 'ID_UVI', 'name': 'UV ID', 'defaults': {'suffix': '_idUVI', 'custom_cs': 'NONCOL'}},
        {'id': 'ID_seam', 'name': 'Seam ID', 'defaults': {'suffix': '_idseam', 'custom_cs': 'NONCOL'}},
        {'id': 'select', 'name': 'Select', 'defaults': {'suffix': '_select', 'custom_cs': 'NONCOL'}},
    ]
}