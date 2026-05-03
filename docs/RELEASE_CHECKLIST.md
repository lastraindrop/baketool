# BakeNexus 发布检查清单

本文档用于正式打包和对外发布前的最后核对。它的价值不在于“看起来专业”，而在于把那些最容易被遗漏、却会直接影响用户第一印象和后续维护成本的事项固定下来。建议每次发布都实际过一遍，而不是口头默认已经完成。

## 1. 版本与元数据

- 确认 `__init__.py` 中的 `bl_info` 版本号正确。
- 确认 `blender_manifest.toml` 中的 `version`、`blender_version_min`、`website` 正确。
- 确认 `README.md`、`CHANGELOG.md` 与当前版本号一致。
- 确认 `doc_url` 和 `tracker_url` 不再使用占位地址。

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

- Blender `3.3.x`
- Blender `3.6.x`
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

- 安装 ZIP 并启用插件
- 新建 Job 并执行单对象基础烘焙
- Selected-to-Active 烘焙
- 自定义图生成与通道打包
- UDIM 模式基础验证
- 节点烘焙
- 导出联动
- 崩溃恢复提示与清理入口
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
- 包内不包含自动化测试、开发脚本和历史归档资料。
- `MANIFEST.in` 与当前目录结构一致。
- 插件目录结构在 Blender 中可直接识别。

推荐直接使用仓库内脚本生成分发包，而不是手工压缩整个工作目录：

```bash
python automation/build_release_zip.py
```

这样可以稳定排除 `.venv/`、`test_output/`、`docs/legacy/`、`dev_tools/` 等本地或开发期内容；发布包会保留 `automation/cli_runner.py`、`automation/headless_bake.py` 和测试套件，以支持 Debug 模式下的 `Run Safety Audit` 与文档中的 headless CLI。

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
