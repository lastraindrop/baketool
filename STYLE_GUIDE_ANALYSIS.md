# BakeNexus Code Style Analysis Report
## Based on Google Python Style Guide

**Date:** 2026-05-13
**Status:** Fresh Comprehensive Audit

---

## Executive Summary

The BakeNexus codebase was analyzed against Google Python Style Guide using AST analysis, pycodestyle, and manual review. **Bare except clauses have been eliminated** since the previous audit, but substantial documentation, type annotation, and formatting debt remains.

**Overall Health Score:** 4.5/10

| Category | Score | Severity | Total Count |
|----------|-------|----------|-------------|
| Exception Handling | 8/10 | HIGH | 0 bare excepts (fixed) |
| Import Organization | 5/10 | MEDIUM | 28 E402 + 40 unused imports |
| Code Documentation | 3/10 | HIGH | 34 missing module + 170 missing class/func docstrings |
| Function Complexity | 4/10 | HIGH | 18 functions > 80 lines |
| Type Safety | 3/10 | MEDIUM | 29.5% typed (161/546 functions) |
| Naming Conventions | 5/10 | LOW | 10 ambiguous `l` names, Blender names OK |
| Whitespace/Formatting | 5/10 | LOW | 385 pycodestyle violations |
| Global State | 6/10 | MEDIUM | 2 mutable module-level globals |

---

## 1. EXCEPTION HANDLING (Score: 8/10)

### Status: Substantially Improved

The previous audit (April 2026) documented 17 bare `except:` clauses. **Current count: 0** — all have been narrowed to specific exception types.

### Remaining Issues

| File | Line | Issue | Severity |
|------|------|-------|----------|
| `core/engine.py` | 211, 1168, 1570 | `except Exception as e` — too broad | MEDIUM |
| `core/execution.py` | 132, 224 | Same | MEDIUM |
| `core/common.py` | 482, 497 | Same | MEDIUM |
| `core/image_manager.py` | 56 | Same | MEDIUM |
| `core/math_utils.py` | 408 | Same | MEDIUM |
| `preset_handler.py` | 250 | Same | MEDIUM |
| `ops.py` | 753, 833 | Same | MEDIUM |
| `automation/*.py` | multiple | Same | MEDIUM |

These should be narrowed to the specific exceptions actually expected (e.g., `AttributeError`, `RuntimeError`, `ReferenceError`).

---

## 2. IMPORT ORGANIZATION (Score: 5/10)

### §3.13.2 of Google Style: Three Groups

**Violations: 28 × E402 + 40 unused imports**

### 2.1 E402 — Imports Not at Top of File

| File | Lines |
|------|-------|
| `__init__.py` | 15-37 (13 imports buried inside `get_classes`) |
| `test_cases/helpers.py` | 265 |
| `test_cases/suite_cleanup.py` | 11-12 |
| `test_cases/suite_context_lifecycle.py` | 11-14 |
| `test_cases/suite_denoise.py` | 11-13 |
| `test_cases/suite_export.py` | 11-12 |
| `test_cases/suite_udim_advanced.py` | 12-13 |

### 2.2 Unused Imports (40 instances)

Significant examples that should be cleaned:

| File | Unused Import |
|------|---------------|
| `ops.py` | `traceback`, `List`, `apply_baked_result`, `safe_context_override`, `check_objects_uv` |
| `core/engine.py` | `reset_channels_logic`, `DEFAULT_BAKE_TARGET` |
| `core/common.py` | `SOCKET_DEFAULT_TYPE` |
| `core/math_utils.py` | `List` |
| `core/node_manager.py` | `Dict`, `Tuple` |
| `property.py` | `DENOISE_METHODS`, `ATLAS_PACK_METHODS` |
| `headless_bake.py` | `os`, `logging` |
| `cli_runner.py` | `os` |
| `thumbnail_manager.py` | `os` |

Many test files also import setup-only utilities (`ensure_cycles`, `MockSetting`, `assert_no_leak`, etc.) that are never referenced in the test body.

