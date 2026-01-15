# Simple Bake Tool 开发者指引 (Developer Guide)

本文件旨在为 Simple Bake Tool 的后续开发提供架构说明、技术规范及已知问题的记录。

## 1. 架构概览 (Architecture - v0.9.4)

插件遵循 **UI-Engine-Core** 三层解耦原则：

- **表现层 (`ui.py` / `__init__.py`)**: 负责 Blender 菜单、面板绘制。
- **调度层 (`ops.py`)**: 包含 Operator 类。它们仅负责收集 Job，并交由 `BakeStepRunner` 执行。
- **核心引擎层 (`core/engine.py`)**: 
    - **`BakeStepRunner`**: **唯一逻辑入口**。封装了上下文管理、UV 处理、节点注入、NumPy 合成及结果应用。
    - **`BakePassExecutor`**: 负责单次 API 调用及 Blender 5.0 适配。
- **原子功能层 (`core/`)**: 图像管理、UV 分配、节点计算等无状态函数。

## 2. 核心协议与机制

### 2.1 BakeStepRunner (唯一执行闭环)
所有烘焙任务（包括常规任务和 Quick Bake）必须通过 `BakeStepRunner.run()` 执行。它返回一个结果字典列表，由 Operator 决定如何显示给用户。严禁在 Operator 中手动编写 Context 堆栈。

### 2.2 非破坏性配置 (Non-Destructive Sync)
- **`valid_for_mode`**: 位于 `BakeChannel` 中。
- **逻辑**: 当用户切换烘焙类型（如 BSDF -> BASIC）时，不匹配的通道会被隐藏（`valid_for_mode = False`）但**不会被删除**。这确保了用户在不同模式间切换时，自定义的后缀、采样和路径设置得以保留。

### 2.3 Blender 5.0 适配 (Compatibility)
- 5.0 中烘焙设置已从 `RenderSettings` 迁移至 `scene.render.bake` (BakeSettings)。
- 在操作任何烘焙属性前，必须使用 `BakePassExecutor` 提供的兼容性分支，或检查 `bpy.app.version`。

## 3. 测试体系 (Testing System) - **开发必读**

为了保证跨版本稳定性，本项目严禁未经测试的逻辑提交。

### 3.1 单元测试用例 (`test_cases/`)
所有的业务逻辑（命名、任务拆分、NumPy 计算）必须在 `test_cases/` 下有对应的 `test_xxx.py`。
- **`test_performance.py`**: 性能基准测试。用于量化评估 NumPy 算子在不同分辨率下的耗时。
- **`test_shading_complexity.py`**: 压力测试。涵盖非 BSDF 材质、嵌套节点组等极端着色逻辑。
- **`test_complex_geometry.py`**: 网格边缘情况。包含 8 层 UV 限制测试及非法 UV 范围检测。
- **`test_versioning.py`**: 跨版本属性兼容性测试。重点验证 Blender 5.0 的 `BakeSettings` 迁移及 `SceneSettingsContext` 的映射。
- **`test_node_compatibility.py`**: *[New]* 节点系统兼容性测试。验证 4.0+ 及 5.0 下的 ShaderNode 命名与插槽一致性。
- **`test_advanced_workflows.py`**: 高级工作流测试。包含动画序列烘焙、UDIM 重新分配以及色彩空间完整性验证。

### 3.2 数据泄露检测 (Data Leak Prevention)
为了保持插件的轻量性，所有新测试应尽可能使用 `helpers.assert_no_leak` 上下文管理器。该工具已增强，会监控图像、网格、材质、节点组、笔刷、曲线及世界环境等 10 余种数据块，确保所有临时数据已被正确清理。

### 3.3 UI 快速测试 (`tests.py`)
- **入口**: 插件面板底部的 "Run Test Suite" 按钮（需在开发模式下）。
- **注意**: 开发模式下，面板会显示 "Developer Zone"，允许在当前窗口运行全量测试。

### 3.4 跨版本自动化测试 (`automation/`) - **金标准**
在发布新版本或进行重大重构（如 `BakeStepRunner` 改动）后，**必须**运行此体系。
- **运行方式**: 外部终端运行 `python automation/multi_version_test.py`。
- **能力**: 自动调度系统已安装的 3.6 至 5.0 所有 Blender 版本，并在 Headless 模式下运行全量测试。
- **改进**: 脚本现在能更好地处理路径差异，并提供详细的错误堆栈回溯。性能报告会在控制台实时输出。

## 4. 开发规范与踩坑记录 (Pitfalls)

### 4.1 属性类型安全
- **规范**: 从 `PropertyGroup` 获取数值后，参与数学运算前务必显式转换，例如 `int(setting.res_x)`。

### 4.2 材质保护节点
- **机制**: 烘焙期间会向非活跃材质注入 `BT_Protection_Dummy` 贴图节点。
- **清理**: 若发生异常崩溃，用户应运行 `bake.emergency_cleanup`。开发新功能时需确保该操作符能覆盖新的临时数据。

## 5. 迭代计划 (Roadmap)
- [x] **架构统一**: 完成 `BakeStepRunner` 闭环。
- [x] **5.0 适配**: 完成 BakeSettings 迁移。
- [ ] **异步导出**: 优化大规模模型导出时的 UI 响应。
- [ ] **LOD 链式烘焙**: 支持多级简化模型自动烘焙。