# 更新日志 /Changelog

本文件记录 BakeNexus 在正式发布前的主要版本变化。/This file records major version changes before official release.

## Unreleased
### 架构一致性、运行时安全与文档同步 / Architecture Consistency, Runtime Safety & Documentation
- **执行安全**：modal 烘焙队列长度变化转为受控错误；cage 视口切换失败时恢复选择状态；补齐 Quick Bake、Reset 与导出预检的用户反馈。
- **依赖边界**：新增 `core/bake_types.py` 承载 `BakeStep` / `BakeTask`；新增 `core/udim_utils.py` 作为 UDIM 检测叶模块，消除 `common.py` 对 `uv_manager.py` 的反向依赖。
- **职责分离**：将 `apply_baked_result` 与 `create_simple_baked_material` 从 `core/common.py` 移至 `core/shading.py`；旧导入路径保留 facade 重导出，避免破坏外部脚本。
- **DRY/KISS**：合并重复的 Light Path / ID 通道 UI 配置；统一活动 Job 报告守卫；移除预览代码中的对话式注释和闭包内重复常量。
- **验证**：跨 Blender 3.3.21、3.6.23、4.2.14、4.5.3、5.0.1 的 `unit` 矩阵 5/5 通过；4.2 的 `verification`、注册循环与公开 facade 检查通过；5.0 的 `production_workflow` 10/10 通过。
- **文档与发布**：同步技术、开发、自动化、生态、标准化、路线图、任务板和发布清单；构建脚本生成 65 文件发布 ZIP 并确认包含新核心模块。

## 1.0.0 - 2026-07-02
### 发布前最终清理与 DRY 重构 / Pre-release Final Cleanup & DRY Refactoring

#### 死代码与死导入清理 / Dead Code Removal
- **constants.py**：删除 12 个零引用常量（JOB_TYPES, ATLAS_PACK_METHODS, DENOISE_METHODS, DEFAULT_BAKE_TARGET, API_VERSION, SYSTEM_ID, UDIM_DEFAULT_TILE, UDIM_TILE_RANGE, GOLDEN_RATIO, MIN_THRESHOLD, DEFAULT_SMART_UV_ANGLE, DEFAULT_SMART_UV_MARGIN）。
- **property.py**：删除 `use_antialiasing` 死属性（声明但烘焙管线从未读取）。
- **死导入清理**：__init__.py（types, persistent, bpy.props.*, CHANNEL_BAKE_INFO）、ops.py（traceback）、ui.py（os, json）——共计 7 个未用导入删除。
- **MANIFEST.in**：删除——与 build_release_zip.py 冲突的死文档，打包已有独立的显式文件列表。

#### UX 修复 / UX Fixes
- **ops.py 静默 CANCELLED 修复**：全部 9 处无 `self.report()` 的 `return {"CANCELLED"}` 添加用户反馈（SetSaveLocal, RefreshUDIMLocations, TogglePreview, AnalyzeCage ×2, OneClickPBR, ManageObjects, SaveSetting, LoadSetting）。

#### DRY 重构 / DRY Refactoring
- **`get_active_job()` 辅助函数**（`core/common.py`）：消除 ops.py/ui.py/property.py/common.py 之间 12 处重复的 BakeJob 索引钳制模式，同时修正了缺少空 Job 集检查的潜在 IndexError。
- **`tag_redraw_view3d()` 辅助函数**（`core/common.py`）：消除 ops.py/property.py 之间 3 处重复的 View3D area redraw 循环。
- **`EXTENSION_TO_FORMAT` 映射**（`constants.py`）：从 FORMAT_SETTINGS 自动计算，消除 `ops.py` 的 `_get_format_from_path` 双重事实源。
- **预览路径统一**：TogglePreview.execute 简化为仅翻转标志，`update_preview` RNA 回调成为预览应用/移除/redraw 的唯一执行路径。
- **魔法字符串集中化**：`BT_Denoise_Temp/camera`、`BT_Packing_Preview` 纳入 `SYSTEM_NAMES`。

