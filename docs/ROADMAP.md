# BakeNexus 路线图 / Roadmap

## 1. 当前版本 (v1.0.0) - 稳定发布 ✅
- **核心定位**：从实验性脚本转向工业级稳定的 Blender 插件。
- **完成项**：
  - 全面品牌重塑 (BakeTool -> BakeNexus)。
  - 完善的自动化验证套件（158 测试用例，5 个 Blender 版本 100% 通过）。
  - 支持 UDIM、Selected-to-Active、自定义通道打包、ORM 打包。
  - 修复了渲染参数透传、可见性污染和内存泄露问题。
  - 跨版本测试框架（Blender 3.3 – 5.1）稳定运行，正式 Extension 发布包定位 4.2+。
  - 完整翻译支持（en_US, zh_CN, fr_FR, ja_JP, ru_RU）。
  - 参数动态对齐机制：property.py → constants.py → engine.py 全链路一致性保证。

## 2. 短期计划 (v1.1.x) - 生产力增强
- **AI 辅助功能**：集成简单的 AI 降噪预设建议。
- **UV 优化联动**：烘焙前自动检测 UV 重叠并提供修复建议。
- **预设库扩展**：内置更多行业标准的 PBR 导出预设（UE5, Unity, Substance 风格）。
- **性能监控**：增加烘焙过程中的显存占用预警。
- **参数动态对齐加固**：继续收敛 UI 枚举、RNA 属性、`constants.py` 映射和执行层读取路径；新增动态枚举默认值、通道 UI 属性路径和保存参数传递的专项回归。
- **发布自动化增强**：为 `multi_version_test.py` 增加更清晰的报告归档策略，并在文档中区分正式 Extension 包与源码/Legacy 兼容验证。
- **路径与命名策略**：继续完善输出文件、子目录、UDIM tile 和自定义通道名称的清洗与冲突处理。

## 3. 长期愿景 (v2.x) - 智能烘焙生态
- **跨软件联动**：支持一键导出到外部渲染引擎的着色器配置。
- **云端验证**：支持在远程计算节点执行超大规模场景烘焙。
- **全自动化资产处理**：从原始高模到优化后的 LOD 资产实现一键全流程自动化。
- **数据驱动参数系统**：将通道元数据、UI 布局、保存格式约束和执行参数逐步统一为可校验 schema，减少手写映射分叉。
- **持续跨版本实验室**：建立可重复的 Blender 3.3/3.6/4.2/4.5/5.x 验证矩阵，跟踪动态 RNA、颜色空间、导出 API 和 compositor 行为差异。

---

# 技术原理概要 / Technical Principles

### 1. 非破坏式执行管道 (Non-Destructive Pipeline)
BakeNexus 不直接修改用户的场景数据。在烘焙开始前，`BakeContextManager` 会通过 `common.py` 中的 `safe_context_override` 保存当前视图、选择、渲染设置和节点树状态。在烘焙结束后，无论成功与否，系统都会通过 `finally` 块强制还原状态，确保用户的编辑流程不被打断。

### 2. 动态参数对齐 (Dynamic Parameter Alignment)
为了避免 UI 与引擎逻辑的脱节，我们引入了"单一事实源"机制：
- `property.py` 定义 RNA 属性（用户可调参数）。
- `constants.py` 定义底层引擎所需的映射（`CHANNEL_BAKE_INFO` / `CHANNEL_UI_LAYOUT` / `BAKE_CHANNEL_INFO`）。
- 自动化测试通过 `SuiteCodeReview` 强制验证 UI 标签与内部键的一致性。
- **参数传递路径**：`property.py` → `engine.py`（`_handle_save` / `BakePassExecutor`) → `image_manager.py`（`save_image`) / `core/shading.py`（`apply_baked_result`)。
- **关键一致性保证**：`folder_name` 优先使用 `setting.folder_name`（用户自定义），回退到 `task.folder_name`（自动生成 base name）。
- **动态枚举约束**：`items` 为函数的 `EnumProperty` 使用整数默认值，并通过跨版本 `unit` 与参数矩阵测试保护，避免注册期回归。

### 3. 资源生命周期管理 (Resource Lifecycle)
所有的临时图像和中间节点均带有 `BT_` 前缀。执行引擎在完成后会自动调用清理脚本，根据引用计数和标记识别并移除不再需要的 datablocks，防止 `.blend` 文件体积膨胀。
- `DataLeakChecker` 在测试中监控 `bpy.data` 各类资源计数。
- `assert_no_leak` 上下文管理器确保每次测试后无残留。

### 4. 跨版本兼容性 (Cross-Version Compatibility)
- 正式发布包支持 Blender 4.2+ Extensions；源码/Legacy 自动化验证覆盖 Blender 3.3 – 5.x。
- 动态枚举返回 5 元组以兼容 Blender 4.2+ 的 RNA 变更。
- 测试框架通过 `cli_runner.py` + `multi_version_test.py` 实现完全自动化跨版本验证。
