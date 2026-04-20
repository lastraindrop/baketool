# BakeTool
## AI-Assisted Texture Baking Utility for Blender

**Version:** 1.0.0
**Supported Blender:** 3.3 - 5.0

---

> [!CAUTION]
> **Risk Disclosure**: This plugin was heavily AI-assisted in its development. While it has passed internal automated tests, it has not been extensively validated in real production environments. **Always backup your project files** before using this tool for important work.

---

## Features
- **Non-Destructive Workflow**: Auto-manages node connections and image creation
- **Multi-Version Support**: Preliminary compatibility for Blender 3.3 to 5.0
- **Parameter Sync**: Basic validation to reduce UI/engine state desync

---

## Installation

### Method 1: Install from Releases
1. Download `baketool.zip` from [Releases](https://github.com/lastraindrop/baketool/releases)
2. In Blender, go to `Edit > Preferences > Add-ons`
3. Click `Install...` and select the downloaded ZIP file
4. Enable **BakeTool** to activate the plugin

### Method 2: Install from Source
1. Clone the repository locally
2. Copy the `baketool` folder to Blender's addon directory:
   - Windows: `%APPDATA%\Blender Foundation\Blender\{version}\scripts\addons\`
   - macOS: `~/Library/Application Support/Blender/{version}/scripts/addons/`
   - Linux: `~/.config/blender/{version}/scripts/addons/`
3. Enable the plugin in Blender

---

## Quick Start
### 1. Create a Bake Job

1. Find **Baking** in the Blender N-panel
2. Click `+ Add` to create a new job
3. Add objects to bake in the object list
4. Select channel types (Base Color, Roughness, Normal, etc.)
5. Set resolution and output path
6. Click **START BAKE PIPELINE** to begin

### 2. Use Presets
1. Click **Load** to load a preset
2. Select a `.json` preset file
3. Modify parameters and click **Save** to save

### 3. One-Click PBR
Click **One-Click PBR** to automatically configure standard PBR channel组合

---

## Documentation

| Document | Description |
|----------|--------------|
| [User Manual](docs/USER_MANUAL.md) | Complete feature guide |
| [Developer Guide](docs/dev/DEVELOPER_GUIDE.md) | Architecture and dev specs |
| [Ecosystem Guide](docs/dev/ECOSYSTEM_GUIDE.md) | Testing, CI/CD, tooling |
| [Automation Reference](docs/dev/AUTOMATION_REFERENCE.md) | CLI tools and utilities |
| [Style Analysis](STYLE_GUIDE_ANALYSIS.md) | Code style analysis |
| [Roadmap](docs/ROADMAP.md) | Development plans |
| [Task Board](docs/task.md) | Task tracking |

---

## Testing

```bash
# Blender UI
N panel > Baking > Debug Mode > Run Safety Audit

# CLI
blender -b --python automation/cli_runner.py -- --suite all
```

### Test Coverage
- Unit tests (suite_unit.py)
- Memory leak detection (suite_memory.py)
- Export safety (suite_export.py)
- API stability (suite_api.py)
- Parameter matrix (suite_parameter_matrix.py)
- End-to-end workflow (suite_production_workflow.py)
- Code review (suite_code_review.py)

**Total**: 220+ test cases

---

## Development
### Requirements
- Python 3.10+
- Blender 3.3 - 5.0+
- Git

### Clone Repository
```bash
git clone https://github.com/lastraindrop/baketool.git
cd baketool
```

### Run Tests
```bash
# Single version test
blender -b --python automation/cli_runner.py -- --suite all

# Multi-version verification
python automation/multi_version_test.py --verification
```

---

## Version History

| Version | Date | Major Changes |
|---------|------|---------------|
| 1.0.0 | 2026-04-17 | Code quality: 7 exception handling fixes |
| 1.0.0 | 2026-01-15 | Blender 5.0 support, production hard |
| 1.0.0 | 2024-06-01 | Interactive preview, cage distribution |
| 0.9.5 | 2024-01-20 | GLB/USD export, denoise pipeline |
| 0.9.0 | 2023-09-01 | Modular engine refactor |

See [CHANGELOG](CHANGELOG.md) and [Roadmap](docs/ROADMAP.md) for more.

---

## Contributing
Contributions welcome! Please:
1. Fork this repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Create a Pull Request

See [Developer Guide](docs/dev/DEVELOPER_GUIDE.md) for development standards.

---

## License
This project is licensed under [GPL-3.0](LICENSE).

---

## Support
- **Issue Reports**: [GitHub Issues](https://github.com/lastraindrop/baketool/issues)
- **Feature Requests**: [GitHub Discussions](https://github.com/lastraindrop/baketool/discussions)
- **Documentation Fixes**: Pull Request

---

<p align="center">
  <strong>BakeTool</strong> - Making texture baking simple
</p>