# BakeNexus 自动化参考

本文档描述 BakeNexus 当前仓库中的自动化入口、可用参数、推荐命令和发布前验证策略。重点在于“现在仓库里真实可运行的内容”，而不是历史上曾经存在的脚本名或理想化 CI 方案。正式发布前已经完成一次全面同步，因此本文中的脚本名、套件名和行为都应与当前代码一致。

## 1. 自动化体系概览

BakeNexus 当前的自动化主要分为三类：

- 统一测试入口：`automation/cli_runner.py`
- 跨版本矩阵验证：`automation/multi_version_test.py`
- 背景烘焙入口：`automation/headless_bake.py`

这三者分别解决不同问题：

- `cli_runner.py` 解决“在某个 Blender 版本里跑哪些测试”
- `multi_version_test.py` 解决“同一套检查如何跨多个 Blender 版本执行”
- `headless_bake.py` 解决“如何在无界面模式下执行已配置好的 Bake Job”

## 2. `automation/cli_runner.py`

### 2.1 作用

这是当前 BakeNexus 自动化的主入口。它会：

- 配置导入环境
- 重新注册插件
- 根据命令参数加载指定测试
- 统一输出结果
- 可选生成 JSON 报告

### 2.2 基本用法

```bash
blender -b --factory-startup --python automation/cli_runner.py -- --suite unit
```

建议保留 `--factory-startup`，这样测试结果更接近干净环境。

### 2.3 参数

| 参数 | 说明 |
|------|------|
| `--suite` | 运行指定套件，默认 `all` |
| `--test` | 运行单个测试对象 |
| `--discover` | 自动发现 `suite_*.py` |
| `--json` | 输出 JSON 报告 |
| `--category` | 按类别运行 |
| `--list` | 列出可用套件和类别 |

### 2.4 当前可用套件

当前代码中声明的可用套件如下：

- `unit`
- `shading`
- `negative`
- `memory`
- `automation_tools`
- `export`
- `api`
- `compat`
- `context_lifecycle`
- `custom_channel_hardened`
- `cleanup`
- `denoise`
- `localization`
- `parameter_matrix`
- `preset`
- `production_workflow`
- `udim_advanced`
- `ui_logic`
- `code_review`
- `verification`
- `extension_validation`

### 2.5 当前可用类别

| 类别 | 实际包含内容 |
|------|--------------|
| `core` | `unit`、`negative`、`api`、`verification` |
| `memory` | `memory` |
| `export` | `export` |
| `ui` | `ui_logic` |
| `integration` | `production_workflow`、`context_lifecycle` |

### 2.6 示例

```bash
blender -b --factory-startup --python automation/cli_runner.py -- --suite verification
blender -b --factory-startup --python automation/cli_runner.py -- --suite export
blender -b --factory-startup --python automation/cli_runner.py -- --category integration
blender -b --factory-startup --python automation/cli_runner.py -- --test baketool.test_cases.suite_unit.SuiteUnit.test_ui_operator_integrity
blender -b --factory-startup --python automation/cli_runner.py -- --list
```

### 2.7 交互式 Safety Audit 按钮

`ops.py` 中的 `bake.run_dev_tests` 不是在当前 Blender 会话里原地跑整套测试，而是会：

1. 启动一个独立的后台 Blender 进程
2. 复用 `automation/cli_runner.py --discover`
3. 读取 JSON 摘要
4. 将结果写回 `scene.last_test_info` 和 `scene.test_pass`

这样做的原因很直接：交互式会话中的 UI 仍在持有当前 scene/job/result 的 RNA 引用，如果直接在同一会话里运行整套测试，测试对数据结构的修改可能会让 Blender 在 redraw 或 operator 返回后崩溃。这个按钮因此是“自动化入口的 UI 外壳”，而不是另一套独立测试逻辑。

## 3. 推荐的发布前套件组合

正式发布前，至少建议执行：

```bash
blender -b --factory-startup --python automation/cli_runner.py -- --suite unit
blender -b --factory-startup --python automation/cli_runner.py -- --suite export
blender -b --factory-startup --python automation/cli_runner.py -- --suite ui_logic
blender -b --factory-startup --python automation/cli_runner.py -- --suite verification
blender -b --factory-startup --python automation/cli_runner.py -- --suite production_workflow
```

