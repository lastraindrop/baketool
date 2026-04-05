# BakeTool Development Roadmap (Strategic Vision)

This document outlines the long-term strategic vision for Simple Bake Tool (SBT), evolving it from a utility addon into a professional-grade **Baking Middleware** for the Blender ecosystem.

## 📅 Phase 1: Visual & UX Revolution (Focus: Artist Feedback)
*Goal: Bridge the gap between parameter tuning and visual results, eliminating "blind baking".*

### 1.1 Interactive Packing Preview [DONE]
- **Status**: Completed in v1.0.0.
- **Feature**: Use GLSL Viewport Shaders to simulate channel packing (ORM) in real-time before baking.
- **Tech**: Temporary shader trees mixing inputs based on "Pack" settings.
- **Benefit**: Visualize RGBA channel distribution instantly.

### 1.2 Visual Cage Analysis [DONE]
- **Status**: Completed (v0.9.5).
- **Feature**: A "Heatmap" overlay on the mesh showing areas where the Cage might intersect with the High Poly mesh or miss details.
- **Tech**: Ray-cast analysis between Low-Poly (with Cage extrusion) and High-Poly objects using BVH-Tree.
- **Benefit**: Visually identify "missed rays" or artifacts before committing to a bake.

### 1.3 Asynchronous Progress UI [DONE]
- **Status**: Completed (Modal Progress with Event Loop decoupling).
- **Tech**: Uses `BakeModalOperator` to maintain UI responsiveness during heavy bakes.

### 1.4 Automated UI Logic Guard [NEW]
- **Status**: Completed (v0.9.0).
- **Feature**: Static analysis of `CHANNEL_UI_LAYOUT` vs Blender RNA properties to prevent runtime UI crashes.
- **Benefit**: 100% confidence when adding new bake channels.

---

---

## 🏭 Phase 2: Pipeline Integration (Focus: TD & Automation)
*Goal: Decouple the Engine from the UI, enabling headless operation and external script integration.*

### 2.1 Engine-UI Decoupling [DONE]
- **Status**: Refined in v0.9.0.
- **Feature**: God-functions split into granular methods (`_create_target_image`, `_execute_blender_bake_op`). 
- **Benefit**: Pure headless operation without relying on active Viewport context.

### 2.2 Public Python API [DONE]
- **Status**: Completed in v1.0.0.
- **Feature**: Standardized API for other addon developers via `core/api.py`.

### 2.3 Preset Library 2.0 (Visual UI) [DONE]
- **Status**: Completed in v0.9.3.
- **Feature**: A dedicated Preset Gallery supporting thumbnail previews and dynamic refresh.
- **Goal**: Improved artist experience for managing complex material projects.

### 2.4 Bake Performance Profiler [DONE]
- **Status**: Completed in v0.9.3.
- **Feature**: Real-time breakdown of Bake time vs I/O (Save) time per channel.
- **Benefit**: Identify bottlenecks in large-scale asset production.

---

## 馃 Phase 3: Intelligence & Algorithms (Focus: Workflow Speed)
*Goal: Replace manual trial-and-error with algorithmic assistance.*

### 3.1 Auto-Cage 2.1 (Proximity-Based) [DONE]
- **Status**: Refined for Production in v0.9.0.
- **Upgrade**: Algorithm predicts safe average extrusion using Numpy ray-casting proximity analysis.

### 3.2 Smart Texel Density [DONE]
- **Status**: Completed in v1.0.0.
- **Feature**: Auto-calculate output resolution based on physical object size.

### 3.3 Anti-Aliasing & Denoise Pipeline [DONE]
- **Status**: Completed in v0.9.3.
- **Feature**: Integrated OIDN (Open Image Denoise) via temporary composito## 🚀 Phase 4: Production Hardening & Ecosystem [STABLE v1.5.0]
*Goal: 100% architectural stability and cross-version parameter alignment.*

### 4.1 Parameter Consistency & Dynamic Alignment (Hardened) [DONE]
- **Status**: Implemented for v1.5.0.
- **Mechanism**: Triple-Point Alignment Protocol (Constants -> Engine -> Automation).
- **Benefit**: Ensures zero `NameError` regressions. Added `suite_parameter_matrix.py` to verify mapping integrity.

### 4.2 UDIM Massive Batching (Refined) [DONE]
- **Status**: Completed in v1.5.0.
- **Tech**: Recursive tile detection with zero-copy buffer initialization.

### 4.3 Production E2E Validation Loop [DONE]
- **Status**: Completed (v1.5.0).
- **Matrix**: 100% Pass Rate confirmed for Blender 3.3, 3.6, 4.2 LTS, and 5.0 (Alpha).

### 4.4 UX & Interaction Hardening [DONE]
- **Features**: ESC-to-Confirm cancellation, per-operator bounds checking, and unified mode restoration.

---

## 🔮 Phase 5: Pipeline Evolution (Planned v1.6.0)
*Goal: Decouple baking processes and enhance external connectivity.*

### 5.1 Background Process Baking (Worker Thread)
- **Concept**: Spawn a detached Blender worker process to perform heavy bakes, keeping the main interface 100% responsive for modeling.
- **Priority**: HIGH.

### 5.2 Asset Bridge: Zero-Friction Delivery
- **Concept**: Automatic GLB/USDZ export with PBR material embedding immediately after baking.
- **Priority**: MEDIUM.

### 5.3 External Engine Bridge (API)
- **Concept**: Standardized hooks to trigger external bakers (Marmoset/Substance) through the SBT interface.

---

## 🧠 Phase 6: Intelligence & Scalability
*Goal: Leverage AI and dashboard-level management.*

### 6.1 SBT Dashboard Hub
- **Feature**: Central health monitor for all project assets, detecting missing UVs or resolution mismatches globally.

### 6.2 Collaborative Network Baking
- **Feature**: Delegate tiles or objects to other machines on the local network running the SBT Worker.

---

## 🎨 Phase 7: UI & User Experience 2.0 (v2.0 Vision)
*Goal: Floating HUDs and predictive automation.*

### 7.1 3D Viewport HUD
- **Feature**: Progress bars and status badges drawn directly in the 3D viewport using the GPU module.

### 7.2 Smart Asset Naming Tokens
- **Feature**: Dynamic paths using `<OBJECT>`, `<ENGINE>`, and `<DATE>` tokens.

---
**Current Status**: v1.5.0 Stable Release.
**Next Focus**: Background Worker (v1.6.0 Dev Cycle).
ck)
+- **Concept**: A floating progress bar and "Bake Complete" badge directly in the 3D scene (using GPU modules).
+
+### 7.3 Multi-Job Parallelization (Background)
+- **Concept**: Seamlessly hand off all enabled jobs to a separate thread/process to keep Blender alive for modeling.
+
+### 7.4 Smart Asset Naming Tokens
+- **Concept**: Standardized tokens like `<OBJECT>`, `<DATE>`, `<VERSION>`, `<ENGINE>` for dynamic output folder structures.
+
+### 7.5 Batch Asset Sync & Export
+- **Concept**: One-click sync from bake results to multiple game engines (Unity/Unreal/Godot) output folders simultaneously.
