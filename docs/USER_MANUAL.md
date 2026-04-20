# BakeTool User Manual
## Professional Texture Baking Suite for Blender

**Version:** 1.0.0
**Supported Blender:** 3.3 - 5.0+
**Location:** 3D View > N Panel > Baking

---

## Overview

BakeTool is a comprehensive texture baking solution designed for Blender that automates the complex process of generating texture maps from 3D scenes. Whether you're preparing assets for game engines, real-time rendering, or archviz projects, BakeTool streamlines the workflow with intelligent automation and multi-channel support.

### Key Features
- **Non-Destructive Workflow**: No manual node connections required
- **Automatic Resource Creation**: Auto-creates images, UVs, and materials
- **Multi-Channel Support**: PBR, Light, Mesh, and Custom channels
- **Smart Analysis**: Auto-detects Principled BSDF configurations
- **Interactive Preview**: Real-time channel packing preview in viewport
- **Cross-Version Support**: Supports Blender 3.3 through 5.0+

---

## Section 1: Interface Overview

### 1.1 Panel Layout

The BakeTool panel is located in Blender's N Panel (sidebar) and organized into the following collapsible sections:

```
┌──────────────────────────────────────────────┐
│ [ENVIRONMENT CHECK]                          │
│  ├ Addon Dependencies: FBX ✓ GLB ✓          │
│  └ Output Path: Valid ✓                      │
├──────────────────────────────────────────────┤
│ [PRESET LIBRARY]           [Refresh] [+ Add] │
├──────────────────────────────────────────────┤
│ [JOB MANAGEMENT]                            │
│  ├ Job 1 ● [One-Click PBR]                   │
│  └ [+ Add] [- Remove] [Save] [Load]            │
├──────────────────────────────────────────────┤
│ 1. SETUP & TARGETS        [▼]                 │
│ 2. BAKE CHANNELS        [▼]                  │
│ 3. OUTPUT & EXPORT     [▼]                  │
│ 4. CUSTOM MAPS        [▼]                  │
├──────────────────────────────────────────────┤
│ [START BAKE PIPELINE]                         │
└──────────────────────────────────────────────┘
```

### 1.2 Environment Health Check

The top section performs real-time system validation:

| Status Icon | Meaning | Action Required |
|-------------|---------|-----------------|
| Green ✓ | Normal | No action needed |
| Orange ⚠ | Warning | Check settings |
| Red ✗ | Error | Fix before baking |

**Checks Performed:**
- **Addon Dependencies**: Verifies export addons (FBX/GLB/USD) are enabled
- **Path Validation**: Confirms export path exists and is writable
- **UV Detection**: Checks objects have valid UV maps

---

## Section 2: Job Management

### 2.1 Creating and Managing Jobs

Jobs are templates that store and reuse bake configurations:

**Create New Job:**
1. Click `+ Add` button
2. Select the newly created job from the list
3. Configure bake parameters

**Save Preset:**
1. Configure all parameters
2. Click `Save` button
3. Choose save location
4. Preset saves as `.json` file containing all channel configurations

**Load Preset:**
1. Click `Load` button
2. Browse to preset file
3. Parameters auto-load to current job

### 2.2 One-Click PBR Setup

Click `One-Click PBR Setup` to automatically configure standard PBR bake channels:
- Base Color
- Roughness
- Normal
- Metallic
- Ambient Occlusion

This is recommended for Substance Painter/Substance Painter workflow automatic texturing.

---

## Section 3: Object Management

### 3.1 Adding Bake Objects

**Manual Addition:**
1. Select objects in 3D viewport
2. Click `+ Add` button
3. Objects added to list

**Auto-Select:**
1. Select all objects that need baking in 3D viewport
2. Click `Auto-Select`
3. All selected mesh objects added to list

### 3.2 Object List Indicators

The object list displays real-time status information:

| Icon | Meaning | Description |
|------|---------|-------------|
| ✓ Green | UV Valid | Object has valid UV maps |
| ⚠ Orange | No UV | Object missing UV, needs creation |
| ✗ Red | Error | Object has issues, cannot bake |

### 3.3 Adding UVs

1. Select objects lacking UVs
2. Press `U` in 3D viewport
3. Choose UV method (Smart UV Project / Unwrap)

### 3.4 High-to-Low Baking (Selected to Active)

For high-poly to low-poly baking workflow:
1. Select all high-poly objects
2. Hold `Shift` and select low-poly object (becomes active)
3. Set `Bake Mode` to `Select to Active`
4. Bake

**Advantage**: High-poly objects don't need UVs; system auto-handles processing

---

## Section 4: Channel Configuration

### 4.1 PBR Channels

| Channel | Description | Blender Bake Type |
|---------|------------|-------------------|
| Base Color | Base color/Albedo | Diffuse |
| Roughness | Surface roughness | Roughness |
| Metallic | Metalness | Glossy (Metallic) |
| Specular | Specular level | Specular |
| Normal | Normal map | Normal |
| Height | Displacement | Displacement |
| Ambient Occlusion | Ambient occlusion | Ambient Occlusion |
| Emit | Emission | Emit |