#### 文档修正 / Documentation Fixes
- **task.md / ROADMAP.md**：更正"BakeTool 残留为 0"为如实描述（bl_idname 已统一，类名保留 BAKETOOL 前缀）。
- **ROADMAP.md / task.md**：新增 Phase 10-14 完成记录。

## 1.0.0 - 2026-06-15
### 发布前最终审查、加固与收尾 / Pre-release Final Review, Hardening & Wrap-up

#### 审查与报告 / Review & Report
- **全维度代码审查**：架构、代码质量、Blender API、测试覆盖、安全性、发布配置 6 个维度全面审计，无阻断性缺陷。
- **审查报告**：`docs/PRE_RELEASE_REVIEW.md` 记录完整审查结果与 8 项人工验证清单。

#### 代码质量加固 / Code Quality Hardening
- **重复异常合并**：`core/node_manager.py` 中 `bake_node_to_image()` 两个连续 except 块（`AttributeError/KeyError/ReferenceError` 与 `RuntimeError`）合并为单一块，消除冗余代码。
- **I/O 性能优化**：`state_manager.py` 中 `BakeStateManager` 引入 `_cached_data` 内存缓存机制，`update_step()` 不再每次从磁盘读取 JSON，大批量烘焙时显著减少磁盘 I/O。
- **finish_session/clear_state**：增加 `_cached_data = None` 重置，确保缓存生命周期与磁盘状态同步。

#### 发布打包完善 / Release Packaging
- **文档完整**：`build_release_zip.py` 的 DOC_FILES 添加 `docs/dev/TECHNICAL_GUIDE.md`，确保技术指南随发布包分发。

#### 一致性验证 / Consistency Verification
- **全项目 py_compile**：所有源文件通过 Python 语法编译检查（0 错误）。
- **打包验证**：`build_release_zip.py` 成功生成 `dist/bakenexus-1.0.0.zip`（63 文件）。

#### 文档同步 / Documentation Sync
- **CHANGELOG**：补充 2026-06-15 发布前收尾记录。
- **ROADMAP**：将 engine.py 拆分推迟至 v1.1，更新短期计划反映当前状态。
- **TECHNICAL_GUIDE**：新增崩溃恢复与状态缓存章节，修复章节编号跳空与重复问题。
- **PRE_RELEASE_REVIEW**：新增完整发布前审查报告文档。

## 1.0.0 - 2026-06-06
### 发布前最终审计与加固 / Pre-release Final Audit & Hardening

#### Phase 6: 关键缺陷修复 / Critical Bug Fixes
- **UNDO 支持 (C-1)**：为 12 个修改场景的 Operator 添加 `bl_options = {"REGISTER", "UNDO"}`，6 个文件/导出/只读操作保持不加。
- **Draw 性能 (C-2)**：将 `draw_env_status()` 中每帧 `os.path.exists()` 移出到 `update_save_path_validity` 属性回调，消除 UI 绘制中的文件 I/O。
- **Headless 安全 (C-3)**：为 `preset_handler.py` 中 `load_default_preset()` 和 `update_crash_cache()` 添加 `bpy.context` 空值守卫。
- **图像泄漏 (C-4)**：`bake_node_to_image` 烘焙失败时自动清理已创建的 Image datablock。
- **属性边界 (H-1)**：`quality` 添加 min=0/max=100；`res_x/res_y` min 降至 1；`radius`/`distance`/`id_count` 添加 min 边界；7 个 `bake_motion_*` 属性添加 min/max 约束。

#### Phase 7: 基础设施修复 / Infrastructure Fixes
- **CI 路径 (H-8)**：`test.yml` 中 BLENDER_DIR 使用 `find` 精确定位 Blender 二进制文件。
- **构建打包 (H-9)**：`build_release_zip.py` 的 AUTOMATION_FILES 添加 `multi_version_test.py`。
- **跨版本测试**：`multi_version_test.py` 添加 `BAKE_TOOL_BLENDER_PATHS` 环境变量支持。
- **临时目录容错**：`state_manager.py` 中 `bpy.app.tempdir` 为空时回退至 `$TEMP` 或 `/tmp`。
- **路径安全**：`headless_bake.py` 中 `sys.path` 修改前添加 `os.path.isdir()` 验证。

