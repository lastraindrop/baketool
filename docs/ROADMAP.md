# BakeNexus 路线图 / Roadmap

## 1. 当前版本 (v1.0.0) - 稳定发布 ✅
- **核心定位**：从实验性脚本转向工业级稳定的 Blender 插件。
- **完成项**：
  - 全面品牌重塑 (BakeTool -> BakeNexus)。
  - 完善的自动化验证套件（158 测试用例，5 个 Blender 版本 100% 通过）。
  - 支持 UDIM、Selected-to-Active、自定义通道打包、ORM 打包。
  - 修复了渲染参数透传、可见性污染和内存泄露问题。
  - **Blender 5.0 专项适配**：解决了 Compositor Node API 变更导致的全黑/崩溃问题，并验证了降噪管线。
  - **增强岛屿检测**：`_find_islands_bmesh` 现已支持 Seam 标记与 UV 边界感知分割。
  - 参数动态对齐机制：`property.py` → `constants.py` → `engine.py` 全链路一致性保证。
- **发布前最终修复 (2026-05-09)**：
  - **统一分发策略**：`automation/build_release_zip.py` 现已包含 `dev_tools` 目录。
  - **B5.0 烘焙类型修复**：修正了 `compat.py` 中过时的 `NORMALS` 强制映射，恢复使用 `NORMAL`。
  - **Compositor 原子性**：优化了合成器树的初始化与清理流程，防止背景任务场景残留。

## 2. 短期计划 (v1.1.x) - 生产力增强
- **USD 属性安全审计**：为 `ModelExporter` 的 USD 导出参数添加更严谨的属性存在性检查（替代 `hasattr`）。
- **崩溃恢复 Schema 验证**：为 `ui.py` 加载的 JSON 崩溃日志添加 Schema 校验，防止因旧版本日志损坏导致启动崩溃。
- **CI 门控优化**：实现对多版本测试报告的自动解析汇总。
- **预设库扩展**：内置更多行业标准的 PBR 导出预设（UE5, Unity, Substance 风格）。

## 3. 长期愿景 (v2.x) - 智能烘焙生态
- **异步像素回传**：研究 B5.0 下的高性能像素拷贝方案。
- **全自动化资产处理**：从原始高模到优化后的 LOD 资产实现一键全流程自动化。
- **数据驱动参数系统**：将通道元数据、UI 布局、保存格式约束和执行参数逐步统一为可校验 schema。


---

# 技术原理概要 / Technical Principles

### 1. 非破坏式执行管道 (Non-Destructive Pipeline)
BakeNexus 不直接修改用户的场景数据。在烘焙开始前，`BakeContextManager` 会通过 `common.py` 中的 `SceneSettingsContext` 保存当前渲染引擎、采样数、图像格式和色彩管理设置。`BakeContextManager` 使用 `ExitStack.pop_all()` 模式确保即使某个 `SceneSettingsContext` 进入失败，已进入的上下文仍能被正确还原。`safe_context_override` 负责保存和恢复视图、选择和对象上下文。

### 2. 临时节点隔离 (Temporary Node Isolation)
`NodeGraphHandler` 在 `_prepare_session_nodes()` 中创建的所有临时节点均标记 `is_bt_temp = True`。`_find_socket_source` 在搜索用户材质节点时会过滤这些标记，避免会话临时节点被误认为用户源数据。清理阶段通过 `is_bt_temp` 标记批量识别和移除临时节点。

### 3. 动态参数对齐 (Dynamic Parameter Alignment)
为了避免 UI 与引擎逻辑的脱节，我们引入了"单一事实源"机制：
- `property.py` 定义 RNA 属性（用户可调参数）。
- `constants.py` 定义底层引擎所需的映射（`CHANNEL_BAKE_INFO` / `CHANNEL_UI_LAYOUT` / `BAKE_CHANNEL_INFO`）。
- 自动化测试通过 `SuiteCodeReview` 强制验证 UI 标签与内部键的一致性。
- **参数传递路径**：`property.py` → `engine.py`（`_handle_save` / `BakePassExecutor`) → `image_manager.py`（`save_image`) / `core/shading.py`（`apply_baked_result`)。
- **关键一致性保证**：`folder_name` 优先使用 `setting.folder_name`（用户自定义），回退到 `task.folder_name`（自动生成 base name）。
- **动态枚举约束**：`items` 为函数的 `EnumProperty` 使用整数默认值，并通过跨版本 `unit` 与参数矩阵测试保护，避免注册期回归。

### 4. 资源生命周期管理 (Resource Lifecycle)
所有的临时图像和中间节点均带有 `BT_` 前缀或 `is_bt_temp` 标记。执行引擎在完成后会自动调用清理脚本，根据引用计数和标记识别并移除不再需要的 datablocks，防止 `.blend` 文件体积膨胀。
- `DataLeakChecker` 在测试中监控 `bpy.data` 各类资源计数。
- `assert_no_leak` 上下文管理器确保每次测试后无残留。

### 5. 跨版本兼容性 (Cross-Version Compatibility)
- 正式发布包支持 Blender 4.2+ Extensions；源码/Legacy 自动化验证覆盖 Blender 3.3 – 5.x。
- 动态枚举返回 5 元组以兼容 Blender 4.2+ 的 RNA 变更。
- 测试框架通过 `cli_runner.py` + `multi_version_test.py` 实现完全自动化跨版本验证。