### 4.2 Light/Render Channels

| Channel | Description |
|---------|-------------|
| Curvature | Edge wear detection |
| Normal | Point normal |
| Position | Object position |
| UV | UV coordinates viewable |

### 4.3 Mesh Analysis Channels

| Channel | Description |
|---------|-------------|
| Material ID | Material identification |
| Fac | Face count |
| Element ID | Element identification |

### 4.4 Channel Suffixes

Configure output file suffixes:
| Channel | Default Suffix |
|---------|----------------|
| Base Color | `_color` |
| Roughness | `_rough` |
| Normal | `_normal` |
| Metallic | `_metal` |

### 4.5 Custom Channels

Support for custom channel building:
1. Click `+ Add Channel`
2. Choose channel type
3. Configure suffix and parameters
4. Drag to adjust order

---

## Section 5: Advanced Settings

### 5.1 Cage Settings (Cage)

Cage is an intermediate body for raycasting between high and low poly.

**Modes:**
- **Uniform**: Uniform extrusion, all faces same distance
- **Proximity**: Smart nearest neighbor analysis, auto-detects high-poly to low-poly distance

**Settings:**
- **Cage Extrusion**: Extrusion distance (default 0.01)
- **Cage Offset**: Additional cage offset
- **Cage Object**: Use custom cage object

### 5.2 Cage Analysis

Click `Analyze Cage` to perform raycast analysis between high and low poly meshes.

**Visual Feedback:**
- 🟢 Green: Safe areas, baking safe
- 🟡 Yellow: Proximity areas,可能出现间隙
- 🟠 Orange: Warning areas, review recommended

**Analysis Report:**
- Error count
- Warning percentage
- Recommended extrusion distance

### 5.3 Texel Density

Define target texel density to maintain consistent texture quality.

**Formula:**
```
Resolution = Texel Density × Object Size
```

**Configuration:**
1. Enter target density (e.g., 512 px/unit)
2. System auto-calculates recommended resolution
3. Click apply recommendation

### 5.4 Denoise Settings

Enable Intel Open Image Denoise (OIDN) for post-processing:

1. Enable `Denoise`
2. Choose denoise strength (1-10)
3. Configure strength affects smoothing

**Best Use Cases:**
- Low sampling fast preview
- Complex multi-bounce baking
- Reduce noise artifacts

### 5.5 Performance Profiling

After baking, view each channel's performance metrics:

| Metric | Description |
|--------|-------------|
| Bake Time | Calculation time |
| Save Time | File save time |
| Total Time | Total elapsed time |
| Memory Peak | Maximum memory used |

---

## Section 6: Saving and Exporting

### 6.1 Apply to Scene

After baking, create new material and assign to objects automatically.

**Automatic Update:**
- If material exists in scene, system directly updates material and node connections
- No recreation, keeping scene clean

**Naming Convention:**
- Material: `{Original Material Name}_Baked`
- Material: `{Original Material Name}_Baked`

### 6.2 External Save

Save baking results to disk after completion.

**Supported Formats:**
- PNG (default, recommended)
- JPEG
- EXR (32-bit, supports HDR)
- TIFF

**Path Configuration:**
- Absolute path: `C:/textures/`
- Relative path: `//textures/` (relative to .blend file)

### 6.3 One-File Delivery (GLB/GLTF Export)

Auto-export baked results to immediately usable formats:

**Supported Formats:**
- **GLB/GLTF**: For Web, Three.js, game engines
- **USD**: For film/compositing, DC workflow

**Workflow:**
1. Enable `Export Model`
2. Choose export format
3. Choose export path
4. Baking completes and auto-executes export

**PBR Automatic Binding:**
- Auto-create industry-standard PBR material
- Auto-link all baked textures
- Usable directly in Substance, Unity, Unreal, etc.

---

## Section 7: Quick Baking

### 7.1 Quick Bake Feature

Bake without configuring complex task - directly bake selected objects:

1. Select objects in 3D viewport
2. Click `Quick Bake`
3. Uses current job settings (or default settings if none)

**Characteristics:**
- **Memory Mode**: Uses in-memory execution without modifying current job settings
- **Fast Preview**: Suitable for quick quality checks
- **No Panel Switch**: No need to switch panels

### 7.2 UDIM Baking

Designed for UDIM workflow:
1. Ensure model uses UDIM format UVs
2. Display all detected tiles in list
3. Each tile auto-creates corresponding image
4. Single bake outputs all tiles

---

## Section 8: Interactive Preview

### 8.1 Interactive Preview Mode

Preview channel packing results in viewport before baking:
1. Click `Preview Packing`
2. View 3D viewport see ORM result in real-time
3. Adjust parameters and auto-update preview
- Occlusion (R channel)
- Roughness (G channel)
- Metallic (B channel)

### 8.2 Auto-Recovery

After closing preview, system auto-restores original material:
- No persistent viewport artifacts
- Non-destructive workflow
- 100% safe

