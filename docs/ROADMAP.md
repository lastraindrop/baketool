---

# BakeTool 发展路线图

**版本:** 1.0.0
**更新日期:** 2026-04-17
**状态:** Production Hardened (生产就绪)

---

## 概述

BakeTool 是一款专为 Blender 设计的专业级纹理烘焙插件，支持 Blender 3.3 至 5.0+ 的所有主流版本。本路线图详细阐述了插件从实用工具向专业级烘焙中间件演进的战略愿景。

### 版本历史

| 版本 | 日期 | 状态 | 主要特性 |
|------|------|------|----------|
| 1.0.0 | 2026-04-17 | 当前版本 | 代码质量增强、异常处理硬化 |
| 0.9.5 | 2024-01-20 | 历史版本 | GLB/USD 导出、降噪管道 |
| 0.9.0 | 2023-09-01 | 历史版本 | 模块化引擎重构 |

---

## 第一阶段：视觉与用户体验革命

**目标**: 弥合参数调优与视觉结果之间的差距，消除盲烘焙。

### 1.1 交互式打包预览
**状态**: 已完成 (v1.0.0)

**功能描述**:
使用 GLSL Viewport Shaders 在实际烘焙前实时模拟通道打包效果（ORM 格式）。

**技术实现**:
- 创建临时着色器树，混合输入基于 "Pack" 设置
- 支持 RGBA 通道分布的实时可视化
- 自动恢复原始材质状态

**用户体验价值**:
- 无需反复烘焙即可预览最终效果
- 节省大量迭代时间
- 减少无效烘焙对 GPU 的消耗

---

### 1.2 视觉笼子分析
**状态**: 已完成 (v0.9.5)

**功能描述**:
在网格上生成“热力图”叠加层，显示笼子与高模相交或遗漏细节的区域。

**技术实现**:
- 使用 BVH-Tree 进行低模（带笼子挤出）与高模之间的射线投射分析
- 红色区域表示“碰撞/遗漏”，绿色区域表示“安全”
- 错误总数直接显示在物体列表中

**用户体验价值**:
- 在提交烘焙前可视化识别“丢失射线”或伪影
- 减少因笼子设置不当导致的返工

---

### 1.3 异步进度 UI
**状态**: 已完成 (Modal Progress 事件循环解耦)

**技术实现**:
- 使用 `BakeModalOperator` 在重型烘焙期间保持 UI 响应
- 实时显示当前通道、物体、预估剩余时间
- 支持取消操作并保留已完成结果

---

### 1.4 自动化 UI 逻辑守护
**状态**: 已完成 (v0.9.0)

**功能描述**:
静态分析 `CHANNEL_UI_LAYOUT` 与 Blender RNA 属性，防止运行时 UI 崩溃。

**技术实现**:
- 自动验证所有 UI 通道属性存在
- 确保新增烘焙通道拥有 100% 信心
- 自动化回归测试覆盖

---

## 第二阶段：管线集成
**目标**: 将引擎与 UI 解耦，实现无头操作和外部脚本集成。

### 2.1 引擎-UI 解耦
**状态**: 已完成 (v0.9.0 精化)

**技术实现**:
- 上帝函数拆分为粒化方法：
  - `_create_target_image`: 图像创建
  - `_execute_blender_bake_op`: Blender 烘焙调用
  - `_apply_numpy_processing`: NumPy 处理

**用户体验价值**:
- 完全无头操作，不依赖活跃 Viewport 上下文
- 支持渲染农场与 CI/CD 管道集成

---

### 2.2 公共 Python API
**状态**: 已完成 (v1.0.0)

**API 示例**:
```python
from baketool.core import api

# 基础烘焙 - 使用当前场景中的 Job 设置
result = api.bake(objects=bpy.context.selected_objects)
# 或者使用视口选择
result = api.bake(use_selection=True)

# 获取 UDIM tiles
tiles = api.get_udim_tiles(bpy.context.selected_objects)

# 验证设置
is_valid, msg = api.validate_settings(bpy.context.scene.BakeJobs.jobs[0])
```

---

### 2.3 预设库 2.0 (可视化 UI)
**状态**: 已完成 (v0.9.3)

**功能特性**:
- 专用预设画廊，支持缩略图预览
- 动态刷新逻辑
- 支持用户自定义预设库路径

---

### 2.4 烘焙性能分析器
**状态**: 已完成 (v0.9.3)

**功能特性**:
- 每个通道的 Bake Time（计算耗时）vs Save Time（存储耗时）
- 帮助识别大规模资产生产中的瓶颈

---

## 第三阶段：智能化与算法
**目标**: 用算法辅助替代手动试错。