#### Phase 8: 代码质量强化 / Code Quality Hardening
- **异常处理**：`DeleteResult`/`DeleteAllResults` 静默异常改为 logger.warning。
- **注册/注销安全**：`__init__.py` 中 `register()`/`unregister()` 循环添加 try/except。
- **Handler 注册**：AutoLoadHandler/UpdateCrashCacheHandler/RestorePreviewMaterialsHandler 注册添加独立错误处理。
- **属性完整性**：`BakedImageResult.filepath` 添加 `subtype="FILE_PATH"`。
- **代码风格**：`ui.py` 中 `import json` 从函数内部提升至模块顶层。

#### Phase 9: 测试套件优化 / Test Suite Optimization
- **去重**：移除 `suite_negative.py` 中与 `suite_unit.py` 重复的 `test_context_manager_exception_restores_state`。
- **MockSetting 对齐**：添加 27 个新属性（udim_mode、auto_cage_mode、extrusion、texel_density、use_*_map、name_setting 等），与 UI 引用的属性保持一致。
- **category_map 完善**：`cli_runner.py` 的 `_load_category` 覆盖全部 22 个 suite。
- **新增 COMBINE_OBJECT E2E 测试**：`suite_production_workflow.py` 添加 `test_combine_objects_2_objs_e2e`，补齐唯一未测试的架构模式。

#### 验证结果 / Verification
- **158/158 测试通过**（Blender 4.2.14，0 失败）。
- 全部 16 个修改文件的 `lsp_diagnostics` 通过。
- 5/5 BAKE_MODES 全覆盖，MockSetting 缺口缩减 43%。

---

## 1.0.0 - 2026-05-14
### 正式发布前代码风格系统整肃 / Pre-release Code Style Overhaul

#### Phase 1: 自动修复与 import 清理 / Automated Cleanup & Import Sanitation
- **空白字符批量清除**：修复 196 处空白行空格 (W293)、23 处行末空格 (W291)、2 处缺失 EOF 换行 (W292)、10 处缩进错误 (E111/E117)。
- **40 个未使用 import 删除**：涵盖全部生产代码 (`ops.py`、`core/*.py`、`automation/*.py`) 和测试代码。
- **发现并修复两个潜伏 Bug**：`core/common.py` 中 `reset_channels_logic` 依赖未导入的 `BAKE_CHANNEL_INFO`；`core/thumbnail_manager.py` 中 Blender 4.2+ 已移除的 `bpy.utils.previews` API 增加降级守卫。

#### Phase 2: 命名规范与多语句修复 / Naming & Multi-Statement Fixes
- **E741 (ambiguous `l` 变量) 全清除**：`ui.py` 中 5 处 `l = self.layout` → `layout`；`node_manager.py` `l` → `link`；`suite_api.py` `l` → `loop`；`suite_code_review.py` `l` → `line`；`suite_memory.py` `l` → `entry`。
- **E701/E702 全清除**：`headless_bake.py`、`suite_api.py`、`suite_parameter_matrix.py`、`suite_verification.py` 中的 6 处单行多语句拆分为多行。

#### Phase 3: 文档补全 / Documentation Completion
- **34 个模块 docstring 全部补全**：覆盖 `core/*.py`、`automation/*.py`、`dev_tools/*.py`、`test_cases/suite_*.py` 和 `property.py`/`preset_handler.py` 等关键文件。
- **关键类/函数 docstring 补全**：`BakeJobs`、`BakeJobSetting`、`TranslationExtractor`、`build_release_zip.py` 全部函数、`multi_version_test.py` 核心函数、`BakeModalOperator`、`BakePassExecutor` 等。

#### Phase 4: 类型标注强化 / Type Annotation Hardening
- **公共 API 完整类型化**：`core/api.py`（`bake`、`get_udim_tiles`、`validate_settings`）、`core/execution.py`（`add_bake_result_to_ui`、`BakeModalOperator` 全部方法）。
- **所有 Operator `execute()`/`invoke()` 返回类型验证**：全部已标注 `-> Set[str]`。
- 类型覆盖率从 25% → 30.8%。

