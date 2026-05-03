# BakeNexus Code Style Analysis Report
## Based on Google Python Style Guide

**Date:** 2026-04-17
**Status:** Remediation In Progress - HIGH Priority Fixes Complete

---

## Executive Summary

The BakeNexus codebase was analyzed against Google Python Style Guide. The analysis revealed several categories of issues ranging from critical (bare except clauses) to minor (import organization).

**Overall Health Score:** 6.5/10

| Category | Score | Priority |
|----------|-------|----------|
| Exception Handling | 4/10 | HIGH |
| Code Documentation | 5/10 | HIGH |
| Function Complexity | 5/10 | HIGH |
| Type Safety | 6/10 | MEDIUM |
| Naming Conventions | 7/10 | LOW |
| Whitespace/Formatting | 7/10 | LOW |
| Import Organization | 7/10 | LOW |

---

## 1. EXCEPTION HANDLING (Priority: HIGH)

### 1.1 Bare Except Clauses Found

| File | Line | Issue | Status |
|------|------|-------|--------|
| `state_manager.py` | 66 | `except Exception: pass` | Fixed |
| `state_manager.py` | 91 | `except Exception: pass` | Fixed |
| `state_manager.py` | 102 | `except Exception: pass` | Fixed |
| `core/cleanup.py` | 83 | `except Exception: pass` | Fixed |
| `core/cleanup.py` | 93 | `except Exception: pass` | Fixed |
| `core/cleanup.py` | 104 | `except Exception: pass` | Fixed |
| `core/engine.py` | 178 | `except Exception: pass` | Fixed |
| `core/engine.py` | 252 | `except Exception: pass` | Fixed |
| `core/engine.py` | 341 | `except Exception as e` | Fixed |
| `core/engine.py` | 985 | `except Exception as e` | Fixed |
| `core/engine.py` | 1006 | `except Exception as e` | Fixed |
| `core/engine.py` | 1106 | `except Exception: pass` | Fixed |
| `core/engine.py` | 1120 | `except Exception: pass` | Fixed |
| `core/engine.py` | 1122 | `except Exception: pass` | Fixed |
| `ops.py` | 450 | `except Exception as e` | Fixed |
| `ops.py` | 477 | `except Exception as e` | Fixed |
| `ops.py` | 503 | `except Exception: pass` | Fixed |

### 1.2 Recommendation

Replace bare `except:` with specific exceptions:

```python
# BAD
try:
    os.remove(self.log_file)
except Exception:
    pass

# GOOD
try:
    os.remove(self.log_file)
except (OSError, FileNotFoundError):
    pass  # File doesn't exist, which is fine
except PermissionError:
    _LOG.warning("Could not remove log file: %s", self.log_file)
```

---

## 2. DOCUMENTATION (Priority: HIGH)

### 2.1 Missing Docstrings

#### Files Without Module Docstrings:
- `core/__init__.py` Fixed - Added module docstring

#### Classes Without Docstrings (Major):

| File | Class | Lines |
|------|-------|-------|
| `ops.py` | `BAKETOOL_OT_BakeOperator` | 100 |
| `ops.py` | `BAKETOOL_OT_OneClickPBR` | 300 |
| `ops.py` | `BAKETOOL_OT_LoadSetting` | 340 |
| `ops.py` | `BAKETOOL_OT_SaveSetting` | 380 |
| `core/engine.py` | `BakePostProcessor` | 80 |
| `core/engine.py` | `BakeStepRunner` | 120 |
| `core/engine.py` | `ModelExporter` | 970 |
| `core/node_manager.py` | `BakeNodeBuilder` | 84 |
| `core/shading.py` | All classes | - |
| `ui.py` | `BAKE_PT_BakePanel` | 401 |
| `ui.py` | `BAKE_PT_NodePanel` | 367 |

### 2.2 Recommendation

Add docstrings following Google Style:

```python
# BAD
class BAKETOOL_OT_BakeOperator(bpy.types.Operator, BakeModalOperator):
    bl_label = "Bake"
    bl_idname = "bake.bake_operator"

# GOOD
class BAKETOOL_OT_BakeOperator(bpy.types.Operator, BakeModalOperator):
    """Executes the texture baking process for selected objects.

    This operator handles the complete baking pipeline including
    UV preparation, cage generation, and image output.

    Args:
        context: Blender context with selected objects.

    Returns:
        set: {'FINISHED'} on success, {'CANCELLED'} on failure.
    """
    bl_label = "Bake"
    bl_idname = "bake.bake_operator"
```

---

## 3. FUNCTION COMPLEXITY (Priority: HIGH)

### 3.1 Functions Exceeding 40 Lines (Recommended Max)