### 3.1 Auto-Cage 2.1 (基于邻近度)
**状态**: 已完成 (v0.9.0 生产硬化)

**技术实现**:
- NumPy 射线追踪邻近度分析
- 算法预测安全的平均挤出距离
- 支持两种模式：
  - `Uniform`: 传统统一挤出
  - `Proximity`: 智能邻近度模式

---

### 3.2 智能像素密度
**状态**: 已完成 (v1.0.0)

**功能特性**:
- 根据物体物理尺寸自动计算输出分辨率
- 确保资产库质量一致性
- 支持 px/unit 目标密度设置

---

### 3.3 抗锯齿与降噪管道
**状态**: 已完成 (v0.9.3)

**技术实现**:
- 集成 Intel OIDN (Open Image Denoise)
- 通过临时合成器节点实现
- 零泄漏场景清理

---

## 第四阶段：生产硬化与生态
**目标**: 100% 架构稳定性、零泄漏场景管理、跨版本参数对齐。

### 4.1 参数一致性 & 动态对齐 (硬化)
**状态**: 100% CI PASS (3.3, 3.6, 4.2, 4.5, 5.0+)

**技术实现**:
- **三点对齐协议**: Constants ↔ Engine ↔ Automation
- 标准化的 `add_bake_result_to_ui` 确保元数据（bake_time, resolution）使用严格的 RNA 契约映射
- `suite_parameter_matrix.py` 跨所有 Blender 版本动态验证映射

**测试覆盖**:
- 70+ 核心测试套件
- 80+ 个别用例
- 5 个 Blender 版本全覆盖

---

### 4.2 零泄漏降噪管道 (递归清理)
**状态**: 已完成 (v1.0.0)

**技术实现**:
- 专门的 `finally` 块逻辑
- 递归识别并清除所有 `BT_Denoise_Temp*` 场景
- 清除节点树并使用 `user_clear()` 满足 B5.0 删除约束

**好处**:
- 防止批量烘焙期间内存峰值
- 避免“活动场景”冲突

---

### 4.3 Blender 5.0.x 完全支持
**状态**: 已完成 (v1.0.0)

**技术实现**:
- 健壮的树发现（Direct ↔ Compositor Object ↔ Fallback creation）
- 支持 B5.0 统一节点系统（使用 `CompositorNodeTree` ↔ `NodeGroupOutput`）
- 通过强制整数默认值解决 B5.0 注册约束

**跨版本验证**:
- Blender 3.3.21 ↔ Blender 3.6.23 ↔ Blender 4.2.14 LTS ↔ Blender 4.5.3 LTS ↔ Blender 5.0.1+

---

### 4.4 生产 E2E 验证循环
**状态**: 已完成 (v1.0.0)

**工具链**:
- `multi_version_test.py`: 自动监控多个本地 Blender 安装，70+ 核心测试套件
- 负面测试套件确保错误路径弹窗
- 综合验证脚本 (规划中)

---

### 4.5 UI/UX 生产重构
**状态**: 已完成 (v1.0.0)

**功能特性**:
- 综合仪表板式重构
- 用对齐列替换嵌套布局
- 分组功能区域获得更好的垂直流
- 专业、流线型的美学匹配高端 Blender 插件

---

### 4.6 多版本图像 & 操作符审计
**状态**: 已完成 (v1.0.0)

**功能特性**:
- 自动化完整性检查 (`test_ui_operator_integrity`)
- 验证 `ui.py` 中每个操作符正确注册
- 审计并替换高版本图标（如 `SYNCHRONIZED`, `RAYCAST`）为广泛兼容的替代品

---

## 第五阶段：异步与性能
**目标**: 解耦烘焙进程并增强外部连接。

### 5.1 后台进程烘焙 (工作线程)
**概念**: 生成分离的 Blender 工作进程执行重型烘焙，保持主界面 100% 响应用于建模。
**优先级**: HIGH (v1.6.0 重点)

**技术挑战**:
- 进程间通信
- 进度同步
- 错误处理和恢复

---

### 5.2 资产桥接：零摩擦交付
**概念**: GLB/USDZ 导出已上线，下一步是烘焙后自动 PBR 材质嵌入。
**状态**: 部分完成

---

### 5.3 并行瓦片烘焙 (UDIM 优化)
**概念**: UDIM 项目的多进程瓦片烘焙，利用高核心数 CPU。
**技术要求**:
- 多进程协作
- 瓦片依赖管理
- 结果合并

---

## 第六阶段：代码质量与可维护性
**目标**: 提高代码可维护性，遵循 Google Python Style Guide，防止未来回归。

### 6.1 导入标准化
**状态**: 已完成 (v1.0.0)

