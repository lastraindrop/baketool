# BakeNexus 路线图 / Roadmap

## 1. 当前版本 (v1.0.0) - 稳定发布 ✅
- **核心定位**：从实验性脚本转向工业级稳定的 Blender 插件。
- **完成项**：
  - 全面品牌重塑 (BakeTool -> BakeNexus)。
  - 完善的自动化验证套件（158 测试用例，12 个 Blender 版本 100% 通过）。
  - 支持 UDIM、Selected-to-Active、自定义通道打包、ORM 打包。
  - 修复了渲染参数透传、可见性污染和内存泄露问题。
  - **Blender 5.0 专项适配**：解决了 Compositor Node API 变更导致的全黑/崩溃问题，并验证了降噪管线。
  - **增强岛屿检测**：`_find_islands_bmesh` 现已支持 Seam 标记与 UV 边界感知分割。
  - 参数动态对齐机制：`property.py` → `constants.py` → `engine.py` 全链路一致性保证。
- **发布前最终修复 (2026-05-13)**：
  - **全量 Code Review**：两轮审查共修复 20 个 CRITICAL/HIGH/MEDIUM 问题。
  - **性能优化**：`evaluated_depsgraph_get()` 移出高模循环（N 次→1 次），大幅提升多重烘焙速度。
  - **降噪安全增强**：注入 `context` 参数替代全局 `bpy.context`，渲染失败时确保临时场景清理。
  - **预览材质可靠性**：新增 `RestorePreviewMaterialsHandler`，崩溃后加载文件自动恢复原始材质。
  - **CI 管道加固**：verify job 解析 JSON 报告阻断失败；lint 失败生效；路径分隔符修复跨平台兼容性。
  - **错误日志治理**：`bake_error_log` 添加 8000 字符滚动窗口，防止场景内存无限膨胀。
  - **上下文物联网**：`core/api.py` 支持可选的 `context` 参数，headless/API 模式安全调用。
  - 更多修复详情见 `CHANGELOG.md` 和 `STYLE_GUIDE_ANALYSIS.md`。

## 2. 已完成代码风格整肃 (2026-05-14) ✅
- **Phase 1 — 自动修复与 import 清理**：196 W293 + 23 W291 + 2 W292 + 10 E111/E117 归零；40 个未使用 import 删除；发现并修复 2 个潜伏 bug (`BAKE_CHANNEL_INFO` 未导入 + `bpy.utils.previews` API 缺失降级)。
- **Phase 2 — 命名规范与多语句**：10 E741 (ambiguous `l`) + 6 E701/E702 归零。
- **Phase 3 — 文档补全**：34 模块 docstring + 关键类/函数 docstring 全部补全。
- **Phase 4 — 类型标注**：公共 API 完整类型化，覆盖率 25% → 30.8%。
- **累计效果**：pycodestyle 385 → 97 (-75%)；5 版本跨版本全部通过。
- 更多细节见 `CHANGELOG.md` 2026-05-14 条目。

## 3. 已完成发布前最终加固 (2026-05-14) ✅
- **异常安全加固**：全项目 18 处 `except Exception` 收紧为具体异常类型，覆盖 `core/engine.py`、`core/execution.py`、`ops.py`、`property.py`、`automation/*.py` 等 9 个文件。
- **全局状态封装**：`__init__.py` 引入 `_RegistryState` 类封装 `classes_to_register`/`addon_keymaps`；`thumbnail_manager.py` 的 `preview_collections` 改为模块私有 `_preview_collections`。
- **上下文管理统一**：`save_image` 和 `bake_node_to_image` 改用 `SceneSettingsContext`，消除手动场景设置恢复。
- **CI 管道修复**：verify job 改用 heredoc 避免 YAML 缩进歧义。
- **类型标注改进**：`api.validate_settings` 返回类型 `Any` → `ValidationResult`；`compat.get_bake_settings` 返回类型 `Optional[Any]` → `object`。
- **命名一致性**：`cleanup.py` operator 前缀统一为 `baketool.`。
- **代码清理**：重复 import 删除、CHANGELOG 格式修复、translations.py 模块 docstring 补全、constants.py license 占位符替换。

## 3. 短期计划 (v1.1.x) - 生产力增强
- **CI 门控优化**：添加 Blender 可执行文件缓存，减少跨版本验证时间；逐步启用 `ruff` 替代 `pycodestyle`。
- **剩余风格债务清理**：继续推进 Phase 5（函数拆分：`BakeStepRunner.run` 129行→拆分）和 Phase 6（CI 集成：`isort` + `ruff`）。
- **类型覆盖率提升**：目标 50%+，重点覆盖 `core/common.py`（`Any` 45+ 处）和 `core/engine.py` 私有方法。
- **预设库扩展**：内置更多行业标准的 PBR 导出预设（UE5, Unity, Substance 风格）。
- **崩溃恢复 Schema 验证**：为 `ui.py` 加载的 JSON 崩溃日志添加 Schema 校验。
- **API 响应性提升**：`core/api.py` 添加异步回调接口，支持外部脚本实时监听烘焙进度。
- **资源利用率优化**：为 `ModelExporter` 的 USD 导出参数添加更严谨的属性存在性检查。

## 4. 长期愿景 (v2.x) - 智能烘焙生态
- **异步像素回传**：研究 B5.0 下的高性能像素拷贝方案。
- **全自动化资产处理**：从原始高模到优化后的 LOD 资产实现一键全流程自动化。
- **数据驱动参数系统**：将通道元数据、UI 布局、保存格式约束和执行参数逐步统一为可校验 schema。
- **完整 Google Python Style 合规**：目标 pycodestyle 违规数降至 15 以下，类型覆盖率 ≥80%。


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
