***

# BakeTool 任务看板
## Task Board - v1.0.0 Production Hardened

**版本:** 1.0.0
**更新日期:** 2026-04-17
**目标:** 持续改进 BakeTool 的稳定性、可维护性和用户体验

---

## 概述

本任务看板记录了 BakeTool 开发过程中的所有改进工作，包括已完成的修复、增强功能和计划中的改进。每个任务都分配了唯一标识符，便于追踪和引用。

---

## 第一阶段：核心 Bug 修复

**优先级:** CRITICAL
**状态:** 已完成
**目标:** 修复影响生产稳定性的关键问题

| ID | 描述 | 文件 | 状态 | 日期 |
|----|------|------|------|------|
| CB-1 | 修复 `core/compat.py` 中的同义反复逻辑，确保 NORMAL 映射正确 (B3.x/B4+) | compat.py | 已完成 | 2026-01-15 |
| CB-2 | 重构 `core/api.py` 的 `bake()` 函数，使其正确处理 `objects` 参数，不再强制调用 UI 算子 | api.py | 已完成 | 2026-01-15 |
| CB-3 | 修复 `core/execution.py` 中的类级可变对象污染问题 (`bake_queue = []`) | execution.py | 已完成 | 2026-01-15 |
| CB-4 | 在 `core/execution.py` 中的 `gl_free()` 增加 Blender 5.0+ 版本守护 | execution.py | 已完成 | 2026-01-15 |
| CB-5 | 修正 `core/cage_analyzer.py` 的裸 `except` 捕获，改为 `except Exception` | cage_analyzer.py | 已完成 | 2026-01-15 |

---

## 第二阶段：高优先级改进

**优先级:** HIGH
**状态:** 已完成
**目标:** 增强功能稳定性和用户体验

| ID | 描述 | 文件 | 状态 | 日期 |
|----|------|------|------|------|
| HP-1 | 解决 `core/cage_analyzer.py` 中的 BMesh 内存泄漏 (使用 `try/finally`) | cage_analyzer.py | 已完成 | 2026-01-10 |
| HP-2 | 修复 `core/cage_analyzer.py` 的选择状态副作用，操作后恢复原始选择 | cage_analyzer.py | 已完成 | 2026-01-10 |
| HP-3 | 优化 `core/cage_analyzer.py` 的性能，减少不必要的计算 | cage_analyzer.py | 已完成 | 2026-01-12 |
| HP-4 | 修复 `core/engine.py` 中空列表可能导致的 `IndexError` | engine.py | 已完成 | 2026-01-12 |
| HP-5 | 修正 `core/shading.py` 节点连接：在颜色输出与 Shader 输入间插入 `Emission` 节点 | shading.py | 已完成 | 2026-01-12 |
| HP-6 | 修复 `core/image_manager.py` 在未保存文件时的路径回退逻辑 (使用 `bpy.app.tempdir`) | image_manager.py | 已完成 | 2026-01-13 |
| HP-7 | 修复 `core/common.py` 中的孤立网格数据残留问题 | common.py | 已完成 | 2026-01-13 |
| HP-8 | 在 `core/engine.py` 导出逻辑前增加插件依赖性检查 (glTF/USD) | engine.py | 已完成 | 2026-01-14 |
| HP-9 | 全局替换：将所有散乱的 `bpy.app.version` 检查统一为 `compat` 模块调用 | 全局 | 已完成 | 2026-01-14 |

---

## 第三阶段：测试套件硬化

**优先级:** HIGH
**状态:** 已完成
**目标:** 建立全面的自动化测试体系

| ID | 描述 | 文件 | 状态 | 日期 |
|----|------|------|------|------|
| TB-1 | 修复 `suite_parameter_matrix.py` 中的 Linux 硬编码路径问题 | suite_parameter_matrix.py | 已完成 | 2026-01-15 |
| TB-2 | 增强 `suite_preset.py`：验证序列化后的频道顺序一致性 | suite_preset.py | 已完成 | 2026-01-15 |
| TB-3 | 修正 `suite_unit.py` 中的无效断言逻辑 | suite_unit.py | 已完成 | 2026-01-15 |
| TB-4 | 增强 `suite_memory.py`：添加更多内存泄漏检测用例 | suite_memory.py | 已完成 | 2026-01-16 |
| TB-5 | 添加 `suite_export.py`：专门测试导出安全性 | suite_export.py | 已完成 | 2026-01-16 |
| TB-6 | 修复 `cli_runner.py` 中的测试套件映射表错误 | cli_runner.py | 已完成 | 2026-01-17 |
| D-3 | 移除 `automation/multi_version_test.py` 中的个人硬编码路径 | multi_version_test.py | 已完成 | 2026-01-17 |
| NEW-1 | 增加端到端测试：取消烘焙后的状态恢复 (State Recovery) | suite_production_workflow.py | 已完成 | 2026-01-17 |
| NEW-2 | 增加端到端测试：降噪 (Denoise) 流程验证 | suite_denoise.py | 已完成 | 2026-01-18 |
| NEW-3 | 新增综合验证套件：`test_cases/suite_verification.py` | suite_verification.py | 已完成 | 2026-04-19 |
| NEW-4 | 自动化系统统一：整合 `multi_version_test`，清理冗余脚本 | 全局 | 已完成 | 2026-04-19 |

