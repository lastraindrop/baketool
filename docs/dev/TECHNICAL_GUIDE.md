# BakeNexus 技术指南 / Technical Guide

本指南详细介绍了 BakeNexus 的核心架构、工作原理以及为保证工业级稳定性所采用的工程实践。

## 1. 架构概述 (Architectural Overview)

BakeNexus 采用模块化的分层架构，旨在解耦 UI、数据管理与执行引擎：

- **UI 层 (`ui.py`, `translations.json`)**: 负责交互显示，通过 `constants.py` 中的配置动态生成界面。
- **数据层 (`property.py`, `constants.py`)**: 定义 RNA 属性、默认值和通道元数据。
- **核心引擎 (`core/`)**:
  - `engine.py`: 执行调度的中枢，包含 `BakeStepRunner` 和 `BakePassExecutor`。
  - `node_manager.py`: 负责非破坏式的材质节点操作。
  - `compat.py`: 跨版本 API 适配层。
  - `math_utils.py`: 拓扑分析与高性能 NumPy 像素处理。

---

## 2. 核心工作流 (Core Workflow)

### 2.1 原子化上下文管理 (`BakeContextManager`)
为防止烘焙过程中断导致用户场景设置（如渲染引擎切换为 Cycles 后未切回）被破坏，我们实现了 `BakeContextManager`：
- **原理**：使用 `contextlib.ExitStack` 嵌套多个 `SceneSettingsContext`。
- **原子性**：采用 `pop_all()` 模式。只有当所有上下文成功进入后，才会提交清理堆栈；否则，任何一步失败都会触发已进入上下文的自动回滚。

### 2.2 非破坏式着色管道 (`NodeGraphHandler`)
- **隔离性**：所有插件创建的辅助节点（如预览纹理、扩展逻辑节点）均打上 `is_bt_temp = True` 标记。
- **防污染搜索**：`_find_socket_source` 在寻找用户材质源时会主动过滤带标记的节点，确保烘焙结果真实反映用户材质，而非插件的中间状态。
- **链接还原**：通过记录并回填 `links` 列表，在 `__exit__` 时精确恢复用户材质的原始连接状态。

---

## 3. 跨版本兼容性设计 (Cross-Version Compatibility)

BakeNexus 支持从 Blender 3.3 LTS 到 5.0+ 的所有主流版本：

### 3.1 Blender 5.0 适配
- **合成器 (Compositor)**：B5.0 移除了 `CompositorNodeComposite`。系统自动识别 B5.0 并切换至 `NodeGroupOutput`，同时适配了 `compositing_node_group` 新属性。
- **GPU 资源管理**：B5.0 移除了 `image.gl_free()`。系统在 `BakeModalOperator` 的 GC 管道中自动检测并安全跳过，同时保留 `buffers_free()` 以释放内存。

### 3.2 动态枚举 (Dynamic Enums)
Blender 4.2+ 对 `EnumProperty` 的回调函数要求更严格。我们通过返回完整的 5 元组（含 ID 整数）来确保 UI 列表在所有版本中的渲染与索引稳定性。

---

## 4. 拓扑分析与数学工具 (`math_utils.py`)

### 4.1 岛屿检测 (Island Detection)
`_find_islands_bmesh` 函数支持两种高级分割模式：
- **SEAM 模式**：通过 `edge.seam` 标记在拓扑层面切断连通性，生成精确的 Seam ID Map。
- **UVI 模式**：通过分析 BMesh Loop 的 UV 坐标差异（阈值 `1e-4`），自动识别 UV 岛边界，确保 ID Map 与纹理空间对齐。

### 4.2 自动笼体分析 (Auto-Cage)
利用 `mathutils.bvhtree.BVHTree` 实现快速射线投射，计算低模顶点到高模表面的平均法线距离，从而动态生成 `Cage Extrusion` 参数，减少手动调参的失败率。

---

## 5. 参数对齐与一致性 (Parameter Alignment)

为解决"重构导致 UI 与引擎不一致"的问题，我们实施了以下约束：

