# BakeTool Roadmap

**Version:** 1.0.0
**Last Updated:** 2026-04-17
**Status:** Production Hardened

---

## Overview

BakeTool is a professional-grade texture baking plugin designed for Blender, supporting versions 3.3 through 5.0+. This roadmap details the strategic vision for evolving from a practical utility tool to a professional-grade baking middleware.

### Version History

| Version | Date | Status | Key Features |
|---------|------|--------|-------------|
| 1.0.0-rc | 2026-04-20 | Current | Core stability, full translation alignment |
| 1.0.0 | 2026-04-17 | Stable | Initial release, compatibility fixes |

---

## Phase 1: Experimental Phase (v1.0.0-rc)

**Goal**: Minimize risk through AI-assisted static analysis and controlled environment testing.

### 1.5 Core Stability & Internationalization (Completed)

**Status**: Completed (2026-04-20)

**Key Changes**:
- **Exception Chain Hardening**: Added fault-tolerant catching for cleanup callbacks to prevent crashes from individual object failures
- **Dynamic Parameter Alignment**: Established validation logic between UI properties and engine tasks, fixed bugs like `save_and_quit` logic reversal
- **Full Localization**: Deep scanned UI definitions, eliminated hardcoded English strings, fixed case mismatches causing translation misses

---

## Phase 2: Future Experimental Plans

Due to the project's small user base and slow feedback cycle, future development will proceed with extreme caution:

### First Phase: Visual and User Experience Exploration

**Goal**: Explore more intuitive baking feedback, reduce configuration confusion for new users.

---

### Second Phase: Pipeline Integration

**Goal**: Further decouple engine from UI. Acknowledging current single-file `engine.py` maintenance pressure.

- **Refactoring Vision**: Split task building, export, and core execution into reusable, testable chunks
- **AI Transparency**: Add more AI-generated test cases to compensate for manual testing gaps

---

### Third Phase: Code Quality and Maintainability

**Goal**: Strictly follow Google Python Style Guide, eliminate overconfidence biases in AI-generated code.

---

## Important Notice

BakeTool is an **early-stage experimental project**. It largely demonstrates AI's capability in assisting Blender scripting. We strongly advise users to **save and backup scene data before any operations**.

---

## Completed Features

### 1.2 Visual Cage Analysis

**Status**: Completed (v0.9.5)

**Function Description**:
Generates "heatmap" overlay on meshes showing cage intersection or detail-missing areas with high poly.

**Technical Implementation**:
- Uses BVH-Tree for raycast analysis between low-poly (with cage extrusion) and high-poly
- Red areas indicate "collision/missing", green indicates "safe"
- Error total displayed directly in object list

**User Experience Value**:
- Visualize "missing rays" or artifacts before committing to bake
- Reduce rework from improper cage settings

---

### 1.3 Asynchronous Progress UI

**Status**: Completed (Modal Progress event loop decoupling)

**Technical Implementation**:
- Uses `BakeModalOperator` to keep UI responsive during heavy baking
- Displays current channel, object, estimated remaining time
- Supports cancellation while preserving completed results

---

### 1.4 Automated UI Logic Guardian

**Status**: Completed (v0.9.0)

**Function Description**:
Statically analyzes `CHANNEL_UI_LAYOUT` and Blender RNA properties to prevent runtime UI crashes.

**Technical Implementation**:
- Auto-validates all UI channel properties exist
- Ensures new bake channels have 100% confidence
- Automated regression test coverage

---

## Second Phase: Pipeline Integration

**Goal**: Decouple engine from UI, enable headless operations and external script integration.

### 2.1 Engine-UI Decoupling

**Status**: Completed (v0.9.0 refinement)

**Technical Implementation**:
- Split god functions into granular methods:
  - `_create_target_image`: Image creation
  - `_execute_blender_bake_op`: Blender bake call
  - `_apply_numpy_processing`: NumPy processing

**User Experience Value**:
- Fully headless operations without active Viewport context
- Support for render farm and CI/CD pipeline integration

---

### 2.2 Public Python API

**Status**: Completed (v1.0.0)

**API Example**:
```python
from baketool.core import api

# Basic baking - use current scene's Job settings
result = api.bake(objects=bpy.context.selected_objects)
# Or use viewport selection
result = api.bake(use_selection=True)

# Get UDIM tiles
tiles = api.get_udim_tiles(bpy.context.selected_objects)

# Validate settings
is_valid, msg = api.validate_settings(bpy.context.scene.BakeJobs.jobs[0])
```

---

### 2.3 Preset Library 2.0 (Visual UI)

**Status**: Completed (v0.9.3)

**Features**:
- Dedicated preset gallery with thumbnail preview
- Dynamic refresh logic
- Support for custom library paths

---

### 2.4 Baking Performance Profiler