---

## 第四阶段：文档与代码质量

**优先级:** MEDIUM
**状态:** 已完成
**目标:** 完善文档和代码质量

| ID | 描述 | 文件 | 状态 | 日期 |
|----|------|------|------|------|
| D-1 | 统一 `__init__.py`、`manifest` 与 `README` 中的版本号为 `1.0.0` | __init__.py, README.md | 已完成 | 2026-01-15 |
| D-2 | 修正 `DEVELOPER_GUIDE.md` 中的重复章节编号 | DEVELOPER_GUIDE.md | 已完成 | 2026-01-15 |
| D-4 | 更新所有文档以反映 v1.0.0 变更 | docs/* | 已完成 | 2026-04-17 |
| D-5 | 创建生态集成指南 `ECOSYSTEM_GUIDE.md` | docs/dev/ | 已完成 | 2026-04-17 |
| D-6 | 创建自动化参考文档 `AUTOMATION_REFERENCE.md` | docs/dev/ | 已完成 | 2026-04-17 |
| MP-1 | 清理 `__init__.py` 中未使用的导入 | __init__.py | 已完成 | 2026-01-16 |
| MP-2 | 清理 `api.py`、`engine.py` 等 6 个文件中的未使用 Import | api.py, engine.py | 已完成 | 2026-01-16 |
| MP-3 | 清理未使用的变量和函数 | 多个文件 | 已完成 | 2026-01-16 |
| MP-10 | 优化 `core/node_manager.py` 的导入顺序 | node_manager.py | 已完成 | 2026-01-17 |
| MP-11 | 将 `core/common.py` 中的 `_create_simple_mat` 嵌套函数提取至模块级别 | common.py | 已完成 | 2026-01-17 |
| MP-12 | 添加 `core/__init__.py` 模块文档字符串 | core/__init__.py | 已完成 | 2026-04-17 |

---

## 第五阶段：参数一致性与动态对应

**优先级:** HIGH
**状态:** 已完成
**目标:** 确保 UI、引擎和常量之间的参数同步

| ID | 描述 | 文件 | 状态 | 日期 |
|----|------|------|------|------|
| LC-1 | 参数一致性守护：实现 `PropertySyncIntegrity` 机制，确保 UI 属性与 Engine 任务参数通过 `Constants` 动态对应 | constants.py | 已完成 | 2026-01-15 |
| LC-2 | 自动化回归测试：增加 `suite_parameter_matrix.py`，专门测试 120+ 组合下的参数同步有效性 | suite_parameter_matrix.py | 已完成 | 2026-01-15 |
| LC-3 | 添加 `suite_code_review.py` 验证所有 bug 修复 | suite_code_review.py | 已完成 | 2026-01-18 |
| LC-4 | 实施三点点对齐协议：Constants 与 Engine 与 UI | 全局 | 已完成 | 2026-01-18 |

---

## 第六阶段：代码规范与质量

**优先级:** MEDIUM
**状态:** 已完成
**目标:** 遵循 Google Python Style Guide，提高代码可维护性

| ID | 描述 | 文件 | 状态 | 日期 |
|----|------|------|------|------|
| CS-1 | 修复 `__init__.py` 中 bl_info 重复定义问题 | __init__.py | 已完成 | 2026-01-15 |
| CS-2 | 修复 `ops.py` 中 UI_MESSAGES KeyError 风险，使用 .get() 优雅降级 | ops.py | 已完成 | 2026-01-15 |
| CS-3 | 修复 `core/engine.py` 中日志重复问题 | engine.py | 已完成 | 2026-01-15 |
| CS-4 | 修复 `core/common.py` 中材质命名冲突，使用 UUID 生成唯一名称 | common.py | 已完成 | 2026-01-16 |
| CS-5 | 优化 `property.py` 中枚举回调性能 | property.py | 已完成 | 2026-01-16 |
| CS-6 | 改进 `core/node_manager.py` 节点链接清理逻辑注释 | node_manager.py | 已完成 | 2026-01-16 |
| CS-7 | Import 顺序规范化：修复 Python 内置模块 property 命名冲突，重命名为 prop_module | __init__.py, ops.py | 已完成 | 2026-01-17 |
| CS-8 | 类型提示添加：为 core/common.py, core/image_manager.py, ops.py 核心函数添加类型注解 | common.py, image_manager.py | 已完成 | 2026-01-17 |
| CS-9 | Docstring 风格统一：统一使用 Google Style 格式，英文 docstring 替代中文注释 | 多个文件 | 已完成 | 2026-01-17 |
| CS-10 | 魔法数字提取：在 constants.py 中定义 UDIM_DEFAULT_TILE, GOLDEN_RATIO 等常量 | constants.py | 已完成 | 2026-01-18 |
| CS-11 | 错误处理改进：裸 except 改为具体异常类型 (AttributeError, RuntimeError) | 多个文件 | 已完成 | 2026-04-17 |
| CS-12 | 新增测试套件：添加 suite_code_review.py 验证所有 bug 修复 | suite_code_review.py | 已完成 | 2026-01-18 |

---

## 第八阶段：代码审查修改 (v1.0.0)

**优先级:** CRITICAL
**状态:** 已完成
**目标:** 修复影响生产稳定性的关键问题

| ID | 描述 | 文件 | 状态 | 日期 |
|----|------|------|------|------|
| CR-1 | 修复 `draw_header()` 未定义变量 `row` | ui.py:24 | 已完成 | 2026-04-17 |
| CR-2 | 修复 `draw_file_path()` 未定义变量 `row` | ui.py:39 | 已完成 | 2026-04-17 |
| CR-3 | 修复 `draw_template_list_ops()` 未定义变量 `col` | ui.py:51 | 已完成 | 2026-04-17 |
| CR-4 | 修复 `draw_image_format_options()` 未定义变量 `f_p` | ui.py:82-86 | 已完成 | 2026-04-17 |
| CR-5 | 修复 `draw_crash_report()` 未定义变量 `mgr` | ui.py:252 | 已完成 | 2026-04-17 |
| CR-6 | 修复 `NodeGraphHandler.__init__` 语法错误（缺少 `self.materials = [`） | core/node_manager.py:106 | 已完成 | 2026-04-17 |
| CR-7 | 修复 `SceneSettingsContext.__init__` 不存在 category/settings/scene 参数 | core/common.py:364-368 | 已完成 | 2026-04-17 |
| CR-8 | 修复 `BakeStepRunner.__init__` 不存在 context/scene 参数 | core/engine.py:231-234 | 已完成 | 2026-04-17 |
| CR-9 | 修复 `UVLayoutManager.__init__` 不存在 objects/settings 参数 | core/uv_manager.py:131-138 | 已完成 | 2026-04-17 |
| CR-10 | 修复 `read_log()` 重复死代码 | state_manager.py:121-125 | 已完成 | 2026-04-17 |
| CR-11 | 删除重复的 `apply_denoise` 方法定义 | core/engine.py:108-117 | 已完成 | 2026-04-17 |
| CR-12 | 修复 `DeleteResult` 重复移除逻辑 | ops.py:454-472 | 已完成 | 2026-04-17 |
| CR-13 | 同步 `blender_manifest.toml` 版本 (1.0.0 与 1.0.0) | blender_manifest.toml:3 | 已完成 | 2026-04-17 |
| CR-14 | 修复 `suite_code_review.py` 版本断言错误 | test_cases/suite_code_review.py:34 | 已完成 | 2026-04-17 |
| CR-15 | 扩展 `test_cases/__init__.py` 导入所有 16 个测试套件 | test_cases/__init__.py | 已完成 | 2026-04-17 |
| CR-16 | 添加 UTF-8 编码指定（SaveSetting/LoadSetting） | ops.py:408,425 | 已完成 | 2026-04-17 |
| CR-17 | 添加 `typing.Any` 导入 | ui.py:3 | 已完成 | 2026-04-17 |

### 新增测试用例

| ID | 描述 | 文件 | 状态 |
|----|------|------|------|
| CT-1 | 验证 `draw_header` 不抛出 NameError | suite_ui_logic.py | 已完成 |
| CT-2 | 验证 `draw_file_path` 不抛出 NameError | suite_ui_logic.py | 已完成 |
| CT-3 | 验证 `draw_template_list_ops` 不抛出 NameError | suite_ui_logic.py | 已完成 |
| CT-4 | 验证 `draw_image_format_options` 正确使用 `f_p` | suite_ui_logic.py | 已完成 |
| CT-5 | 验证 `draw_crash_report` 正确实例化 BakeStateManager | suite_ui_logic.py | 已完成 |
| CT-6 | 验证 `SceneSettingsContext` 存储参数 | suite_unit.py | 已完成 |
| CT-7 | 验证 `NodeGraphHandler` 存储 materials | suite_unit.py | 已完成 |
| CT-8 | 验证 `UVLayoutManager` 存储参数 | suite_unit.py | 已完成 |
| CT-9 | 验证 manifest 版本与 bl_info 一致 | suite_code_review.py | 已完成 |
| CT-10 | 验证所有测试套件可导入 | suite_code_review.py | 已完成 |

---

## 第七阶段：未来演进

**优先级:** MEDIUM
**状态:** 计划中
**目标:** 持续改进和功能增强

| ID | 描述 | 状态 | 目标版本 |
|----|------|------|----------|
| FE-1 | 异步核心：探索基于 `bpy.app.timers` 的后台进度条优化 | 🔲 待开发 | v1.6.0 |
| FE-2 | 分布式烘焙：多机器分块烘焙方案设计 | 🔲 待开发 | v1.6.0 |
| FE-3 | 后台工作线程：生成分离的 Blender 工作进程执行重型烘焙 | 🔲 待开发 | v1.6.0 |
| FE-4 | 多 GPU 支持：并行瓦片烘焙利用高核心数 CPU | 🔲 待开发 | v1.7.0 |
| FE-5 | 智能参数推荐：基于机器学习的参数建议 | 🔲 待开发 | v1.7.0 |
| FE-6 | 云渲染集成：支持主流云渲染服务 | 🔲 待开发 | v2.0.0 |
| FE-7 | AI 辅助重拓扑桥接：自动 LOD 生成和智能烘焙 | 🔲 待开发 | v2.0.0 |

---

## 🔧 进行中的工作

**优先级:** HIGH
**状态:** 进行中

| ID | 描述 | 文件 | 状态 | 进度 |
|----|------|------|------|------|
| WIP-1 | 完善 docstrings：为所有公共类和函数添加文档字符串 | 多个文件 | 🔄 进行中 | 40% |
| WIP-2 | 函数长度优化：拆分超过 40 行的函数 | 多个文件 | 🔄 进行中 | 20% |
| WIP-3 | 类型注解完善：为所有公共 API 添加类型提示 | 多个文件 | 🔄 进行中 | 30% |

---

## 📊 统计摘要

### 按优先级

| 优先级 | 总数 | 已完成 | 进行中 | 待开发 |
|--------|------|--------|--------|--------|
| CRITICAL | 5 | 5 | 0 | 0 |
| HIGH | 15 | 15 | 0 | 0 |
| MEDIUM | 12 | 12 | 0 | 0 |
| LOW | 0 | 0 | 0 | 0 |
| 计划中 | 7 | 0 | 0 | 7 |

### 按类别

| 类别 | 总数 | 已完成 |
|------|------|--------|
| Bug 修复 | 5 | 5 |
| 功能增强 | 9 | 9 |
| 测试 | 10 | 10 |
| 文档 | 6 | 6 |
| 代码质量 | 12 | 12 |
| 未来功能 | 7 | 0 |

---

## 🧪 测试验证

所有已完成的修复都经过以下测试验证：

### 测试覆盖

| 测试套件 | 描述 | 测试数量 |
|----------|------|----------|
| suite_unit.py | 核心单元测试 | 30+ |
| suite_memory.py | 内存泄漏检测 | 14 |
| suite_export.py | 导出安全性测试 | 10 |
| suite_api.py | API 稳定性测试 | 10+ |
| suite_compat.py | 版本兼容性测试 | 15+ |
| suite_parameter_matrix.py | 参数矩阵测试 | 120+ |
| suite_production_workflow.py | 端到端流程测试 | 10+ |
| suite_code_review.py | 代码审查测试 | 15+ |
| **总计** | | **220+** |

### 跨版本验证

所有修复在以下 Blender 版本中验证：

- Blender 3.3.21 LTS
- Blender 3.6.23 LTS
- Blender 4.2.14 LTS
- Blender 4.5.3 LTS
- Blender 5.0.1 alpha

---

## 📋 验证清单

发布前必须完成以下检查：

- [x] 运行所有测试套件 (`--suite all`)
- [x] 运行跨版本测试 (`--verification`)
- [x] 检查内存泄漏 (`suite_memory.py`)
- [x] 验证导出安全性 (`suite_export.py`)
- [x] 更新 `bl_info` 版本号
- [x] 更新 CHANGELOG
- [x] 运行翻译同步 (`--mode sync`)
- [x] 更新所有文档
- [x] 代码风格检查

---

## 🎯 目标与里程碑

### v1.0.0 (当前版本)

**目标**: 代码质量增强
**状态**: 已完成

**主要成果**:
- 17 处异常处理修改
- 完整的生态文档
- 综合验证框架
- CI/CD 工作流示例

### v1.6.0 (下一版本)

**目标**: 异步与性能
**状态**: 🔲 计划中

**计划特性**:
- 后台工作线程
- 进度事件 API
- 多 GPU 支持