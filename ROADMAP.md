# BakeTool Development Roadmap (Strategic Vision)

This document outlines the long-term strategic vision for Simple Bake Tool (SBT), evolving it from a utility addon into a professional-grade **Baking Middleware** for the Blender ecosystem.

## 📅 Phase 1: Visual & UX Revolution (Focus: Artist Feedback)
*Goal: Bridge the gap between parameter tuning and visual results, eliminating "blind baking".*

### 1.1 Interactive Packing Preview
- **Concept**: Use GLSL Viewport Shaders to simulate channel packing (ORM) in real-time before baking.
- **Tech**: Create temporary shader trees that mix Diffuse/Roughness/Metal inputs based on the selected "Pack" settings.
- **Benefit**: Users can visualize RGBA channel distribution instantly without waiting for a full bake cycle.

### 1.2 Visual Cage Analysis
- **Concept**: A "Heatmap" overlay on the mesh showing areas where the Cage might intersect with the High Poly mesh or miss details.
- **Tech**: Ray-cast analysis between Low-Poly (with Cage extrusion) and High-Poly objects.
- **Benefit**: Visually identify "missed rays" or artifacts before committing to a bake.

### 1.3 Asynchronous Progress UI
- **Concept**: Detach the UI from the baking process slightly to prevent the "Blender Freeze" feeling (White Screen on Windows).
- **Tech**: Implement refined modal timer updates or investigate Subprocess-based baking (see Phase 2).

---

## 🏭 Phase 2: Pipeline Integration (Focus: TD & Automation)
*Goal: Decouple the Engine from the UI, enabling headless operation and external script integration.*

### 2.1 Headless CLI Mode (The "Black Box" Engine)
- **Feature**: Run baking jobs from the command line without opening Blender's UI.
- **Usage**: `blender -b file.blend -P baketool_cli.py --job "HeroAsset_Bake"`
- **Requirement**: Full separation of `ops.py` dependencies from `core.engine`.
- **Target**: Render Farms, CI/CD Pipelines (Jenkins/GitHub Actions).

### 2.2 Public Python API
- **Feature**: Standardized API for other addon developers.
- **Signature**: `baketool.api.bake(objects=[], preset="ORM_Unreal", output_path="//textures/")`
- **Benefit**: Allows asset management addons (like Asset Browser tools) to "call" BakeTool for thumbnail generation or export prep.

### 2.3 Preset Library 2.0 (Cloud/Local Sync)
- **Feature**: A dedicated Preset Browser supporting drag-and-drop.
- **Integrations**: Official presets for Unreal Engine 5, Unity HDRP, Godot, Sketchfab, and Marmoset Toolbag.

---

## 🧠 Phase 3: Intelligence & Algorithms (Focus: Workflow Speed)
*Goal: Replace manual trial-and-error with algorithmic assistance.*

### 3.1 Auto-Cage 2.0 (Proximity-Based)
- **Current**: Simple uniform extrusion.
- **Upgrade**: An algorithm that varies extrusion distance per-vertex based on the proximity of the High-Poly mesh, ensuring tight fits without clipping.

### 3.2 Smart Texel Density
- **Feature**: Auto-calculate optimal output resolution based on physical object size and desired "Texels per Meter".
- **Benefit**: Ensures consistent texture quality across an entire game level or scene.

### 3.3 Anti-Aliasing & Denoise Pipeline
- **Feature**: Integrate OIDN (OpenImageDenoise) specifically tuned for baked maps (protecting Normal Map gradients).
- **Tech**: Post-processing compositing nodes injected automatically after bake.

---

## 🚀 Phase 4: Performance & Ecosystem (Focus: Scalability)
*Goal: Handle massive datasets and multi-app workflows.*

### 4.1 Background Process Baking
- **Concept**: Spawn a *separate* Blender background process to perform the bake while the user continues working in the main window.
- **Tech**: `subprocess.Popen` with shared memory or temp file communication.
- **Benefit**: True non-blocking workflow.

### 4.2 UDIM Massive Batching
- **Optimization**: Specific optimizations for assets with 50+ UDIM tiles, managing memory to prevent RAM overflows during pack/save.

### 4.3 Live Link (Bridge)
- **Concept**: Auto-export and trigger "Hot Reload" in external tools (Substance Painter / Unreal Engine).
- **Tech**: Socket communication or file-watcher triggers.

---

## 🛡️ Phase 5: Deep Quality Assurance & Architecture Alignment (Current Focus)
*Goal: Ensure enterprise-grade stability, dynamic alignment, and robust error prevention.*

### 5.1 Dynamic Parameter Alignment & API Consistency
- **Concept**: Ensure all dynamic system lookups and references (such as `getattr` and UI parameters) are strictly typed and consistently evaluated without hardcoding.
- **Tech**: Emphasize unified data access patterns over manual dictionary/list management.

### 5.2 Strict Code Standard Enforcement
- **Concept**: Prevent silent failures through rigorous error handling and path management.
- **Tech**:
  - Adopt strict `except Exception:` instead of bare `except:` to prevent swallowing fatal system signals (completed in v0.9.9).
  - Adopt fully object-oriented `pathlib.Path` structures instead of legacy `os.path` for bullet-proof cross-platform execution (completed in v0.9.9).
  - Adopt unified standard tracing with `logger.exception()`.

### 5.3 Universal Headless Pipeline Automation
- **Concept**: Maintain a robust CI-friendly pipeline ensuring zero regressions.
- **Goal**: Continually optimize `automation/multi_version_test.py` against Blender 3.6, 4.2 LTS, 4.5 LTS, and 5.0.

---

## ✅ Completed Milestones (Archive)
- [x] **v0.9.9**: Code Quality Audit, Pathlib Migration, Core Except Normalization.
- [x] **v0.9.8**: Architecture Hardening (Standardized properties, UI dispatch, unified logging).
- [x] **v0.9.7**: Modular Architecture (UI-Engine-Core separation).
- [x] **v0.9.6**: Cross-Version Compatibility (Blender 3.6 - 5.0).
- [x] **v0.9.5**: Zero-Side-Effect Quick Bake (Runtime Proxies).
- [x] **v0.9.0**: Crash Recovery System (State Manager).