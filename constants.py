import bpy

# 这里的定义直接从原 __init__.py 剪切过来

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
("MULTIRES","Muti-res Bake","Muti-res Baking",3)
]
bake_mode=[
("SINGLE_OBJECT","Single Object Bake","Bake single object ",1),
("COMBINE_OBJECT","Muti Objects Bake","Bake muti objects",2),
("SELECT_ACTIVE","Active Bake","Bake selected to active",3),
("SPILT_MATERIAL","Spilt Material Bake","Bake each spilt material",4)
]
special_bake=[
('NO','No','Normal bake'),
('VERTEXCOLOR','Vertex Color','Bake result to vertex color'),
('AUTOATLAS','ATLAS','Make ATLAS texture')
]
basic_format=[
("JPG","jpg","Use jpg format",1),
("PNG","png","Use png format",2),
("BMP","bmp","Use bmp format(no quality setting)",3),
("EXR","exr","Use exr format(huge,but high quality)",4),
("HDR","hdr","Use hdr format(huge,no quality setting)",5),
("TGA","tga","Use Targa format(I don't know what is it)",6),
]
#BSDF通道 3.0
basic_channel_BSDF=[
("COLOR","Base Color","Use Base Color channel"),
("SUBFACECOL","SSS Base Color","Use SSS Base Color channel"),
("SUBFACEANI","SSS Anisotropy","Use SSS Anisotropy channel"),
("SUBFACE","SSS","Use SSS channel"),
("METAL","Metalness","Use Metalness channel"),
("SPECULAR","Specular","Use Specular channel"),
("SPECULARTINT","Specular Tint","Use Specular Tint channel"),
("ROUGH","Roughness","Use Roughness channel"),
("ANISOTROPIC","Anisotropy","Use Anisotropy channel"),
("ANISOTROPICROT","Anisotropy Rotating","Use Anisotropy Rotating channel"),
("SHEEN","Sheen","Use Sheen channel"),
("SHEENTINT","Sheen Tint","Use Sheen Tint channel"),
("CLEARCOAT","Clearcoat","Use Clearcoat channel"),
("CLEARCOATROU","Clearcoat Roughness","Use Clearcoat Roughness channel"),
("TRAN","Transmission","Use Transmission channel"),
("TRANROU","Transmission Roughness","Use Transmission Roughness channel"),
("EMI","Emission","Use Emission channel"),
("EMISTR","Emission Strength","Use Emission Strength channel"),
("ALPHA","Alpha","Use Alpha channel"),
("NORMAL","Normal","Use Normal channel")
]
#BSDF channel 4.0
basic_channel_BSDF4=[
("COLOR","Base Color","Use Base Color channel"),
("SUBFACE","SSS","Use SSS channel"),
("SUBFACEANI","SSS Anisotropy","Use SSS Anisotropy channel"),
("METAL","Metalness","Use Metalness channel"),
("SPECULAR","Specular","Use Specular channel"),
("SPECULARTINT","Specular Tint","Use Specular Tint channel"),
("ROUGH","Roughness","Use Roughness channel"),
("ANISOTROPIC","Anisotropy","Use Anisotropy channel"),
("ANISOTROPICROT","Anisotropy Rotating","Use Anisotropy Rotating channel"),
("SHEEN","Sheen","Use Sheen channel"),
("SHEENTINT","Sheen Tint","Use Sheen Tint channel"),
("SHEENROUGH","Sheen Roughness","Use Sheen Roughness channel"),
("CLEARCOAT","Clearcoat","Use Clearcoat channel"),
("CLEARCOATROUGH","Clearcoat Roughness","Use Clearcoat Roughness channel"),
("CLEARCOATTINT","Clearcoat Tint","Use Clearcoat Tint channel"),
("TRAN","Transmission","Use Transmission channel"),
("EMI","Emission","Use Emission channel"),
("EMISTR","Emission Strength","Use Emission Strength channel"),
("ALPHA","Alpha","Use Alpha channel"),
("NORMAL","Normal","Use Normal channel")
]
#BASIC channel
basic_channel_basic=[
("DIFF","Diffuse","Use Diffuse channel"),
("ROUGH","Roughness","Use Roughness channel"),
("NORMAL","Normal","Use Normal channel"),
("TRANB","Transmission","Use Transmission channel"),
("EMI","Emission","Use Emission channel"),
("GLO","Gloss","Use Gloss channel"),
("COM","Combine Result","Use Combine Result channel")
]
#Mesh channel
basic_channel_mesh=[
("SHADOW","Shadow","Use Shadow channel"),
("ENVIRONMENT","Environment","Use Environment channel"),
("BEVEL","Bevel","Use Bevel channel"),
("AO","Ambient Occlusion","Use Ambient Occlusion channel"),
("UV","UV","Use UV channel"),
("WIREFRAME","Wireframe","Use Wireframe channel"),
("BEVNOR","Bevel Normal","Use Bevel Normal channel"),
("POSITION","Position","Use Position channel"),
("SLOPE","Slope","Use Slope channel"),
("THICKNESS","Thickness","Use Thickness channel"),
("IDMAT","Material ID","Use Material ID channel"),
("SELECT","Select","Use Select channel"),
("IDELE","Element ID","Use Element ID channel"),
("IDUVI","UV ID","Use UV ID channel"),
("IDSEAM","Seam ID","Use Seam ID channel")
]

