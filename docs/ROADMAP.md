# BakeNexus 路线图 / Roadmap

## 1. 当前版本 (v1.0.0) - 稳定发布 ✅
- **核心定位**：从实验性脚本转向工业级稳定的 Blender 插件。
- **完成项**：
  - 全面品牌重塑 (BakeTool -> BakeNexus：bl_idname、文档、Manifest、README 已完成)。
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
- **外部审计修复与收尾 (2026-08-17)**：
  - **4 个阻断级缺陷修复**：扩展 ID 统一为 `baketool`（B-01）；中文翻译 locale 迁移 `zh_HANS` 并保留 `zh_CN` 运行时别名（B-02）；移除 5 个无引擎实现的 Mesh 通道与 `height` 孤岛数据（B-03）；发布包补齐 `dev_tools/` 使随包 Safety Audit 可用（B-04）。
  - **防护性测试固化**：新增 `test_channel_pipeline_alignment`（通道必须可达引擎）、`test_manifest_id_matches_addon_directory`（扩展 ID == 打包目录名）、`test_release_zip_includes_audit_dependencies`（打包内容完整性），把本轮教训转化为 161 项测试的常驻闸门。
  - **多实例安全**：崩溃会话文件按 PID 隔离 + glob 检测，并行 Blender 互不干扰（H-03）；`Clean Up Bake Junk` 补 UI 入口（H-04）。
  - **词典治理**：翻译死键清理 + 新键补齐（468 词条、0 空值），维护流程统一走 `dev_tools/extract_translations.py --sync`。
  - **验证**：5 版本（3.3.21/3.6.23/4.2.14/4.5.3/5.0.1）161 项测试 0 失败 0 错误；发布 ZIP 结构（根目录==id、dev_tools 随包、无泄漏）全项通过。

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

## 4. 已完成发布前审计与测试优化 (2026-06-06) ✅
- **Phase 6 — 关键缺陷修复**：C-1 至 C-4 全部修复（UNDO 支持、Draw 性能、Headless 安全、图像泄漏），H-1/H-8/H-9 全部修复（属性边界、CI 路径、构建打包）。
- **Phase 7 — 基础设施修复**：CI BLENDER_DIR 精确定位、跨版本测试环境变量支持、state_manager 临时目录容错、headless_bake 路径安全验证。
- **Phase 8 — 代码质量强化**：异常处理从静默改为 logger.warning、register/unregister 添加 try/except、Handler 注册独立错误处理、属性完整性补充。
- **Phase 9 — 测试套件优化**：去重 1 个重复测试、MockSetting 新增 27 个属性、category_map 覆盖全部 22 个 suite、新增 COMBINE_OBJECT E2E 测试。
- **验证结果**：158/158 测试通过（Blender 4.2.14）、全部 16 个修改文件 lsp_diagnostics 通过、5/5 BAKE_MODES 全覆盖。
- 更多细节见 `CHANGELOG.md` 2026-06-06 条目。

## 5. 已完成最终审查与收尾 (2026-06-15) ✅
- **全维度代码审查**：6 维度审计（架构/代码质量/Blender API/测试/安全/发布配置），无阻断性缺陷，详见 `docs/PRE_RELEASE_REVIEW.md`。
- **代码加固**：`node_manager.py` 合并重复异常块；`state_manager.py` 引入内存缓存，消除 `update_step()` 的重复磁盘读取。
- **文档同步**：`TECHNICAL_GUIDE.md` 补充崩溃恢复与状态缓存章节，修复章节编号；`build_release_zip.py` 收录技术指南。
- **打包验证**：`py_compile` 全项目通过（0 错误），`build_release_zip.py` 成功生成 `dist/bakenexus-1.0.0.zip`（63 文件）。
- **路线图调整**：`engine.py` 拆分推迟至 v1.1，发布前夕优先保持代码稳定。

## 6. 已完成发布前最终清理与 DRY 重构 (2026-07-02) ✅
- **死代码清理**：删除 12 个零引用常量（JOB_TYPES, ATLAS_PACK_METHODS, DENOISE_METHODS 等）、7 个未用导入（types/persistent/traceback/os/json）、死属性 `use_antialiasing`、冲突死文档 `MANIFEST.in`——净删除 ~60 行。
- **UX 修复**：ops.py 全部 9 处静默 CANCELLED 返回添加 `self.report()`，用户操作无响应问题修复。
- **DRY 重构 — get_active_job()**：`core/common.py` 新增辅助函数，消除 ops/ui/property/common 之间 12 处重复的索引钳制模式，同时修正了缺少空 Job 集检查的潜在 IndexError。
- **DRY 重构 — 双重事实源消除**：`constants.py` 新增 `EXTENSION_TO_FORMAT` 自动映射（从 FORMAT_SETTINGS 计算），删除 `ops.py` 的 `_get_format_from_path` 硬编码副本。
- **DRY 重构 — 预览路径统一**：TogglePreview.execute 简化为仅翻转标志，`update_preview` RNA 回调成为预览应用/移除/redraw 的唯一执行路径。
- **DRY 重构 — tag_redraw_view3d()**：ops/ui/property 之间 3 处重复的 View3D redraw 循环统一为单函数。
- **魔法字符串集中化**：`BT_Denoise_Temp`、`BT_Denoise_Camera`、`BT_Packing_Preview` 纳入 `SYSTEM_NAMES`。
- **品牌文档修正**：task.md 和 ROADMAP.md 更正品牌残留表述为如实描述。
- **验证**：22/22 运行时源文件 py_compile 全过，0 lsp error。

