import bpy
import json
import logging
from mathutils import Vector, Color, Matrix, Quaternion

logger = logging.getLogger(__name__)

class PropertyIO:
    """
    通用 Blender 属性序列化与反序列化工具。
    支持递归处理 PropertyGroup, CollectionProperty, PointerProperty。
    自动过滤 Blender ID (Object, Material, Image) 以实现安全的预设保存。
    """

    # 默认忽略的系统属性
    DEFAULT_EXCLUDE = {
        'rna_type', 'name', 'is_valid', 
        'path_from_id', 'bl_rna'
    }

    def __init__(self, exclude_props=None, custom_filter=None):
        """
        :param exclude_props: 用户自定义不希望导出的属性名集合 (set of strings)
        :param custom_filter: 自定义过滤函数 (callable), 签名 func(prop_group, key) -> bool. 返回 False 则跳过该属性.
        """
        self.exclude_props = self.DEFAULT_EXCLUDE.copy()
        if exclude_props:
            self.exclude_props.update(exclude_props)
        self.custom_filter = custom_filter
        
        # 统计数据（用于分析）
        self.stats = {
            'loaded': 0,
            'skipped_match': 0, # JSON 有但对象没有（废弃属性）
            'skipped_readonly': 0,
            'error': 0
        }

    def to_dict(self, prop_group):
        """
        将 PropertyGroup 递归转换为字典
        """
        if prop_group is None:
            return None

        data = {}
        
        # 遍历 RNA 属性定义
        for prop in prop_group.bl_rna.properties:
            key = prop.identifier
            
            # 1. 过滤黑名单
            if key in self.exclude_props:
                continue
            
            # 1.1 自定义过滤 (Context aware filtering)
            if self.custom_filter and not self.custom_filter(prop_group, key):
                continue
            
            # 获取实际值
            try:
                value = getattr(prop_group, key)
            except Exception:
                continue

            # 2. 区分处理不同类型
            
            # A. 集合属性 (CollectionProperty) -> 递归列表
            if isinstance(prop, bpy.types.CollectionProperty):
                if value and len(value) > 0:
                    data[key] = [self.to_dict(item) for item in value]
            
            # B. 指针属性 (PointerProperty) -> 递归字典 或 跳过 ID
            elif isinstance(prop, bpy.types.PointerProperty):
                if value is None:
                    continue
                
                # 关键：检查是否是 Blender 数据块 (Object, Material, Image 等)
                # 我们只保存 PropertyGroup (配置数据)，不保存引用数据
                if isinstance(value, bpy.types.ID):
                    continue
                
                # 如果是自定义配置组，递归
                if isinstance(value, bpy.types.PropertyGroup):
                    data[key] = self.to_dict(value)
            
            # C. 基础数据类型 (转换 Vector/Color 为 list 以便 JSON化)
            else:
                if hasattr(value, "to_list"): # mathutils types (Vector, Color, Quaternion)
                    data[key] = value.to_list()
                elif hasattr(value, "to_tuple"):
                    data[key] = value.to_tuple()
                # [Fix] Handle bpy_prop_array which is iterable but not JSON serializable
                elif hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
                    try:
                        data[key] = list(value)
                    except Exception:
                        # Fallback for non-convertible iterables (should be rare in RNA)
                        data[key] = str(value)
                else:
                    data[key] = value

        return data

    def from_dict(self, prop_group, data, clear_collection=True):
        """
        将字典数据递归写入 PropertyGroup
        :param clear_collection: 是否在加载列表前先清空现有列表 (通常为 True)
        """
        if not data or not prop_group:
            return

        # 获取对象所有有效属性名，用于检测“废弃属性”
        valid_keys = set(p.identifier for p in prop_group.bl_rna.properties)

        for key, val in data.items():
            # 1. 分析：废弃属性检测
            if key not in valid_keys:
                self.stats['skipped_match'] += 1
                # logger.debug(f"Property mismatch: '{key}' not found in {type(prop_group).__name__}, skipping.")
                continue

            if key in self.exclude_props:
                continue

            prop_def = prop_group.bl_rna.properties[key]
            
            try:
                # [Fix] 优先处理容器类型 (Collection/Pointer)，即使它们被标记为只读
                # 因为我们不是替换对象，而是递归修改其内容，所以必须忽略 is_readonly 检查
                
                # A. 集合属性处理
                if isinstance(prop_def, bpy.types.CollectionProperty):
                    target_collection = getattr(prop_group, key)
                    
                    if clear_collection:
                        target_collection.clear()
                    
                    # 只有当数据是列表时才处理
                    if isinstance(val, list):
                        for item_data in val:
                            new_item = target_collection.add()
                            # 递归加载子项
                            self.from_dict(new_item, item_data, clear_collection)

                # B. 指针属性处理
                elif isinstance(prop_def, bpy.types.PointerProperty):
                    target_pointer = getattr(prop_group, key)
                    # 同样，只处理 PropertyGroup，忽略 ID
                    if isinstance(target_pointer, bpy.types.PropertyGroup) and isinstance(val, dict):
                        self.from_dict(target_pointer, val, clear_collection)

                # C. 基础属性处理
                else:
                    # 只有基础属性才真正需要检查只读状态
                    if prop_def.is_readonly:
                        self.stats['skipped_readonly'] += 1
                        continue
                        
                    # 类型安全转换
                    setattr(prop_group, key, val)
                    self.stats['loaded'] += 1

            except Exception as e:
                self.stats['error'] += 1
                logger.warning(f"Failed to load property '{key}' in {type(prop_group).__name__}: {e}")

    def report_stats(self):
        """返回加载统计信息字符串"""
        return (f"Loaded: {self.stats['loaded']}, "
                f"Obsolete keys: {self.stats['skipped_match']}, "
                f"Read-only skipped: {self.stats['skipped_readonly']}, "
                f"Errors: {self.stats['error']}")
