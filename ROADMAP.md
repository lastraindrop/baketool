# BakeTool Development Roadmap (Strategic Vision)

This document outlines the long-term strategic vision for Simple Bake Tool (SBT), evolving it from a utility addon into a professional-grade **Baking Middleware** for the Blender ecosystem.

## 📅 Phase 1: Visual & UX Revolution (Focus: Artist Feedback)
*Goal: Bridge the gap between parameter tuning and visual results, eliminating "blind baking".*

### 1.1 Interactive Packing Preview [DONE]
- **Status**: Completed in v1.0.0.
- **Feature**: Use GLSL Viewport Shaders to simulate channel packing (ORM) in real-time before baking.
- **Tech**: Temporary shader trees mixing inputs based on "Pack" settings.
- **Benefit**: Visualize RGBA channel distribution instantly.

### 1.2 Visual Cage Analysis
- **Concept**: A "Heatmap" overlay on the mesh showing areas where the Cage might intersect with the High Poly mesh or miss details.
- **Tech**: Ray-cast analysis between Low-Poly (with Cage extrusion) and High-Poly objects.
- **Benefit**: Visually identify "missed rays" or artifacts before committing to a bake.

### 1.3 Asynchronous Progress UI
- **Concept**: Detach the UI from the baking process slightly to prevent the "Blender Freeze" feeling (White Screen on Windows).
- **Tech**: Implement refined modal timer updates or investigate Subprocess-based baking (see Phase 2).

---

---

## 🏭 Phase 2: Pipeline Integration (Focus: TD & Automation)
*Goal: Decouple the Engine from the UI, enabling headless operation and external script integration.*

### 2.1 Headless CLI Mode [DONE]
- **Status**: Completed in v1.0.0.
- **Feature**: Run baking jobs from the command line without opening Blender's UI.
- **Requirement**: Full separation of `ops.py` dependencies from `core.engine`.

### 2.2 Public Python API [DONE]
- **Status**: Completed in v1.0.0.
- **Feature**: Standardized API for other addon developers via `core/api.py`.

### 2.3 Preset Library 2.0 (Cloud/Local Sync)
- **Feature**: A dedicated Preset Browser supporting drag-and-drop.

---

## 🧠 Phase 3: Intelligence & Algorithms (Focus: Workflow Speed)
*Goal: Replace manual trial-and-error with algorithmic assistance.*

### 3.1 Auto-Cage 2.0 (Proximity-Based) [DONE]
- **Status**: Completed in v1.0.0.
- **Upgrade**: An algorithm that varies extrusion distance based on mesh proximity.

### 3.2 Smart Texel Density [DONE]
- **Status**: Completed in v1.0.0.
- **Feature**: Auto-calculate output resolution based on physical object size.

### 3.3 Anti-Aliasing & Denoise Pipeline
- **Feature**: Integrate OIDN specifically tuned for baked maps.

---

## 🚀 Phase 4: Performance & Ecosystem (Focus: Scalability)
*Goal: Handle massive datasets and multi-app workflows.*

### 4.1 Background Process Baking
- **Concept**: Spawn a *separate* Blender background process to perform the bake while continuing work.

### 4.2 UDIM Massive Batching (Refined)
- **Optimization**: Specific optimizations for 100+ UDIM tiles, managing RAM and context robustness.

---

## ✅ Completed Milestones (Archive)
- [x] **v1.0.0 Final**: **Localization (i18n)**, **Integrated UI Testing**, **Auto-Cage 2.0**, and **CLI/API** support.
- [x] **v1.0.0-RC**: Full Cross-Version pass (3.6-5.0), Interactive Packing Preview, and UI Logic Hardening.
- [x] **v0.9.9**: Code Quality Audit, Pathlib Migration, Core Except Normalization.
- [x] **v0.9.0**: Crash Recovery System (State Manager).