---

## Section 9: Command Line and API

### 9.1 Headless Baking (CLI)

Execute baking in server or headless environments:
```bash
# Basic command
blender -b project.blend -P headless_bake.py

# Specify job
blender -b project.blend -P headless_bake.py -- --job "PBR_Job"

# Specify output directory
blender -b project.blend -P headless_bake.py -- --output "C:/baked/"

# Combined parameters
blender -b project.blend -P headless_bake.py -- --job "PBR" --output "C:/baked/"
```

### 9.2 Python API

Call baking functions directly in scripts:
```python
import bpy
from baketool.core import api

# Basic baking - use current scene's Job settings
# Bake currently selected objects
api.bake(objects=bpy.context.selected_objects)

# Or use viewport selection
api.bake(use_selection=True)

# Get UDIM tiles
tiles = api.get_udim_tiles(bpy.context.selected_objects)
print(f"UDIM tiles: {tiles}")

# Validate settings
is_valid, msg = api.validate_settings(bpy.context.scene.BakeJobs.jobs[0])
print(f"Valid: {is_valid}, Message: {msg}")
```

### 9.3 API Reference
| Function | Description | Parameters |
|----------|-------------|------------|
| `api.bake()` | Execute baking | objects (optional), use_selection (default False) |
| `api.get_udim_tiles()` | Get UDIM tiles | objects list |
| `api.validate_settings()` | Validate Job settings | job object |

---

## Section 10: Troubleshooting

### 10.1 Crash Recovery

If Blender crashes during baking:
1. Reopen Blender
2. Red warning appears in panel header
3. Shows last executed asset and channel
4. Follow information to check issues

### 10.2 Cleanup

If scene has leftover temporary data:
1. Press `F3` (Search)
2. Enter `Clean Up Bake Junk`
3. Click to execute cleanup

**Cleanup Contents:**
- `BT_Bake_Temp_UV` - Temporary UV layers
- `BT_Protection_*` - Protection nodes
- `BT_*` Images - Temporary images

### 10.3 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Normal map incorrect | Incorrect Color Space | Ensure Color Space is `Non-Color` |
| Baking results black | Object not selected or no UV | Add UVs and select objects |
| Missing textures | Image path reference broken | Unlink and fix paths |
| Memory insufficient | High resolution too large | Reduce resolution or tile baking |
| Export failed | Addon not enabled | Enable glTF/USD addon |

### 10.4 Performance Optimization

| Issue | Optimization Method |
|-------|-------------------|
| Baking too slow | Use GPU baking, reduce sample count |
| Memory insufficient | Reduce resolution or use tiled baking |
| Preview too slow | Disable preview, use lower sample count |

---

## Appendix A: Keyboard Shortcuts
| Shortcut | Action |
|----------|-------|
| `F3` | Search (enter `Bake` to find options) |
| `Ctrl + Shift + B` | Open BakeTool panel |
| `U` | UV in UV Editor |

---

## Appendix B: File Structure

```
baketool/
├── __init__.py           # Addon entry point
├── ops.py                # Operator definitions
├── ui.py                 # UI panel
├── property.py           # Property definitions
├── constants.py          # Constants
├── translations.py        # Translation system
├── state_manager.py       # State management
├── preset_handler.py    # Preset handling
├── core/                 # Core modules
│   ├── api.py          # Public API
│   ├── engine.py       # Baking engine
│   ├── execution.py    # Execution context
│   ├── image_manager.py # Image management
│   ├── node_manager.py # Node management
│   ├── uv_manager.py   # UV management
│   ├── shading.py     # Shading utilities
│   ├── cage_analyzer.py # Cage analysis
│   ├── common.py       # Common utilities
│   ├── compat.py       # Version compatibility
│   ├── math_utils.py   # Math utilities
│   ├── thumbnail_manager.py # Thumbnail manager
├── automation/           # Automation tools
│   ├── cli_runner.py   # CLI test runner
│   ├── multi_version_test.py # Multi-version test
│   ├── headless_bake.py # Headless baking
├── dev_tools/           # Development tools
│   ├── extract_translations.py
├── docs/                # Documentation
├── test_cases/          # Test suites
```

---

## Appendix C: Glossary

| Term | Definition |
|------|-----------|
| UDIM | Multi-tile image system supporting 1001, 1002, ... tiles |
| Cage | Intermediate body for raycasting between high and low poly |
| Texel Density | Texture pixel density per unit area |
| PBR | Physics-Based Rendering |
| ORM | Occlusion + Roughness + Metallic channel packing |
| OIDN | Intel Open Image Denoise, GPU-based denoiser |

---

## Appendix D: Support and Feedback
- **Issue Reports**: [GitHub Issues](https://github.com/lastraindrop/baketool/issues)
- **Feature Requests**: [GitHub Discussions](https://github.com/lastraindrop/baketool/discussions)
- **Documentation Fixes**: Pull Request

---

*User Manual Version 1.0.0*
*Last Updated: 2026-04-17*