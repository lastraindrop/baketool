# BakeNexus 技术指南 / Technical Guide

本指南详细介绍了 BakeNexus 的核心架构、工作原理以及为保证工业级稳定性所采用的工程实践。

## 1. 架构概述 (Architectural Overview)

BakeNexus 采用模块化的分层架构，旨在解耦 UI、数据管理与执行引擎：

- **UI 层 (`ui.py`, `translations.json`)**: 负责交互显示，通过 `constants.py` 中的配置动态生成界面。
- **数据层 (`property.py`, `constants.py`)**: 定义 RNA 属性、默认值和通道元数据。
- **核心引擎 (`core/`)**:
  - `engine.py`: 执行调度 facade，包含 `BakeStepRunner`、`BakePassExecutor`、任务准备与导出逻辑。
  - `bake_types.py`: `BakeStep` / `BakeTask` 的中立执行契约；后续拆分 `engine.py` 时，生产者与消费者必须依赖此模块而非相互导入。
  - `udim_utils.py`: 不依赖 UI 或管理器的 UDIM tile 检测叶模块，避免 `common.py` 与 `uv_manager.py` 形成反向依赖。
  - `node_manager.py`: 负责非破坏式的材质节点操作。
  - `shading.py`: 预览材质和烘焙结果材质创建；`common.py` 对历史导入路径保持 facade 重导出。
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
Blender 4.2+ 对 `EnumProperty` 的回调函数要求更严格。我们通过返回完整的 5 元组（含 ID 整数）来确保 UI 列表在所有版本中的渲染与索引稳定性。1.0.0 审计轮进一步把编号契约收紧为"全局唯一 + 恒含 NONE + 与已启用集合无关"，完整规则与失效案例见 §10.3。

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
- **save_image 上下文安全**：所有场景渲染设置修改通过 `SceneSettingsContext` 管理，而非直接操作 `bpy.context.scene.render`
- **公开导入兼容**：结构迁移后，旧的 `core.common.apply_baked_result` / `create_simple_baked_material` 仍必须可用；功能实现在 `core.shading`，旧路径仅作为兼容 facade。
- **UDIM 依赖方向**：业务层可使用 `udim_utils.detect_object_udim_tile`；`common.py` 不得重新导入 `uv_manager.py`。

### 5.3 参数动态对齐的验证闭环

参数一致性不是只靠文档约定，而是由以下链路共同约束：

1. `property.py` 定义可持久化的 RNA 字段、默认值和 update callback。
2. `constants.py` 提供格式约束、通道元数据及 `CHANNEL_UI_LAYOUT`；重复布局通过共享配置对象复用，避免同一参数描述分叉。
3. `ui.py` 依据配置路径绘制属性；`engine.py` / `image_manager.py` / `shading.py` 消费同一 RNA 和通道标识。
4. `suite_unit.test_property_group_integrity`、`suite_unit.test_ui_layout_config_integrity`、`suite_parameter_matrix.test_dynamic_enum_returns_5tuple`、`suite_code_review.test_channel_pipeline_alignment` 验证 RNA、布局、动态枚举、公开接口与引擎可达性。

任何新增通道、保存格式或 UI 参数都必须同时检查这四层；不能只让 UI 显示新字段，或只让引擎读取未注册字段。

### 5.4 通道管线与引擎可达性（Channel Pipeline & Engine Reachability）

本节完整叙述一条烘焙通道从"UI 勾选"到"像素落盘"的全链路。它是 1.0.0 发布前外部审计中 B-03 缺陷（无实现通道烘出全黑图）的直接产物——该缺陷暴露了"通道被列出但没有引擎路径"这一类失配此前没有任何机制拦截。

#### 5.4.1 工作原理：通道的四层数据结构

一个通道在代码库中由四份契约共同描述，任何一层与其他层脱节都会产生用户可见的故障：

| 层 | 事实源（`constants.py`） | 职责 | 失配后果 |
|---|---|---|---|
| ① 通道列表 | `BAKE_CHANNEL_INFO` | 决定 UI 上出现哪些通道、默认后缀与启用状态 | 多列 → 用户可勾选（见 5.4.4）；漏列 → 元数据成孤岛（`height` 案例） |
| ② 通道元数据 | `CHANNEL_BAKE_INFO` | 提供烘焙 pass（EMIT/DIFFUSE/…）、分类、默认色彩空间 | 漏配 → 引擎回退 EMIT + sRGB，颜色空间错误 |
| ③ UI 布局 | `CHANNEL_UI_LAYOUT` | 数据驱动地绘制每通道的专属参数 | 孤儿键 → 面板永不显示（死配置） |
| ④ 引擎映射 | `CHANNEL_MESH_TYPE_MAP` / `BSDF_COMPATIBILITY_MAP` / 引擎特判 | 告诉执行器"这个通道的像素从哪来" | **缺失 → 全黑贴图（B-03）** |

