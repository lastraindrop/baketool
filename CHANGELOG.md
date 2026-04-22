# 更新日志

本文件记录 BakeTool 在正式发布前的主要版本变化。这里不追求逐提交流水账，而是保留对用户、开发者和验证流程有实际意义的版本信息。

## 1.0.0-p1 - 2026-04-23

这是 v1.0.0 的首个生产加固补丁，重点解决了自定义通道的架构设计缺陷及文件导出质量。

### 核心修复与增强
- **自定义通道加固**：
  - 引入了 `default_value` 属性，支持在未接入贴图时自定义通道的填充数值（如设置 AO/金属度默认为 1.0）。
  - 实现了 **自我指涉过滤 (Self-Reference Filter)**，在自定义通道源选择列表中自动排除当前通道，杜绝了逻辑循环引用风险。
- **导出质量优化**：
  - 重构了 `save_image` 核心函数，现在能完整透传并应用详细的图像格式参数（位深、模式、压缩质量、编解码器等）。
  - 实现了导出时的场景设置临时覆盖与自动还原机制，确保导出结果严格符合 Job 配置且不污染原始场景渲染设置。

### 稳定性与自动化
- **全量回归验证**：在 Blender 4.2 LTS 环境下通过了全部 21 个测试套件，通过率为 100%。
- **新增专项测试**：新增 `suite_custom_channel_hardened.py`，专门验证自定义通道的默认值逻辑与自引用防护。
- **一致性处理**：完成了全工作区的缩进归一化处理（Tabs -> Spaces），提升了跨环境代码稳定性。
- **CI 稳定性修复**：
  - 修复了 `test_export_to_readonly_directory` 在 Linux (GitHub Actions) 环境下的跨平台兼容性问题。
  - 修正了 `test_manifest_version_matches_bl_info` 的路径探测逻辑，确保在自动化环境中能正确识别 Manifest 文件。

## 1.0.0 - 2026-04-22

这是发布前的关键收尾版本，重点是修复会直接影响发布质量和自动化可信度的缺陷。

### 补充

- 预设/属性保存链路现在支持常见 Blender ID 指针的稳定往返保存与恢复，包括 `Object`、`Material`、`Image` 等，缺失目标会安全跳过而不是破坏导入流程。
- 多版本测试脚本补齐了 `--blender`、`--paths-file`、`--timeout`、`--report-dir` 等入口，并改为优先读取 `cli_runner.py` 的 JSON 结果判断成功/失败，降低了仅靠控制台关键字判断的误报风险。
- 翻译提取脚本升级为 AST 级提取/审计/同步工具，补齐了 `AnnAssign` 属性声明、UI `text=`、`report()`、`pgettext()`、枚举项与消息字典等来源。
- 翻译审计现在会额外标记坏掉的 locale 值和“键存在但仍回落到英文原文”的条目，能直接拦截 `????`、乱码回写和覆盖不足问题。
- UI 中原本绕过词典的动态拼接文本已接入翻译系统，例如通道设置标题和结果面板元数据标签。
- `fr_FR`、`ja_JP`、`ru_RU`、`zh_CN` 四个 locale 现已全部达到 `missing=0 / broken=0 / untranslated=0`，并完成 Blender `3.3.21 / 3.6.23 / 4.2.14 LTS / 4.5.3 LTS / 5.0.1` 的本地化回归。
- 正式翻译表已清洗为 476 个当前有效键，移除了陈旧键和内部标识键，并补齐本轮新增键的 `zh_CN` 翻译；清洗后的翻译表在 Blender `3.3.21 / 3.6.23 / 4.2.14 LTS / 4.5.3 LTS / 5.0.1` 上完成了注册回归。

### 修复

- 统一了预设加载兼容策略，启动默认预设和库预设现在同时接受单 Job 导出与完整 `BakeJobs` 快照，避免导出的 JSON 在复用时被静默忽略。
- 补齐了 UI 已经引用但未注册的三个 operator：
  - `bake.set_save_local`
  - `bake.selected_node_bake`
  - `bake.refresh_udim_locations`
- 修复了 `automation/headless_bake.py` 在干净 Blender 背景会话中不能初始化插件属性的问题，脚本现在会先尝试注册 BakeTool，再访问 `scene.BakeJobs`。
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
- 通过了 `3.3.21`、`3.6.23`、`4.2.14 LTS`、`4.5.3 LTS`、`5.0.1` 的跨版本 verification 验证。
- 通过了 `3.3.21`、`3.6.23`、`4.2.14 LTS`、`4.5.3 LTS`、`5.0.1` 的跨版本 negative 验证。

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
