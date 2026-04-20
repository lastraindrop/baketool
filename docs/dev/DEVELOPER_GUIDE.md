# BakeTool Developer Guide

**Version:** 1.0.0
**Last Updated:** 2026-04-17

---

## Overview

This guide provides architecture documentation, technical specifications, and known issues for BakeTool development. Following this guide enables effective contribution while maintaining code quality and cross-version compatibility.

---

## Chapter 1: Architecture Design

### 1.1 Three-Layer Architecture

BakeTool follows a **UI-Engine-Core** three-layer logic division:

```
┌─────────────────────────────────────────────────────┐
│  UI / Operator Layer                                 │
│  ops.py, ui.py                                      │
│  - Data-driven UI (CHANNEL_UI_LAYOUT)             │
│  - Operators (Thin Operators)                     │
│  - Environment health monitoring                  │
├─────────────────────────────────────────────────────┤
│  Engine Layer (Orchestration)                      │
│  core/engine.py                                    │
│  - JobPreparer: Validate input and prepare queue │
│  - BakePassExecutor: Execute bake steps            │
│  - BakeStepRunner: Async bake controller           │
│  - BakePostProcessor: Denoise post-processing     │
├─────────────────────────────────────────────────────┤
│  Core Layer (Stateless Utilities)                  │
│  core/*.py                                         │
│  - image_manager: Image management                │
│  - node_manager: Node operations                 │
│  - uv_manager: UV layer handling                  │
│  - shading: Shader utilities                       │
│  - common: Shared utilities                       │
│  - compat: Version compatibility                  │
└─────────────────────────────────────────────────────┘
```

### 1.2 Core Components

#### 1.2.1 JobPreparer

Responsible for validating input and preparing execution queue:

```python
class JobPreparer:
    @staticmethod
    def prepare_execution_queue(context, jobs) -> List[BakeStep]:
        """Validate inputs and prepare execution queue"""
        queue = []
        for job in jobs:
            if not job.enabled:
                continue
            # Validate objects
            # Prepare channel config
            # Create BakeStep
            queue.append(step)
        return queue
```

#### 1.2.2 BakePassExecutor

Executes individual bake step pipeline:
```python
class BakePassExecutor:
    @staticmethod
    def execute(context, setting, task, channel, ...) -> Image:
        """Execute single bake pass"""
        # 1. Create/select target image
        # 2. Set up bake context
        # 3. Execute Blender bake operation
        # 4. Apply post-processing
        return image
```

#### 1.2.3 BakeStepRunner

Controls asynchronous execution with error handling:
```python
class BakeStepRunner:
    def __init__(self, context, scene):
        self.context = context
        self.scene = scene

    def run(self, step, state_mgr=None, queue_idx=0) -> List[Dict]:
        """Execute single step with full context management"""
        # Orchestrates UV setup, node graph, bake, save, channel packing
```

#### 1.2.4 BakePostProcessor

Handles denoising and post-processing:
```python
class BakePostProcessor:
    @staticmethod
    def apply_denoise(context, images, method) -> None:
        """Apply denoising using OIDN"""
        # Uses Blender compositor with OIDN
```

---

## Chapter 2: Data Flow

### 2.1 Execution Flow

```
User Click "START BAKE PIPELINE"
        │
        ▼
JobPreparer.prepare_execution_queue()
        │ Validates jobs, objects, channels
        ▼
BakeStepRunner.run() [Modal Loop]
        │
        ├─► BakeContextManager (Context preservation)
        ├─► UVLayoutManager (UV preparation)
        ├─► NodeGraphHandler (Node setup)
        ├─► BakePassExecutor (Execute bake)
        ├─► ImageManager (Save to disk)
        ├─► ChannelPacker (ORM packing)
        └─► BakePostProcessor (Denoise)
        │
        ▼
Result (Apply to scene / Export)
```

### 2.2 Named Tuples

BakeStep and BakeTask use named tuples for lightweight data passing:

```python
# In constants.py
BakeStep = namedtuple('BakeStep', ['job', 'task', 'channels', 'frame_info'])
BakeTask = namedtuple('BakeTask', ['base_name', 'object', 'udim_tile', ...])
```

---

## Chapter 3: Naming Conventions

### 3.1 File Naming
- **Modules**: `snake_case.py` (e.g., `image_manager.py`)
- **Classes**: `PascalCase` (e.g., `BakeStepRunner`)
- **Functions**: `snake_case()` (e.g., `save_image()`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `BAKE_TYPES`)

### 3.2 Blender-Specific Conventions

Due to Blender API requirements:
- **Operators**: `BAKETOOL_OT_*` (e.g., `BAKETOOL_OT_BakeOperator`)
- **Panels**: `BAKE_PT_*` (e.g., `BAKE_PT_BakePanel`)
- **UI Lists**: `BAKETOOL_UL_*`
- **PropertyGroups**: `Bake*Settings` (e.g., `BakeJobSetting`)

### 3.3 System Names

Avoid name collisions with Blender internal names:
```python
SYSTEM_NAMES = {
    "TEMP_UV": "BT_Bake_Temp_UV",      # Prefix with BT_
    "DUMMY_IMG": "BT_Protection_Dummy",
    "PROTECTION_NODE": "BT_Protection_Node",
}
```

---

## Chapter 4: Version Compatibility

### 4.1 Blender Version Detection

```python
# In core/compat.py
def is_blender_5() -> bool:
    return bpy.app.version >= (5, 0, 0)

def is_blender_4() -> bool:
    return bpy.app.version >= (4, 0, 0) and bpy.app.version < (5, 0, 0)
```

### 4.2 Common Compatibility Issues