### 2.3 Import Order Convention

Google Style mandates: `stdlib → third-party → local`. Several files mix these:

- `core/execution.py` imports `os` (stdlib) after `state_manager` (local)
- `ui.py` imports `bpy` (third-party) after `os` (stdlib)
- `ops.py` imports `bpy` (third-party) after `json`, `Path` (stdlib) — correct order, but interspersed with local imports

**Recommendation:** Use `isort` with black-compatible config.

---

## 3. CODE DOCUMENTATION (Score: 3/10)

### §3.8 of Google Style: Docstrings Required

### 3.1 Module Docstrings — 34 Missing

Automation modules without docstrings:
- `cli_runner.py`, `multi_version_test.py`, `dev_tools/extract_translations.py`

All test suite files:
- `suite_api.py` through `suite_verification.py` (21 files total)

Core modules without docstrings:
- `constants.py`, `preset_handler.py`, `property.py`
- `core/cage_analyzer.py`, `core/common.py`, `core/engine.py`, `core/math_utils.py`, `core/shading.py`, `core/thumbnail_manager.py`, `core/uv_manager.py`

### 3.2 Class/Function Docstrings — 170 Missing

Key classes without docstrings:

| File | Class | Lines |
|------|-------|-------|
| `__init__.py` | `BakeNexusPreferences` | 32 |
| `execution.py` | `BakeModalOperator` | 180 |
| `cli_runner.py` | Top-level functions | 131 |
| `multi_version_test.py` | Top-level functions | 170 |
| `extract_translations.py` | `TranslationExtractor` | 130 |

Key functions:

| File | Function | Lines |
|------|----------|-------|
| `core/engine.py` | `apply_denoise` | 121 |
| `core/engine.py` | `BakeStepRunner.run` | 129 |
| `core/engine.py` | `TaskBuilder.build` | 94 |
| `core/image_manager.py` | `set_image` | 84 |
| `core/image_manager.py` | `save_image` | 125 |
| `core/node_manager.py` | `bake_node_to_image` | 88 |
| `ui.py` | `BAKE_PT_BakePanel.draw` | 101 |
| `ops.py` | `_run_isolated_test_suite` | 87 |

### 3.3 Google Style Docstring Format

All docstrings should follow the Google format:
```python
"""One-line summary.

Args:
    param_name: Description.

Returns:
    Description of return value.
"""
```

Current docstrings use a mix of reStructuredText, Google, and blank. `SUITE_UNIT.py` tests reference tests via `# Comment` rather than docstrings.

---

## 4. FUNCTION COMPLEXITY (Score: 4/10)

### §3.5 of Google Style: Functions Should Be Small

### 4.1 Functions > 80 Lines (18 detected)

| File | Function | Lines |
|------|----------|-------|
| `ui.py` | `BAKE_PT_BakePanel.draw` | 101 |
| `ui.py` | `draw_saves` | 94 |
| `ui.py` | `draw_inputs` | 81 |
| `core/engine.py` | `apply_denoise` | 121 |
| `core/engine.py` | `BakeStepRunner.run` | 129 |
| `core/engine.py` | `TaskBuilder.build` | 94 |
| `core/image_manager.py` | `set_image` | 84 |
| `core/image_manager.py` | `save_image` | 125 |
| `core/node_manager.py` | `bake_node_to_image` | 88 |
| `core/shading.py` | `create_preview_material` | 128 |
| `core/cage_analyzer.py` | `run_raycast_analysis` | 143 |
| `core/common.py` | `apply_baked_result` | 81 |
| `automation/cli_runner.py` | `main` | 131 |
| `automation/multi_version_test.py` | `main` | 169 |
| `automation/multi_version_test.py` | `write_summary_reports` | 84 |
| `ops.py` | `_run_isolated_test_suite` | 87 |
| `test_cases/suite_production_workflow.py` | `test_full_pipeline_execution` | 81 |

