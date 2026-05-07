# BakeNexus 开发者技术指南 / Developer Technical Guide

## 1. 架构核心 (Architecture Core)

BakeNexus 采用 **"配置-验证-执行-还原"** 的四段式架构，确保在复杂的 Blender 环境中保持高度的稳定性。

### 1.1 工作原理 (The Principle)
- **Job 序列化**：用户所有的操作都存储在 `bpy.types.Scene.BakeJobs` 这一自定义集合属性中。
- **状态快照**：执行前，`BakeContextManager` 捕捉当前场景的"快照"（包括 Active Object, Selected Objects, View Layer Settings）。
- **临时环境**：系统通过 `NodeGraphHandler`、`UVLayoutManager`、`BakeContextManager` 和 `BT_` 前缀的临时 datablock 管理烘焙环境，避免污染用户材质、UV 和场景状态。

### 1.2 执行流程 (The Pipeline)
1. **Validation**: 检查对象是否在当前视图层、UV 是否合法、路径是否可写。
2. **Setup**: 根据 Job 配置动态生成烘焙所需的 `Image` 数据块。
3. **Orchestration**: 遍历选中的通道（Channels），为每个通道配置 Cycles 烘焙参数。
4. **Post-Processing**: 执行降噪（Denoise）、通道打包（Packing）或格式转换。
5. **Restoration**: 恢复用户原始的渲染引擎、路径模式和对象可见性。

### 1.3 BakeContextManager 原子上下文 (Atomic Context Manager)
`BakeContextManager` (`core/engine.py:938`) 负责在烘焙期间临时修改渲染引擎、采样数、输出格式、色彩空间等多组场景设置，结束后必须完整还原。采用 `ExitStack.pop_all()` 原子模式避免部分失败导致的场景泄露：

```python
# engine.py:6 — module-level import, 避免 __enter__ 内的 NameError
from contextlib import ExitStack

def __enter__(self):
    scene = self.context.scene if self.context else bpy.context.scene
    with ExitStack() as stack:
        for ctx_type, params in self.configs:
            ctx = SceneSettingsContext(ctx_type, params, scene=scene)
            stack.enter_context(ctx)
        self._stack = stack.pop_all()
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    self._stack.__exit__(exc_type, exc_val, exc_tb)
    return False
```

关键要点：
- `pop_all()` 将内部栈的所有回调转移到 `self._stack`，此时内部栈的 `__exit__` 不会触发任何清理——只有成功进入全部上下文后才保留状态。
- 若任意一个 `SceneSettingsContext` 的 `__enter__` 抛出异常，外层 `with ExitStack()` 自动清理已进入的上下文，不会留下半截状态。
- `ExitStack` 必须在模块级别导入（不能局部 `from contextlib import ExitStack`），否则 `__enter__` 被调用时可能触发 `NameError`。

### 1.4 临时节点隔离 (Temporary Node Isolation)
`NodeGraphHandler` (`core/node_manager.py`) 在烘焙时为材质动态创建 Texture 和 Emission 节点用于生成烘焙纹理，烘焙完成后必须精确移除这些临时节点，不得误删或残留。采用 `is_bt_temp` 自定义属性标记所有临时节点：

- 会话节点（`_prepare_session_nodes`, line 164-165）：为每个材质创建的基础 `ShaderNodeTexImage` 和 `ShaderNodeEmission` 均标记 `n["is_bt_temp"] = True`。
- 逻辑节点（`_add_temp_node`, line 371）：每次通过辅助方法创建的临时节点同样标记。
- 源查找过滤（`_find_socket_source`, line 404-410）：在寻找用户材质中已有的 `ShaderNodeEmission` 作为烘焙来源时，显式排除 `is_bt_temp` 标记的会话节点，防止新的临时节点被误判为用户材质节点从而导致黑图输出。

此标记机制与 `cleanup()` 中的 `BT_TEMP_` 前缀 datablock 扫描形成双层隔离：节点层面通过自定义属性过滤，数据块层面通过命名前缀回收。

## 2. 关键技术细节 (Key Implementation Details)

### 2.1 参数一致化与动态对齐 (Parameter Alignment)
过去最常见的错误是 UI 上的属性名与引擎代码中的硬编码键不匹配。为此，我们建立了以下约束：
- **Constants Mapping**: 在 `constants.py` 中维护 `CHANNEL_BAKE_INFO`、`CHANNEL_UI_LAYOUT`、`BAKE_CHANNEL_INFO`、`FORMAT_SETTINGS` 等映射，避免 UI、属性和执行层各自硬编码。
- **Auto-Mirroring**: UI 通过 `CHANNEL_UI_LAYOUT` 解析属性路径，执行层通过 `BakePassExecutor`、`_handle_save()` 和 `image_manager.save_image()` 消费同一组 RNA 属性。
- **Dynamic Enum Rule**: Blender 对 `items` 为函数的 `EnumProperty` 有特殊要求，动态枚举默认值必须保持整数形式；静态枚举才使用字符串 identifier 默认值。
- **Integration Tests**: 每次提交均运行 `test_ui_operator_integrity`、`test_property_group_integrity`、`test_dynamic_enum_returns_5tuple` 和 `suite_code_review`，确保 UI、RNA、动态枚举和执行映射保持一致。

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

### 3.3 发布前最低验证组合

正式发布前至少保留以下组合：

- 单版本全量：`blender -b --factory-startup --python automation/cli_runner.py -- --discover`
- 跨版本核心：`python automation/multi_version_test.py --suite unit`
- 跨版本综合：`python automation/multi_version_test.py --verification`
- 发布扩展：`extension_validation`、`code_review`、`localization`

若变更触及保存路径、UDIM、Selected-to-Active、动态枚举、打包规则或 UI 映射，必须补跑对应专项套件，而不是只依赖单一 happy path。