**Status**: Completed (v0.9.3)

**Features**:
- Bake Time vs Save Time for each channel
- Helps identify bottlenecks in large-scale asset production

---

## Third Phase: Intelligence and Algorithms

**Goal**: Use algorithmic assistance to replace manual trial-and-error.

### 3.1 Auto-Cage 2.1 (Proximity-Based)

**Status**: Completed (v0.9.0 Production Hardened)

**Technical Implementation**:
- NumPy ray tracing proximity analysis
- Algorithm predicts safe average extrusion distance
- Supports two modes:
  - `Uniform`: Traditional uniform extrusion
  - `Proximity`: Smart proximity mode

---

### 3.2 Smart Texel Density

**Status**: Completed (v1.0.0)

**Features**:
- Auto-calculates output resolution based on physical object size
- Ensures asset library quality consistency
- Supports target density in px/unit

---

### 3.3 Anti-Aliasing and Denoise Pipeline

**Status**: Completed (v0.9.3)

**Technical Implementation**:
- Integrated Intel OIDN (Open Image Denoise)
- Implemented via temporary compositor nodes
- Zero-leak scene cleanup

---

## Fourth Phase: Production Hardening and Ecosystem

**Goal**: 100% architecture stability, zero-leak scene management, cross-version parameter alignment.

### 4.1 Parameter Consistency & Dynamic Alignment

**Status**: 100% CI PASS (3.3, 3.6, 4.2, 4.5, 5.0+)

**Technical Implementation**:
- **Three-Point Alignment Protocol**: Constants ↔ Engine ↔ Automation
- Standardized `add_bake_result_to_ui` ensures metadata (bake_time, resolution) uses strict RNA contract mapping
- `suite_parameter_matrix.py` dynamically validates mapping across all Blender versions

**Test Coverage**:
- 70+ core test suites
- 80+ individual use cases
- Full coverage across 5 Blender versions

---

### 4.2 Zero-Leak Denoise Pipeline (Recursive Cleanup)

**Status**: Completed (v1.0.0)

**Technical Implementation**:
- Dedicated `finally` block logic
- Recursively identifies and clears all `BT_Denoise_Temp*` scenes
- Clears node trees and uses `user_clear()` to satisfy B5.0 deletion constraints

**Benefits**:
- Prevents memory spikes during batch baking
- Avoids "active scene" conflicts

---

### 4.3 Blender 5.0.x Full Support

**Status**: Completed (v1.0.0)

**Technical Implementation**:
- Robust tree discovery (Direct ↔ Compositor Object ↔ Fallback creation)
- Supports B5.0 unified node system (uses `CompositorNodeTree` ↔ `NodeGroupOutput`)
- Solves B5.0 registration constraints through forced integer defaults

**Cross-Version Validation**:
- Blender 3.3.21 ↔ Blender 3.6.23 ↔ Blender 4.2.14 LTS ↔ Blender 4.5.3 LTS ↔ Blender 5.0.1+

---

### 4.4 Production E2E Validation Loop

**Status**: Completed (v1.0.0)

**Toolchain**:
- `multi_version_test.py`: Auto-monitors multiple local Blender installations, 70+ core test suite
- Negative test suite ensures error path popups
- Comprehensive validation scripts

---

### 4.5 UI/UX Production Refactor

**Status**: Completed (v1.0.0)

**Features**:
- Comprehensive dashboard-style refactor
- Replaced nested layouts with aligned columns
- Grouped functional areas for better vertical flow
- Professional, streamlined aesthetic matching high-end Blender plugins

---

### 4.6 Multi-Version Image & Operator Audit

**Status**: Completed (v1.0.0)

**Features**:
- Auto integrity check (`test_ui_operator_integrity`)
- Verifies each operator in `ui.py` registers correctly
- Audited and replaced high-version icons (e.g., `SYNCHRONIZED`, `RAYCAST`) with broadly compatible alternatives

---

## Fifth Phase: Asynchrony and Performance

**Goal**: Decouple baking process and enhance external connectivity.

### 5.1 Background Process Baking (Work Threads)

**Concept**: Generate separate Blender worker processes for heavy baking, keeping main UI 100% responsive for modeling.

**Priority**: HIGH (v1.6.0 Focus)

**Technical Challenges**:
- Inter-process communication
- Progress synchronization
- Error handling and recovery

---

### 5.2 Asset Bridge: Zero-Friction Delivery

**Concept**: GLB/USDZ export is live; next step is auto PBR material embedding after baking.

**Status**: Partially Completed

---

### 5.3 Parallel Tile Baking (UDIM Optimization)

**Concept**: Multi-process tile baking for UDIM projects, utilizing high core count CPUs.

**Technical Requirements**:
- Multi-process collaboration
- Tile dependency management
- Result merging