| Issue | Blender 3.x | Blender 4.x+ | Solution |
|-------|-------------|--------------|----------|
| Vertex Colors | `vertex_colors` | Deprecated | Use mesh attributes API |
| Bake Types | `scene.render.bake_type` | `scene.cycles.bake_type` | Use compat function |

### 4.3 Testing Multi-Version

```bash
# Run automated multi-version tests
python automation/multi_version_test.py --verification
```

---

## Chapter 5: Testing Framework

### 5.1 Test Suites

| Suite | Purpose |
|-------|---------|
| `suite_unit.py` | Unit tests for core functions |
| `suite_memory.py` | Memory leak detection |
| `suite_export.py` | Export safety tests |
| `suite_api.py` | API stability tests |
| `suite_code_review.py` | Code quality checks |

### 5.2 Running Tests

```bash
# Run all tests via Blender
blender -b --python automation/cli_runner.py -- --suite all

# Run specific suite
blender -b --python automation/cli_runner.py -- --suite unit
```

### 5.3 CI/CD Integration

Tests automatically run on:
- Pull requests
- Version tags
- Scheduled daily builds

---

## Chapter 6: Coding Standards

### 6.1 Error Handling

**Always use specific exceptions:**

```python
# BAD
try:
    operation()
except Exception:
    pass

# GOOD
try:
    operation()
except (OSError, FileNotFoundError) as e:
    logger.warning(f"Operation failed: {e}")
```

### 6.2 Type Annotations

Add type annotations for public functions:

```python
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

### 6.3 Docstrings

Follow Google style for docstrings:

```python
class BakeStepRunner:
    """Executes a single bake step with full context management.

    Handles context switching, UV layout setup, node graph manipulation,
    bake execution, result saving, and channel packing.

    Args:
        context: Blender context. Uses bpy.context if None.
        scene: Target scene. Uses context.scene if None.
    """

    def run(self, step: BakeStep) -> List[Dict[str, Any]]:
        """Execute a single Step and return generated results.

        Returns:
            List of dicts containing image data and metadata.
        """
        pass
```

---

## Chapter 7: API Reference

### 7.1 Core Modules

| Module | Purpose | Public API |
|--------|---------|------------|
| `api.py` | Public API | `api.bake()`, `api.get_udim_tiles()` |
| `engine.py` | Bake orchestration | `JobPreparer`, `BakeStepRunner` |
| `image_manager.py` | Image handling | `set_image()`, `save_image()` |
| `node_manager.py` | Node operations | `NodeGraphHandler` |
| `uv_manager.py` | UV operations | `UVLayoutManager`, `detect_object_udim_tile()` |

### 7.2 Constants

Key constants defined in `constants.py`:
- `CHANNEL_BAKE_INFO` - Channel metadata
- `CHANNEL_UI_LAYOUT` - Data-driven UI configuration
- `FORMAT_SETTINGS` - Image format technical settings

---

## Chapter 8: Build and Release

### 8.1 Release Checklist

Before releasing:
- [ ] Run full test suite
- [ ] Update version in `bl_info` (\_\_init\_\_.py)
- [ ] Sync versions in `blender_manifest.toml`
- [ ] Update `translations.json` header
- [ ] Update ROADMAP.md with release notes
- [ ] Run syntax validation: `python -m py_compile *.py`

### 8.2 Creating Release Package

```bash
# Build using MANIFEST.in
python -m build

# Or manual packaging
cd baketool
zip -r baketool.zip . -x "automation/*" "test_cases/*" "docs/dev/*"
```

---

## Chapter 9: Known Issues

### 9.1 AI-Generated Code Risks

Due to AI-assisted development:
- Possible boundary case errors
- Potential edge case not handled
- Limited production validation

**Mitigation:**
- Comprehensive test suite (220+ tests)
- User feedback encouraged
- Regular updates

### 9.2 Performance Notes

- Large resolution baking (>4K) may cause memory issues
- Recommend GPU baking for speed
- Use tiled baking for extremely large textures

---

## Appendix A: Directory Structure

```
baketool/
├── __init__.py              # Main addon entry
├── ops.py                  # Operator definitions
├── ui.py                   # UI panel definition
├── property.py             # PropertyGroup definitions
├── constants.py            # Constants and enums
├── translations.py         # Translation system
├── translations.json       # Translation data
├── state_manager.py        # Session state management
├── preset_handler.py      # Preset serialization
├── core/                   # Core modules
│   ├── __init__.py       # Module exports
│   ├── api.py            # Public API
│   ├── engine.py         # Bake engine
│   ├── execution.py      # Modal execution
│   ├── image_manager.py # Image management
│   ├── node_manager.py  # Node operations
│   ├── uv_manager.py    # UV operations
│   ├── shading.py       # Shading utilities
│   ├── cage_analyzer.py # Cage analysis
│   ├── common.py        # Common utilities
│   ├── compat.py       # Version compatibility
│   └── math_utils.py    # Math utilities
├── automation/             # Automation tools
│   ├── cli_runner.py
│   ├── headless_bake.py
│   └── multi_version_test.py
├── dev_tools/              # Development tools
└── docs/                   # Documentation
```

---

## Appendix B: Contribution Guidelines

1. **Fork** this repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** changes (`git commit -m 'Add amazing feature'`)
4. **Push** to branch (`git push origin feature/amazing-feature`)
5. **Create** Pull Request

---

## Appendix C: Support

- **Issue Reports**: [GitHub Issues](https://github.com/lastraindrop/baketool/issues)
- **Feature Requests**: [GitHub Discussions](https://github.com/lastraindrop/baketool/discussions)
- **Documentation Fixes**: Pull Request

---

*Developer Guide Version 1.0.0*
*Last Updated: 2026-04-17*