| File | Function | Lines | Complexity |
|------|----------|-------|------------|
| `core/engine.py` | `BakeStepRunner.run` | 152 | HIGH |
| `core/engine.py` | `ModelExporter.export` | 152 | HIGH |
| `core/node_manager.py` | `BakeNodeBuilder` class | 387 | HIGH |
| `ui.py` | `BAKE_PT_BakePanel.draw` | 89 | MEDIUM |
| `core/common.py` | `create_simple_baked_material` | 72 | MEDIUM |
| `core/node_manager.py` | `cleanup` | 70 | MEDIUM |
| `core/node_manager.py` | `_create_extension_logic` | 73 | MEDIUM |

### 3.2 Recommendation

Break long functions into smaller, focused helpers:

```python
# Example: Break up ModelExporter.export()
class ModelExporter:
    """Handles exporting meshes for baking."""

    def export(self, context, obj, setting, file_name):
        """Main export entry point."""
        mesh = self._prepare_mesh(obj)
        self._apply_transforms(mesh, obj)
        self._write_to_file(mesh, file_name, setting)

    def _prepare_mesh(self, obj):
        """Extract and prepare mesh data."""
        pass

    def _apply_transforms(self, mesh, obj):
        """Apply object transforms to mesh."""
        pass

    def _write_to_file(self, mesh, file_name, setting):
        """Write mesh to temporary file."""
        pass
```

---

## 4. TYPE ANNOTATIONS (Priority: MEDIUM)

### 4.1 Functions Missing Type Hints

Key functions that would benefit from type annotations:

| File | Function | Current |
|------|----------|---------|
| `core/common.py` | `reset_channels_logic()` | No types |
| `core/common.py` | `manage_objects_logic()` | No types |
| `core/engine.py` | `_physical_clear_pixels()` | No types |
| `core/image_manager.py` | `set_image()` | Partial types |
| `ops.py` | `execute()` (most operators) | No types |

### 4.2 Recommendation

Add type annotations gradually, starting with public APIs:

```python
# GOOD
from typing import List, Optional, Tuple

def set_image(
    name: str,
    x: int,
    y: int,
    alpha: bool = True,
    context: Optional[bpy.types.Context] = None,
) -> bpy.types.Image:
    """Get or create an image with specified settings."""
    pass
```

---

## 5. NAMING CONVENTIONS (Priority: LOW)

### 5.1 Minor Issues

| Issue | Location | Recommendation |
|-------|----------|----------------|
| `_DummyEvent` class prefix | `ops.py:40` | Rename to `DummyEvent` (internal use) |
| Mixed `self.report()` vs `logger` | Multiple | Standardize on logger for debug, report for user |

### 5.2 Blender-Specific Naming

The following naming patterns are **acceptable** due to Blender requirements:
- `BAKETOOL_OT_*` - Operator classes
- `BAKE_PT_*` - Panel classes
- `BAKETOOL_UL_*` - UIList classes

---

## 6. IMPORT ORGANIZATION (Priority: LOW)

### 6.1 Current State

```python
# __init__.py - Current order (mixed)
import logging
import bpy  # Third-party
from bpy import props, types  # Third-party
from .core import cleanup  # Local
from . import ops  # Local
from .constants import CHANNEL_BAKE_INFO  # Local
```

### 6.2 Recommendation

Organize imports in three groups:

```python
# 1. Standard library
import logging
from pathlib import Path

# 2. Third-party (Blender)
import bpy
from bpy import props, types
from bpy.app.handlers import persistent
from bpy.props import IntProperty, CollectionProperty, StringProperty
from bpy.types import AddonPreferences

# 3. Local application
from .core import cleanup
from . import ops
from . import preset_handler
from . import translations
from . import ui
from . import property as prop_module
from .constants import CHANNEL_BAKE_INFO
```

---

## 7. CODE COMPLEXITY HOTSPOTS (Priority: MEDIUM)

### 7.1 Deep Nesting Issues

**File:** `core/common.py` - `manage_objects_logic()`

```python
# Current structure (5+ levels of nesting)
def manage_objects_logic(s, action, sel, act):
    if action == "SET":
        s.bake_objects.clear()
        targets = sel
        if s.bake_mode == "SELECT_ACTIVE" and act and act in targets:
            s.active_object = act
            targets = [o for o in targets if o != act]
        for o in targets:
            if not any(i.bakeobject == o for i in s.bake_objects):
                # ... more logic
```

### 7.2 Recommendation

Use early returns and dispatch patterns:

```python
def manage_objects_logic(s, action, sel, act):
    """Handle object list management based on action type."""
    if action == "REMOVE":
        _remove_objects(s, sel)
        return

    if action == "CLEAR":
        _clear_objects(s)
        return

    targets = _get_targets(s, action, sel, act)
    _add_objects(s, targets)


def _get_targets(s, action, sel, act):
    """Determine which objects to add based on mode."""
    if action == "SET":
        s.bake_objects.clear()
        return sel
    elif action == "ADD":
        return [o for o in sel if o != s.active_object]
    return []
```

---

## 8. WHITESPACE ISSUES (Priority: LOW)

