# BakeTool Automation Tools Reference

**Version:** 1.0.0

---

## Quick Reference

### Test Commands

```bash
# Blender UI
N Panel -> Baking -> Debug Mode -> Run Test Suite

# CLI
blender -b --python automation/cli_runner.py -- --suite all

# Cross-version testing
python automation/multi_version_test.py --verification
```

---

## 1. CLI Runner (`cli_runner.py`)

Unified test entry point.

### Basic Usage

```bash
blender -b --python automation/cli_runner.py [options]
```

### Options

| Option | Description | Example |
|-------|-------------|----------|
| `--suite` | Specify test suite | `--suite unit` |
| `--category` | Run by category | `--category memory` |
| `--test` | Run single test | `--test suite_api.SuiteAPI.test_example` |
| `--discover` | Auto-discover all tests | `--discover` |
| `--json` | Output JSON report | `--json report.json` |
| `--list` | List all suites | `--list` |

### Available Suites

| Suite | Description |
|-------|-------------|
| `unit` | Core unit tests |
| `shading` | Shading logic tests |
| `negative` | Negative/edge case tests |
| `memory` | Memory leak detection |
| `export` | Export safety tests |
| `api` | API stability tests |
| `context_lifecycle` | Context lifecycle |
| `cleanup` | Resource cleanup tests |
| `denoise` | Denoiser tests |
| `parameter_matrix` | Parameter matrix tests |
| `preset` | Preset functionality tests |
| `production_workflow` | End-to-end workflow |
| `udim_advanced` | UDIM advanced features |
| `ui_logic` | UI logic tests |
| `code_review` | Code review |
| `all` | All suites |

### Available Categories

| Category | Included Suites |
|----------|---------------|
| `core` | unit, negative, api, cleanup, compat, parameter_matrix |
| `memory` | memory |
| `export` | export |
| `ui` | ui_logic |
| `integration` | production_workflow, context_lifecycle |

### Examples

```bash
# Run single suite
blender -b --python automation/cli_runner.py -- --suite unit

# Run multiple categories
blender -b --python automation/cli_runner.py -- --category memory

# Discover and run all tests
blender -b --python automation/cli_runner.py -- --discover

# Generate JSON report
blender -b --python automation/cli_runner.py -- --json test_report.json --suite all

# List all available suites
blender -b --python automation/cli_runner.py -- --list
```

---

## 2. Multi-Version Test (`multi_version_test.py`)

Blender version test runner.

### Basic Usage

```bash
python automation/multi_version_test.py [options]
```

### Options

| Option | Description |
|--------|-------------|
| `--verification` | Run comprehensive verification |
| `--suite` | Specify test suite |
| `--category` | Run by category |
| `--list` | List available Blender versions |
| `--json` | Save detailed JSON report |

### Environment Variables

```bash
# Custom Blender paths
export BLENDER_PATHS="D:\Blender\3.6\blender.exe;D:\Blender\4.2\blender.exe"
python automation/multi_version_test.py
```

### Default Test Versions

- Blender 3.3.21 LTS
- Blender 3.6.23 LTS
- Blender 4.2.14 LTS
- Blender 4.5.3 LTS
- Blender 5.0.1

### Examples

```bash
# Full verification
python automation/multi_version_test.py --verification

# Run unit tests
python automation/multi_version_test.py --suite unit

# Memory tests
python automation/multi_version_test.py --category memory

# List available versions
python automation/multi_version_test.py --list

# JSON output
python automation/multi_version_test.py --json cross_version_report.json
```

---

## 3. Comprehensive Verification (`comprehensive_verification.py`)

**Status**: Planning - Not yet implemented

This script is intended to run complete code review verification. Currently covered via test suites:
```bash
blender -b --python automation/cli_runner.py -- --suite all
```

### Verification Items

| ID | Verification Item | Description |
|----|----------------|-------------|
| FIX-1 | Memory Leak | `use_fake_user` default behavior |
| FIX-2 | Image Cleanup | `DeleteResult` removes datablock |
| FIX-3 | NumPy Memory | `_physical_clear_pixels` memory optimization |
| FIX-4 | Export Safety | Hidden object export safety |
| FIX-5 | UI Poll Safety | `context.space_data` safe access |
| FIX-6 | Mesh Cleanup | `do_unlink=True` correct cleanup |

### Example Output

