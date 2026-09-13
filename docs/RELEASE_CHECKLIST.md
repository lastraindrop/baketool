# BakeNexus 发布检查清单

本文档用于正式打包和对外发布前的最后核对。它的价值不在于“看起来专业”，而在于把那些最容易被遗漏、却会直接影响用户第一印象和后续维护成本的事项固定下来。建议每次发布都实际过一遍，而不是口头默认已经完成。

## 1. 版本与元数据

- 确认 `__init__.py` 中的 `bl_info` 版本号正确。
- 确认 `blender_manifest.toml` 中的 `version`、`blender_version_min`、`website` 正确。
- 确认 manifest 的 `id` 与 ZIP 内顶层目录名（即仓库目录名 `baketool`）完全一致，否则 Blender 4.2+ 从磁盘安装扩展会直接失败（由 `suite_extension_validation.test_manifest_id_matches_addon_directory` 把关）。
- 确认 `README.md`、`CHANGELOG.md` 与当前版本号一致。
- 确认 `doc_url` 和 `tracker_url` 不再使用占位地址。
- 确认 `__init__.py` 中 `bl_info["warning"]` 已更新为发布版（非 Beta 提示）。

## 2. 代码规范与一致性

- 确认无 bare `except:` 子句残留（应已清零）。
- 确认核心烘焙、数据和资源路径的 `except Exception` 已收紧为具体类型；仅插件注册/注销等顶层隔离边界可保留带日志的广泛捕获，并应有明确理由。
- 确认模块级可变状态已封装（`_RegistryState` / `_preview_collections`）。
- 确认 `cleanup.py` operator 前缀统一为 `baketool.`。
- 确认所有临时场景设置修改通过 `SceneSettingsContext` 管理。
- 确认无孤儿 operator（`bl_idname` 已声明但无任何 UI/菜单/快捷键引用）——此类 operator 会注册进 Blender 却永远不可达。
- 确认无"已声明、未接线"的死链功能（函数与 UI 存在但调用链断裂，如预设缩略图加载曾从未被调用）。
- 确认无命名冲突变量（`l`、`O`、`I`）。

## 2. 仓库整洁度

- 删除或忽略本次发布不需要携带的临时文件。
- 确认没有残留 `__pycache__`、`test_output` 等运行期目录。
- 确认工作区内没有残留 `blender.crash.txt`、`crash_log.txt`、临时截图或类似一次性调试文件。
- 确认不将本地临时验证脚本误带入发布。
- 确认最新验证报告已归档，旧的临时报告已清理或忽略。
- 确认旧的 `dist/` 产物已清理或准备重新生成，避免误把过期 ZIP 当成本次正式发布物。

## 3. 文档同步

- `README.md` 与当前实际功能一致。
- `docs/USER_MANUAL.md` 与当前 UI、工作流、限制条件一致。
- `docs/dev/DEVELOPER_GUIDE.md` 与当前核心架构和扩展点一致。
- `docs/dev/AUTOMATION_REFERENCE.md` 中的命令和脚本名可直接运行。
- `docs/dev/STANDARDIZATION_GUIDE.md` 中关于参数一致化、动态 UI 对齐和测试隔离的约束与当前代码一致。
- `docs/ROADMAP.md` 与 `docs/task.md` 反映真实阶段状态，不使用失真表述。
- `CHANGELOG.md` 记录了当前发布包含的关键修复。

## 4. 自动化验证

至少完成以下验证：

- `unit`
- `export`
- `ui_logic`
- `verification`
- `production_workflow`

推荐命令：

```bash
blender -b --factory-startup --python automation/cli_runner.py -- --suite unit
blender -b --factory-startup --python automation/cli_runner.py -- --suite export
blender -b --factory-startup --python automation/cli_runner.py -- --suite ui_logic
blender -b --factory-startup --python automation/cli_runner.py -- --suite verification
blender -b --factory-startup --python automation/cli_runner.py -- --suite production_workflow
```

如果运行环境对临时目录写入有限制，应显式将 `TEMP` 和 `TMP` 指向工作区内的可写目录后再执行端到端套件。

如果本次改动触及以下方向，还应补跑对应套件：

- 输入校验、View Layer、失败清理、异常路径：`negative`
- 翻译提取、词典回写、多语言显示：`localization`

## 5. 跨版本验证

至少执行：

```bash
python automation/multi_version_test.py --verification
```

建议最低覆盖：