运行期入口是 `reset_channels_logic()`（`core/common.py`）：它按①的声明对 RNA `channels` 集合做破坏性同步（增/删/改名），保证场景数据与列表声明一致，旧场景升级时被移除的通道会被安全剔除。

#### 5.4.2 具体过程：一条通道的执行流水线

```
用户勾选通道 (RNA BakeChannel.enabled)
    ↓
JobPreparer._collect_channels()            # 读①+② → 通道执行配置 {id, bake_pass, prop, …}
    ↓
BakePassExecutor.execute()                 # 三路分发：
    ├─ _try_custom_channel()               #   CUSTOM：NumPy 从既有结果组装（无需 Blender bake）
    ├─ _try_numpy_pbr()                    #   pbr_conv_*：NumPy 镜面反射转换
    └─ _run_blender_bake_pipeline()        #   标准管线：
         ├─ _get_mesh_type()               #     查④：mesh 通道 → 节点逻辑类型 (AO/BEVEL/POS/UV/WF/ID)
         ├─ _ensure_attributes()           #     ID_* 通道 → 写临时 BYTE_COLOR 顶点色属性
         ├─ NodeGraphHandler.setup_for_pass()
         │     ├─ mesh_type → _create_mesh_map_logic()   # 注入 AO/Bevel/Geometry 等着色节点
         │     ├─ pbr_conv_*/node_group → 扩展逻辑
         │     └─ 其余 → _find_socket_source()           # 查④：BSDF 插座 → 取上游或常量
         ├─ compat.set_bake_type()         #     原生 pass（DIFFUSE/NORMAL/…）直接交给 Cycles
         └─ bpy.ops.object.bake()
    ↓
BakeStepRunner._handle_save() → image_manager.save_image()   # 格式参数（②⑤ FORMAT_SETTINGS）落盘
```

关键点：`bake_pass` 为原生 pass（DIFFUSE/GLOSSY/TRANSMISSION/COMBINED/NORMAL/SHADOW/ENVIRONMENT）的通道由 Cycles 直接执行，不需要④的插座映射；而 `bake_pass = EMIT` 的通道**必须**有一条④层来源，否则 Emission 节点无输入，烘出的就是目标图的清底色（通常是黑）。

#### 5.4.3 引擎可达性判定规则

一个列在①中的通道 id 是"可达的"，当且仅当满足以下五条之一：

1. 其②元数据的 `bake_pass` ∈ 原生 pass 集合（Cycles 直接执行）；
2. `id ∈ {pbr_conv_base, pbr_conv_metal, node_group}`（`BakePassExecutor`/`NodeGraphHandler` 引擎特判）；
3. `id` 以 `ID_` 开头（`setup_mesh_attribute` 顶点色属性路径）；
4. `id ∈ CHANNEL_MESH_TYPE_MAP`（网格分析节点逻辑）；
5. `id ∈ BSDF_COMPATIBILITY_MAP`（Principled BSDF 插座来源）。

不满足任何一条的通道会被列出、可勾选、正常走完烘焙流程、返回"成功"——然后产出一张黑图。**这正是 B-03 的失效模式：静默失败比崩溃更危险。**

#### 5.4.4 B-03 案例复盘

**缺陷**：`Vertex Color / Curvature / Slope / Thickness / Select` 五个通道被①列出且②有元数据，但④没有任何路径（Slope 有 `CHANNEL_MESH_TYPE_MAP` 映射到 `"SLOPE"`，而 `_create_mesh_map_logic` 没有 SLOPE 分支——映射表指向不存在的实现；其余四个连映射都没有）。另 `height` 通道反向失配：②有元数据但①从未列出，属不可达死数据。

**为何 158 个测试没有拦住**：既有测试断言了①内部的一致性（BSDF/BASIC 列表的默认启用集合）和③ ⊆ ①，但没有任何测试问过"①中的每个通道，引擎真的会执行吗"。测试覆盖的是"声明之间的 harmony"，而非"声明与实现的 harmony"。

