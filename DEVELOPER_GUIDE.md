# Simple Bake Tool (SBT) - 开发者深度指南

本文档提供 Simple Bake Tool 的底层架构深度解析，旨在帮助开发人员理解其执行流程、数据流向及关键算法实现。

## 1. 核心架构与模块职责 (Refactored Architecture)

SBT 在 `v0.9.2` 引入了模块化架构，将核心逻辑从 `utils.py` 拆解至 `core/` 包中。

| 模块 | 核心类/对象 | 职责详解 |
| :--- | :--- | :--- |
| **`__init__.py`** | `register()` | 插件生命周期管理。负责注册 Operator、UI 面板、Keymap 和全局 Scene 属性。 |
| **`ops.py`** | `BAKETOOL_OT_BakeOperator` | **流程控制器**。使用 Modal Timer 模式调度整个烘焙任务。负责调用 `core` 模块执行具体逻辑。 |
| **`utils.py`** | (Facade) | **兼容性接口**。重新导出 `core.*` 中的功能，确保旧代码和测试脚本无需修改即可运行。 |
| **`core/node_manager.py`** | `NodeGraphHandler` | **节点图管理**。负责材质节点的“脏操作”：创建 Emission/Texture 节点，连接逻辑，以及烘焙后的**节点清理**。 |
| **`core/math_utils.py`** | `Numpy Algorithms` | **高性能计算**。包含 `setup_mesh_attribute` (ID Map 生成) 和 `process_pbr_numpy` (PBR 像素处理)。 |
| **`core/uv_manager.py`** | `UVLayoutManager` | **UV/UDIM 管理**。负责 Smart UV 生成、UDIM Tile 自动打包 (`UDIMPacker`) 以及临时 UV 层的创建与销毁。 |
| **`core/image_manager.py`** | `set_image`, `save_image` | **图像 I/O**。负责图像的创建（含 UDIM Tiled Image）、色彩空间管理、以及包含 `<UDIM>` 标记的文件保存。 |
| **`core/cleanup.py`** | `BAKETOOL_OT_EmergencyCleanup` | **灾难恢复**。提供在 Blender 崩溃后清理残留数据（如 `BT_Bake_Temp_UV`）的工具。 |
| **`state_manager.py`** | `BakeStateManager` | **容错系统**。负责将烘焙状态实时写入磁盘 JSON，用于崩溃分析。 |

---

## 2. 烘焙管线执行流程 (The Baking Pipeline)

当用户点击 `START BAKE` 后，系统进入以下严格定义的流水线：

### Phase 1: 初始化与任务构建 (`invoke`)
位于 `ops.py` -> `BAKETOOL_OT_BakeOperator.invoke`

1.  **环境检查**: 强制切换到 Object Mode。
2.  **状态记录**: 初始化 `BakeStateManager`，写入 `STARTED` 状态至 `logs/last_session.json`。
3.  **任务构建 (`_prepare_job`)**:
    *   调用 `TaskBuilder.build`。将复杂的选区逻辑（如 Active Bake）拆解为标准化的 `BakeTask`。
    *   **UDIM 检测**: 如果是 UDIM 模式，预先计算所有物体的 Tile 位置。
4.  **通道收集**: 根据优先级排序通道（ID Map 优先）。

### Phase 2: 模态执行循环 (`modal`)
位于 `ops.py` -> `BAKETOOL_OT_BakeOperator.modal`

1.  **日志更新**: 记录当前 Step 信息。
2.  **上下文隔离**: `BakeContextManager` 设置渲染参数。
3.  **UV/UDIM 准备**: `core.uv_manager.UVLayoutManager` 介入。
    *   如果启用 Smart UV，计算新布局。
    *   如果启用 UDIM Repack，将物体 UV 偏移到目标 Tile (1002, 1003...)。
    *   **关键**: 创建临时 UV 层 `BT_Bake_Temp_UV` 保护原始数据。
4.  **节点图接管**: `core.node_manager.NodeGraphHandler` 介入。
    *   在材质中注入 Emission 节点和必要的逻辑节点（如 Bevel, Geometry）。

### Phase 3: 单通道烘焙逻辑 (`_bake_channel`)

*   **分支 A: Numpy 加速 (core.math_utils)**
    *   针对 Extension Map (`pbr_conv_*`)。
    *   直接读取内存中的 Source Image 像素，通过 NumPy 进行矩阵运算（如 Specular -> Metallic），写入 Target Image。**速度比 Cycles 渲染快 10-100 倍**。

*   **分支 B: 标准烘焙**
    *   **图像准备**: `core.image_manager.set_image` 处理 Tiled Image (UDIM) 的创建。
    *   **ID Map 生成**: 调用 `core.math_utils.setup_mesh_attribute`，利用 BMesh C-API 或 Numpy 快速生成 Vertex Color。
    *   **执行**: `bpy.ops.object.bake(type='EMIT')`。

*   **清理**: `NodeGraphHandler` 和 `UVLayoutManager` 在 `__exit__` 时自动清理临时节点和 UV 层。

---

## 3. 关键算法实现细节

### 3.1 优化的 ID Map 生成 (`core.math_utils`)

*   **策略**: 优先使用 Numpy 处理 Material ID。对于 Geometric ID (Islands)，使用 `bmesh.ops.find_adjacent_mesh_islands` (C-level) 替代 Python 递归。
*   **色彩生成**: 使用黄金分割率 (`0.618`) 生成色相，确保相邻 ID 颜色差异最大化，避免相近色导致的 Mask 提取困难。

### 3.2 UDIM 打包逻辑 (`core.uv_manager`)

*   **Repack 模式**:
    1.  检测所有物体的当前 UV Tile。
    2.  保留已位于 >1001 Tile 的物体。
    3.  收集所有位于 1001 的物体。
    4.  按名称排序后，依次分配到下一个可用的空 Tile。
    5.  使用 Numpy `foreach_set` 批量偏移 UV 坐标。

---

## 4. 异常处理与灾难恢复

### 4.1 崩溃日志
*   系统会在 `%TEMP%/sbt_last_session.json` 记录每一步的状态。
*   Blender 重启后，插件读取此文件，若上次未正常结束，则在 UI 显示警告。

### 4.2 紧急清理 (Emergency Cleanup)
*   **场景**: 若 Blender 崩溃，`__exit__` 清理代码未执行，场景中会残留 `BT_Bake_Temp_UV` 层或紫色/白色贴图。
*   **工具**: 调用 `bpy.ops.bake.emergency_cleanup()` (或 F3 搜索 "Clean Up Bake Junk")。
*   **逻辑**: 扫描全场景，按命名特征暴力删除所有临时数据。