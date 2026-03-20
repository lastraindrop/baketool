import sys
import os
from pathlib import Path
import bpy

def setup_environment():
    """统一的插件测试环境初始化"""
    current_dir = Path(__file__).resolve().parent
    addon_root = current_dir.parent
    parent_dir = str(addon_root.parent)
    addon_name = "baketool"

    # 1. 确保开发目录在 sys.path 最前面
    if parent_dir in sys.path:
        sys.path.remove(parent_dir)
    sys.path.insert(0, parent_dir)

    # 2. 清理已加载的旧模块缓存
    for mod in list(sys.modules.keys()):
        if mod == addon_name or mod.startswith(f"{addon_name}."):
            del sys.modules[mod]

    print(f"\n>>> Environment Setup: Blender {bpy.app.version_string}")
    print(f">>> Addon Root: {addon_root}")
    
    return addon_name, addon_root