---

## Sixth Phase: Code Quality and Maintainability

**Goal**: Improve code maintainability, follow Google Python Style Guide, prevent future regressions.

### 6.1 Import Standardization

**Status**: Completed (v1.0.0)

**Fixes**:
- Renamed `property` module to `prop_module` to avoid Python built-in conflicts
- Standardized import order (stdlib ↔ bpy ↔ local modules)

---

### 6.2 Type Hints & Docstring Consistency

**Status**: Completed (v1.0.0)

**Fixes**:
- Added type hints to core functions in `common.py`, `image_manager.py`, `ops.py`
- Unified docstring style to Google Style (English)

---

### 6.3 Magic Number Extraction

**Status**: Completed (v1.0.0)

**Fixes**:
- Extracted constants to `constants.py`:
  - `UDIM_DEFAULT_TILE`
  - `GOLDEN_RATIO`
  - `MIN_THRESHOLD`
  - And more

---

### 6.4 Exception Handling Hardening

**Status**: Completed (v1.0.0)

**Fixes**:
- Replaced bare `except` with specific exception types (`AttributeError`, `RuntimeError`)
- Added safe fallbacks using `.get()` for dictionary access

**Fixed Files**:
- `core/cleanup.py` - 3 instances
- `state_manager.py` - 3 instances
- `core/engine.py` - 7 instances
- `ops.py` - 3 instances

---

### 6.5 Test Coverage Expansion

**Status**: Completed (v1.0.0)

**Additions**:
- `suite_code_review.py` validates all bug fixes
- Comprehensive validation scripts
- Multi-version test framework `multi_version_test.py`

---

## Seventh Phase: Future Evolution...

---

## Eighth Phase: Industrial Productivity Enhancement (TexTools Benchmark)

**Goal**: Introduce mature industrial workflows, elevate BakeTool to top-tier asset processing platform.

### 8.1 Explode Baking System

**Concept**: Auto-push overlapping low-poly/high-poly pairs by name suffix, eliminate normal bleeding artifacts, auto-restore coordinates after baking.

**Core Advantage**: Solves projection occlusion issues for complex mechanical structures.

### 8.2 Advanced Geometry Passes

**Concept**: Introduce more TexTools-style preset channels:
- **Bevel Mask**: Simulate edge wear
- **Soft/Fine Curvature**: Detail capture at different scales
- **Tangent/World Space Normal**: Flexible normal space transformations
- **Dust/Cavity**: Topology-based dirt distribution map

### 8.3 Smart Suffix Matching 2.0

**Concept**: Enhance `SMART_SET` logic with regex support and multi-suffix (e.g., `_high`, `_hp`, `_source`) automatic identification and batch pairing.

---

## Version Release Plan

### v1.0.0 (Current Version) - Production Ready & Code Consolidation

**Release Date**: 2026-04-17

**Main Work**:
- Architecture unification: single automation entry and bootstrap testing
- Code consolidation: full Google Style Docstrings and type hints
- Quality hardening: fixed 17+ exception handling issues and syntax bugs
- Cross-version validation: 100% pass on Blender 3.3 - 5.0

---

### v1.1.0 (Planned) - Industrial Enhancement (TexTools Tribute)

**Goal**: Background work thread implementation, multi-GPU tile baking

**Main Features**:
- [ ] Background process baking
- [ ] Progress event API
- [ ] Multi-GPU support

---

### v1.7.0 (Planned) - Smart Enhancement

**Goal**: AI-assisted features

**Main Features**:
- [ ] Smart parameter recommendations
- [ ] Material auto-analysis
- [ ] Workflow templates

---

### v2.0.0 (Distant) - Ecosystem

**Goal**: Become Blender ecosystem's baking middleware

**Main Features**:
- [ ] External engine bridges (Marmoset, Substance)
- [ ] Cloud rendering integration
- [ ] AI-assisted retopology bridge

---

## Contribution Guidelines

Contributions welcome! Please:
1. Fork this repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Create Pull Request

### Development Environment Requirements
- Python 3.10+
- Blender 3.3 - 5.0+
- Git

### Running Tests

```bash
# Single version test
blender -b --python automation/cli_runner.py -- --suite all

# Multi-version test
python automation/multi_version_test.py --verification
```

---

## Resource Links

- [User Manual](USER_MANUAL.md)
- [Developer Guide](docs/dev/DEVELOPER_GUIDE.md)
- [Ecosystem Integration Guide](docs/dev/ECOSYSTEM_GUIDE.md)
- [Automation Reference](docs/dev/AUTOMATION_REFERENCE.md)
- [Style Analysis](STYLE_GUIDE_ANALYSIS.md)

---

*This roadmap is maintained by the BakeTool Team*
*Last Updated: 2026-04-17*