原因如下：

- `unit` 覆盖核心协议和本轮回归修复
- `export` 保护导出与场景状态恢复
- `ui_logic` 防止界面与属性链失步
- `verification` 作为综合稳定性检查
- `production_workflow` 覆盖更接近真实使用的端到端流程

如果这轮改动涉及以下主题，建议把附加套件也视为发布前必跑项：

- 输入校验、对象上下文、失败清理：`negative`
- 翻译键提取、词典回写、多语言显示：`localization`

## 4. `automation/multi_version_test.py`

### 4.1 作用

它用于在多个 Blender 可执行文件之间循环运行测试，并把结果保存到 `reports/`。当前默认会尝试一些常见安装路径，也可以通过环境变量覆盖。

### 4.2 基本用法

```bash
python automation/multi_version_test.py --verification
python automation/multi_version_test.py --suite unit
python automation/multi_version_test.py --category core
python automation/multi_version_test.py --list
```

### 4.3 参数

| 参数 | 说明 |
|------|------|
| `--suite` | 指定套件 |
| `--category` | 指定类别 |
| `--verification` | 直接运行 verification 套件 |
| `--json` | 自定义 JSON 输出路径 |
| `--blender` | 直接追加某个 Blender 可执行文件路径，可重复传入 |
| `--paths-file` | 从文本或 JSON 文件读取 Blender 路径 |
| `--timeout` | 单个 Blender 版本的超时时间，单位秒 |
| `--report-dir` | 自定义报告输出目录 |
| `--list` | 列出检测到的 Blender 安装 |

### 4.4 Blender 路径来源

脚本优先读取环境变量：

```text
BLENDER_PATHS
BLENDER_PATHS_FILE
```

`BLENDER_PATHS` 使用分号分隔。`BLENDER_PATHS_FILE` 或 `--paths-file` 可以指向：

- 纯文本路径列表
- 或包含 `paths` 数组的 JSON 文件

若未提供，脚本会尝试内置的一组常见安装路径。

### 4.5 输出

脚本会在 `reports/` 下生成：

- `cross_version_report_<timestamp>.txt`
- `cross_version_report_<timestamp>.json`

当传入 `--json path/to/report.json` 时，JSON 汇总会写到指定路径，对应文本摘要会写到同目录同名 `.txt` 文件。

这些报告属于验证产物，不应作为插件发布包内容。

## 5. `automation/headless_bake.py`

### 5.1 作用

这是无界面背景烘焙入口，用于在命令行环境中运行已经配置好的 Bake Job。

### 5.2 基本用法

```bash
blender -b scene.blend -P automation/headless_bake.py -- --job "JobName"
blender -b scene.blend -P automation/headless_bake.py -- --output "C:/baked"
blender -b scene.blend -P automation/headless_bake.py -- --job "JobName" --output "C:/baked"
```

### 5.3 参数

| 参数 | 说明 |
|------|------|
| `--job` | 指定 Job 名称；不传时运行所有已启用 Job |
| `--output` | 覆盖输出目录，并自动启用外部保存 |

### 5.4 当前行为

本轮修复后，它会先执行插件初始化保护：

- 自动将插件目录加入可导入路径
- 若当前场景尚未注册 BakeNexus 属性，则先调用 `baketool.register()`
- 注册成功后再访问 `scene.BakeJobs`

### 5.5 限制

- 只会运行当前 `.blend` 中已有的 BakeNexus 作业
- 不会自动新建 Job
- 不会替代更复杂的任务调度系统
- 若未找到可运行 Job，会直接退出并提示 `No jobs to run. Exiting.`

## 6. JSON 报告与结果管理

`cli_runner.py` 可通过 `--json` 输出 JSON 结果。`multi_version_test.py` 会自动生成文本和 JSON 两种报告。建议做法：

