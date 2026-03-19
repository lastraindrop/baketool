# Simple Bake Tool (SBT) v1.0.0

A simplified, high-efficiency baking solution for Blender.

### Key Features (v1.0.0-RC Refactor)
- **Resume Interrupted Bake**: Advanced state recovery allowing you to resume complex bake jobs precisely where they failed.
- **Data-Driven UI**: 100% decoupled UI architecture. Channels and panels are rendered purely from metadata, eliminating logic from the view layer.
- **Robust Context Management**: Utilizes `contextlib.ExitStack` and native low-level APIs to ensure system stability and zero context-hijacking, even in Headless mode.
- **Atomic Cleanup**: Employs UUID/Tagging (`is_bt_temp`) for temporary nodes to guarantee safe cleanup without affecting user assets.
- **Hardened Architecture**: Standardized snake_case properties, and unified logging across all modules.
- **Industry-Standard Testing**: Exhaustive Matrix Testing suite (5x2 modes) covers 135+ cases per version.
- **Cross-Version Rock-Solid**: 100% Pass Rate (540+ total tests) for Blender 3.6, 4.2 LTS, 4.5 LTS, and 5.0.1.
- **Interactive Packing Preview** (**v1.0.0**): Real-time GLSL viewport visualization for ORM/Channel packing logic.

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