### 8.1 Issues Found

| File | Line | Issue |
|------|------|-------|
| `ui.py` | 155 | `scene.baked_image_results_index>=0` |
| `core/uv_manager.py` | 13 | `!= 'MESH' or not` |
| `ops.py` | 39 | Long line with operators |

### 8.2 Recommendation

```python
# BAD
if scene.baked_image_results_index>=0:

# GOOD
if scene.baked_image_results_index >= 0:
```

---

## 9. GLOBAL STATE (Priority: MEDIUM)

### 9.1 Current Globals

```python
# __init__.py
classes_to_register = []  # Mutable global
addon_keymaps = []      # Mutable global
HAS_TESTS = False       # Constant
```

### 9.2 Recommendation

Encapsulate in a class or use module-level initialization:

```python
# Option 1: Use a class
class BakeNexusState:
    """Manages addon registration state."""
    _classes = []
    _keymaps = []

    @classmethod
    def register(cls, cls_to_add):
        cls._classes.append(cls_to_add)

# Option 2: Add underscore prefix to indicate private
_classes_to_register = []
_addon_keymaps = []
```

---

## 10. REMEDIATION PLAN

### Phase 1: Critical Fixes (1-2 weeks) - Completed
1. Replace all bare `except:` with specific exceptions (17 fixes applied)
2. Add docstrings to operator classes (deferred)
3. Fix whitespace issues (verified - already fixed)

### Phase 1.5: Code Review Critical Fixes (2026-04-17) - Completed
1. Fix `ui.py` undefined variables (draw_header, draw_file_path, draw_template_list_ops, draw_image_format_options, draw_crash_report)
2. Fix `core/node_manager.py` NodeGraphHandler.__init__ syntax error (missing `self.materials = [`)
3. Fix `core/common.py` SceneSettingsContext.__init__ not storing parameters
4. Fix `core/engine.py` BakeStepRunner.__init__ not storing parameters
5. Fix `core/uv_manager.py` UVLayoutManager.__init__ not storing parameters
6. Fix `state_manager.py` read_log duplicate dead code
7. Fix `core/engine.py` apply_denoise duplicate method definition
8. Fix `ops.py` DeleteResult duplicate removal logic
9. Sync blender_manifest.toml version (1.0.0)
10. Fix suite_code_review.py version assertion
11. Expand test_cases/__init__.py to import all 16 suites
12. Add UTF-8 encoding to SaveSetting/LoadSetting
13. Add typing.Any import to ui.py
14. Add comprehensive tests for all fixes

### Phase 2: Documentation (2-4 weeks) - IN PROGRESS
1. Add module docstrings (`core/__init__.py`)
2. Add class docstrings (pending)
3. Add function docstrings for public APIs (pending)

### Phase 3: Refactoring (4-8 weeks)
1. Break up long functions (>100 lines)
2. Add type annotations to public functions
3. Standardize logging

### Phase 4: Maintenance (Ongoing)
1. Add lint checks to CI/CD
2. Use `pylint` or `ruff` for automated checks
3. Code review checklist

---

## 11. TOOLS RECOMMENDATION

### 11.1 Linting Configuration (.pylintrc)

```ini
[MASTER]
load-plugins=pylint.extensions.docparams
max-line-length=120
max-args=8
max-returns=8
max-branches=15

[MESSAGES CONTROL]
disable=C0111,  # missing-docstring (defer)
         C0103,  # invalid-name (Blender naming)
         R0903,  # too-few-public-methods
         R0913,  # too-many-arguments
```

### 11.2 Ruff Configuration (pyproject.toml)

```toml
[tool.ruff]
line-length = 120
target-version = "py310"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "UP",  # pyupgrade
    "N",   # pep8-naming
]
ignore = [
    "N818",  # exception naming (Blender convention)
]
```

---

## 12. APPENDIX: FILE-BY-FILE SUMMARY

### High Priority Files (Need Immediate Attention)

| File | Issues | Est. Fix Time |
|------|--------|---------------|
| `core/cleanup.py` | 4 bare excepts | 30 min |
| `state_manager.py` | 2 bare excepts | 15 min |
| `ops.py` | Missing docstrings | 2 hours |
| `core/engine.py` | Long functions | 4 hours |

### Medium Priority Files

| File | Issues | Est. Fix Time |
|------|--------|---------------|
| `core/common.py` | Complex logic | 2 hours |
| `core/node_manager.py` | Long class | 3 hours |
| `ui.py` | Whitespace | 30 min |

### Low Priority Files

| File | Issues | Est. Fix Time |
|------|--------|---------------|
| `__init__.py` | Import order | 15 min |
| `translations.py` | OK | - |
| `constants.py` | OK | - |

---

## References

- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Blender Python API Style Guide](https://wiki.blender.org/wiki/Style_Guide/Python)
- [Real Python: Docstring Guide](https://realpython.com/documenting-python-code/)
