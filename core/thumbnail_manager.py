import bpy
import bpy.utils.previews
import os
from pathlib import Path

# 全局预览集合字典 // Global preview collections
preview_collections = {}

def get_preview_collection(name="main"):
    """获取或创建一个预览集合"""
    global preview_collections
    if name not in preview_collections:
        pcoll = bpy.utils.previews.new()
        preview_collections[name] = pcoll
    return preview_collections[name]

def clear_preview_collection(name="main"):
    """清理特定的预览集合"""
    global preview_collections
    if name in preview_collections:
        bpy.utils.previews.remove(preview_collections[name])
        del preview_collections[name]

def load_preset_thumbnails(directory):
    """
    扫描目录下的 .png 文件并将其作为预览图标加载。
    文件名应与 .json 预设文件名匹配。
    """
    pcoll = get_preview_collection("presets")
    dir_path = Path(directory)
    if not dir_path.exists():
        return

    # 支持的文件扩展名
    valid_exts = {'.png', '.jpg', '.jpeg'}
    
    for f in dir_path.iterdir():
        if f.suffix.lower() in valid_exts:
            # 使用文件名作为标识符
            name = f.stem
            if name not in pcoll:
                pcoll.load(name, str(f.resolve()), 'IMAGE')

def get_icon_id(name, collection="presets"):
    """获取加载图标的整数 ID"""
    pcoll = get_preview_collection(collection)
    if name in pcoll:
        return pcoll[name].icon_id
    return 0