**修复与固化**：
- 从①②③及 `DATA_BAKE_FORCE_SINGLE_SAMPLE`、`CHANNEL_MESH_TYPE_MAP` 中移除全部无实现条目；`mesh_settings` 的 `contrast/direction/invert` RNA 字段保留（v1.1 重实装时免迁移，`property.py` 有注释保护）。
- 新增 `suite_code_review.test_channel_pipeline_alignment`，将 5.4.3 的判定规则与"①②双向一致""③无孤儿键"固化为断言。此后任何人往 `BAKE_CHANNEL_INFO` 加通道而不同时提供引擎路径，CI 会在 `code_review` 套件直接红掉。

#### 5.4.5 新增/修改通道的强制检查单

1. 在①加条目（id、显示名、默认后缀/启用状态）。
2. 在②补元数据（bake_pass、分类、def_cs、def_mode）——①②必须双向覆盖。
3. 若通道有专属参数：在③加布局；参数本体加进 `BakeChannel` 或其子 PropertyGroup。
4. **回答"像素从哪来"**：按 5.4.3 五选一落位；需要新的 mesh 逻辑时同步扩展 `_create_mesh_map_logic()` 并在 `CHANNEL_MESH_TYPE_MAP` 注册。
5. 若为数据图（无需采样）：加入 `DATA_BAKE_FORCE_SINGLE_SAMPLE`。
6. 翻译键：运行 `python dev_tools/extract_translations.py --source . --existing translations.json --sync --print-missing` 后补全 5 语言。
7. 跑 `--suite code_review`——`test_channel_pipeline_alignment` 是这一检查单的机器化版本。

---

## 6. 崩溃恢复与状态缓存 (Crash Recovery & State Caching)

### 6.1 崩溃恢复机制

BakeNexus 通过 `state_manager.py` 的 `BakeStateManager` 实现了轻量级崩溃恢复：

```
烘焙开始 → start_session() → 写入 {tempdir}/sbt_last_session_<PID>.json
    ↓
每通道更新 → update_step() → 读-改-写 JSON（含 fsync 落盘保证）
    ↓
异常中断 → log_error() → 标记 status="ERROR"
    ↓
正常结束 → finish_session() → 删除本实例 JSON + 重置 UI
```

**多实例隔离（1.0.0 收尾加固）**：会话文件按进程 PID 命名（`sbt_last_session_<PID>.json`）。`has_crash_record()` / `read_log()` / `clear_state()` 通过 `SESSION_FILE_GLOB = "sbt_last_session*.json"` 前缀扫描所有实例的文件（按 mtime 新者优先），因此：并行运行的多个 Blender 互不覆盖彼此的记录；新实例仍能发现旧实例崩溃留下的记录；`finish_session()` 只清理本实例文件（不打断并行会话），`clear_state()`（用户主动清理）删除全部。该机制取代了 1.0.0 早期的单一固定文件名 `sbt_last_session.json`。

**持久化内容**：`status`, `start_time`, `job_name`, `total_steps`, `current_step`, `current_queue_idx`, `current_object`, `current_channel`, `last_error`

**检测逻辑**：`has_crash_record()` glob 会话文件 → 若存在说明上次未正常完成 → UI 显示警告

**写入安全**：每次 `_write()` 执行 `f.flush()` + `os.fsync()`，确保断电/进程杀灭时数据已落盘。损坏的 JSON 文件读取返回 `None` 而非崩溃。

**生命周期集成**：
- `BakeModalOperator.init_modal()` → `start_session()`
- `BakeStepRunner.run()` → 每个通道前 `update_step()`
- 异常捕获 → `log_error()`
- `_cleanup_state()` → `finish_session()` / `clear_state()`
- 紧急清理 `BAKETOOL_OT_EmergencyCleanup`（Baked Results 面板 `Clean Up Bake Junk` 按钮）→ `reset_ui_state()`

### 6.2 状态缓存优化

为避免 `update_step()` 每次通道更新都从磁盘读取 JSON 的 I/O 开销，`BakeStateManager` 引入了实例级内存缓存 `_cached_data`：

- **`_write(data)`**：同时更新 `self._cached_data = data` 并写入磁盘
- **`read_log()`**：若 `_cached_data` 非空直接返回，否则从磁盘读取并缓存
- **`finish_session()` / `clear_state()`**：将 `_cached_data` 置 `None` 并删除磁盘文件