#### 累计效果 / Cumulative Impact
- pycodestyle 违规总数从 385 降至 97（-75%）。
- bare `except` 子句清零（17→0）。
- 全部 4 个 Phase 通过跨版本回归验证（5 个 Blender 版本，各 158 测试）。

#### Phase 5: 发布前最终加固 / Pre-release Final Hardening
- **异常安全大幅提升**：全项目 18 处 `except Exception` 收紧为具体异常类型，覆盖 `core/engine.py`、`core/execution.py`、`ops.py`、`property.py`、`automation/*.py` 等 9 个文件。
- **全局状态封装**：`__init__.py` 引入 `_RegistryState` 类封装模块级可变状态；`thumbnail_manager.py` 的 `preview_collections` 改为模块私有 `_preview_collections`。
- **上下文管理统一**：`save_image` 和 `bake_node_to_image` 改用 `SceneSettingsContext` 管理场景设置，消除手动恢复。
- **CI 修复**：verify job 改用 heredoc 避免 YAML 缩进歧义。
- **类型标注**：`api.validate_settings` 返回类型 `Any` → `ValidationResult`；`compat.get_bake_settings` 返回类型 `Optional[Any]` → `object`。
- **命名一致性**：`cleanup.py` operator 前缀统一为 `baketool.`。
- **代码清理**：重复 import 删除、CHANGELOG 格式修复、translations.py 模块 docstring 补全、constants.py license 占位符替换。
- **文档同步**：更新 ROADMAP.md、TECHNICAL_GUIDE.md、DEVELOPER_GUIDE.md、STYLE_GUIDE_ANALYSIS.md，确保发布前文档一致。

---

## 1.0.0 - 2026-05-13
### 发布前最终 Code Review 加固 / Pre-release Code Review Hardening

#### 核心执行引擎修复 / Engine Fixes
- **降噪安全增强**：`apply_denoise` 注入 `context` 参数替代全局 `bpy.context`；渲染失败时 `try/finally` 确保 `BT_Denoise_Temp` 清理。
- **Depsgraph 性能优化**：`calculate_cage_proximity` 将 `evaluated_depsgraph_get()` 移出循环（N 次→1 次）。
- **预览材质崩溃恢复**：新增 `RestorePreviewMaterialsHandler`，`load_post` 时自动恢复原始材质。
- **Bake Target 统一管理**：通过 `compat.get_bake_target()` 集中管控，`engine.py` 和 `node_manager.py` 统一调用。
- **纹素密度参数化**：`TexelDensityCalculator.get_mesh_density` 新增 `resolution` 参数，消除 1024 硬编码。
- **场景上下文容错**：`SceneSettingsContext.__enter__` except 收紧为具体异常（AttributeError/TypeError/ValueError/RuntimeError）。
- **错误日志防膨胀**：`bake_error_log` 添加 8000 字符滚动窗口。

#### API 与自动化修复 / API & Automation Fixes
- **API 上下文注入**：`api.bake()` 和 `api.validate_settings()` 新增可选的 `context` 参数，headless 模式安全调用。
- **模块加载优化**：`cli_runner.py` 使用 `importlib.reload()` 替代 `del sys.modules` 暴力删除。
- **路径分隔符跨平台**：`multi_version_test.py` 使用 `os.pathsep` 替代硬编码分号。
- **测试签名同步**：更新 `suite_unit.py` 和 `suite_denoise.py` 中 `apply_denoise` 的三处旧签名调用。
- **CI 管道加固**：verify job 解析 JSON 报告验证测试结果；lint 移除 `|| true` 使其生效。
- **导入性测试补全**：`suite_code_review.test_all_test_suites_importable` 补充 `suite_custom_channel_hardened`。

#### 资源与状态管理 / Resource & State Management
- **保护镜像 GC 预防**：`node_manager.py` 中 `DUMMY_IMG` 创建时设置 `use_fake_user = True`。
- **时间轴状态恢复**：`BakeModalOperator` 在 `init_modal` 保存 `_original_frame`，`_cleanup_state` 恢复。
- **无头模式崩溃修复**：`cage_analyzer.py` 添加 `context.screen` None 守卫。
- **缩略图 TOCTOU 修复**：`thumbnail_manager.get_icon_id` 缓存 `pcoll.get()` 结果。