- Blender `3.3.x`（源码/Legacy 兼容验证）
- Blender `3.6.x`（源码/Legacy 兼容验证）
- Blender `4.2 LTS`
- Blender `4.5 LTS`
- Blender `5.0.x`

如果某个版本无法运行，不要只记录“失败”，还应记录是：

- 路径不存在
- 环境不完整
- 插件兼容性问题
- 自动化脚本问题

## 6. 功能烟测

正式发布前建议人工跑完以下场景：

- 安装 ZIP 并启用插件（在语言设为简体中文的界面下重复一次，抽查中文翻译是否生效——词典使用 `zh_HANS` locale）
- 预设库缩略图正常显示：在偏好设置指向含 `.png` 缩略图的预设库后，顶部图库应显示图标而非纯文字
- 新建 Job 并执行单对象基础烘焙
- Selected-to-Active 烘焙
- 自定义图生成与通道打包
- UDIM 模式基础验证
- 节点烘焙
- 导出联动
- 崩溃恢复提示与清理入口（`Baked Results` 面板底部的 `Clean Up Bake Junk` 按钮）
- `Run Safety Audit` 返回隔离测试摘要，且不会把当前交互式会话改乱
- headless CLI 运行已保存 Job

## 7. 输出正确性核查

- 数据图颜色空间正确，尤其是法线、粗糙度、金属度、AO。
- 自定义图能正确生成，不是纯黑或空白错误结果。
- 通道打包读取的是最新结果，而不是旧缓存或错误键。
- 导出结束后对象 `hide_viewport` 与 `hide_set()` 状态正确恢复。
- 对象不在当前 View Layer 时，Job 会被明确跳过而不是在 Blender 原生 bake 阶段炸栈。

## 8. 分发包内容

- 包内包含插件运行所需的 Python 源文件和必要用户文档。
- 包内保留运行 `Run Safety Audit` 和 headless CLI 所需的最小自动化脚本与测试套件；不包含本地临时文件、虚拟环境、旧版归档和一次性调试资料。
- `automation/build_release_zip.py` 的显式收录规则与当前目录结构一致；不得重新引入已废弃的 `MANIFEST.in`。
- 插件目录结构在 Blender 中可直接识别。

推荐直接使用仓库内脚本生成分发包，而不是手工压缩整个工作目录：

```bash
python automation/build_release_zip.py
```

这样可以稳定排除 `.venv/`、`test_output/`、`docs/legacy/` 等本地或验证期内容；发布包会保留 `automation/cli_runner.py`、`automation/headless_bake.py`、`test_cases/` **以及 `dev_tools/`**（`suite_localization` 的直接依赖，缺失会导致打包后的 Run Safety Audit 报导入错误），以支持 Debug 模式下的 `Run Safety Audit` 与文档中的 headless CLI。此收录关系由 `suite_extension_validation.test_release_zip_includes_audit_dependencies` 固化为回归测试。

**解压包级验证（强制，2026-09-11 起）**：发布质量以解压后的 ZIP 为准，不以源码目录为准——两者可能因打包规则漂移而不一致。生成 ZIP 后必须：

```bash
# 1. 官方元数据校验
blender --background --factory-startup --command extension validate dist/baketool-<版本>.zip

# 2. 解压后在隔离目录运行全套 Safety Audit（必须 0 失败 0 错误）
blender -b --factory-startup --python-exit-code 1 \
  --python <解压目录>/baketool/automation/cli_runner.py -- --suite all
```

源码目录全绿 + 解压包 159/162（如曾有）这类结果都不得放行；两项验证均为硬性门槛。

## 9. 发布说明

对外发布说明至少应包含：

- 支持的 Blender 版本范围
- 本次版本的关键修复
- 已知限制
- 建议的首轮使用方式
- 问题反馈入口

如果本次版本有需要用户特别注意的行为变化，例如 `One-Click PBR` 实际只开启三张基础图，也应在发布说明中明确写出。

## 10. 发布后第一轮观察

即使发布前全部通过，也建议在发布后第一时间关注：

- 安装反馈
- Headless 使用反馈
- 大场景、多对象和导出联动故障
- 旧预设兼容问题
- 不同 Blender 小版本下的颜色空间差异

结论很简单：真正的发布质量，不只靠“本地这次跑通了”，还要靠每次发布都把验证、文档、打包和人工验收当成标准动作，而不是临时发挥。
