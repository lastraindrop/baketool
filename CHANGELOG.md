# 更新日志 /Changelog

本文件记录 BakeNexus 在正式发布前的主要版本变化。/This file records major version changes before official release.

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
