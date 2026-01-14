# Simple Bake Tool 开发者指引 (Developer Guide)

本文件旨在为 Simple Bake Tool 的后续开发提供架构说明、技术规范及已知问题的记录。

## 1. 架构概览 (Architecture)
插件遵循数据与逻辑分离的原则，主要分为以下模块：

- **`__init__.py`**: 插件入口，负责类注册、菜单集成、偏好设置定义及应用处理器（Handler）。
- **`property.py`**: 数据模型。所有用户配置（Job, Channel, Object）均存储在 `bpy.types.Scene.BakeJobs` 下。
- **`ops.py`**: 逻辑控制。核心是 `BAKETOOL_OT_BakeOperator`，它通过 `JobPreparer` 生成任务流，并由 `BakePassExecutor` 执行单步操作。
- **`core/`**: 算法与底层。包含图像管理、节点注入、UV 计算等无状态函数。
- **`preset_handler.py`**: 序列化引擎。基于 PropertyGroup 的递归解析实现 JSON 预设的存取。

## 2. 核心逻辑组件

### 2.1 任务系统 (The Queue System)
烘焙任务被拆解为 `BakeStep` 元组。
- `JobPreparer`: 静态校验器。检查 UV、物体的合法性，并将用户的 Job 配置“展平”为一个个具体的执行步骤。
- `BakeTask`: 包含执行该步骤所需的所有上下文（物体、材质、基础文件名）。

### 2.2 上下文保护 (Context Management)
为了保证烘焙不破坏用户的原始工程，我们使用了大量的上下文管理器：
- `BakeContextManager`: 临时修改渲染引擎、采样率、分辨率等全局设置。
- `NodeGraphHandler`: 负责在材质球中临时注入烘焙所需的 Shader 节点，并在 `__exit__` 时撤销修改。
- `UVLayoutManager`: 负责临时的 UDIM 偏移或 Smart UV 自动展开。

## 3. 开发规范与踩坑记录 (Pitfalls)

### 3.1 动态枚举 (Dynamic Enums)
- **规则**: 在 `EnumProperty` 的定义中，如果 `items` 是回调函数，其 `default` 必须是**整数索引**（如 `0`），绝对不能是字符串 ID。
- **示例**: `bake_mode: EnumProperty(items=get_items, default=0)` 是正确的。

### 3.2 节点操作
- **注意**: 向材质树添加节点后，必须将目标 `ShaderNodeTexImage` 设置为 `active` (`tree.nodes.active = tex_node`)，否则 Blender 的烘焙操作符将不知道向哪张图写入数据。

### 3.3 属性忽略
- **注意**: 在 `preset_handler` 中，默认不应忽略 `'name'`。这对于恢复 Job 的 UI 显示至关重要。

### 3.4 快速烘焙 (Quick Bake)
- `BAKETOOL_OT_QuickBake` 是同步执行的。它绕过了 Job 列表，直接捕获 `context.selected_objects`。它旨在提供一键式体验，不应持久化存储物体配置。

## 4. 调试与测试

### 4.1 开启开发者模式
在插件设置中开启 "Debug Mode"，这会降低日志过滤级别并显示测试按钮。

### 4.2 单元测试
测试代码位于 `tests.py`。
- **添加测试**: 如果添加了新功能，请在 `tests.py` 中新增 `TestCase` 类。
- **运行测试**: 使用面板底部的 "Run Test Suite" 按钮。测试涵盖了：
    - 预设序列化逻辑
    - 状态管理（崩溃记录）
    - UDIM 逻辑
    - 任务队列生成
    - 自动加载 Handler 安全性

## 5. 未来计划 (Roadmap)
- **并行烘焙研究**: 探索多 Blender 实例后端烘焙的可能性（绕过 UI 阻塞）。
- **材质库适配**: 增加对非 Principled BSDF（如第三方渲染器节点）的更好兼容性。
- **多通道打包**: 一键生成 RGBA 混合图（如将 AO, Roughness, Metallic 合并到一张图中）。