此优化在大批量烘焙（如 20+ 通道）场景下消除了 90% 以上的冗余磁盘读取，且不影响崩溃恢复的可靠性——每次关键状态变更仍同步写盘。

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

当前状态：全项目 0 个 bare `except`。生产烘焙、数据和资源管理路径不使用 `except Exception`；仅 `__init__.py` 的插件注册/注销边界保留带日志的广泛捕获，以允许其余可注册类、handler 或预览资源继续清理。任何新增广泛捕获都必须限于同类顶层隔离边界并记录原因。

---

## 9. DRY 基础设施与一致性机制 (DRY Infrastructure & Consistency)

为消除代码库中积累的重复模式并建立单一事实源，v1.0 发布前引入了以下集中式辅助机制：

### 9.1 `get_active_job()` — 活动 Job 索引钳制

位于 `core/common.py`，封装了全项目最频繁的重复模式——从 `BakeJobs` 集合中按索引获取活动 Job，同时处理越界回退：

```python
def get_active_job(bj, sync_index=True):
    """返回活动 BakeJob，或 None。钳制 job_index 并可选同步回写。"""
    if not bj.jobs:
        return None
    idx = bj.job_index
    if idx < 0 or idx >= len(bj.jobs):
        idx = 0
        if sync_index:
            bj.job_index = idx
    return bj.jobs[idx]
```

统一了之前分散在 `ops.py`（8 处）、`ui.py`（2 处）、`property.py`（1 处）、`core/common.py`（1 处）的 12 处重复索引钳制逻辑，同时修正了部分调用点缺少空 Job 集检查的潜在 `IndexError`。

### 9.2 `tag_redraw_view3d()` — View3D 区域刷新

位于 `core/common.py`，统一了 `ops.py` 和 `property.py` 之间 3 处重复的 View3D 区域标记重绘循环：

```python
def tag_redraw_view3d(context):
    """标记所有 VIEW_3D 区域重绘，含 context/screen 空值保护。"""
    if context and context.screen:
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
```

### 9.3 `EXTENSION_TO_FORMAT` — 文件扩展名反向映射

位于 `constants.py`，从 `FORMAT_SETTINGS` **自动计算** 生成扩展名→格式名的反向映射，消除了 `ops.py` 的 `_get_format_from_path` 硬编码副本（双重事实源）。新增格式时仅需更新 `FORMAT_SETTINGS`，反向映射自动同步：

```python
EXTENSION_TO_FORMAT = {}
for _fmt, _cfg in FORMAT_SETTINGS.items():
    for _ext in _cfg.get("extensions", []):
        EXTENSION_TO_FORMAT[_ext] = _fmt
```

### 9.4 `SYSTEM_NAMES` — Blender 命名集中管理

所有插件创建的 Blender 数据块名称（临时场景、相机、预览材质）均从 `constants.py` 的 `SYSTEM_NAMES` 字典引用，禁止在各模块中硬编码字符串字面量。v1.0 新增了 `DENOISE_SCENE`、`DENOISE_CAMERA`、`PREVIEW_MAT` 三个键。

### 9.5 测试验证

以上辅助函数和映射的一致性由以下测试套件保障：
- `suite_code_review`：验证 UI 标签与内部键的一致性。
- `suite_unit`：MockSetting 属性完整性检查。
- `suite_production_workflow`：端到端烘焙管道验证。

### 9.6 本轮重构后的执行与验证结果

- `BakeModalOperator` 对运行中的队列长度变化显式报错并由统一错误管道记录，避免未捕获 `IndexError`。
- `UVLayoutManager` 接受可选 `context`，调用方优先传入显式上下文；仅在未提供时回退 `bpy.context`，保证 headless/API 可用。
- `common.py` 的材质结果函数迁移至 `shading.py`，同时 re-export 旧路径，兼顾职责分离与第三方脚本兼容。
- 通过 Blender 3.3.21、3.6.23、4.2.14、4.5.3、5.0.1 的 `unit` 跨版本矩阵（5/5）；并通过 4.2 的 `verification`、注册循环、facade 导入，以及 5.0 的 `production_workflow` 10/10。

### 9.7 外部审计修复轮的工程产物 (2026-08-17)

