# Simple Bake Tool (SBT) v0.9.4

A simplified, high-efficiency baking solution for Blender.

### Key Features
- **UI-Engine-Core Decoupled Architecture**: Robust and easy to maintain.
- **Blender 5.0 Support**: Full compatibility with the new BakeSettings API.
- **NumPy Accelerated Workflows**: Vectorized PBR conversion and channel packing.
- **Robust UDIM System**: Smart tile detection and automatic repacking.
- **Comprehensive Testing**: 50+ test cases covering edge cases and performance.
- **Detailed Audit Logs**: Persistent logging for crash recovery and emergency cleanup.

## 🚀 安装方法

1.  从 [Releases](https://github.com/你的用户名/baketool/releases) 下载 `baketool.zip`。
2.  在 Blender 中进入 `Edit > Preferences > Add-ons`。
3.  点击 `Install...` 并选择下载的 ZIP 文件。
4.  勾选 **Simple Bake Tool** 启用插件。

## 📖 文档

- [用户参考手册 (中文)](USER_MANUAL.md)
- [Developer Guide (Architecture & Testing)](DEVELOPER_GUIDE.md)

## 🛠️ 开发与贡献

如果您发现了 Bug 或有功能建议，欢迎提交 [Issue](https://github.com/你的用户名/baketool/issues) 或 Pull Request。

运行测试：
在 N 面板开启 **Debug Mode**，点击 **Run Full Test Suite**。

## 📄 许可协议

本项目遵循 [GPL-3.0](LICENSE) 开源协议。
