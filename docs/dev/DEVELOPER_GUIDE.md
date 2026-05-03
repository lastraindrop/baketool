# BakeNexus 开发者技术指南 / Developer Technical Guide

## 1. 架构核心 (Architecture Core)

BakeNexus 采用 **“配置-验证-执行-还原”** 的四段式架构，确保在复杂的 Blender 环境中保持高度的稳定性。

### 1.1 工作原理 (The Principle)
- **Job 序列化**：用户所有的操作都存储在 `bpy.types.Scene.BakeJobs` 这一自定义集合属性中。
- **状态快照**：执行前，`BakeContextManager` 捕捉当前场景的“快照”（包括 Active Object, Selected Objects, View Layer Settings）。
- **临时环境**：系统会创建一个名为 `BT_INTERNAL_ENV` 的临时层级，用于存放烘焙过程中产生的辅助节点和临时材质，避免污染用户的主材质球。

### 1.2 执行流程 (The Pipeline)
1. **Validation**: 检查对象是否在当前视图层、UV 是否合法、路径是否可写。
2. **Setup**: 根据 Job 配置动态生成烘焙所需的 `Image` 数据块。
3. **Orchestration**: 遍历选中的通道（Channels），为每个通道配置 Cycles 烘焙参数。
4. **Post-Processing**: 执行降噪（Denoise）、通道打包（Packing）或格式转换。
5. **Restoration**: 恢复用户原始的渲染引擎、路径模式和对象可见性。

## 2. 关键技术细节 (Key Implementation Details)

### 2.1 参数一致化与动态对齐 (Parameter Alignment)
过去最常见的错误是 UI 上的属性名与引擎代码中的硬编码键不匹配。为此，我们建立了以下约束：
- **Constants Mapping**: 在 `constants.py` 中定义 `BAKE_PASS_MAP`，所有 UI 的 `type` 枚举必须在该字典中存在对应。
- **Auto-Mirroring**: 引擎通过 `getattr(setting, prop_name)` 动态读取属性，不再手动编写 `if/else`。
- **Integration Tests**: 每次提交均运行 `test_ui_operator_integrity`，确保每个按钮都有对应的后台 Operator 注册。

### 2.2 资源清理机制 (Cleanup Strategy)
- **标记清除**：所有临时产生的图像 `name` 均以 `BT_TEMP_` 开头。
- **引用回收**：`core/cleanup.py` 会在烘焙结束或插件禁用时扫描场景，删除没有用户关联的、带特定前缀的 datablocks。

## 3. 测试与验证策略 (Testing Strategy)

### 3.1 跨版本自动化
我们通过 `automation/multi_version_test.py` 驱动不同版本的 Blender 核心，验证：
- **RNA 路径兼容性**：Blender 4.0+ 的渲染 API 变更适配。
- **导出路径一致性**：不同版本下文件保存路径的权限处理。

### 3.2 负面测试 (Negative Testing)
重点验证以下异常场景：
- 对象被隐藏或锁定。
- 磁盘空间不足或路径只读。
- 材质节点树为空或存在循环引用。
- 在烘焙过程中强制关闭 Blender（通过 `state_manager.py` 实现崩溃记录）。