## 7. 短期计划 (v1.1.x) - 生产力增强
- **通道实装补齐（2026-08-16 外部审计立项，最高优先）**：v1.0.0 从 `BAKE_CHANNEL_INFO["MESH"]` 移除了 `Vertex Color / Curvature / Slope / Thickness / Select` 五个无引擎实现的通道（静默产出黑图）以及不可达的 `height` 元数据；v1.1 需为其补齐真实生成路径（节点逻辑或 BMesh 分析）后重新挂出。`mesh_settings` 的 `contrast/direction/invert` RNA 字段已按 v1.1 预留（`property.py` 有注释保护），重实装无需预设迁移。实施时必须走 `TECHNICAL_GUIDE.md` §5.4.5 检查单——`test_channel_pipeline_alignment` 会强制引擎路径同步落地。
- **Normal 轴向分量决策**：`BakeNormalSettings` 的 X/Y/Z 分量属性与预设迁移映射仍在，但引擎从未读取（`normal_r/g/b` 参数未传入 bake operator）。v1.1 决定实装（含 CUSTOM 模式）或删除属性，不允许继续处于"可保存、不生效"状态。
- **崩溃记录归属细化**：会话文件已按 PID 隔离，但恢复 UI 只展示最新记录；结合 blend 文件名哈希区分"本场景的崩溃"与"其他场景的崩溃"，避免误报。
- **架构拆分（CM.1，后续）**：在 `core/bake_types.py` 共享 `BakeStep` / `BakeTask` 契约的前提下，将 `core/engine.py` 的 `ModelExporter` 提取至 `exporter.py`，并将 `TaskBuilder` / `JobPreparer` 提取至 `job_prep.py`；`engine.py` 保持 facade 重导出，避免破坏现有 API。
- **i18n 全量覆盖**：`ops.py` self.report 与 `ui.py` 面板标签走 `pgettext` 或 `UI_MESSAGES`。
- **继续 DRY 清理**：`draw_collapsible_header()` UI 辅助函数（4 处重复）、`report_cancel` 装饰器（26 处重复模式）。
- **剩余风格债务清理**：继续推进 Phase 5（函数拆分）和 Phase 6（CI 集成：`isort` + `ruff`）。
- **类型覆盖率提升**：目标 50%+，重点覆盖 `core/common.py` 和 `core/engine.py`。

### 7.1 维护前置完成项 (2026-07-12)
- `core/bake_types.py` 已承载 `BakeStep` / `BakeTask`；在提取 `TaskBuilder` / `JobPreparer` 前必须继续以此为共享契约，禁止让 `job_prep.py` 回导 `engine.py`。
- `core/udim_utils.py` 已成为主要 UDIM tile 检测的叶模块；`common.py` 不得重新依赖 `uv_manager.py`。
- `UVLayoutManager` 接受可选 context，调用者应优先传入显式 context，同时保留后台/交互模式的 `bpy.context` 回退。
- 本轮已完成跨版本 `unit` 矩阵：Blender 3.3.21、3.6.23、4.2.14、4.5.3、5.0.1 共 5/5 通过；并在 4.2 通过 `verification`、注册循环和 facade 导入检查，在 5.0 通过 `production_workflow` 10/10。

## 8. 长期愿景 (v2.x) - 智能烘焙生态
- **异步像素回传**：研究 B5.0 下的高性能像素拷贝方案。
- **全自动化资产处理**：从原始高模到优化后的 LOD 资产实现一键全流程自动化。
- **数据驱动参数系统**：将通道元数据、UI 布局、保存格式约束和执行参数逐步统一为可校验 schema。v1.0.0 的 `test_channel_pipeline_alignment` 是该方向的第一个机器化子集（通道层已达声明-引擎双向可校验），后续把保存格式与导出参数纳入同一 schema 体系。
- **完整 Google Python Style 合规**：目标 pycodestyle 违规数降至 15 以下，类型覆盖率 ≥80%。
- **声明式通道定义**：把 `TECHNICAL_GUIDE.md` §5.4.5 的"新增通道强制检查单"进一步压缩为单处声明——开发者只写一份通道定义（含引擎路径引用），①②③④四层由代码生成，从根上消灭多层失配的可能。


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