- 仅保留对当前发布或当前修复有意义的最新报告
- 避免把大量历史报告堆在仓库中
- 如果需要在外部留档，把报告复制到专门归档目录，而不是长期保存在源码树里

## 7. 运行环境注意事项

### 7.1 临时目录写入

某些端到端测试会写入临时目录。如果你的执行环境对默认系统临时目录有限制，应显式把 `TEMP` 和 `TMP` 指向工作区内可写位置，再运行测试。这对 `production_workflow` 之类会生成真实输出的套件尤其重要。

### 7.2 保持干净环境

建议：

- 测试时使用 `--factory-startup`
- 避免同时加载其他会改上下文的插件
- 确保 Blender 路径清晰、版本可识别

### 7.3 避免误判

自动化的目标不是“看见任何输出就算通过”，而是看退出码和关键信号。BakeNexus 当前跨版本脚本以 `CONSOLIDATED SUITES PASSED` 或 `ALL TESTS PASSED` 作为成功标记，不应自行篡改这类约定而不同时更新脚本逻辑。

## 8. 建议的本地验证顺序

对单个修复分支，推荐顺序如下：

1. 先跑最相关的单套件。
2. 再跑 `verification`。
3. 涉及 UI 时补跑 `ui_logic`。
4. 涉及导出时补跑 `export` 和 `production_workflow`。
5. 收口前再跑跨版本 verification。

这样可以避免一开始就跑全量，浪费调试时间，同时又能在收尾阶段把关键风险重新覆盖一遍。

## 9. 当前版本最值得关注的回归点

由于本轮修复过以下问题，后续改动时要重点关注这些位置：

- UI operator 是否仍全部已注册
- headless 是否还能在干净会话下初始化
- 自定义图是否仍能正确生成
- 自定义图是否仍能被打包逻辑识别
- pass filter 是否仍真正生效
- 导出是否仍恢复 `hide_viewport`
- 数据图颜色空间是否仍正确映射
- View Layer 预检是否仍在入队阶段就拦住非法对象
- 失败 bake 后是否仍会回收本次新建的图像 datablock
- `Run Safety Audit` 是否仍通过隔离子进程执行

## 10. 翻译工作流

`dev_tools/extract_translations.py` 现在承担三件事：

- 从源码中提取当前有效的人类可见文本
- 对比 `translations.json`，给出 `missing/stale/suspicious/broken/untranslated` 审计结果
- 生成可直接回写的同步结果

推荐命令：

```bash
python dev_tools/extract_translations.py --sync --prune --existing translations.json --output translations.cleaned.json --report translation_clean_audit.json --print-missing
```

推荐收口顺序：

1. 先跑上面的同步/清洗命令，确认 `missing/stale/suspicious` 的真实规模。
2. 只在确认审计结果合理后，用 `translations.cleaned.json` 回写正式 `translations.json`。
3. 对新增键补齐目标语言翻译；如果某些非主语言本轮来不及完成，至少明确使用英文原文占位，而不是留空。
4. 回写后再次运行同一条命令，目标是 `missing/stale/suspicious` 都归零。
   对正式发布建议同时确认 `broken_by_locale` 和主目标语言的 `untranslated_by_locale` 也归零。
5. 最后在真实 Blender 里跑 `localization` 套件，确认翻译表注册不会破坏插件加载。

建议把主目标 locale 的验收标准明确成：

- `missing_by_locale[locale] == 0`
- `broken_by_locale[locale] == 0`
- `untranslated_by_locale[locale] == 0`

本轮发布前验证命令：

```bash
python dev_tools/extract_translations.py --sync --prune --existing translations.json --output translations.cleaned.json --report translation_clean_audit.json --print-missing
python automation/multi_version_test.py --suite localization --json reports/multi_version_localization.json
```

## 11. 结论

BakeNexus 当前的自动化体系并不依赖外部 CI 平台就能完成高质量本地验证，这对 Blender 插件开发是现实且重要的优势。真正需要维持的不是“脚本数量很多”，而是：

- 名称稳定
- 参数真实
- 报告可读
- 关键路径有回归保护

只要守住这几点，自动化就能持续服务于发布质量，而不是沦为装饰性的目录结构。
