# BakeNexus 生态说明

本文档用于说明 BakeNexus 仓库内各类文件、脚本、测试、文档和发布物之间的关系。它回答的不是“某个函数怎么写”，而是“这个项目作为一个完整插件产品，是如何组织、验证、记录和交付的”。这对于发布前收口尤其重要，因为很多质量问题并不来自单个函数错误，而来自生态层的失配：脚本名变了、文档没改、测试还在验证旧路径、发布包混入了开发文件，等等。

## 1. 仓库的基本分层

BakeNexus 仓库大致可以看成五个子系统：

1. 运行时插件子系统
2. 自动化验证子系统
3. 文档与规范子系统
4. 开发辅助子系统
5. 发布与分发子系统

它们并不是彼此独立的岛，而是围绕同一套插件行为互相约束。

## 2. 运行时插件子系统

这一层决定 Blender 中真正会发生什么。

### 2.1 入口与注册

- `__init__.py`：插件入口、模块注册、`bl_info`
- `blender_manifest.toml`：Blender 新版 manifest 信息

这两者共同定义插件对外可见的基本身份。它们必须与文档中的版本、链接和支持范围保持一致。

### 2.2 UI 与交互

- `ui.py`：所有面板绘制
- `ops.py`：UI 操作触发的 operator
- `property.py`：Job、设置、自定义贴图、节点烘焙等数据结构
- `translations.py` / `translations.json`：界面文案与翻译

这一层的健康度不仅取决于“面板能画出来”，还取决于 UI 所引用的 operator 和属性是否真实存在。发布前本轮修复已经说明，如果这里失步，用户会第一时间撞上硬错误。

### 2.3 核心执行

- `core/engine.py`：执行编排、队列构造、打包、导出等核心逻辑
- `core/image_manager.py`：图像创建、保存、颜色空间处理
- `core/node_manager.py`：节点相关操作
- `core/uv_manager.py`：UV/UDIM 相关辅助
- `core/api.py`：公共 API
- 其他 `core/*.py`：兼容、公共工具和辅助逻辑

这是 BakeNexus 的“工作引擎”，也是自动化最需要保护的部分。

## 3. 自动化验证子系统

BakeNexus 的自动化并不是一个附属目录，而是项目交付的一部分。原因很简单：Blender 插件的错误很多都和上下文、版本和执行状态相关，不做自动化就很难保持发布质量。

### 3.1 自动化入口

- `automation/cli_runner.py`
- `automation/multi_version_test.py`
- `automation/headless_bake.py`

这三个脚本分别对应：

- 单版本套件执行
- 多版本矩阵验证
- 无界面烘焙入口

### 3.2 测试集合

- `test_cases/suite_unit.py`
- `test_cases/suite_export.py`
- `test_cases/suite_ui_logic.py`
- `test_cases/suite_verification.py`
- `test_cases/suite_production_workflow.py`
- 其他专项套件

这些测试不是平均分布价值的。发布前应优先确保保护核心协议和真实工作流的套件可用，而不是执着于“所有测试名都跑一次”。

### 3.3 报告与临时输出

- `reports/`：跨版本验证报告
- `test_output/`：测试生成物

它们属于验证产物，不属于插件分发内容。当前仓库已经将这类目录加入忽略规则，发布前也应清理不再需要的临时内容。

## 4. 文档与规范子系统

文档是 BakeNexus 生态的第三条腿。没有它，运行时和自动化再完整，项目依然会在发布前或交接时失真。

### 4.1 用户文档

- `README.md`
- `docs/USER_MANUAL.md`

用户文档负责告诉使用者：

- 插件是什么
- 能做什么
- 怎么开始
- 有哪些限制
- 出问题先看哪里

### 4.2 开发文档

- `docs/dev/DEVELOPER_GUIDE.md`
- `docs/dev/AUTOMATION_REFERENCE.md`
- `docs/dev/ECOSYSTEM_GUIDE.md`
- `docs/dev/STANDARDIZATION_GUIDE.md`

开发文档的目标不是重复代码注释，而是给维护者提供：

- 结构边界
- 协议约定
- 自动化入口
- 标准化要求
- 发布前应关注什么

### 4.3 项目状态文档

- `docs/ROADMAP.md`
- `docs/task.md`
- `docs/RELEASE_CHECKLIST.md`
- `CHANGELOG.md`

这部分文档负责记录“现在项目在哪个阶段、接下来做什么、这次发布改了什么”。

## 5. 开发辅助子系统

### 5.1 `dev_tools/`

这里放开发辅助脚本，例如翻译提取与审计（`extract_translations.py`）。它们服务于开发流程，不进入插件运行时核心路径。

