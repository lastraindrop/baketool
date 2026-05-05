# BakeNexus

BakeNexus 是一个面向 Blender 的专业贴图烘焙插件套件。
/BakeNexus is a professional texture baking suite for Blender.

> [!CAUTION]
> **严正申明与风险公示 (Project Disclaimer)**
>
> 1. **开发背景 (Development Context)**: 本项目目前由 **lastraindrop** 一人利用业余时间维护。代码逻辑大量依赖 **vibecode (AI 辅助开发)** 完成。虽然通过了 150+ 自动化测试，但 AI 生成的逻辑在极端边缘场景或复杂生产环境下可能存在不可预知的行为。/This project is currently maintained by **lastraindrop** in spare time. While 150+ automated tests pass, AI-generated code may have unpredictable behavior in edge cases.
>
> 2. **稳定性状态 (Stability Status)**: BakeNexus 尚处于**早期验证阶段 (Experimental Prototype)**。它在"实验室环境"下表现良好，但严重缺乏大规模用户实战验证。/BakeNexus is in **early verification stage**. It performs well in lab environment but lacks large-scale production validation.

> 3. **核心警告 (Core Warning)**: **极有可能出现"测试全过，实战报错"的情况**。它目前还远远达不到工业级的稳定性。/**"All tests pass, production fails" is very likely.** It is far from production-grade stability.
>
> 4. **使用建议 (Usage Recommendation)**: **在将其应用于正式生产前，请务必对 .blend 场景进行手工备份。** 开发者不承担因插件故障导致的任何数据丢失责任。/**Backup your .blend scenes before production use.** Developer assumes no liability for data loss.

---

## 当前定位 /Current Position

- 面向 Blender 4.2+ Extensions 的专业贴图烘焙工具；源码兼容验证覆盖 Blender 3.3+/A texture baking tool for Blender 4.2+ Extensions; source-level validation covers Blender 3.3+
- 支持单对象、Selected-to-Active、UDIM 等多种模式/Supports Single Object, Selected-to-Active, UDIM and more
- 内置批量作业、非破坏式流程和自动化验证/Built-in batch jobs, non-destructive workflow and automation

## 核心能力 /Core Features

- **非破坏式流程 (Non-Destructive)**: 自动创建和清理临时图像、节点和上下文状态/Automatically create and clean temporary images, nodes, contexts
- **批量作业 (Batch Jobs)**: 同一场景可维护多个 Bake Job/Maintain multiple Bake Jobs in one scene
- **多种目标模式 (Target Modes)**: 单对象、合并对象、Selected-to-Active、拆材质、UDIM/Single Object, Combined, Selected-to-Active, Split Material, UDIM
- **通道控制 (Channel Control)**: PBR、光照、辅助图和自定义贴图/PBR, Lighting, Auxiliary and Custom Maps
- **通道打包 (Channel Packing)**: 将多个烘焙结果合并到一个 RGBA 贴图/Multiple bakes to one RGBA texture
- **自定义贴图 (Custom Maps)**: 按通道来源组装灰度或 RGBA 结果/Assemble grayscale or RGBA from channel sources
- **节点烘焙 (Node Baking)**: 在节点编辑器中直接烘焙/Bake directly in Node Editor
- **导出联动 (Export Integration)**: FBX、GLB、USD 导出/FBX, GLB, USD export
- **崩溃恢复 (Crash Recovery)**: state_manager.py 记录未完成任务/Record incomplete tasks
- **自动化验证 (Automation)**: CLI 套件、跨版本验证/CLI suite, cross-version verification

## 版本与兼容性 /Version & Compatibility

| Item | Value |
|------|-------|
| 插件版本 /Plugin Version | `1.0.0` |
| Manifest | `blender_manifest.toml` (Extensions) |
| 正式扩展最低版本 /Extension Min Version | Blender 4.2.0+ |
| 源码/Legacy 验证覆盖 /Source & Legacy Tested Versions | 3.3.21, 3.6.23, 4.2.14, 4.3.2, 4.4.3, 4.5.3, 5.0.1, 5.1.0 |

## 安装 /Installation

### 从发布包安装 /From Release Package

1. 下载发布 ZIP /Download release ZIP
2. Blender: `Edit > Preferences > Add-ons` → `Install...`
3. 选择 ZIP /Select ZIP → `Install Add-on`
4. 启用 BakeNexus /Enable BakeNexus

### 从源码安装 /From Source

1. 将仓库目录放入 Blender add-ons 目录/Put repo in Blender add-ons folder
2. 目录名必须为 `baketool`/Directory must be named `baketool` (物理目录名保持不变以保持兼容性)
3. 启用后在 `3D View > Sidebar > Baking` 访问/Access via `3D View > Sidebar > Baking`

## 快速开始 /Quick Start

1. 打开 `3D View`，在 Sidebar 找到 `Baking` 面板/Find `Baking` panel in Sidebar
2. 创建新 Job/Create new Job
3. SETUP & TARGETS: 指定对象、模式、分辨率/Specify object, mode, resolution
4. BAKE CHANNELS: 勾选需要通道/Select channels
5. OUTPUT & EXPORT: 保存路径、图像格式/Output path, image format
6. CUSTOM MAPS: (可选) 添加自定义通道/(Optional) Add custom maps
7. START BAKE PIPELINE
8. 在图像编辑器中检查结果/Check results in Image Editor

如需快速 PBR 贴图，使用 `One-Click PBR`（启用 Base Color/Roughness/Normal）。/For quick PBR, use `One-Click PBR`.

## 典型工作流 /Typical Workflows

### 单对象贴图 /Single Object

适合低模有目标材质、需快速生成贴图的场景。/For low-poly with target material.
- 新建 Job → 选择 `SINGLE_OBJECT` → 设置分辨率 → 勾选通道 → 执行/Create Job → Select SINGLE_OBJECT → Set resolution → Select channels → Run

### Selected-to-Active

适合高模到低模烘焙。/For high-poly to low-poly baking.
- 高模+低模准备 → Job 选择 `SELECT_ACTIVE` → 设置 cage/extrusion → 执行/Prepare high+low → Select SELECT_ACTIVE → Set cage → Run

### 拆材质与 UDIM /Split Material & UDIM

- 多材质物体: `SPLIT_MATERIAL`/Multi-material: SPLIT_MATERIAL
- UDIM 资产: `UDIM` 模式/UDIM assets: UDIM mode

### 自定义贴图与打包 /Custom Maps & Packing

从现有结果生成新贴图，合并到 RGBA。/Generate new maps from existing, pack to RGBA.

### 节点烘焙 /Node Baking

节点编辑器中激活节点 → 节点面板执行烘焙/Activate node in Editor → Bake via node panel

## 自动化与验证 /Automation & Verification

### CLI 测试入口 /CLI Test Entry

```bash
# 单元测试 /Unit tests
blender -b --factory-startup --python automation/cli_runner.py -- --suite unit

# 验证测试 /Verification tests
blender -b --factory-startup --python automation/cli_runner.py -- --suite verification

# 集成测试 /Integration tests
blender -b --factory-startup --python automation/cli_runner.py -- --category integration
```

### 跨版本验证 /Cross-Version Verification

```bash
python automation/multi_version_test.py --verification
python automation/multi_version_test.py --suite unit
python automation/multi_version_test.py --list
```

### Headless 烘焙 /Headless Baking

```bash
blender -b scene.blend -P automation/headless_bake.py -- --job "JobName"
blender -b scene.blend -P automation/headless_bake.py -- --output "C:/baked"
```

> 注意 /Note: `headless_bake.py` 会自动注册插件。需要在 .blend 中已有保存的 Job 配置。/Auto-registers plugin. Requires saved Job config in .blend.

## 文档导航 /Documentation

- [用户手册](docs/USER_MANUAL.md) - 完整操作说明 /User Manual
- [开发者指南](docs/dev/DEVELOPER_GUIDE.md) - 架构与扩展点 /Developer Guide
- [自动化参考](docs/dev/AUTOMATION_REFERENCE.md) - 测试入口 /Automation Reference
- [生态说明](docs/dev/ECOSYSTEM_GUIDE.md) - 仓库结构 /Ecosystem Guide
- [标准化指南](docs/dev/STANDARDIZATION_GUIDE.md) - 编码规范 /Standards Guide
- [路线图](docs/ROADMAP.md) - 后续方向 /Roadmap
- [任务看板](docs/task.md) - 任务状态 /Task Board
- [更新日志](CHANGELOG.md) - 版本变更 /Changelog

## 仓库结构 /Repository Structure

```
baketool/  (物理目录名)
  automation/       自动化入口 /Automation entries
  core/           执行引擎 /Execution engine
  docs/           文档 /Documentation
  test_cases/      测试套件 /Test suites
  __init__.py     入口 /Entry point
  ops.py          操作符 /Operators
  property.py    属性定义 /Properties
  ui.py          界面布局 /UI layout
  constants.py   常量映射 /Constants
  preset_handler.py 预设 /Presets
  state_manager.py 状态管理 /State management
```

## 许可 /License

GPL-3.0-or-later - 见 [LICENSE](LICENSE) 文件/See LICENSE file.
