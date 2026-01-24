# Simple Bake Tool 开发者指引 (Developer Guide)

本文件旨在为 Simple Bake Tool 的后续开发提供架构说明、技术规范及已知问题的记录。

## 1. Architecture (v0.9.5)

The project follows a strict **UI-Engine-Core** three-layer decoupling principle:

1.  **UI/Operator Layer** (`ops.py`, `ui.py`): 
    *   **BakeModalOperator**: 抽象混合类，统一了模态执行逻辑、进度管理、序列追踪及崩溃日志记录。
    *   **RuntimeProxy**: 为 Quick Bake 提供内存代理，确保实时执行不修改 `Scene` 的持久化预设。
2.  **Engine Layer** (`core/engine.py`): The orchestrator.
    *   `JobPreparer`: 验证输入并准备执行队列。支持 Proxy 模式。
    *   `TaskBuilder`: 将复杂的 Blender 选择抽象为原子烘焙任务。
    *   `BakeStepRunner`: 核心执行核心。管理 `bpy.ops.object.bake` 的迭代执行，并提供实时状态反馈。
3.  **Core Layer** (`core/`): 无状态工具模块（UV, Math, Image, Node）。

---

## 2. Technical Feature Breakdown

### 2.1 Principled BSDF Analysis
`NodeGraphHandler` 自动识别 Principled BSDF 节点。支持 4.0+ 的插槽更名适配。

### 2.2 NumPy Acceleration
PBR 转换和通道打包使用 NumPy 向量化计算。支持在 8K 分辨率下保持极低 CPU 开销。

### 2.3 Smart Object Reuse (Post-Bake)
`apply_baked_result` 会检测现有的 `_Baked` 结果物体并执行 `refresh_mesh` 原地更新材质，而非创建重复的 Object 容器。

### 2.4 Select to Active (High-to-Low)
`SELECT_ACTIVE` 工作流由 `JobPreparer` 智能处理。仅验证 Active 物体的 UV，允许高模源物体无需 UV 坐标。

---

## 3. Testing Suite
### 3.1 单元测试用例 (`test_cases/`)
- **`test_quick_bake.py`**: 验证代理模式。确保 Quick Bake 运行后 `Scene.BakeJobs` 无任何残留修改。
- **`test_versioning.py`**: 验证 3.6 - 5.0 的属性映射逻辑。

### 3.4 跨版本自动化测试 (`automation/`) - **金标准**
- **要求**: 在发布重构（如 `BakeModalOperator` 改动）后，必须运行全量跨版本测试。
- **报告**: 脚本在 `reports/` 目录下生成 ASCII 测试报告。

## 4. 开发规范与踩坑记录 (Pitfalls)

### 4.1 属性类型安全
- **EnumProperty**: 当 `items` 参数使用函数回调时，`default` **必须是整数索引**。若使用静态列表，可直接使用标识符字符串。

### 4.2 材质保护节点
- **库链接材质**: `NodeGraphHandler` 在注入保护节点前会检查 `mat.library`。如果是链接资产，则自动跳过以防止权限崩溃。

## 5. Iteration Plan & Roadmap

- [x] **Modular Engine**: Unified `BakeStepRunner` pipeline.
- [x] **Zero-Side-Effect Quick Bake**: Implemented via Runtime Proxies.
- [x] **Smart Object Reuse**: Reduce scene clutter and memory usage.
- [ ] **Interactive Preview**: Live viewport feedback for packing results.
- [ ] **Auto-Cage 2.0**: Smart proximity-based cage generation.