**修复内容**:
- 将 `property` 模块重命名为 `prop_module` 避免与 Python 内置冲突
- 标准化导入顺序 (stdlib ↔ bpy ↔ local modules)

---

### 6.2 类型提示 & Docstring 一致性
**状态**: 已完成 (v1.0.0)

**修复内容**:
- 为 `common.py`, `image_manager.py`, `ops.py` 核心函数添加类型提示
- 统一 docstring 风格为 Google Style（英文）

---

### 6.3 魔法数字提取
**状态**: 已完成 (v1.0.0)

**修复内容**:
- 将常量提取到 `constants.py`:
  - `UDIM_DEFAULT_TILE`
  - `GOLDEN_RATIO`
  - `MIN_THRESHOLD`
  - 等

---

### 6.4 异常处理硬化
**状态**: 已完成 (v1.0.0)

**修复内容**:
- 将裸 `except` 替换为具体异常类型 (`AttributeError`, `RuntimeError`)
- 添加使用 `.get()` 的安全回退用于字典访问

**修复文件**:
- `core/cleanup.py` - 3 处
- `state_manager.py` - 3 处
- `core/engine.py` - 7 处
- `ops.py` - 3 处

---

### 6.5 测试覆盖扩展
**状态**: 已完成 (v1.0.0)

**新增内容**:
- `suite_code_review.py` 验证所有 bug 修复
- 综合验证脚本 (规划中)
- 多版本测试框架 `multi_version_test.py`

---

## 第七阶段：未来演进...

## 第八阶段：工业级生产力增强 (对标 TexTools)

**目标**: 引入成熟的工业级工作流，将 BakeTool 提升为顶尖的资产处理平台。

### 8.1 爆炸烘焙系统 (Explode System)
**概念**: 自动将重叠的低模/高模对按名称后缀推开，消除法线漏色（Bleeding）瑕疵，烘焙后自动还原坐标。
**核心优势**: 解决复杂机械结构的投影遮挡问题。

### 8.2 高级几何算子 (Advanced Geometry Passes)
**概念**: 引入更多 TexTools 风格的预设通道：
*   **Bevel Mask**: 模拟边缘磨损
*   **Soft/Fine Curvature**: 针对不同尺度的细节捕捉
*   **Tangent/World Space Normal**: 灵活的法线空间转换
*   **Dust/Cavity**: 基于拓扑的污垢分布图

### 8.3 智能后缀匹配 2.0 (Smart-Suffix Matching)
**概念**: 增强 `SMART_SET` 逻辑，支持正则表达式和多后缀（如 `_high`, `_hp`, `_source`）的自动识别与批量配对。

---

## 版本发布计划

### v1.0.0 (当前版本) - 生产就绪与代码整合
**发布日期**: 2026-04-17

**主要工作**:
- 架构统一：单一自动化入口与自举测试
- 代码整肃：全量补充 Google Style Docstrings 与类型提示
- 质量硬化：修复 17+ 处异常处理隐患与语法瑕疵
- 跨版本验证：Blender 3.3 - 5.0 100% 通过

---

### v1.1.0 (计划中) - 工业级增强 (致敬 TexTools)
**目标**: 后台工作线程实现、多 GPU 瓦片烘焙

**主要特性**:
- [ ] 后台进程烘焙
- [ ] 进度事件 API
- [ ] 多 GPU 支持

---

### v1.7.0 (计划中) - 智能增强
**目标**: AI 辅助功能

**主要特性**:
- [ ] 智能参数推荐
- [ ] 材质自动分析
- [ ] 工作流模板

---

### v2.0.0 (远期) - 生态系统
**目标**: 成为 Blender 生态的烘焙中间件
**主要特性**:
- [ ] 外部引擎桥接（Marmoset, Substance）
- [ ] 云渲染集成
- [ ] AI 辅助重拓扑桥接

---

## 贡献指南

欢迎贡献！请遵循以下步骤：
1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. Push 到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 开发环境要求
- Python 3.10+
- Blender 3.3 - 5.0+
- Git

### 运行测试

```bash
# 单版本测试
blender -b --python automation/cli_runner.py -- --suite all

# 跨版本测试
python automation/multi_version_test.py --verification
```

---

## 资源链接

- [用户手册](USER_MANUAL.md)
- [开发者指南](docs/dev/DEVELOPER_GUIDE.md)
- [生态集成指南](docs/dev/ECOSYSTEM_GUIDE.md)
- [自动化参考](docs/dev/AUTOMATION_REFERENCE.md)
- [风格分析](STYLE_GUIDE_ANALYSIS.md)

---

*本路线图由 BakeTool 团队维护*
*最后更新: 2026-04-17*