### 4.2 Refactoring Priority

**High:** `BakeStepRunner.run` (129 lines) has 5+ levels of nesting inside a single `with ExitStack()` block. The denoise scene lifecycle, channel loop, packing, and post-bake could be separate methods.

**Medium:** `BAKE_PT_BakePanel.draw` (101 lines) drives all sub-sections; could delegate to `draw_inputs`, etc. (which exist).

---

## 5. TYPE ANNOTATIONS (Score: 3/10)

### §3.19 of Google Style: Use Type Hints

| Metric | Value |
|--------|-------|
| Total functions | 546 |
| Functions with ANY type annotation | 161 (29.5%) |
| Functions with return type | ~80 (15%) |
| Functions with arg types | ~150 (27%) |

### 5.1 Key Public APIs Missing Types

| File | Function |
|------|----------|
| `core/common.py` | `reset_channels_logic`, `manage_objects_logic` |
| `core/image_manager.py` | `set_image` (partial — `basiccolor`, `tile_resolutions` missing) |
| `core/engine.py` | `_execute_blender_bake_op` |
| `ops.py` | Most `execute()` methods |

### 5.2 'Any' Abused

`Any` is used extensively as an escape hatch (e.g., `setting: Any`). Most of these should be `Protocol` classes or at minimum `bpy.types.PropertyGroup`:

- `core/common.py` — 45 occurrences of `Any`
- `core/engine.py` — 10 occurrences
- `core/image_manager.py` — 6 occurrences

---

## 6. NAMING CONVENTIONS (Score: 5/10)

### §3.16 of Google Style

### 6.1 Ambiguous Names — 10 × E741

`l` used as variable name (confusable with `1`):

| File | Lines |
|------|-------|
| `ui.py` | 504, 508, 520, 636, 647, 718, 729, 755, 766, 850, 861 |
| `core/node_manager.py` | 147-148 |
| `core/uv_manager.py` | 191 |
| `test_cases/suite_api.py` | 26-27 |
| `test_cases/suite_code_review.py` | 134 |
| `test_cases/suite_memory.py` | 179-180 |

### 6.2 Blender-Specific Naming (Acceptable)

The following patterns are **required by Blender** and should be ignored:
- `BAKETOOL_OT_*` — Operator classes
- `BAKE_PT_*` — Panel classes  
- `BAKETOOL_UL_*` — UIList classes
- `Suite*` — unittest classes

### 6.3 Module-Level Constants

Google Style: `ALL_CAPS`. The following are uppercase correctly:
- `constants.py` — all OK

But some internal constants in modules use mixed case (e.g., `_LEGACY_DEPTH_MAP` in `property.py`). These should be `_LEGACY_DEPTH_MAP` (already correct with underscore prefix).

---

## 7. WHITESPACE & FORMATTING (Score: 5/10)

### 7.1 Total pycodestyle Counts (385 violations)

| Code | Count | Meaning |
|------|-------|---------|
| W293 | 196 | Blank line contains whitespace |
| W503 | 27 | Line break before binary operator |
| W291 | 23 | Trailing whitespace |
| E302 | 22 | Expected 2 blank lines (found 1) |
| E305 | 16 | Expected 2 blank lines after class/func |
| E402 | 28 | Module level import not at top |
| E261 | 13 | At least 2 spaces before inline comment |
| E501 | 11 | Line too long (> 120) |
| E701 | 5 | Multiple statements on one line (colon) |
| E111/E117 | 7/3 | Indentation not multiple of 4 / over-indented |
| E741 | 10 | Ambiguous variable name `l` |
| E226 | 11 | Missing whitespace around operator |
| W292 | 2 | No newline at EOF |
| E231 | 2 | Missing whitespace after `,` |

### 7.2 Worst Offenders