basic_channel_BSDF_3=basic_channel_BSDF+basic_channel_mesh
basic_channel_BSDF_4=basic_channel_BSDF4+basic_channel_mesh
basic_channel_basic_c=basic_channel_basic+basic_channel_mesh

denoise_method=[
("NONE","No"," No Prefilter"),
("FAST","Fast","Fast Prefilter"),
("ACCURATE","Accurate","Accurate Prefilter")
]

basic_name=[
("OBJECT","Object","Use object as basic name",1),
("MAT","Material","Use material as basic name",2),
("OBJ_MAT","Object-Material","Use object and material as basic name",3),
("CUSTOM","Custom","Use custom name as basic name",4)
]
color_depth=[
('8','8','8 Bits'),
('16','16','16 Bits'),
('32','32','32 Bits')
]
normal_type=[
('OPENGL','OPENGL','Use OPENGL Standard'),
('DIRECTX','DIRECTX','Use DIRECTX Standard'),
('CUSTOM','Custom','Use Custom Standard')
]
normal_channel=[
('POS_X','+X','+X'),
('POS_Y','+Y','+Y'),
('POS_Z','+Z','+Z'),
('NEG_X','-X','-X'),
('NEG_Y','-Y','-Y'),
('NEG_Z','-Z','-Z')
]
color_mode=[
('RGBA','RGBA','RGB and Alpha channel'),
('RGB','RGB','RGB channel'),
('BW','BW','BW channel')
]
directions=[
('X','X','X'),
('Y','Y','Y'),
('Z','Z','Z')
]
device=[
('GPU','GPU','Use GPU'),
('CPU','CPU','Use CPU')
]
altas_pack=[
('REPACK','Smart Project','Use Smart UV Project repack UV'),
('ISLAND','Pack Island','Pack UV island for current UV')
]
exr_code = [
('NONE', 'None', 'No compression'),
('PXR24', 'Pxr24', 'Lossy compression'),
('ZIP', 'ZIP', 'Almost no loss compression (lossless)'),
('PIZ', 'PIZ', 'Lossless compression'),
('RLE', 'RLE', 'Lossless compression'),
('ZIPS', 'ZIPS', 'Lossless compression'),
('B44', 'B44', 'Lossy compression'),
('B44A', 'B44A', 'Lossy compression'),
('DWAA', 'DWAA', 'Lossy compression, but reduce size'),
('DWAB', 'DWAB', 'Lossy compression, but reduce size')
]
color_space=[
('NONCOL','non-color','Same as linear but no Alpha'),
('SRGB','sRGB','Color space settings more based on human perception, more applied to channels directly perceived by humans'),
('LINEAR','linear','Color space settings based on the real physical world are more applicable to channels that cannot be directly perceived by the human eye')
]
color_space2=[
('NONCOL','non-color','Same as linear but no Alpha'),
('SRGB','sRGB','Color space settings more based on human perception, more applied to channels directly perceived by humans'),
('LINEAR','linear','Color space settings based on the real physical world are more applicable to channels that cannot be directly perceived by the human eye'),
('DEFAULT','default','Stay the same color space by default')
]
if bpy.app.version>=(4, 0, 0):
    linear='Linear Rec.709'
else:
    linear='Linear'

color_space_map={
'NONCOL':'Non-Color',
'LINEAR':linear,
'SRGB':'sRGB',
'DEFAULT':'default',
}
format_map={
"JPG":"JPEG",
"PNG":"PNG",
"BMP":"BMP",
"EXR":"OPEN_EXR",
"HDR":"HDR",
"TGA":"TARGA"
}

uv_setting=[
('DEFAULT','default','Use default UV'),
('GIVEN','given','Use given UV'),
('NEW','new','Make new UV')
]

