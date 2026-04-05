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
- **Feature**: Integrated OIDN (Open Image Denoise) via temporary compositor pipelin## 🚀 Phase 4: Performance & Ecosystem (Focus: Scalability) [STABLE v1.5.0]
*Goal: Handle massive datasets and multi-app workflows with production-grade stability.*

### 4.1 Background Process Baking
- **Concept**: Spawn a *separate* Blender background process to perform the bake while continuing work.
- **Status**: Planning (Target v1.6.0).

### 4.2 UDIM Massive Batching (Refined) [DONE]
- **Status**: Completed (v1.5.0).

### 4.3 Production E2E Validation Loop [DONE]
- **Status**: Completed (v1.5.0).
- **Update**: Robust 100% pass rate across Blender 3.3, 3.6, 4.2, 4.5, 5.0 matrices.

### 4.4 跨版本关键死角与核心避坑 (Version-Specific Pitfalls) [STABLE]
针对 v1.5.0 修复的深层兼容性问题的总结：
- **Blender 5.0 (Node Access)**: 自 5.0 起，场景节点树属性由 `node_tree` 迁移至 `compositing_node_group`（或在某些 context 下不可用）。代码中必须使用 `hasattr` 探测。
- **Blender 4.2+ (Bake Settings)**: 烘焙设置从 `scene.render` 迁移到了 `scene.render.bake`。已通过 `compat.get_bake_settings()` 统一中转。
- **Blender 3.3/3.6 (Bake Type Naming)**: 存在 `'NORMAL'` vs `'NORMALS'` 冲突。已通过 `compat.set_bake_type` 自动映射。

### 4.5 动态对齐与参数一致性协议 (Triple-Point Alignment Protocol) [NEW]
为了防范因拼写错误或逻辑遗漏导致的 `NameError`，新增任何烘焙参数必须遵循以下 **“三点对齐”** 流程：
1. **常量注册** (`constants.py`): 定义所有底层映射、元数据和默认值。
2. **导入校验** (`core/engine.py`): 在引擎入口显式导入并验证常量存在性，严禁使用硬编码字符串替代。
3. **回归防御**: 在 `test_cases/suite_unit.py` 增加断言验证，并在 `multi_version_test.py` 中跨版本跑通。

### 4.6 UX 交互硬化 (UX Hardening) [NEW]
- **ESC 取消确认**: 模态烘焙过程中按下 `ESC` 会进入二次确认状态，防止长时间误触导致进度全失。
- **Operator 边界拦截**: 所有涉及列表索引的操作（`job_index`, `results_index`）均增加了严格的 `IndexError` 防护。

---

## 🎨 Phase 7: UI & User Experience 2.0 (Planned v1.1.0)
 with PBR materials to USD or GLTF formats.
- **Benefit**: Streamlined asset transfer to game engines, other DCCs, or web viewers. Zero-friction delivery.

### 5.2 External Bake Engine Integration
- **Concept**: Allow users to swap Blender's internal baker for external engines (e.g., Marmoset Toolbag, Substance Painter) via a standardized API.

---


 ---
 
-## 🤖 Phase 6: Intelligence & Scalability (Focus: Next Generation)
+## 🧠 Phase 6: Intelligence & Scalability (Focus: Next Generation)
 *Goal: Leverage AI and distributed computing for extreme-scale baking.*
 
 ### 6.1 AI-Assisted Cage Optimization (AI-Cage)
@@ -134,3 +134,22 @@
 ### 6.2 Distributed Node Baking
 - **Concept**: A simple client-server architecture to delegate bake jobs to multiple machines on the same network.
 
+---
+
+## 🎨 Phase 7: UI & User Experience 2.0 (Planned v1.1.0)
+*Goal: Proactive assistance and extreme workflow simplification.*
+
+### 7.1 Dashboard Hub (Visual Status Management)
+- **Concept**: A single "Health Dashboard" showing status for all objects, materials, and paths in the current project.
+- **Sub-Feature**: "Global Auto-Fix" button for missing UVs or invalid resolutions.
+
+### 7.2 3D Viewport HUD (Real-time Feedback)
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