| File | Count | Main Issues |
|------|-------|-------------|
| `test_cases/suite_production_workflow.py` | ~90 | W293 (blank line whitespace) |
| `test_cases/suite_context_lifecycle.py` | ~50 | W293 |
| `core/execution.py` | ~45 | W293, W291, E111 |
| `core/shading.py` | ~35 | W293, W291 |
| `core/engine.py` | ~15 | W293, W291, W503, E501 |
| `ui.py` | ~15 | E741, W293, W503 |

### 7.3 Google Style Line Length

Set at 120 chars (above Google's 80, but consistent with the project's `pyproject.toml` target). 11 lines exceed even 120:

- `core/engine.py:1499` (126 chars)
- `core/execution.py:141` (130 chars)
- `test_cases/suite_denoise.py:40-41` (134, 122 chars)
- `test_cases/suite_production_workflow.py:88,171,326-327` (131, 124, 124, 148 chars)
- `test_cases/suite_negative.py:125,149` (130, 121 chars)
- `test_cases/suite_cleanup.py:49` (130 chars)

---

## 8. GLOBAL STATE (Score: 6/10)

### §3.13.3 of Google Style: Avoid Module-Level State

```python
# __init__.py
classes_to_register = []  # mutable global
addon_keymaps = []        # mutable global
```

These are mutated in `register()` and `unregister()`. They are scoped to the module and not exported, but they could be:

```python
class _RegistryState:
    _classes: list = []
    _keymaps: list = []
```

---

## 9. COMPREHENSIVE REMEDIATION PLAN

### Phase 1: Clean-Up (1-2 hours, no behavior change)

1. Remove **40 unused imports** across 25 files.
2. Fix **196 blank line whitespace** (W293) — `find . -name '*.py' -exec sed -i 's/[[:space:]]*$//' {} +`
3. Fix **23 trailing whitespace** (W291) — same command.
4. Add missing **newlines at EOF** in `core/math_utils.py` and `core/thumbnail_manager.py`.
5. Fix **7 indentation issues** (E111/E117) in `core/execution.py:110-115, 210-211`.

### Phase 2: Imports & Naming (2-3 hours)

1. Reconcile 28 E402 violations:
   - `__init__.py`: move all imports above `bl_info` (Google Style allows `bl_info` as the only exception before imports; alternatively move `get_classes` below imports).
   - Test files: use `from baketool.test_cases.helpers import ...` at top-level.
2. Rename 10+ occurrences of `l` → `_layout` or `col` in `ui.py`, `node_manager.py`, `uv_manager.py`, test files.
3. Add `isort` to CI pipeline with `--profile black` config.

### Phase 3: Documentation (4-6 hours)

1. Add **34 module docstrings** — focus on `core/*.py`, `automation/*.py`, and all test suite files.
2. Add **170 missing class/function docstrings** — priority on `BakeStepRunner`, `BakePostProcessor`, `BakePassExecutor`, `ModelExporter`, and operator classes.
3. Standardize on Google docstring format.

### Phase 4: Type Annotations (6-8 hours)

Goal: raise from 29.5% to 50%+ coverage.

1. Add return types to all public functions in `core/*.py`.
2. Replace `Any` with `bpy.types.PropertyGroup`, `Protocol`, or `TypeVar` in:
   - `PropertyIO.from_dict/to_dict`
   - `SceneSettingsContext`
   - All `setting: Any` parameters.
3. Add `-> Set[str]` return type to all operator `execute()` and `invoke()` methods.

### Phase 5: Function Complexity (4-6 hours)

1. Break `BakeStepRunner.run` (129 lines): extract channel loop → `_process_channel()`, packing → `_pack_channels()`.
2. Break `BAKE_PT_BakePanel.draw` (101 lines): sub-sections already exist as methods — ensure they are the only draw paths.
3. Break `clr.py:main` (131 lines) and `multi_version_test.py:main` (169 lines): extract report building and path discovery.

### Phase 6: CI Integration (1 hour)

1. Remove all suppression codes from the CI pycodestyle ignore list gradually.
2. Enable `ruff` with selected rules (I, N, W, E sections except suppressed).
3. Add `mypy --strict` on `core/api.py` as a starting point for type checking.

