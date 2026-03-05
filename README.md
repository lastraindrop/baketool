# Simple Bake Tool (SBT) v0.9.8

A simplified, high-efficiency baking solution for Blender. 

### Key Features (v0.9.8 Refactor)
- **Hardened Architecture**: Standardized snake_case properties, UI dispatch patterns, and unified logging across all modules.
- **Modular Engine**: Decoupled UI-Engine-Core logic with 100% test coverage for Blender 3.6 - 5.0.
- **Dynamic Parameter Alignment**: Fully dynamic property evaluation ensures exact sync between UI configuration and engine execution, without hardcoded fragility.
- **Cross-Platform Rock-Solid Paths**: Core migrated to `pathlib.Path` with normalized exceptions to fully eradicate silent runtime crashes.
- **Zero-Side-Effect Quick Bake**: Powered by Runtime Proxies—bake selected objects without modifying your scene presets.
- **Smart Object Reuse**: Automatically updates existing `_Baked` objects instead of duplicating mesh data.
- **Production Resilience**: Intelligent handling of Library Linked assets and NaN mesh data.
- **Cross-Version**: 100% Test Pass Rate for Blender 3.6, 4.2, 4.5, and 5.0.

## Documentation
- [User Manual](USER_MANUAL.md) - How to use.
- [Developer Guide](DEVELOPER_GUIDE.md) - How to extend.
- [Roadmap](ROADMAP.md) - Future vision.
- **Comprehensive Testing**: 110+ test cases covering edge cases and multi-version APIs.
- **Detailed Audit Logs**: Persistent logging for emergency cleanup actions.

## 🚀 安装方法

1.  从 [Releases](https://github.com/你的用户名/baketool/releases) 下载 `baketool.zip`。
2.  在 Blender 中进入 `Edit > Preferences > Add-ons`。
3.  点击 `Install...` 并选择下载的 ZIP 文件。
4.  勾选 **Simple Bake Tool** 启用插件。

## 📖 文档

- [用户参考手册 (中文)](USER_MANUAL.md)
- [Developer Guide (Architecture & Testing)](DEVELOPER_GUIDE.md)
## 🚀 Installation

1.  Download `baketool.zip` from [Releases](https://github.com/lastraindrop/baketool/releases).
2.  In Blender, go to `Edit > Preferences > Add-ons`.
3.  Click `Install...` and select the ZIP file.
4.  Enable **Simple Bake Tool**.

## 📖 Documentation

- [User Manual](USER_MANUAL.md) - Standard operating procedures for artists.
- [Developer Guide](DEVELOPER_GUIDE.md) - Deep dive into architecture, tests, and APIs.
- [Roadmap](ROADMAP.md) - Future vision and development phases.

## 🛠️ Development

If you encounter bugs, please submit an [Issue](https://github.com/lastraindrop/baketool/issues) or Pull Request.
To run tests: Open the N-panel, enable **Debug Mode**, and click **Run Full Test Suite**, or run `python automation/multi_version_test.py` from your terminal.

## 📄 License

This project is licensed under [GPL-3.0](LICENSE).
