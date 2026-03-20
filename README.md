# Simple Bake Tool (SBT) v0.9.5

A simplified, high-efficiency baking solution for Blender.

### Key Features (v0.9.5 Update)
- **Enhanced Performance Profiler**: Track precise `Bake Time` vs `Save Time` per channel to optimize your production pipeline.
- **Node-Based Denoising**: Integrated OIDN (Open Image Denoise) support for high-quality results even with low sample counts.
- **Preset Gallery Beta**: Browse your bake configurations with thumbnails via the new gallery UI.
- **Data-Driven UI**: 100% decoupled UI architecture. Channels and panels are rendered purely from metadata.
- **Resume Interrupted Bake**: Advanced state recovery allowing you to resume complex bake jobs precisely where they failed.
- **Robust Context Management**: Utilizes `contextlib.ExitStack` to ensure system stability even in Headless mode.
- **Cross-Version Rock-Solid**: 100% Pass Rate confirmed for Blender 3.6, 4.2 LTS, 4.3, 4.5, and 5.0.1. Verified with dynamic resource protection.

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