#### 代码审查与文档 / Code Review & Documentation
- **全量两轮 Code Review**：审查 44 个源文件，修复 20 个 CRITICAL/HIGH/MEDIUM 问题。
- **完善技术指南**：新增上下文注入模式、Depsgraph 优化实践、错误日志治理、CI 有效性规则章节。
- **更新路线图**：同步 v1.0.0 最终修复记录，调整短期计划反映已完成优化。
- **更新开发者指南**：新增上下文注入模式、Compat Layer 函数表、API 上下文约定。

---

## 1.0.0 - 2026-05-05

### 本次发布前综合收尾 / Pre-Release Comprehensive Wrap-up

#### UI 架构审计与修复 / UI Audit & Fixes
- **参数暴露补全**：`draw_inputs` 补回了 `sample`、`margin`、`device`、`use_clear_image`、`color_base`；`draw_saves` 补回了 `use_denoise`、`create_new_folder`、`folder_name`、`pack_suffix`、`export_textures_with_model`。
- **数据驱动对齐**：`CHANNEL_UI_LAYOUT` 所有通道属性现已通过 `SuiteCodeReview` 自动验证存在于 `BakeChannel` 中。
- **空安全**：`BAKE_UL_BakedImageResults.draw_item` 增加 `item.image` 空值守卫，避免 NoneType 崩溃。
- **国际化**：`draw_active_channel_properties` 中硬编码 `"Naming:"` → `pgettext("Naming") + ":"`；结果列表空通道显示 `pgettext("(Empty)")`。
- **布局优化**：`draw_saves` 重构为 Common Settings / External Save / Animation / Smart Intelligence 四个功能区，减少认知负荷。

#### 单元测试体系优化 / Test Suite Optimization
- **Mock 同步**：`MockSetting` 补全 `color_base`、`create_new_folder`、`folder_name`；`JobBuilder` 新增 `.folder()`、`.packing()`、`.denoise()` 流式 API。
- **覆盖率提升**：新增 `test_denoise_integration_trigger`、`test_output_subfolder_creation`、`test_apply_baked_result_collection` 三个集成测试。
- **跨版本框架修复**：修正 `multi_version_test.py` 中 `stdout_tail` 缺失、`write_summary_reports` 键名不一致、`cli_runner.py` 引用不存在的 `suite_verification.py` 等问题。
- **最终验证**：5 个 Blender 版本（3.3 / 3.6 / 4.2 LTS / 4.5 LTS / 5.0）全部 158 测试 100% 通过。

#### 核心引擎一致性修复 / Engine Consistency Fixes
- **参数传递路径**：`_handle_save` 和 `ModelExporter.export` 中 `folder_name` 统一为 `s.folder_name if s.create_new_folder else task.folder_name`。
- **集合名称修正**：`test_apply_baked_result_mesh_cleanup` 中集合名从错误的 `"BakeResults"` 修正为 `SYSTEM_NAMES["RESULT_COLLECTION"]`（即 `"Baked_Results"`）。
- **API 健壮性**：`test_bake_trigger_api` 移除 `from .. import baketool` 的内部导入，改为直接检查 `scene.BakeJobs` 属性。

#### 文档与发布准备 / Documentation & Release Prep
- 更新 `ROADMAP.md`：补充参数动态对齐机制、资源生命周期管理、跨版本兼容性说明。
- 补充技术原理概要：参数传递路径、一致性保证、资源监控机制。
- 清理所有 `__pycache__` 目录，确保发布包干净。
- 发布前复核修复：补齐 `verification` 自动化入口、修正动态枚举默认值、统一发布 ZIP 顶层包名、收紧保存路径命名、补强 UDIM 多 tile 检测与 Selected-to-Active 上下文。
- 跨版本回归修复：恢复动态枚举回调的 Blender 兼容默认值、修复 `cli_runner.py --test` 被 discovery 覆盖的问题、避免 `multi_version_test.py` 并行报告文件名碰撞，并清理 denoise 临时场景删除时的 `lib_remap` 噪声。

