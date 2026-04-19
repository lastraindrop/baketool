# BakeTool v1.0.0
## Professional Texture Baking Suite for Blender

**版本:** 1.0.0 (Code Quality Enhanced)
**支持 Blender:** 3.3 - 5.0+

---

## 特性亮?
- **生产就绪**: 通过 70+ 测试套件、跨 5 ?Blender 版本?00% 通过率验?- **非破坏性工作流**: 自动处理节点连接、图像创建和 UV 管理
- **智能烘焙**: 自动分析 Principled BSDF 配置，支?PBR、金属度/粗糙度流?- **实时预览**: 在烘焙前预览通道打包效果
- **一键交?*: 自动导出 GLB/USD，支?Substance、Unity、Unreal
- **全面兼容**: Blender 3.3, 3.6, 4.2 LTS, 4.5, 5.0.1+ 全覆?
---

## 安装

### 方法一: ?Releases 安装

1. ?[Releases](https://github.com/lastraindrop/baketool/releases) 下载 `baketool.zip`
2. ?Blender 中进?`Edit > Preferences > Add-ons`
3. 点击 `Install...` 并选择下载?ZIP 文件
4. 勾?**Simple Bake Tool** 启用插件

### 方法? 从源码安?
1. 克隆仓库到本?2. ?`baketool` 文件夹复制到 Blender ?addon 目录
   - Windows: `%APPDATA%\Blender Foundation\Blender\{version}\scripts\addons\`
   - macOS: `~/Library/Application Support/Blender/{version}/scripts/addons/`
   - Linux: `~/.config/blender/{version}/scripts/addons/`
3. ?Blender 中启用插?
---

## 快速开?
### 1. 创建烘焙任务

1. ?Blender N 面板中找?**Baking** 选项?2. 点击 `+ Add` 创建新任?3. 在对象列表中添加需要烘焙的对象
4. 选择通道类型（Base Color, Roughness, Normal 等）
5. 设置分辨率和输出路径
6. 点击 **BAKE** 开始烘?
### 2. 使用预设

1. 点击 **Load** 加载预设
2. 选择 `.json` 预设文件
3. 修改参数后点?**Save** 保存

### 3. 一?PBR

点击 **One-Click PBR Setup** 自动配置标准 PBR 通道组合?
---

## 文档

| 文档 | 描述 |
|------|------|
| [用户手册](docs/USER_MANUAL.md) | 完整的功能说明和使用指南 |
| [开发者指南](docs/dev/DEVELOPER_GUIDE.md) | 架构、技术规范和开发规?|
| [生态集成指南](docs/dev/ECOSYSTEM_GUIDE.md) | 测试框架、CI/CD 和工具链集成 |
| [自动化参考](docs/dev/AUTOMATION_REFERENCE.md) | CLI 工具和测试实用程?|
| [风格分析](STYLE_GUIDE_ANALYSIS.md) | 代码风格分析与修复计?|
| [路线图](docs/ROADMAP.md) | 开发计划和未来愿景 |
| [任务看板](docs/task.md) | 开发任务追?|

---

## 测试

### 运行测试

```bash
# Blender UI
N 面板 ?Baking ?Debug Mode ?Run Test Suite

# CLI
blender -b --python automation/cli_runner.py -- --suite all

# 跨版本测?python automation/multi_version_test.py --verification
```

### 测试覆盖

- 单元测试 (suite_unit.py)
- 内存泄漏检?(suite_memory.py)
- 导出安全?(suite_export.py)
- API 稳定?(suite_api.py)
- 参数矩阵测试 (suite_parameter_matrix.py)
- 端到端流?(suite_production_workflow.py)
- 代码审查 (suite_code_review.py)

**总计**: 220+ 测试用例

---

## 开?
### 环境要求

- Python 3.10+
- Blender 3.3 - 5.0+
- Git

### 克隆仓库

```bash
git clone https://github.com/lastraindrop/baketool.git
cd baketool
```

### 运行测试

```bash
# 单版本测?blender -b --python automation/cli_runner.py -- --suite all

# 跨版本测?python automation/multi_version_test.py --verification
```

---

## 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| 1.0.0 | 2026-04-17 | 代码质量增强?7 处异常处理修?|
| 1.0.0 | 2026-01-15 | Blender 5.0 支持，生产硬?|
| 1.0.0 | 2024-06-01 | 交互预览，笼子分?|
| 0.9.5 | 2024-01-20 | GLB/USD 导出，降噪管?|
| 0.9.0 | 2023-09-01 | 模块化引擎重?|

详见 [CHANGELOG](CHANGELOG.md) ?[路线图](docs/ROADMAP.md)

---

## 贡献

欢迎贡献！请遵循以下步骤?
1. Fork 本仓?2. 创建特性分?(`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. Push 到分?(`git push origin feature/amazing-feature`)
5. 创建 Pull Request

请阅?[开发者指南](docs/dev/DEVELOPER_GUIDE.md) 了解更多开发规范?
---

## 许可?
本项目采?[GPL-3.0](LICENSE) 许可证?
---

## 支持

- **问题反馈**: [GitHub Issues](https://github.com/lastraindrop/baketool/issues)
- **功能请求**: [GitHub Discussions](https://github.com/lastraindrop/baketool/discussions)
- **文档纠错**: Pull Request

---

<p align="center">
  <strong>BakeTool</strong> - 让纹理烘焙变得简?</p>
