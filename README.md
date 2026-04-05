# Simple BakeTool 2.0 (Stable v1.5.0)

Professional texture baking suite for Blender 3.3 through 5.1. Features optimized OpenGL/Vulkan/Cycles backend, production-grade resilience, and cross-version stability.

### Key Features (v1.5.0 Update)
- **Enhanced Performance Profiler**: Track precise `Bake Time` vs `Save Time` per channel to optimize your production pipeline.
- **Node-Based Denoising**: Integrated OIDN (Open Image Denoise) support for high-quality results even with low sample counts.
- **Environment & Health Check**: Automatic validation for missing addons, paths, and UV maps before baking.
- **One-Click PBR Setup**: Instant initialization for Color, Roughness, and Normal channels.
- **Cross-Version Rock-Solid**: 100% Pass Rate confirmed for Blender 3.6, 4.2 LTS, and 5.0. Verified with dynamic resource protection.

## Documentation
- [User Manual](docs/USER_MANUAL.md) - How to use.
- [Developer Guide](docs/dev/DEVELOPER_GUIDE.md) - How to extend.
- [Roadmap](docs/ROADMAP.md) - Future vision.
## 🚀 **v1.5.0 PRODUCTION HARDENED** 🚀

- **Core**: Multi-version Engine (Blender 3.3 - 5.0).
- **Status**: **100% CI PASS** for 3.6, 4.2, 5.0. 
- **Highlights**: Zero-Friction Delivery (GLB/USD), Heatmap Cage Analysis, Denoise OIDN Pipeline.

---
## 🚀 安装方法

1.  从 [Releases](https://github.com/你的用户名/baketool/releases) 下载 `baketool.zip`。
2.  在 Blender 中进入 `Edit > Preferences > Add-ons`。
3.  点击 `Install...` 并选择下载的 ZIP 文件。
4.  勾选 **Simple Bake Tool** 启用插件。

## 📖 文档

- [用户参考手册 (中文)](docs/USER_MANUAL.md)
- [Developer Guide (Architecture & Testing)](docs/dev/DEVELOPER_GUIDE.md)
## 🚀 Installation

1.  Download `baketool.zip` from [Releases](https://github.com/lastraindrop/baketool/releases).
2.  In Blender, go to `Edit > Preferences > Add-ons`.
3.  Click `Install...` and select the ZIP file.
4.  Enable **Simple Bake Tool**.

## 📖 Documentation

- [User Manual](docs/USER_MANUAL.md) - Standard operating procedures for artists.
- [Developer Guide](docs/dev/DEVELOPER_GUIDE.md) - Deep dive into architecture, tests, and APIs.
- [Roadmap](docs/ROADMAP.md) - Future vision and development phases.

## 🛠️ Development

If you encounter bugs, please submit an [Issue](https://github.com/lastraindrop/baketool/issues) or Pull Request.
To run tests: Open the N-panel, enable **Debug Mode**, and click **Run Full Test Suite**, or run `python automation/multi_version_test.py` from your terminal.

## 📄 License

This project is licensed under [GPL-3.0](LICENSE).