---

## 1.0.0-p1 - 2026-04-23

### 核心修复与增强 /Core Fixes & Enhancements

- **自定义通道加固 /Custom Channel Hardening**:
  - 引入 `default_value` 属性，支持自定义通道默认值（如 AO/金属度默认为 1.0）/Introduced `default_value` property
  - 实现 **自我指涉过滤 /Self-Reference Filter**，自动排除当前通道/Automatically exclude current channel

- **导出质量优化 /Export Quality**:
  - 重构 `save_image()`，透传详细图像参数/Refactored to pass detailed image parameters
  - 实现场景设置临时覆盖与自动还原/Temporary override and auto-restore

### 稳定性与自动化 /Stability & Automation

- **全量回归验证 /Full Regression**: Blender 4.2 LTS 21 套件 100% 通过/21 test suites pass at 100%
- **新增专项测试 /New Tests**: `suite_custom_channel_hardened.py`
- **CI 稳定性 /CI Stability**: 修复 GitHub Actions 跨平台兼容性/Fixed cross-platform compatibility
- **测试覆盖 /Test Coverage**: 扩展到 12 个 Blender 版本/Expanded to 12 Blender versions

## 1.0.0 - 2026-04-22

这是发布前的关键收尾版本，重点是修复会直接影响发布质量和自动化可信度的缺陷。

### 补充

- 预设/属性保存链路现在支持常见 Blender ID 指针的稳定往返保存与恢复，包括 `Object`、`Material`、`Image` 等，缺失目标会安全跳过而不是破坏导入流程。
- 多版本测试脚本补齐了 `--blender`、`--paths-file`、`--timeout`、`--report-dir` 等入口，并改为优先读取 `cli_runner.py` 的 JSON 结果判断成功/失败，降低了仅靠控制台关键字判断的误报风险。
- 翻译提取脚本升级为 AST 级提取/审计/同步工具，补齐了 `AnnAssign` 属性声明、UI `text=`、`report()`、`pgettext()`、枚举项与消息字典等来源。
- 翻译审计现在会额外标记坏掉的 locale 值和“键存在但仍回落到英文原文”的条目，能直接拦截 `????`、乱码回写和覆盖不足问题。
- UI 中原本绕过词典的动态拼接文本已接入翻译系统，例如通道设置标题和结果面板元数据标签。
- `fr_FR`、`ja_JP`、`ru_RU`、`zh_CN` 四个 locale 现已全部达到 `missing=0 / broken=0 / untranslated=0`，并完成 Blender `3.3.21 / 3.4.1 / 3.5.1 / 3.6.23 / 4.0.2 / 4.1.1 / 4.2.14 / 4.3.2 / 4.4.3 / 4.5.3 / 5.0.1 / 5.1.0` 的本地化回归。
- 正式翻译表已清洗为 476 个当前有效键，移除了陈旧键和内部标识键，并补齐本轮新增键的 `zh_CN` 翻译；清洗后的翻译表在 Blender `3.3.21 / 3.4.1 / 3.5.1 / 3.6.23 / 4.0.2 / 4.1.1 / 4.2.14 / 4.3.2 / 4.4.3 / 4.5.3 / 5.0.1 / 5.1.0` 上完成了注册回归。

### 修复

- 统一了预设加载兼容策略，启动默认预设和库预设现在同时接受单 Job 导出与完整 `BakeJobs` 快照，避免导出的 JSON 在复用时被静默忽略。
- 补齐了 UI 已经引用但未注册的三个 operator：
  - `bake.set_save_local`
  - `bake.selected_node_bake`
  - `bake.refresh_udim_locations`
