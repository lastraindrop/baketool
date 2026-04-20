# BakeTool Ecosystem Integration Guide

**Version:** 1.0.0
**Updated:** 2026-04-20

---

## Table of Contents

1. [Ecosystem Overview](#1-ecosystem-overview)
2. [Blender Testing Ecosystem](#2-blender-testing-ecosystem)
3. [BakeTool Testing Framework](#3-baketool-testing-framework)
4. [Automation Toolchain](#4-automation-toolchain)
5. [CI/CD Integration](#5-cicd-integration)
6. [Internationalization Workflow](#6-internationalization-workflow)
7. [Maintenance Guide](#7-maintenance-guide)
8. [Best Practices](#8-best-practices)

---

## 1. Ecosystem Overview

BakeTool provides a complete development toolchain:

```
baketool/
├── automation/           # Automation tools
│   ├── cli_runner.py           # Unified CLI test entry
│   ├── comprehensive_verification.py  # Verification scripts
│   ├── multi_version_test.py   # Cross-version testing
│   ├── headless_bake.py        # Headless bake CLI
│   └── env_setup.py            # Environment setup
├── test_cases/          # Test suites
│   ├── helpers.py              # Test utilities
│   ├── suite_unit.py           # Unit tests
│   ├── suite_memory.py         # Memory tests
│   ├── suite_export.py        # Export tests
│   ├── suite_api.py           # API tests
│   └── ... (15+ test suites)
├── dev_tools/
│   └── extract_translations.py  # Translation extraction
└── docs/dev/
    ├── DEVELOPER_GUIDE.md      # Developer guide
    └── STANDARDIZATION_GUIDE.md # Standardization guide
```

---

## 2. Blender Testing Ecosystem

### 2.1 Official Blender Testing Methods

| Method | Description | Use Case |
|--------|-------------|----------|
| **unittest (built-in)** | Blender's built-in `unittest` module | Basic unit tests |
| **pytest-blender** | pytest plugin for Blender | Advanced testing framework |
| **Headless CLI** | `blender -b --python` | CI/CD automation |
| **Manual Testing** | Blender GUI | Manual acceptance tests |

### 2.2 Blender Testing Best Practices

```python
# Standard Blender test template
import bpy
import unittest

class TestMyAddon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize Blender environment
        bpy.ops.mesh.primitive_cube_add()

    def setUp(self):
        # Clean before each test
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()

    def tearDown(self):
        # Clean after each test
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()

    def test_example(self):
        self.assertIsNotNone(bpy.context.object)
```

### 2.3 Blender Version Compatibility Strategy

```python
# core/compat.py example
import bpy

# Version checks
IS_BLENDER_5 = bpy.app.version >= (5, 0, 0)
IS_BLENDER_4 = bpy.app.version >= (4, 0, 0)
IS_BLENDER_3 = bpy.app.version >= (3, 0, 0)

def get_bake_settings(scene):
    """Unified access to bake settings (compatible 3.3 - 5.0+)."""
    if IS_BLENDER_5:
        return scene.render.bake
    return scene.render
```

---

## 3. BakeTool Testing Framework

### 3.1 Framework Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI Entry Point                         │
│         automation/cli_runner.py                            │
│         - --suite, --category, --json, --list               │
└─────────────────────────────────────────────────────────────┘
                              │
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Test Suites                          │
│            test_cases/suite_*.py                          │
│            - suite_unit.py      # Core logic               │
│            - suite_memory.py    # Memory leak detection   │
│            - suite_export.py    # Export safety         │
│            - suite_api.py       # API stability       │
│            - ...                                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Utilities                             │
│            test_cases/helpers.py                          │
│            - DataLeakChecker    # Leak detection        │
│            - JobBuilder         # Fluent API for jobs    │
│            - MockSetting       # Mock objects          │
│            - cleanup_scene()   # Scene cleanup       │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Core Component Details

#### 3.2.1 DataLeakChecker

Detects Blender datablock leaks:

```python
from test_cases.helpers import DataLeakChecker

class TestMemoryLeaks(unittest.TestCase):
    def test_no_image_leak(self):
        checker = DataLeakChecker()

        # Perform operation
        img = bpy.data.images.new("TestImg", 64, 64)

        # Check for leaks
        leaks = checker.check()
        self.assertEqual(len(leaks), 0, f"Leaks detected: {leaks}")
```

#### 3.2.2 assert_no_leak (Context Manager)

```python
from test_cases.helpers import assert_no_leak

def test_operations(self):
    with assert_no_leak(self, aggressive=True):
        # Perform potentially leaking operation
        create_bake_result()
        apply_baked_result()
    # Automatically detects leaks
```

#### 3.2.3 JobBuilder (Fluent API)

```python
from test_cases.helpers import JobBuilder

job = (JobBuilder("TestJob")
    .mode("SINGLE_OBJECT")
    .type("BSDF")
    .resolution(512)
    .add_objects([obj1, obj2])
    .enable_channel("color")
    .build())
```

### 3.3 Test Suite Inventory

| Suite | File | Description | Category |
|-------|------|-------------|----------|
| Unit Tests | `suite_unit.py` | Core component logic tests | core |
| Memory Tests | `suite_memory.py` | Memory leak detection | memory |
| Export Tests | `suite_export.py` | Export safety verification | export |
| API Tests | `suite_api.py` | Public API stability | core |
| UI Tests | `suite_ui_logic.py` | Panel drawing logic | ui |
| Preset Tests | `suite_preset.py` | Serialization and migration | core |
| Negative Tests | `suite_negative.py` | Edge conditions | core |
| Denoise Tests | `suite_denoise.py` | Denoiser sets | core |
| Production Flow | `suite_production_workflow.py` | End-to-end flow tests | integration |
| Context Lifecycle | `suite_context_lifecycle.py` | Context management | integration |
| Cleanup Tests | `suite_cleanup.py` | Resource cleanup | core |
| Compatibility Tests | `suite_compat.py` | Version compatibility | core |
| Parameter Matrix | `suite_parameter_matrix.py` | Parameter combinations | core |
| UDIM Advanced | `suite_udim_advanced.py` | UDIM features | core |
| Shading Tests | `suite_shading.py` | Shader logic | core |
| Code Review | `suite_code_review.py` | Static analysis | core |

### 3.4 Running Tests

#### 3.4.1 Running via Blender UI

```
Blender UI → N Panel → Baking → Debug Mode → Run Test Suite
```

#### 3.4.2 Running via CLI

```bash
# Single test suite
blender -b --python automation/cli_runner.py -- --suite unit

# All test suites
blender -b --python automation/cli_runner.py -- --suite all

# Run by category
blender -b --python automation/cli_runner.py -- --category memory

# List all suites
blender -b --python automation/cli_runner.py -- --list

# Output JSON report
blender -b --python automation/cli_runner.py -- --json report.json
```

#### 3.4.3 Cross-Version Testing

```bash
python automation/multi_version_test.py --verification

# Specific category
python automation/multi_version_test.py --category memory
```

---

## 4. Automation Toolchain

### 4.1 Tool Inventory

| Tool | Path | Usage |
|------|------|-------|
| **cli_runner.py** | `automation/` | Unified test entry point |
| **multi_version_test.py** | `automation/` | Cross-Blender version testing |
| **comprehensive_verification.py** | `automation/` | Fix verification |
| **headless_bake.py** | `automation/` | Headless bake CLI |
| **extract_translations.py** | `dev_tools/` | Translation extraction and sync |

### 4.2 CLI Runner Details

```bash
# Basic usage
blender -b --python automation/cli_runner.py [options]

# Options
--suite {unit|shading|negative|memory|export|api|all}
    Specify test suite to run
--category {all|core|memory|export|ui|integration}
    Run tests by category
--test <test_name>
    Run specific test case

--discover
    Auto-discover all suite_*.py files

--json <path>
    Save JSON format report

--list
    List all available test suites
```

### 4.3 Comprehensive Verification Script

Used to verify fixes identified in code review:
```bash
# Run verification
blender -b --python automation/comprehensive_verification.py

# Multi-version verification
python automation/multi_version_test.py --verification
```

**Verification Coverage:**
1. Memory leak fix (`use_fake_user`)
2. Image cleanup fix (`DeleteResult`)
3. NumPy memory optimization (`_physical_clear_pixels`)
4. Export safety (`hidden_object_export`)
5. UI safety (`space_data` access)
6. Mesh cleanup (`do_unlink=True`)

### 4.4 Headless Bake

```bash
# Basic usage
blender -b scene.blend -P automation/headless_bake.py -- --job "JobName" --output "C:/output"

# Run all enabled tasks without parameters
blender -b scene.blend -P automation/headless_bake.py
```

---

## 5. CI/CD Integration

### 5.1 GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: BakeTool Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        blender-version: ['3.3.21', '3.6.23', '4.2.14', '4.5.3', '5.0.1']

    container:
      image: user/blender:${{ matrix.blender-version }}

    steps:
      - uses: actions/checkout@v4

      - name: Run Tests
        run: |
          blender -b --python automation/cli_runner.py -- --json test_report.json

      - name: Upload Report
        uses: actions/upload-artifact@v4
        with:
          name: test-report-${{ matrix.blender-version }}
          path: test_report.json

  verify:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Verification
        run: python automation/multi_version_test.py --verification
```

### 5.2 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml

  - repo: local
    hooks:
      - id: blender-lint
        name: Blender Python Syntax
        entry: blender -b --python-expr "exec(open('tests/lint_check.py').read())"
        language: system
        files: \.py$
```

### 5.3 Local Development Workflow

```bash
# 1. Install pre-commit
pip install pre-commit
pre-commit install

# 2. Run all tests
make test

# 3. Run cross-version tests
make test-multi-version

# 4. Generate translations
python dev_tools/extract_translations.py --mode sync
```

---

## 6. Internationalization Workflow

### 6.1 Translation Extraction Tool

```bash
# Scan code, extract translatable strings
python dev_tools/extract_translations.py --mode update

# Sync: remove unused keys
python dev_tools/extract_translations.py --mode sync

# Clean: reset all translations
python dev_tools/extract_translations.py --mode clean
```

### 6.2 Tool Features

**SmartFilter Intelligent Filtering:**
- **Preserves**: User-visible strings (`"Bake"`, `"Select Object"`)
- **Ignores**: Internal IDs (`"BAKETOOL_OT_Bake"`)
- **Ignores**: Numbers (`"1024"`, `"3.14"`)
- **Ignores**: Single characters (`"X"`, `"Y"`, `"Z"`)

### 6.3 Blender i18n Integration

BakeTool uses Blender's built-in translation system:

```python
# Register translations
bpy.app.translations.register(__name__, translations.translation_dict)

# Use translations
layout.label(text=bpy.app.translations.pgettext("Bake"))

# Unregister
bpy.app.translations.unregister(__name__)
```

### 6.4 Adding a New Language

1. Edit `translations.py`
2. Add language code to `translation_dict`
3. Translate all strings

---

## 7. Maintenance Guide

### 7.1 Release Checklist

- [ ] Run all test suites (`--suite all`)
- [ ] Run cross-version tests (`--verification`)
- [ ] Check memory leaks (`suite_memory.py`)
- [ ] Verify export safety (`suite_export.py`)
- [ ] Update `bl_info` version
- [ ] Update CHANGELOG
- [ ] Run translation sync (`--mode sync`)

### 7.2 Regression Prevention

When modifying the following, run corresponding tests:

| Modification | Required Tests |
|-------------|---------------|
| `core/engine.py` | `suite_unit.py`, `suite_production_workflow.py` |
| `core/image_manager.py` | `suite_memory.py`, `suite_unit.py` |
| `core/node_manager.py` | `suite_shading.py`, `suite_unit.py` |
| `ui.py` | `suite_ui_logic.py` |
| `property.py` | `suite_parameter_matrix.py`, `suite_preset.py` |
| Any core module | `suite_compat.py` (cross-version) |

### 7.3 Performance Benchmarks

```bash
# Run performance tests
blender -b --python automation/cli_runner.py -- --suite unit --test test_performance
```

### 7.4 Debugging Techniques

```python
# Add breakpoint in tests
import code; code.interact(local=dict(globals(), **locals()))

# Print scene state
print(f"Objects: {len(bpy.data.objects)}")
print(f"Images: {len(bpy.data.images)}")
print(f"Materials: {len(bpy.data.materials)}")
```

---

## 8. Best Practices

### 8.1 Test Naming Conventions

```python
# Naming pattern: test_<feature>_<scenario>_<expected>
def test_image_manager_creates_with_correct_resolution(self):
    pass

def test_export_hidden_object_no_crash(self):
    pass

def test_memory_leak_no_accumulation_after_bake(self):
    pass
```

### 8.2 Test Isolation

```python
def setUp(self):
    cleanup_scene()  # Ensure clean environment

def tearDown(self):
    cleanup_scene()  # Clean test artifacts
```

### 8.3 Mock Object Strategy

```python
# Prefer using MockSetting from helpers.py
from test_cases.helpers import MockSetting

setting = MockSetting(
    res_x=512,
    res_y=512,
    bake_type="BSDF"
)
```

### 8.4 Continuous Improvement

1. **TDD First**: Write tests before features
2. **Test Coverage**: Target >80%
3. **Automation**: All tests run in CI/CD
4. **Documentation**: Tests are documentation

---

## Appendix A: Blender Testing Resources

- [Blender Python API Docs](https://docs.blender.org/api/current/)
- [Blender Stack Exchange](https://blender.stackexchange.com/)
- [Blender Development Forum](https://developer.blender.org/)

## Appendix B: Related Tools

| Tool | Usage |
|------|------|
| [pytest-blender](https://github.com/puckow/pytest-blender) | pytest plugin |
| [blender-addon-tests](https://github.com/p2or/blender-addon-tests) | Test templates |
| [pre-commit-blender](https://github.com/scientific-assets/pre-commit-blender) | pre-commit hooks |

---

*Maintained by BakeTool Team - Last updated 2026-04-20*