# Simple Bake Tool 开发者指引 (Developer Guide)

本文件旨在为 Simple Bake Tool 的后续开发提供架构说明、技术规范及已知问题的记录。

## 1. Architecture (v1.0.0-RC)

The project follows a strict **UI-Engine-Core** three-layer decoupling principle:

1.  **UI/Operator Layer** (`ops.py`, `ui.py`): 
    *   **Data-Driven UI** (**v1.0.0**): 通道属性绘制完全由 `constants.py` 中的 `CHANNEL_UI_LAYOUT` 配置驱动，实现了真正的 100% 哑视图 (Dumb View)，UI 内部移除了所有的业务判断（如 `if channel.id == 'rough'`）。
    *   **UI Dispatch Pattern**: 针对特殊通道的绘制（如 Normal, Combine），使用 `SPECIAL_CHANNEL_DRAWERS` 字典进行逻辑分发，符合开闭原则。
    *   **Thin Operators**: Operator 仅作为入口，具体的数据操作已迁移至 Core 层。新增 `Resume Interrupted Bake` 机制。
2.  **Engine Layer** (`core/engine.py`): The orchestrator.
    *   `JobPreparer`: 验证输入并准备执行队列。支持 Proxy 模式用于 Quick Bake。
    *   `BakePassExecutor` (**v1.1.0**): 彻底拆分巨型逻辑。采用流水线策略（Pipe-lining），将图像创建、Numpy 处理、Blender 原生调用与参数组装隔离为私有原子方法，极大地降低了核心路径的条件耦合。
    *   `BakeStepRunner`: 异步烘焙主控。
    *   **Context Management**: `BakeContextManager` 全面迁移至 `contextlib.ExitStack`。所有的场景临时设置都能保证 100% 原子级回滚。
3.  **Core Layer** (`core/`): 无状态工具模块。
    *   **Standardized Properties**: 核心属性名已统一为 `snake_case`，并通过 `PRESET_MIGRATION_MAP` 保持向后兼容。
    *   **Global SYSTEM_NAMES** (**v1.0.0**): 引入统一的常量字典 `constants.SYSTEM_NAMES`，彻底消除散落各处的 `BT_` 魔法字符串。
    *   `compat.py`: 版本兼容层 (3.6 - 5.0+)。

---

## 2. Technical Feature Breakdown

### 2.1 Principled BSDF Analysis
`NodeGraphHandler` 自动识别 Principled BSDF 节点。支持 4.0+ 的插槽更名适配。

### 2.2 NumPy Acceleration
PBR 转换和通道打包使用 NumPy 向量化计算。支持在 8K 分辨率下保持极低 CPU 开销。

### 2.3 Smart Property Migration
`PropertyIO` 包含一个内置的映射表,当加载旧版本的 `.json` 预设时,会自动将扁平属性映射到新的嵌套设置结构中,确保向后兼容性。

### 2.4 Smart Object Reuse (Post-Bake)
`apply_baked_result` 会检测现有的 `_Baked` 结果物体并执行 `refresh_mesh` 原地更新材质，而非创建重复的 Object 容器。

### 2.5 Select to Active (High-to-Low)
`SELECT_ACTIVE` 工作流由 `JobPreparer` 智能处理。仅验证 Active 物体的 UV,允许高模源物体无需 UV 坐标。

### 2.6 Version Compatibility Layer
`core/compat.py` 提供统一的版本兼容接口:
- `IS_BLENDER_5`, `IS_BLENDER_4`, `IS_BLENDER_3`: 版本检测标志
- `get_bake_settings(scene)`: 统一访问烘焙设置 (处理 5.0 的 `render.bake` vs 旧版本)
- `configure_bake_settings()`: 一站式配置所有烘焙参数

### 2.7 Modal Execution Layer & State Recovery
`core/execution.py` 提供 `BakeModalOperator` Mixin，处理烘焙时的事件循环、进度汇报和动画序列追踪。
**新功能**: `BakeStateManager` 现在记录执行队列的游标 (`current_queue_idx`)。系统可据此提供断点续烘功能。

### 2.8 Atomic Emergency Cleanup (**v1.0.0**)
`core/cleanup.py` 的 `BAKETOOL_OT_EmergencyCleanup` Operator 用于崩溃后的清理。
**安全性强化**: 系统在生成保护节点等临时对象时，会打上底层标记（如 `n["is_bt_temp"] = True`），清理过程优先依据此 GUID 标签销毁，杜绝误伤同名的用户资产。

---

