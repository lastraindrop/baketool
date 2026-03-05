# Simple Bake Tool 开发者指引 (Developer Guide)

本文件旨在为 Simple Bake Tool 的后续开发提供架构说明、技术规范及已知问题的记录。

## 1. Architecture (v0.9.8)

The project follows a strict **UI-Engine-Core** three-layer decoupling principle:

1.  **UI/Operator Layer** (`ops.py`, `ui.py`): 
    *   **Data-Driven UI** (**v0.9.7**): 通道属性绘制完全由 `constants.py` 中的 `CHANNEL_UI_LAYOUT` 配置驱动。
    *   **UI Dispatch Pattern** (**v0.9.8**): 针对特殊通道的绘制（如 Normal, Combine），使用 `SPECIAL_CHANNEL_DRAWERS` 字典进行逻辑分发，消除了冗长的 `if-elif` 链，符合开闭原则。
    *   **Thin Operators**: Operator 仅作为入口，具体的数据操作（如列表增删改移）已迁移至 Core 层。
2.  **Engine Layer** (`core/engine.py`): The orchestrator.
    *   `JobPreparer`: 验证输入并准备执行队列。支持 Proxy 模式。
    *   `BakeStepRunner`: 核心执行核心。
3.  **Core Layer** (`core/`): 无状态工具模块。
    *   **Standardized Properties** (**v0.9.8**): 核心属性名已统一为 `snake_case`（如 `apply_to_scene`, `use_external_save`），并通过 `PRESET_MIGRATION_MAP` 保持向后兼容。
    *   **Collection Utility**: `core/common.py` 中的 `manage_collection_item` 辅助函数统一处理所有 `CollectionProperty` 的 CRUD 操作。
    *   `compat.py`: 版本兼容层 (3.6 - 5.0+)。

---

## 2. Technical Feature Breakdown

### 2.1 Principled BSDF Analysis
`NodeGraphHandler` 自动识别 Principled BSDF 节点。支持 4.0+ 的插槽更名适配。

### 2.2 NumPy Acceleration
PBR 转换和通道打包使用 NumPy 向量化计算。支持在 8K 分辨率下保持极低 CPU 开销。

### 2.3 Smart Property Migration (**v0.9.7**)
`PropertyIO` 包含一个内置的映射表,当加载旧版本的 `.json` 预设时,会自动将扁平属性映射到新的嵌套设置结构中,确保向后兼容性。

### 2.4 Smart Object Reuse (Post-Bake)
`apply_baked_result` 会检测现有的 `_Baked` 结果物体并执行 `refresh_mesh` 原地更新材质，而非创建重复的 Object 容器。

### 2.5 Select to Active (High-to-Low)
`SELECT_ACTIVE` 工作流由 `JobPreparer` 智能处理。仅验证 Active 物体的 UV,允许高模源物体无需 UV 坐标。

### 2.6 Version Compatibility Layer (**v0.9.6**)
`core/compat.py` 提供统一的版本兼容接口:
- `IS_BLENDER_5`, `IS_BLENDER_4`, `IS_BLENDER_3`: 版本检测标志
- `get_bake_settings(scene)`: 统一访问烘焙设置 (处理 5.0 的 `render.bake` vs 旧版本)
- `configure_bake_settings()`: 一站式配置所有烘焙参数

**优势**: 消除了散布在代码中的 `if bpy.app.version >= (5, 0, 0):` 检查,所有版本差异集中管理。

### 2.7 Modal Execution Layer
`core/execution.py` 提供 `BakeModalOperator` Mixin，处理烘焙时的事件循环、进度汇报和动画序列追踪。支持定时器驱动的步进执行，避免 UI 卡顿。

### 2.8 Emergency Cleanup
`core/cleanup.py` 的 `BAKETOOL_OT_EmergencyCleanup` Operator 用于崩溃后的清理，可清除临时 UV 层、保护节点、BT_TEMP 图像和 ID Map 属性。

---

## 3. Testing Suite
### 3.1 单元测试用例 (`test_cases/`)
- **`test_quick_bake.py`**: 验证代理模式。确保 Quick Bake 运行后 `Scene.BakeJobs` 无任何残留修改。
- **`test_versioning.py`**: 验证 3.6 - 5.0 的属性映射逻辑。
- **`test_core.py`**: 验证核心工具模块（节点图逻辑、UDIM、PBR 转换、UV 管理、清理、Apply Result）。
- **`test_edge_cases.py`**: 边界条件与无效输入处理。
- **`test_logic.py`**: 纯函数单元测试（无 Blender 副作用）。

### 3.2 运行方式
在 Blender N 面板 → Baking → 开启 **Debug Mode** → 点击 **Run Test Suite**。

### 3.3 Headless 命令行测试
```
blender --background --factory-startup --python automation/headless_runner.py
```

### 3.4 跨版本自动化测试 (`automation/`) - **金标准**
- **要求**: 在发布重构（如 `BakeModalOperator` 改动）后，必须运行全量跨版本测试。
- **报告**: 脚本在 `reports/` 目录下生成 ASCII 测试报告。

## 4. 开发规范与踩坑记录 (Pitfalls)

### 4.1 属性类型安全
*   **EnumProperty**: 当 `items` 参数使用函数回调时，`default` **必须是整数索引**。

### 4.2 统一日志规范 (v0.9.8)
*   **Logger**: 禁止使用 `print()` 或裸 `traceback` (代码库中所有 `traceback.print_exc()` 已被替换为 `logger.exception()`)。必须使用 `logging.getLogger(__package__)` 获取的 logger。
*   **Debug Mode**: 全局调试开关会动态调整整个插件包的日志级别。
*   **Error Reporting**: 使用 `core/common.py` 中的 `log_error` 函数，确保错误同时记录到控制台、场景 UI 状态和崩溃恢复日志中。
*   **异常捕获**: 严禁使用裸 `except:`，所有捕获必须指定异常类型（如 `except Exception:`），以避免吞掉 `KeyboardInterrupt` 或 `SystemExit`。

### 4.3 动态对齐与参数一致性 (Dynamic Alignment & Consistency)
为了彻底防范拼写导致的 `AttributeError` 或更新遗漏，系统内严禁过度硬编码，所有跨逻辑共享的参数均需遵循“动态对齐”原则：
*   **属性提取**: 坚决使用结构化的获取模式（例如 `getattr(target, key, default)`）。
*   **数据模型同步**: 对 `BakeJob` 或 `BakeChannel` 等重要模型设定好缺省值，UI、Engine 与 Core 逻辑链应通过引用同一套常量或类型提示签名来确保通道参数的无缝衔接。
*   **异常拦截补偿**: 如果发生动态映射丢失，确保引擎抛出具有追踪价值的结构异常而不是触发底层空指针。

### 4.3 材质保护节点
- **库链接材质**: `NodeGraphHandler` 在注入保护节点前会检查 `mat.library`。如果是链接资产，则自动跳过以防止权限崩溃。

## 5. Iteration Plan & Roadmap

- [x] **Modular Engine**: Unified `BakeStepRunner` pipeline.
- [x] **Zero-Side-Effect Quick Bake**: Implemented via Runtime Proxies.
- [x] **Architecture Hardening (v0.9.8)**: Standardized properties, UI dispatch, unified logging.
- [ ] **Interactive Preview**: Live viewport feedback for packing results.
- [ ] **Auto-Cage 2.0**: Smart proximity-based cage generation.
