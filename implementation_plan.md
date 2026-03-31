# Simple Bake Tool (SBT) 项目同步与文档对齐计划 (Phase 4.3 & 4.5)

本计划旨在将近期完成的**跨版本兼容性硬化（Blender 3.3 - 5.0）**工作同步至项目的核心文档与路线图中，并确立“参数动态对齐协议”，防止未来因 API 变更或拼写疏忽导致的回归。

## 一、 核心目标与特性拆解

### 🎯 目标 1: 零摩擦资产交付 (One-Click USD/glTF Export) [DONE]
**执行结果**：
- [x] 强化 `apply_baked_result`：自动编织 PBR 材质节点链。
- [x] 扩展 `ModelExporter.export`：支持贴图打包进 GLB。
- [x] v0.9.5 稳定版已验证。

### 🎯 目标 2: 视觉包裹框分析 (Visual Cage Analysis) [DONE]
**执行结果**：
- [x] 引入基于 NumPy 的射线检测引擎。
- [x] 顶点色热力图绘制：自动标记包裹漏掉的区域。
- [x] v0.9.5 稳定版已验证。

### 🎯 目标 3: 跨版本兼容性硬化 (Multi-Version Hardening) [NEW/DONE]
**预期方案**：
- [x] 重构 `compat.py`：实现基于引擎强制锁定的 `set_bake_type`。
- [x] 硬化 UDIM 初始化：针对 B3.3 Headless 模式实施像素触摸触发。
- [x] 验证 3.3 - 5.0 全量测试矩阵 (540+ Cases)。

---

## 二、 关键设计方案：参数一致化与动态对齐 (Proposed Changes)

> [!IMPORTANT]
> **“三点对齐协议” (Triple-Point Alignment Protocol)** 是防止反复出现 `AttributeError` 的核心防线。

### 模块 A: 跨版本兼容层 (Compat Layer)
- **[MODIFY] `core/compat.py`**：支持自动映射 B3.x 与 B4+ 的不同 `bake_type` 字符串（如 `EMIT` vs `EMISSION`）。

### 模块 B: 数据生产与 UI 映射 (Data-UI Mapping)
- **[MODIFY] `core/execution.py`**：统一 `add_bake_result_to_ui` 的参数提取逻辑，确保新增的性能指标（采样数、分辨率等）在所有版本下均能安全映射到 RNA 属性。

### 模块 C: 文档同步与开发者契约 (Documentation)
- **[MODIFY] `DEVELOPER_GUIDE.md`**：录入“三点对齐”标准流程。
- **[MODIFY] `ROADMAP.md`**：同步里程碑状态。

---

## 三、 全方位验证与测试方略 (Verification Plan)

### 1. 跨版本回归矩阵
- 运行 `automation/multi_version_test.py`。
- 确认 B3.6, B4.2, B4.5, B5.0 通行率 100%。

### 2. 参数一致性测试
- **新增 Test**: `test_baked_image_result_attributes`。
- 验证 `BakedImageResult` 中定义的所有属性在烘焙后是否被正确填充，且未因版本差异导致 API 返回 None。

---

## 四、 开放问题 (Open Questions)

> [!WARNING] 
> 1. **B3.3 的 UDIM 支持度**：目前我们修复了 Headless 下的缓冲区初始化问题，但其内核仍旧容易在极大贴图下报 OOM。是否需要将 B3.3 标记为 Legacy 支持而非全功能支持？
2. **文档统一语言**：是否需要将所有 `.md` 说明文件统一为中文？

---
请审核上述同步计划。确认后我将开始增量更新文档内容。