- **`test_channel_pipeline_alignment`**（`suite_code_review`）：将 §5.4.3 引擎可达性规则机器化，是防止"UI 列出、引擎落空"类缺陷复发的第一道闸门。
- **`test_manifest_id_matches_addon_directory` / `test_release_zip_includes_audit_dependencies`**（`suite_extension_validation`）：分别防止扩展 ID 与打包目录名漂移（B-01）、打包内容与随包审计依赖断裂（B-04）。
- **`translations.py` 双 locale 注册**：JSON 单一事实源使用 `zh_HANS`（Blender 4.2+），注册期自动派生 `zh_CN` 别名兼容 ≤4.1 legacy 源码安装——新旧版本共用一份词典，不产生数据分叉。
- **词典治理**：以 `dev_tools/extract_translations.py --sync --prune` 收敛死键（19 个旧品牌/已删功能/已删通道键）并补齐 6 个缺失键的多语言，落盘 468 词条、0 空值；此后词典维护必须走该工具而非手工编辑。

### 9.8 发布候选清理轮的工程产物 (2026-09-10)

本轮（净 -153 行）修复了两类用户可感知缺陷并移除全部已确认的死代码，其方法学沉淀如下。

#### 9.8.1 "声明↔接线"可达性失配：缩略图链路案例

§5.4 处理的是**数据层**的声明-引擎失配（通道四层结构）。本轮在**功能接线层**发现了同族缺陷：

- **症状**：Visual Preset Gallery 的图标恒为空，图库静默降级为纯文字列表。
- **根因**：`thumbnail_manager.load_preset_thumbnails()` 是全库唯一调用 `pcoll.load()` 的函数，但**没有任何调用方**——`get_library_preset_items()` 只创建空 preview collection 后直接查询图标。功能"已声明（函数存在、UI 存在）、未接线（调用链断裂）"。
- **修复**：枚举回调接线调用 `load_preset_thumbnails()`，并将其改为**幂等加载**（`pcoll.get()` 命中即跳过）。幂等是硬性要求：动态枚举回调在每次 UI 重绘都会触发，而 Blender previews API 对重复加载同名条目会抛错。
- **同族教训归集**：B-03（通道列出但引擎无路径）、缩略图（函数/UI 存在但调用链断裂）、孤儿 operator（`bl_idname` 声明但无任何 UI/菜单/快捷键引用，如已删除的 `TogglePreview`）本质相同——**静态检查"定义之间存在 harmony"无法发现"声明与使用之间的失配"**。

#### 9.8.2 死代码判定标准与审计方法

本轮移除死代码时采用的双重判定，后续清理应沿用：

1. **零引用判定**：符号在运行时源码（`.`/`core`/`automation`）与 `test_cases` 中均无引用。注意甄别三类合法例外：①有 UI/引擎消费路径但暂无 UI 入口的预留字段（如 `mesh_settings.contrast`，有注释保护，不得误删）；②RNA 无继承导致的属性重复（如 `BakeImageSettings`）；③历史记录文档（CHANGELOG）中的提及。
2. **测试引用同步**：删除符号时必须同步处理测试（存在性断言、Mock 字段、builder 方法），否则测试套件红掉或留下"测试只验证存在性"的假覆盖。
3. **词典同步**：删除任何 UI 字符串/RNA 名称后，运行翻译审计移除对应死键（本轮 468 → 465），维持"0 死键"不变量。
4. **验证闭环**：静态审计（死符号 0 残留、孤儿 operator 0、i18n 0 缺失、register/unregister 对称）+ 全版本矩阵实测。本轮为 5 版本 160 项 0 失败 0 错误。

#### 9.8.3 UI 去重：数据驱动布局与通用绘制的边界

`CHANNEL_UI_LAYOUT` 声明的是**每通道专属**参数；所有通道**共享**的属性（如 Naming 行的 prefix/suffix）由 `draw_active_channel_properties` 统一绘制。本轮缺陷（Normal 通道前后缀出现两次）即"专属布局里重复声明了共享属性"。规则：**往 `CHANNEL_UI_LAYOUT` 加条目前，先确认该属性未被通用绘制路径覆盖**。

---

## 10. 发布前独立审计修复轮 (2026-09-11)

本节完整记录 1.0.0 发布前的独立审计轮：审计如何发现既有 162 项测试没有覆盖的缺陷、修复遵循了哪些新契约、参数一致化与动态对齐如何被强制，以及为避免同类错误而固化的检查单。完整诊断明细（30 组，含逐项文件行号与运行证据）见 `docs/RELEASE_AUDIT_2026-09-11.md`；本节聚焦可复用的工程结论。