- 修复了 `automation/headless_bake.py` 在干净 Blender 背景会话中不能初始化插件属性的问题，脚本现在会先尝试注册 BakeNexus，再访问 `scene.BakeJobs`。
- 将自定义通道真正接入执行管线，不再在执行阶段退回默认黑色结果。
- 统一了自定义通道结果键命名，执行结果和通道打包统一使用 `BT_CUSTOM_<name>`，消除了自定义图可烘焙但不可打包的问题。
- 将 diffuse、glossy、transmission 和 combined 的 pass filter 选项实际映射到 Blender bake 设置，不再是“界面可改但执行不生效”的状态。
- 修复导出流程只恢复 `hide_set()` 不恢复 `hide_viewport` 的问题，避免导出后对象可见性被污染。
- 增加颜色空间枚举与 Blender 实际 colorspace 名称的映射，避免 `NONCOL`、`LINEAR` 等内部值直接写入 RNA 导致的异常。
- 将 View Layer 预检前移到 `JobPreparer`，对象、active object 或 cage object 不在当前 View Layer 时会明确跳过 Job，而不再等到 Blender 原生 bake 阶段才报运行时错误。
- 为失败 bake 增加新建图像回收逻辑，避免通道执行失败后在场景里残留无效 image datablock。
- 将 `Run Safety Audit` 改为启动独立 Blender 后台进程执行测试，并回填 JSON 摘要，避免在当前交互式会话里原地跑测试导致 RNA 路径解析崩溃。

### 自动化

- 重写 UI operator 完整性测试，改用 `get_rna_type()` 验证注册状态，避免 `hasattr(bpy.ops...)` 带来的假阳性。
- 新增和补强以下回归测试：
  - headless 初始化测试
  - 自定义通道结果键规范测试
  - 自定义通道 NumPy 组装测试
  - 自定义结果参与通道打包测试
  - pass filter 映射测试
  - 导出可见性恢复测试
- 新增 View Layer 预检回归、失败 bake 图像清理回归，以及开发调试测试隔离执行回归。
- 在 Blender 4.5.3 LTS 上通过了 `unit`、`export`、`ui_logic`、`verification` 和 `production_workflow` 关键套件。
- 通过了 `3.3.21`、`3.4.1`、`3.5.1`、`3.6.23`、`4.0.2`、`4.1.1`、`4.2.14`、`4.3.2`、`4.4.3`、`4.5.3`、`5.0.1`、`5.1.0` 的跨版本 verification 验证。
- 通过了 `3.3.21`、`3.4.1`、`3.5.1`、`3.6.23`、`4.0.2`、`4.1.1`、`4.2.14`、`4.3.2`、`4.4.3`、`4.5.3`、`5.0.1`、`5.1.0` 的跨版本 negative 验证。

### 文档与发布准备

- 更新 `__init__.py` 中的 `doc_url` 和 `tracker_url`，替换占位链接。
- 清理 `bl_info.warning` 的 Beta 提示，并修正 GitHub Actions 中未真正命中当前仓库源码的 lint/style 配置。
- 增加正式分发 ZIP 打包脚本，避免本地 `.venv/`、测试输出和历史资料被误带入发布包。
- 重写 `README.md`、用户手册、开发者文档和自动化说明，移除乱码与旧脚本引用。
- 增加发布检查清单，统一正式打包前需要执行的验证和人工验收动作。
- 修正 `MANIFEST.in`，使其与当前仓库布局一致。
- 补充参数一致化、动态 UI 对齐和交互式调试隔离的开发约束说明，并同步更新路线图与任务看板。

## 1.0.0-pre - 2026-04-17

这是 1.0 线的稳定化节点，主要目标是让插件在 Blender 3.3 到 5.x 范围内具备可持续验证和维护的基本条件。

### 变化

- 稳定化核心执行链与异常处理。
- 收敛 UI、属性和引擎参数映射。
- 清理部分未使用导入和维护性问题。
- 完成多份基础文档与测试脚本的初版整理。

## 0.9.5 - 2024-01-20

### 变化

- 增加 GLB/USD 导出联动支持。
- 增加降噪后处理相关流程。
- 持续调整执行引擎与资源清理逻辑。

## 0.9.0 - 2023-09-01

### 变化

- 将烘焙执行逻辑重构为更清晰的模块化核心组件。
- 引入更明确的 UI、operator、engine 分层。
- 开始形成自动化套件与开发规范。