> **分发说明（1.0.0 起）**：`dev_tools/` **会**随发布 ZIP 分发。原因是测试套件中的 `suite_localization.py` 直接导入 `..dev_tools.extract_translations`，而发布包刻意保留了完整测试套件以支持 Debug 模式下的 `Run Safety Audit`。若 `dev_tools/` 缺失，打包后的安全审计会因导入错误而永远报红。此约束已由 `suite_extension_validation.test_release_zip_includes_audit_dependencies` 固化为回归测试。

### 5.2 `docs/legacy/`

这是历史参考材料归档区，用于保存旧文档、API 摘录或调研资料。它的存在是合理的，但它不是当前行为的权威来源，也不应被当成对外文档。当前打包规则已将其排除在分发之外。

## 6. 分发与发布子系统

### 6.1 元数据

- `__init__.py` 中的 `bl_info`
- `blender_manifest.toml`
- `automation/build_release_zip.py`

三者共同决定：

- 版本信息
- Blender 支持范围
- 项目链接
- 源分发或打包包含哪些文件

### 6.2 忽略规则

- `.gitignore`
- `.gitattributes`

前者用于避免验证产物和本地临时目录污染仓库，后者用于统一文本文件换行和基础属性。这些看似外围，实际上会直接影响多人协作和发布包整洁度。

## 7. 生态内部的关键依赖关系

### 7.1 UI 依赖属性和 operator

`ui.py` 中每一个用户入口都依赖：

- `property.py` 中真实存在的属性
- `ops.py` 中真实注册的 operator

如果新增了按钮但没有注册 operator，用户会直接看到运行时错误。当前自动化已经把这一点纳入回归保护。

### 7.2 引擎依赖参数协议

`core/engine.py` 不直接信任 UI，而是依赖属性和常量层提供的参数结构。若属性名变化、默认值变化或枚举协议变化，但引擎没有同步更新，就会出现“界面能改、执行无效”的问题。本轮修复的 pass filter 失配就是典型案例。

### 7.3 文档依赖真实脚本名和行为

一旦自动化脚本名变化、参数变化或功能边界变化，文档必须同步更新。过去文档里曾出现对不存在脚本的引用，这类问题会在团队交接和发布说明里造成直接混乱，因此已经在本轮收尾中清理。

### 7.4 发布包依赖忽略和打包规则

如果没有正确的 `build_release_zip.py` 显式收录规则和清理步骤，开发脚本、临时输出或历史资料就可能混入发布物。BakeNexus 当前由该脚本决定发布包内容，而非使用已废弃的 `MANIFEST.in`。

当前发布 ZIP 的实际收录策略（2026-08 收尾定稿）：

- **随包分发**：`automation/`（cli_runner / headless_bake / multi_version_test）、`test_cases/`、`dev_tools/`——三者共同支撑 Debug 模式的 `Run Safety Audit` 与 headless CLI，缺一都会造成打包后功能断裂（B-04 教训）；以及用户手册、路线图和 `docs/dev/` 指南等必要文档。
- **排除在外**：`docs/legacy/`、`.venv/`、`test_output/`、`reports/`、`dist/` 等本地或验证期内容。

另有一条硬约束：**ZIP 内顶层目录名必须与 `blender_manifest.toml` 的 `id` 完全一致**（当前均为 `baketool`），否则 Blender 4.2+ 从磁盘安装扩展会直接失败。该约束已由 `suite_extension_validation.test_manifest_id_matches_addon_directory` 固化。

## 8. 推荐的生态工作流

下面是一条更适合 BakeNexus 现状的开发到发布路径：

1. 在 `core/` 或属性层实现变更。
2. 补充或修改对应测试。
3. 在单版本下跑最相关套件。
4. 收口前跑 `verification` 与跨版本验证。
5. 同步更新 README、用户文档和开发文档。
6. 清理临时文件和报告。
7. 依据发布检查清单执行最终打包与烟测。

这条流程的价值在于让代码、测试、文档和发布动作形成闭环，而不是互相脱节。

## 9. 当前版本生态层最重要的经验

本轮发布前收尾暴露了几个很有代表性的经验：

- 单靠 UI 看起来“像是有功能”并不可靠，必须验证 operator 和执行链都已接通。
- 单靠存在某条测试也不可靠，测试本身也可能因为验证方法错误而失效。
- 文档一旦落后，哪怕代码已经修复，外部使用和内部维护仍然会被误导。
- 发布清理不是可有可无，它直接影响仓库整洁度和分发质量。

## 10. 结论

BakeNexus 的生态不是“代码仓库外加一些说明文件”，而是一整套彼此约束的交付系统：

- 运行时代码提供能力
- 自动化提供验证
- 文档提供解释和约束
- 打包规则提供分发边界

只要其中任意一个长期失真，项目就会重新回到“作者自己知道怎么用，但别人难以接手”的状态。当前版本的文档和验证整理，目的就是避免再次回到那个状态。
