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

### 1.3 Asynchronous Progress UI [DONE]
- **Status**: Completed (Modal Progress with Event Loop decoupling).
- **Tech**: Uses `BakeModalOperator` to maintain UI responsiveness during heavy bakes.

### 1.4 Automated UI Logic Guard [NEW]
- **Status**: Completed (v1.1.0).
- **Feature**: Static analysis of `CHANNEL_UI_LAYOUT` vs Blender RNA properties to prevent runtime UI crashes.
- **Benefit**: 100% confidence when adding new bake channels.

---

---

## 🏭 Phase 2: Pipeline Integration (Focus: TD & Automation)
*Goal: Decouple the Engine from the UI, enabling headless operation and external script integration.*

### 2.1 Engine-UI Decoupling [DONE]
- **Status**: Refined in v1.1.0.
- **Feature**: God-functions split into granular methods (`_create_target_image`, `_execute_blender_bake_op`). 
- **Benefit**: Pure headless operation without relying on active Viewport context.

### 2.2 Public Python API [DONE]
- **Status**: Completed in v1.0.0.
- **Feature**: Standardized API for other addon developers via `core/api.py`.

### 2.3 Preset Library 2.0 (Visual UI)
- **Feature**: A dedicated Preset Browser supporting thumbnail previews and drag-and-drop.
- **Goal**: Improved artist experience for managing complex material projects.

### 2.4 Bake Performance Profiler [NEW]
- **Feature**: Real-time breakdown of CPU/GPU/Numpy time per channel.
- **Benefit**: Identify bottlenecks in large-scale asset production.

---

## 🧠 Phase 3: Intelligence & Algorithms (Focus: Workflow Speed)
*Goal: Replace manual trial-and-error with algorithmic assistance.*

### 3.1 Auto-Cage 2.1 (Proximity-Based) [DONE]
- **Status**: Refined for Production in v1.1.0.
- **Upgrade**: Algorithm predicts safe average extrusion using Numpy ray-casting proximity analysis.

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

## 🌐 Phase 5: Ecosystem & Interoperability (Focus: Broader Adoption)
*Goal: Seamless integration with external tools and pipelines.*

### 5.1 USD/GLTF Export Pipeline
- **Concept**: Direct export of baked assets with PBR materials to USD or GLTF formats.
- **Benefit**: Streamlined asset transfer to game engines, other DCCs, or web viewers.

### 5.2 External Bake Engine Integration
- **Concept**: Allow users to swap Blender's internal baker for external engines (e.g., Marmoset Toolbag, Substance Painter) via a standardized API.
- **Benefit**: Leverage specialized baking features from other software within the BakeTool workflow.

## 🤖 Phase 6: Intelligence & Scalability (Focus: Next Generation)
*Goal: Leverage AI and distributed computing for extreme-scale baking.*

### 6.1 AI-Assisted Cage Optimization (AI-Cage)
- **Concept**: Use a lightweight neural network to predict optimal cage extrusion/offset values by analyzing mesh topology and occlusion.
- **Benefit**: Zero-setup baking for complex organic or mechanical hard-surface parts.

### 6.2 Distributed Node Baking
- **Concept**: A simple client-server architecture to delegate bake jobs to multiple machines on the same network.
- **Benefit**: Massive reduction in time for large architectural or environment projects.

---

## ✅ Completed Milestones (Archive)
- [x] **v1.1.5 Solid**: **Code Audit**, **IDProperty Safety**, **Iterator Fallbacks**, and **Preset/State Integrated Testing**.
- [x] **v1.1.0 Refined**: **Engine Decoupling**, **Generic Data-Driven UI**, and **Proximity Cage Refinement**.
- [x] **v1.0.0 Final**: **Localization (i18n)**, **Integrated UI Testing**, **Auto-Cage 2.0**, and **CLI/API** support.
- [x] **v1.0.0-RC**: Full Cross-Version pass (3.6-5.0), Interactive Packing Preview, and UI Logic Hardening.
- [x] **v0.9.9**: Code Quality Audit, Pathlib Migration, Core Except Normalization.
- [x] **v0.9.0**: Crash Recovery System (State Manager).