### 10.1 审计方法：为什么"测试全绿"仍然藏有阻断缺陷

审计采用三级证据分级，避免把推测当结论：

1. **R（运行复现）**：在独立 `--factory-startup` 后台进程中复现。控制流类问题（如"保存失败仍退出"）用模块级替身拦截 `bpy.ops.wm.quit_blender` 等调用，不冒充真实实验。
2. **S（源码确认）**：有明确赋值/遗漏/调用链证据，但不宣称做过生产场景验证。
3. **V（待场景验证）**：缺口存在，但需交互环境或真实崩溃才能确认完整表现。

这轮审计的核心教训与 §5.4（B-03）同源但更深一层：**既有测试断言的大多是"声明之间的 harmony"（通道表一致、函数不抛异常、文件存在），而不是"输出与承诺的 harmony"（像素正确、编码正确、失败如实报告）**。典型弱断言案例（均已修复）：

| 弱断言 | 实际掩盖的缺陷 | 修复后的契约断言 |
|---|---|---|
| 动画测试只检查两个文件名存在 | API/headless 从不切换场景帧，所有帧在同一帧位烘焙 | runner 统一 `frame_set`；E2E 日志出现 Fra:1→Fra:2 |
| API 测试断言"返回 bool" | 通道全失败也返回 False 满足断言 | 失败必须抛错或计数；探测 `CANCELLED → False` |
| 降噪测试比较随机数组与 byte 图回读 | 量化本身就能制造"像素改变"假阳性；后台假处理 | float 基线 + 后台必须逐位不变（显式跳过契约） |
| 预设测试只比分辨率/采样 | 扩展通道的 node_group 与 enabled 往返即丢 | 非默认字段 + 空集合/空指针全量往返断言 |
| 通道映射存在即通过 | Element/UV/Seam ID 的 BMesh 实现一执行就 TypeError | 实际执行 + 输出内容断言 |

**推论**：测试数量的增长不等于可信度增长。替换一个弱断言的价值高于新增十个存在性检查；允许测试数下降但可信度上升。

### 10.2 三条核心契约（本轮确立）

#### 契约一：失败契约——"成功"必须表示"实际完成要求的烘焙与保存"

- `bpy.ops.object.bake()` 的返回集合**必须**包含 `FINISHED`，否则视为该通道失败（清理新建图像并返回 None）。
- 外部保存失败（`save_image` 返回 None）**必须抛错**，不允许继续生成"成功"结果条目。
- 模态操作符对步骤异常**计数**并在结束时如实显示 `Finished (N step errors)`，同时按错误状态收尾会话记录。
- 导出失败（目标 addon 缺失）返回 False，**禁止**打印 "Exported:" 成功日志。
- 结果元数据如实记录实际执行参数：强制单采样通道记录 `samples=1` 而非 job 设置值。

#### 契约二：资源所有权——禁止按名字认领用户数据

- 插件创建的图像与烘焙结果对象打上自定义属性 `is_bt_result = True`；`set_image` / `apply_baked_result` **只复用带标记的自有 datablock**。用户恰好同名的对象/图像绝不被替换、清空、缩放或删除。
- 复用时契约不匹配（TILED↔普通、float↔byte）即销毁重建，而不是迁就地改参数。
- 临时资源清理（降噪场景、相机、UV 层、节点）限定为**本次创建**的引用，禁止按前缀全局扫描"看起来像我的"数据。

#### 契约三：入口一致性——所有执行入口共用同一条准备与执行链

- Quick Bake 的 runtime proxy 构建后**必须**过 `JobPreparer.validate_job`，与普通烘焙同规则（对象存在、View Layer、UV、目标合法性）。
- 动画帧切换（`frame_set`）属于 `BakeStepRunner.run()`，不属于任何 UI operator——面板、Quick Bake、API、headless CLI 四入口行为天然一致。
- Auto Smart UV 启用时，"无 UV"不再是拒绝理由（UV 会由流程生成）；SELECT_ACTIVE 的低模目标与高模源一并纳入 UV 管理。

### 10.3 参数一致化与动态对齐：规则、案例与测试

#### 10.3.1 动态枚举稳定契约（`get_channel_source_items`）

来源类动态枚举（自定义通道来源、通道打包 R/G/B/A）遵循以下硬性规则：