## 3. Testing Suite
### 3.1 核心套件 (`test_cases/suite_*.py`)
- **`suite_unit.py`**: 验证核心工具模块与底层数学逻辑（Cage, Texel Density）。
- **`suite_ui_logic.py`**: 验证 N 面板与图像编辑面板的绘制逻辑。
- **`suite_api.py`**: 验证 `core/api.py` 的公共函数稳定性。
- **`suite_preset.py` [New]**: 验证预设序列化、崩溃恢复状态机、场景属性对称性及通道生成完整性。
- **`suite_production_workflow.py`** (**v1.1.0**): 动态流程验证。移除硬编码通道，自动测试核心 PBR 通道链路（Color/Rough/Normal/Emit）在无头环境下的执行完整性。
- **`suite_parameter_matrix.py`**: 穷举矩阵测试。在各种模式组合下验证任务生成的正确性。

### 3.2 运行方式
1.  **UI 运行**: 在 Blender N 面板 → Baking → 开启 **Debug Mode** → 点击 **Run Test Suite**。结果将直接显示在面板上。
2.  **CLI 运行**: 使用 `automation/suite_runner.py` 或 `automation/multi_version_test.py` 进行跨版本验证。

### 3.3 跨版本自动化测试 (`automation/`) - **金标准**
- **要求**: 在发布重构（如 `BakeModalOperator` 改动）后，必须运行全量跨版本测试。

## 4. 开发规范与踩坑记录 (Pitfalls)

### 4.1 属性类型安全
*   **EnumProperty**: 当 `items` 参数使用函数回调时，`default` **必须是整数索引**。

### 4.2 统一日志规范
*   **Logger**: 必须使用 `logging.getLogger(__package__)` 获取的 logger。
*   **Error Reporting**: 使用 `core/common.py` 中的 `log_error` 函数，确保错误同时记录到控制台、场景 UI 状态和崩溃恢复日志中。
*   **IDProperty Security**: **严禁**直接将 `bpy.types.ID` (如 Material) 存入 IDProperty (`obj["key"]`)。必须存储 `.name` 并在使用时动态获取，以防无效指针崩溃。
*   **Iterator Safety**: 在使用 `next()` 获取 Active Object 等集合元素时，必须提供默认值 fallback，以防 StopIteration 抛出。

### 4.3 动态对齐与参数一致性 (Dynamic Alignment & Consistency)
为了彻底防范拼写导致的 `AttributeError` 或更新遗漏，系统内严禁过度硬编码。
- **数据流对齐**: `JobPreparer` (验证层) 与 `BakeStepRunner` (执行层) 共享相同的 `BakeJob` 数据结构。
- **常量字典**: 所有的系统临时资源名称（图层、材质等）**必须**使用 `constants.py` 里的 `SYSTEM_NAMES`。
- **i18n 对齐**: `extract_translations.py` 现在会自动扫描 `constants.py` 中的 `UI_MESSAGES`，确保逻辑代码中的提示语与翻译词库动态同步。

### 4.4 材质保护节点 (BT Protection) 与上下文
为了防止 Blender 误用非活动材质的节点，引擎会自动注入保护节点，并通过 `is_bt_temp` 打标。
在为 UDIM 生成新瓦片或强制进行操作时，请利用 `bpy.context.temp_override` 或底层的 `image.tiles.new` 来执行，**严禁**随意篡改或劫持 UI Area 的类型（`area.type = 'IMAGE_EDITOR'`），以防无头模式或复杂 UI 崩溃。

## 5. Iteration Plan & Roadmap

- [x] **Modular Engine (v1.1.0)**: Split `BakePassExecutor` into granular pipeline methods.
- [x] **UI Structural Guard (v1.1.0)**: Automated RNA-based config integrity check.
- [x] **Zero-Side-Effect Quick Bake**: Implemented via Runtime Proxies.
- [x] **Architecture Hardening**: Robust context manager (`ExitStack`), atomic cleanup, and 100% data-driven UI.
- [x] **State Recovery**: JSON-based crash logs with Resume capability.
- [x] **Interactive Preview**: Live viewport feedback for packing results.
- [x] **Exhaustive Matrix Testing**: 100% cross-version coverage (540+ cases).
- [x] **Auto-Cage 2.1**: Refined proximity analysis integration.
- [x] **Public API & CLI**: Decoupled engine for automation.
- [x] **i18n Support**: Full Chinese localization with automated extraction.
- [x] **Modal Execution Layer**: Event-loop decoupled baking with progress tracking.
- [x] **Integrated UI Testing**: Real-time test status in the Blender panel.
- [x] **Security Audit (v1.1.5)**: Fixed IDProperty references, added iterator fallbacks, and multi-version test suite extension.