1.  **单一事实源 (SSOT)**：所有通道的默认后缀、色彩空间和启用状态均定义在 `constants.py` 的 `BAKE_CHANNEL_INFO` 中。
2.  **动态 UI 映射**：`ui.py` 不再硬编码属性路径，而是读取 `CHANNEL_UI_LAYOUT` 配置。
3.  **一致性测试**：`SuiteCodeReview` 会扫描 `BakeChannel` 属性与 `constants.py` 定义的交集，任何命名不匹配都会拦截构建。

### 5.1 参数传递路径图

```
property.py (RNA 定义)
    ↓
ui.py 通过 CHANNEL_UI_LAYOUT 渲染属性
    ↓
engine.py: JobPreparer / BakePassExecutor 消费属性
    → _handle_save / _execute_blender_bake_op
    ↓
image_manager.py: save_image 使用图像格式参数
core/shading.py: apply_baked_result 消费通道映射
```

### 5.2 一致性关键规则

- **`folder_name` 传递规则**：优先 `s.folder_name if s.create_new_folder else task.folder_name`
- **动态枚举默认值**：`items` 为回调函数的 `EnumProperty` 必须使用整数默认值（而非字符串 identifier），否则 Blender 4.2+ 注册时抛出 `RuntimeError`
- **降噪场景清理**：`BakePostProcessor.apply_denoise(context, img)` 必须注入 `context` 参数 + `temp_override`，渲染失败时 `finally` 块确保临时场景被删除

---

## 7. 全局状态与模块级可变状态 (Global State Management)

为符合 Google Python Style Guide §3.5，BakeNexus 对模块级可变状态进行了封装：

### 7.1 Registry Pattern（`__init__.py`）

```python
class _RegistryState:
    def __init__(self):
        self.classes_to_register: list = []
        self.addon_keymaps: list = []

registry = _RegistryState()
```

所有 `register()` / `unregister()` 操作通过 `registry.classes_to_register` 和 `registry.addon_keymaps` 访问，避免模块级 `global` 声明和多次注册/注销时的残留风险。

### 7.2 Private Module State（`thumbnail_manager.py`）

```python
_preview_collections = {}  # 模块私有，通过函数 API 访问
```

外部代码通过 `get_preview_collection()` / `clear_all_previews()` 函数接口操作，而非直接修改字典。

---

## 8. 异常安全策略 (Exception Safety)

BakeNexus 遵循以下异常处理原则：

1. **禁止 bare `except:`**：必须显式指定可捕获的异常类型。
2. **`except Exception` 仅用于顶层入口**（如 `main()` 函数），核心逻辑中必须收紧：
   - Blender API 操作：`(AttributeError, RuntimeError, ReferenceError)`
   - 文件操作：`(OSError, IOError, PermissionError)`
   - JSON 操作：`(json.JSONDecodeError, OSError)`
   - 子进程操作：`(subprocess.TimeoutExpired, OSError)`
3. **`finally` 块中的异常必须捕获**（`finally` 中抛异常会覆盖原始异常）。
4. **`KeyboardInterrupt` 和 `SystemExit` 永远不捕获**。

当前状态：全项目 0 个 bare `except`，0 个 `except Exception` 在生产代码核心路径中。

---

## 9. 参数传递路径图 (Parameter Flow)

```
property.py (RNA 定义)
    ↓
ui.py 通过 CHANNEL_UI_LAYOUT 渲染属性
    ↓
engine.py: JobPreparer / BakePassExecutor 消费属性
    → _handle_save / _execute_blender_bake_op
    ↓
image_manager.py: save_image 使用图像格式参数 (通过 SceneSettingsContext)
core/shading.py: apply_baked_result 消费通道映射
```

### 9.1 一致性关键规则

- **`folder_name` 传递规则**：优先 `s.folder_name if s.create_new_folder else task.folder_name`
- **动态枚举默认值**：`items` 为回调函数的 `EnumProperty` 必须使用整数默认值
- **降噪场景清理**：`apply_denoise` 使用 `context` 参数 + `temp_override`，`finally` 块确保临时场景删除
- **save_image 上下文安全**：所有场景渲染设置修改通过 `SceneSettingsContext` 管理，而非直接操作 `bpy.context.scene.render`
