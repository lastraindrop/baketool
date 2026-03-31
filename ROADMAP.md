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
- **Feature**: Integrated OIDN (Open Image Denoise) via temporary compositor pipeline.

---

## 🚀 Phase 4: Performance & Ecosystem (Focus: Scalability)
*Goal: Handle massive datasets and multi-app workflows.*

### 4.1 Background Process Baking
- **Concept**: Spawn a *separate* Blender background process to perform the bake while continuing work.
- **Tech**: Subprocess management with IPC (Inter-Process Communication) for status reporting. 
- **Implementation**: Uses a headless script and temp file serialization to pass bake job definitions.
- **Status**: Planning (Target v1.1.0).

### 4.2 UDIM Massive Batching (Refined) [DONE]
- **Status**: Completed (v0.9.5).
- **Optimization**: Specific optimizations for 100+ UDIM tiles, managing RAM and context robustness. Verified via E2E test suite.

### 4.3 Production E2E Validation Loop [DONE]
- **Status**: Completed (v0.9.5).
- **Feature**: Full engine-level execution in automated tests for all architectures (Single, High-to-Low, UDIM).
- **Benefit**: Zero-regression guarantee for core bake pipelines across 5 Blender versions.

### 4.4 跨版本关键死角与核心避坑 (Version-Specific Pitfalls)
针对 v0.9.5 修复的深层兼容性问题的总结：
- **Blender 5.0 (Node Access)**: 自 5.0 起，场景节点树属性由 `node_tree` 迁移至 `compositing_node_group`（或在某些 context 下不可用）。代码中必须使用 `hasattr` 探测，并优先通过 `node_tree_add()` 确保对象存在。
- **Blender 4.2+ (Bake Settings)**: 烘焙设置从 `scene.render` 迁移到了 `scene.render.bake`。必须通过 `compat.get_bake_settings()` 中转访问。
- **Blender 3.3/3.6 (Bake Type Naming)**: 存在 `'NORMAL'` vs `'NORMALS'` 以及 `'EMIT'` vs `'EMISSION'` 的冲突。
    - **避坑规范**: 必须使用 `compat.set_bake_type(scene, pass_id)` 设置烘焙类型。底层实现了“引擎强制锁定策略”：在设置前强制切换引擎为 Cycles 以确保 Cycles-specific 属性可见，并执行版本自适应映射。
- **Blender 3.3/3.6 (UDIM Headless Init)**: 在旧版 Headless 环境下，仅仅创建 Tile 不足以触发内部缓冲区分配，会导致烘焙算子报 `Uninitialized image`。
    - **避坑指南**: 必须执行“双重触发”：首先设置 `image.filepath_raw` 并调用 `image.save()`，同时在脚本层进行一次微小的像素触碰（如 `image.pixels[0] = 1.0`）。

### 4.5 动态对齐与参数一致性协议 (Triple-Point Alignment Protocol)
为了彻底防范因拼写错误或逻辑遗漏导致的 `AttributeError`（特别在跨版本环境下的元数据丢失），新增任何烘焙指标（如 `vram_usage`）必须遵循以下 **“三点对齐”** 流程：
1. **RNA 注册** (`property.py`): 在 `BakedImageResult` 定义属性。
2. **数据生产** (`core/engine.py`): 在 `BakeStepRunner` 的 `meta` 字典中填入数值。
3. **数据映射** (`core/execution.py`): 在 `add_bake_result_to_ui` 中将 `meta` 映射至已注册的 RNA 属性。
4. **回归防御**: 在 `test_cases/suite_production_workflow.py` 增加断言验证字段完整性。

### 4.6 自动化测试架构与矩阵
- **统一入口**: 使用 `automation/multi_version_test.py` 负责跨版本全量矩阵验证。
- **环境隔离**: 所有的 E2E 测试必须配套 `DataLeakChecker` 确保内存安全。
- **Benefit**: Unified engine code regardless of LTS target.

---

## 🌐 Phase 5: Ecosystem & Interoperability (Focus: Broader Adoption)
*Goal: Seamless integration with external tools and pipelines.*

### 5.1 USD/GLTF Export Pipeline [DONE]
- **Status**: Completed (v0.9.5).
- **Feature**: Direct export of baked assets with PBR materials to USD or GLTF formats.
- **Benefit**: Streamlined asset transfer to game engines, other DCCs, or web viewers. Zero-friction delivery.

### 5.2 External Bake Engine Integration
- **Concept**: Allow users to swap Blender's internal baker for external engines (e.g., Marmoset Toolbag, Substance Painter) via a standardized API.

---

## 🤖 Phase 6: Intelligence & Scalability (Focus: Next Generation)
*Goal: Leverage AI and distributed computing for extreme-scale baking.*

### 6.1 AI-Assisted Cage Optimization (AI-Cage)
- **Concept**: Use a lightweight neural network to predict optimal cage extrusion/offset values by analyzing mesh topology and occlusion.

### 6.2 Distributed Node Baking
- **Concept**: A simple client-server architecture to delegate bake jobs to multiple machines on the same network.