1. **恒含 `NONE`**：列表首项固定为 `("NONE", "None", ..., 0)`。候选为空不能省略它，否则"清除选择"无法表达，且 RNA 保存值无法回退。
2. **编号全局唯一且与启用集合无关**：内置通道使用 `i + 1`（i 为完整通道集合索引），自定义通道使用 `len(channels) + 1 + i`。编号**绝不**基于"当前已启用的通道数"这类可变基数。
   - *失效案例（修复前）*：自定义项以"已启用数"为偏移。用户选择 `BT_CUSTOM_Custom`（编号 3）后再启用一个普通通道，编号 3 被另一个通道占用，原选择静默变成非法值，RNA 读回空串并打印 `current value '3' matches no enum` 警告。
3. **RNA 警告即契约破裂信号**：任何 `matches no enum in ...` 运行时警告都视为缺陷，不是噪音。
4. 既有规则沿用：回调返回 5 元组；`items` 为函数的 EnumProperty 默认值必须用整数。

#### 10.3.2 UI 控件准入规则："可设置但不生效"= 缺陷

每个暴露给用户的控件都必须有明确的引擎消费路径。无消费者的控件**删除**（而非保留"供以后使用"），因为它会持续产生"我设置过为什么没效果"的用户困惑与误诊断：

| 已处理案例 | 处置 |
|---|---|
| `BakeChannel.custom_mode`（通道级 Export Mode） | 保存链只消费 job 级 color_mode → **删除 RNA + UI** |
| `BakeJobSetting.auto_uv_name`（Smart UV 层名） | 引擎使用固定临时层名 → **删除 RNA** |
| `BakeNormalSettings.type / X / Y / Z` | **接线**：OPENGL/DIRECTX → `normal_r/g/b`（Y 轴约定），CUSTOM → 显式三分量 |
| `BakeMeshSettings.local_only`（AO Only Local） | **接线**：写入 Ambient Occlusion 节点 `only_local` |
| `bake_motion_use_custom` | **接线 UI**：动画区暴露 Custom 开关， Start/Frames 仅在开启时生效（此前引擎读该字段但 UI 无法切换，等于 UI 与引擎各说各话） |
| `mesh_settings.contrast/direction/invert` | **保留**：为 v1.1 通道重实装预留，有注释保护（合法例外，见 §9.8.2） |

判定顺序：先问"引擎在哪一行读它"——读不到就删除；能读到但 UI 不可达就补 UI；两者都不是才考虑预留并注释保护。

#### 10.3.3 执行对齐的四个强制点

1. **bake 设置目标统一**：`SceneSettingsContext("bake", ...)` 的取目标逻辑**必须**复用 `compat.get_bake_settings(scene)`，禁止在 common 里重写版本分支。
   - *失效案例（A08）*：common 自己判断 `is_blender_5()` 才使用 `scene.render.bake`，导致 Blender 4.x 的 `use_pass_direct/indirect/color` 开关被静默丢弃——上下文进入/退出"看起来正常"，但属性从未写进真正的目标。修复后 4.2 复现：上下文内 `use_pass_direct` 实际为 False。
2. **图像落盘统一走 `save_render`**：格式、位深、颜色模式、质量、编解码由 `scene.render.image_settings`（经 `SceneSettingsContext("image")` 临时接管）驱动。`image.save()` 与场景设置脱钩，是"界面设置真实生效"的反例（A10：请求 16-bit 落盘 8-bit、请求 BW 落盘 RGBA）。验证必须到**文件头级**（PNG IHDR 的 bit depth / color type），交叉改变 buffer 类型与请求参数，单一组合的"碰巧一致"不算证据。
3. **通道间输出链接恢复**：`setup_for_pass()` 每个 pass 开始时先移除 Material Output 的当前输入链接，并从 `original_links` 回填用户原始连接——否则前一个 EMIT pass 的临时 Emission 会泄漏进后续原生 pass（A06：EMIT → COMBINED 后输出源仍是 `ShaderNodeEmission`）。
4. **预览与烘焙互斥**：`use_preview` 开启时，`BakeStepRunner.run()` 在进入烘焙上下文前对任务对象执行 `remove_preview()`；`apply_preview()` 对"当前材质已是预览"的对象直接早退——从预览自身重建会摧毁首次捕获的源节点逻辑（A23）。

#### 10.3.4 预设往返与加载顺序

`PropertyIO.from_dict` 的顺序敏感点（A20 案例：扩展通道的 `node_group` 与 `enabled` 往返即丢）：

