# Simple Bake Tool 开发者指引 (Developer Guide)

本文件旨在为 Simple Bake Tool 的后续开发提供架构说明、技术规范及已知问题的记录。

## 1. Architecture (v0.9.5)

The project follows a strict **UI-Engine-Core** three-layer decoupling principle:

1.  **UI/Operator Layer** (`ops.py`, `ui.py`): Defined by properties and UI layout. Minimal logic, delegates execution to the Engine layer.
2.  **Engine Layer** (`core/engine.py`): The orchestrator.
    *   `JobPreparer`: Validates inputs, calculates image resolutions, and prepares the execution queue.
    *   `TaskBuilder`: Abstracts complex Blender object selections into atomic bake tasks.
    *   `BakeStepRunner`: Manages the iterative execution of `bpy.ops.object.bake` within a secured context.
3.  **Core Layer** (`core/`): stateless utility modules for UVs, Math, and Image management.

---

## 2. Technical Feature Breakdown

### 2.1 Principled BSDF Analysis
The `NodeGraphHandler` automatically identifies the Principled BSDF node in materials. It maps physical sockets (Base Color, Metallic, etc.) to bake passes. If no target BSDF is found, it falls back to analyzing the emission output.

### 2.2 NumPy Acceleration
Critical paths like **PBR Conversion** and **Channel Packing** are vectorized using NumPy. This allows BakeTool to process 8K images with minimal CPU overhead.

### 2.3 Select to Active (High-to-Low)
The `SELECT_ACTIVE` workflow is handled intelligently in `JobPreparer`. It only validates UVs on the active target object, allowing high-poly source objects to be UV-less. 
### 3.1 单元测试用例 (`test_cases/`)
所有的业务逻辑（命名、任务拆分、NumPy 计算）必须在 `test_cases/` 下有对应的 `test_xxx.py`。
- **`test_stress_scenarios.py`**: *[New]* 压力测试。验证 100+ 物体、深层材质槽及极限目录深度的导出稳定性。
- **`test_ui_poll.py`**: *[New]* UI 上下文测试。验证 Operator 的 `poll()` 逻辑在不同场景下的正确性。
...
### 3.5 测试辅助工具 (`helpers.py`)
- **`JobBuilder`**: *[New]* 链式辅助类。推荐在编写新测试时使用它来快速构建 Job 场景。
    ```python
    job = JobBuilder("MyTest").mode('UDIM').resolution(2048).add_objects(objs).build()
    ```



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

## 5. Iteration Plan & Roadmap

Our development is now moving from "Refactoring" to "Feature Expansion".

- [x] **Modular Engine**: Unified `BakeStepRunner` pipeline.
- [x] **Cross-Version Suite**: Headless automation for Blender 3.6 - 5.0.
- [ ] **Interactive Preview**: Live viewport feedback for packing results.
- [ ] **Auto-Cage 2.0**: Smart proximity-based cage generation.

For the full architectural vision, see the [Roadmap](ROADMAP.md).