---

## 10. FILE-BY-FILE PRIORITY

### Production Code (Highest Priority)

| File | Score | Key Issues | Est. Fix |
|------|-------|------------|----------|
| `core/engine.py` | 4/10 | ~15 format, 2 long funcs, missing docstrings | 4h |
| `core/execution.py` | 3/10 | ~45 format, 7 indent errors, missing class doc | 1h |
| `ui.py` | 5/10 | 10 ambiguous names, ~15 format | 2h |
| `core/image_manager.py` | 5/10 | 2 long funcs, missing docstrings | 2h |
| `core/common.py` | 5/10 | 1 long func, Any abuse | 2h |
| `core/node_manager.py` | 5/10 | format, ambiguous name, missing doc | 1h |
| `ops.py` | 6/10 | unused imports, format | 1h |
| `__init__.py` | 6/10 | 13 E402, mutable globals | 1h |
| `preset_handler.py` | 7/10 | missing module doc | 30min |
| `property.py` | 7/10 | 2 unused imports, missing module doc | 30min |

### Test Code (Lower Priority)

| File | Count | Main Issues |
|------|-------|-------------|
| `suite_production_workflow.py` | ~90 | W293, E501 |
| `suite_context_lifecycle.py` | ~50 | W293 |
| `suite_negative.py` | ~20 | W293, E501 |
| `suite_shading.py` | ~20 | W293, W291 |
| `helpers.py` | 1 | E402 |

### Build/Automation

| File | Issues |
|------|--------|
| `automation/cli_runner.py` | missing module doc, 1 unused import, 1 long func |
| `automation/multi_version_test.py` | missing module doc, 2 long funcs |
| `dev_tools/extract_translations.py` | missing module doc, missing class doc |

---

## 11. TOOLS RECOMMENDATION

### Immediate

```bash
# Fix all whitespace in one pass:
find . -name "*.py" -not -path "./.venv/*" -not -path "./.git/*" \
  -exec sed -i 's/[[:space:]]*$//' {} +

# Install isort + black (style enforcement):
pip install isort black mypy ruff
isort --profile black .
black --line-length 120 .
```

### CI Configuration

```yaml
- name: Style Enforcement
  run: |
    isort --check-only --profile black --line-length 120 .
    ruff check --select=I,N,W,E .
```

### Long-Term

- Switch from `pycodestyle` to `ruff` for 10-100x faster linting.
- Enable `mypy` incrementally: start with `core/api.py`, then `core/compat.py`, then `preset_handler.py`.
- Use `pydocstyle` with Google convention for docstring enforcement.

---

## 12. OVERALL ASSESSMENT

The codebase has **good structural architecture** (clear separation into `core/`, `ops.py`, `ui.py`, `property.py`) and **strong test coverage** (158 tests across 22 suites, cross-version verified). The practical functionality is solid.

The style debt is concentrated in:

1. **Test files** — bulk of formatting issues (W293, W291). Test files were written for coverage, not style.
2. **Docstrings** — 34/48 modules lack docstrings; 170 missing class/func docstrings.
3. **Type annotations** — only 29.5% coverage, heavy use of `Any`.
4. **Unused imports** — 40 instances, mostly accumulated during refactors.

**None of these issues represent an immediate release blocker.** The previous bare-except problem (which was a correctness risk) has been fully resolved. The remaining issues are maintainability concerns: they will slow down future development and make onboarding harder.

**Recommended order:**
1. Fix Phase 1 (whitespace, unused imports) — automated, low risk, can be done before any further feature work.
2. Fix Phase 3 (docstrings) — as you touch each file for other changes, add the module docstring and class docstring.
3. Fix Phase 4 (types) — incrementally, one file at a time.

Setting a hard deadline for full Google Style compliance is not realistic for a solo-maintainer project; instead, integrate automated checks (isort, ruff, `py_compile`) into CI so new contributions don't add new style debt.