1. **迁移仅限旧键**：`PRESET_MIGRATION_MAP` 的改写只在键**不是**当前层合法字段时执行。此前 `extension_settings.node_group`（当前合法键）被误当旧键 `node_group` 迁移到不存在的路径上，数据直接丢弃。
2. **先集合后标量**：加载排序把 CollectionProperty 排在最前。原因：`use_light_map` 等开关的 update 回调会按声明**重建**通道集合——先加载开关再加载通道，通道的 enabled/配置会被回调销毁。
3. **空集合与空指针必须可写回**：序列化始终输出集合（含空列表）；加载时仅当新值是合法 list 才 clear+重建。否则"导入一个没有 custom channels 的预设"无法清空目标上已有的旧数据。
4. **先验证类型再 clear**：对错误类型的值先 clear 等于先破坏现有配置再失败。

回归固化：`suite_preset.test_preset_keeps_extension_channel_and_empty_collections`（扩展通道 enabled + node_group 往返、空集合清空语义）。

#### 10.3.5 一致性验证闭环（本轮新增/加强的测试）

| 测试 | 固化的契约 |
|---|---|
| `suite_context_lifecycle.test_uv_manager_rolls_back_partial_setup_failure` | `UVLayoutManager.__enter__` 中途失败必须自回滚（Python 不会为进入失败的管理器调用 `__exit__`） |
| `suite_preset.test_preset_keeps_extension_channel_and_empty_collections` | §10.3.4 的迁移边界与空集合语义 |
| `suite_shading.test_apply_preview_skips_if_already_preview`（加强） | 幂等 = 源节点逻辑存活，而非仅材质名不变 |
| `suite_unit.test_apply_denoise_pixels_modified`（重写） | float 基线；后台模式逐位不变（显式跳过契约） |
| `suite_ui_logic.test_ui_message_consistency`（收紧） | 消息表只允许有接线消费者的键存在（5 个死键已删） |

另有若干契约（同名数据保护、PNG 文件头、节点烘焙像素、后台不退出等）当前由审计探测脚本验证，**尚未固化为套件**——这是 v1.1 测试扩展的优先项，避免本轮探测能力随临时脚本流失。

### 10.4 已知限制（v1.1 明示保留项）

以下问题在审计中确认、经评估后**有意保留**至 v1.1，且已在文档中明示，不构成静默宣称：

1. **UDIM 边界与逐 tile 后处理（A17 余项）**：floor 边界使 [0,1] UV 误判出多 tile；numpy custom/PBR/打包不逐 tile 处理；`api.get_udim_tiles` 只收集主导 tile 与命名不符。
2. **多对象自动应用/导出范围（A18）**：COMBINE/UDIM/SPLIT 模式下 Apply/Export 仅覆盖 `task.active_obj`——这些组合下应关闭 Apply/Export。
3. **Proximity 笼体语义（A19 余项）**：最近点距离均值，非逐顶点自适应；非均匀缩放法线未做逆转置校验。
4. **崩溃恢复跨进程归属（A25 余项）**：`bpy.app.tempdir` 按实例隔离时跨进程发现天然失效；共享目录时无 blend 归属区分；真实强杀续跑未在本机验证。
5. **交互式降噪的像素级验证（A12 余项）**：后台已显式跳过；交互路径依赖 Viewer 回读，需真实 GUI 会话做像素级确认。

### 10.5 本轮验证结果（基线快照）

- 5 版本矩阵（3.3.21 / 3.6.23 / 4.2.14 / 4.5.3 / 5.0.1）：162 项，0 失败 0 错误（3.3/3.6 各 5 项预期跳过）。
- 发布 ZIP（`build_release_zip.py` 随包）官方 extension validate 通过；**解压后**独立运行全套 Safety Audit 162/162——发布质量以解压包为准，不以源码目录为准。
- 行为复现：节点红常量 `max_red=1.0`；PNG 文件头与请求一致（8/16-bit × RGB/BW 全组合）；预设 `node_group`/`enabled` 保真；同名用户对象 `mesh_replaced=false`；4.2 `use_pass_direct` 上下文内实际生效；后台 `quit_called=false`；临时 UV/节点/相机计数清理前后相等。
- 静态：全仓 `ruff --select F,E9` 0 项；翻译词典 0 缺失 0 过期；全部 `.py` `py_compile` 通过；运行时代码净增约 90 行（均为失败检查与回滚所需），未新增模块或抽象层。