```
======================================================================
      BAKETOOL v1.0.0 VERIFICATION SUITE
======================================================================
  Blender Version: 4.2.14 LTS
  Python Version:  3.11.7
======================================================================

[FIX-1] Memory Leak Fix: use_fake_user
  [PASS] use_fake_user_not_default
  [PASS] use_fake_user_with_setting

[FIX-2] Image Cleanup Fix: DeleteResult
  [PASS] delete_result_removes_datablock
  [PASS] no_accumulation

...

======================================================================
      COMPREHENSIVE VERIFICATION SUMMARY
======================================================================
  Total Tests:  15
  Passed:      15
  Failed:      0
----------------------------------------------------------------------

>>> ALL VERIFICATIONS PASSED!
```

---

## 4. Headless Bake (`headless_bake.py`)

Headless mode bake CLI tool.

### Basic Usage

```bash
blender -b scene.blend -P automation/headless_bake.py -- [options]
```

### Options

| Option | Description | Example |
|--------|-------------|----------|
| `--job` | Specify job name | `--job "MainBake"` |
| `--output` | Output directory | `--output "C:/baked/"` |

### Examples

```bash
# Run all enabled jobs
blender -b scene.blend -P automation/headless_bake.py

# Specify job
blender -b scene.blend -P automation/headless_bake.py -- --job "PBR_Job"

# Specify output directory
blender -b scene.blend -P automation/headless_bake.py -- --output "C:/output/"

# Combined
blender -b scene.blend -P automation/headless_bake.py -- --job "PBR" --output "C:/baked/"
```

---

## 5. Environment Setup (`env_setup.py`)

**Status**: Planning - Not yet implemented

Test environment initialization module (planned).

### Current Alternative

Use CLI Runner to load test environment directly:
```bash
blender -b --python automation/cli_runner.py -- --suite all
```

---

## 6. Translation Extractor (`dev_tools/extract_translations.py`)

Translation string extraction and sync tool.

### Basic Usage

```bash
python dev_tools/extract_translations.py [options]
```

### Options

| Option | Description |
|--------|-------------|
| `--mode` | Sync mode |
| `--path` | Scan root directory |

### Modes

| Mode | Description |
|------|-------------|
| `update` | Add new keys, keep old keys (default) |
| `sync` | Delete unused keys |
| `clean` | Delete all keys and reset translations |

### Examples

```bash
# Scan and update translations
python dev_tools/extract_translations.py

# Sync: delete unused keys
python dev_tools/extract_translations.py --mode sync

# Clean: reset all translations
python dev_tools/extract_translations.py --mode clean

# Specify path
python dev_tools/extract_translations.py --path /path/to/addon
```

### Output

```json
{
    "header": {
        "system": "Extracted by Universal Tool"
    },
    "data": {
        "Bake": {
            "zh_CN": "烘焙",
            "fr_FR": "Cuire"
        }
    }
}
```

---

## 7. Test Utilities (`test_cases/helpers.py`)

### DataLeakChecker

Detects Blender datablock leaks:

```python
from test_cases.helpers import DataLeakChecker

checker = DataLeakChecker()
# ... perform operation ...
leaks = checker.check()
if leaks:
    print(f"Leaks: {leaks}")
```

### assert_no_leak

Context manager for leak detection:

```python
from test_cases.helpers import assert_no_leak

def test_example(self):
    with assert_no_leak(self):
        create_images()
        create_meshes()
```

### JobBuilder

Fluent API for building test jobs:

```python
from test_cases.helpers import JobBuilder

job = (JobBuilder("TestJob")
    .mode("SINGLE_OBJECT")
    .type("BSDF")
    .resolution(256)
    .add_objects([obj])
    .enable_channel("color")
    .build())
```

### cleanup_scene

Deep scene cleanup:

```python
from test_cases.helpers import cleanup_scene

cleanup_scene()  # Clean all test data
```

### create_test_object

Create standard test object:

```python
from test_cases.helpers import create_test_object

obj = create_test_object(
    name="TestCube",
    location=(0, 0, 0),
    color=(0.8, 0.2, 0.2, 1.0),
    metal=0.5,
    rough=0.3,
    mat_count=1
)
```

### MockSetting

Mock setting object:

```python
from test_cases.helpers import MockSetting

setting = MockSetting(
    res_x=512,
    res_y=512,
    bake_type="BSDF",
    use_external_save=True,
    external_save_path="/tmp/baked"
)
```

---

## 8. Environment Variables

| Variable | Description | Example |
|----------|-------------|----------|
| `BLENDER_PATHS` | Custom Blender paths (semicolon-separated) | `D:\Blender\3.6\blender.exe;D:\Blender\4.2\blender.exe` |
| `PYTHONIOENCODING` | Python output encoding | `utf-8` |

---

## 9. Exit Codes

| Exit Code | Description |
|-----------|-------------|
| 0 | All tests verified successfully |
| 1 | Some tests failed or errored |