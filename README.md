# Simple Bake Tool (SBT) v0.9.5

A simplified, high-efficiency baking solution for Blender.

### Key Features (v0.9.5 Refactor)
- **Modular Arch**: Decoupled UI-Engine-Core logic for 100% reliability.
- **Quick Bake 2.0**: Same robust pipeline as standard jobs, zero configuration needed.
- **Select-to-Active (Fixed)**: Intelligent source-object filtering for high-poly to low-poly baking.
- **PBR Packing**: Native NumPy-accelerated channel packing (ORM, etc.).
- **Cross-Version**: 100% Test Pass Rate for Blender 3.6, 4.2, 4.5, and 5.0.

## Documentation
- [User Manual](file:///e:/blender%20project/project/script%20project/Addons/baketool/USER_MANUAL.md) - How to use.
- [Developer Guide](file:///e:/blender%20project/project/script%20project/Addons/baketool/DEVELOPER_GUIDE.md) - How to extend.
- [Roadmap](file:///e:/blender%20project/project/script%20project/Addons/baketool/ROADMAP.md) - Future vision.
- **Comprehensive Testing**: 100+ test cases covering edge cases and performance.
- **Detailed Audit Logs**: Persistent logging for crash recovery and emergency cleanup.

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
