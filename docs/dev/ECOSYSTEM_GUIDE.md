# BakeTool 生态集成指?## Ecosystem Integration Guide

**版本:** 1.0.0
**更新日期:** 2026-04-17

---

## 目录

1. [生态概述](#1-生态概?
2. [Blender 测试生态](#2-blender-测试生?
3. [BakeTool 测试框架](#3-baketool-测试框架)
4. [自动化工具链](#4-自动化工具链)
5. [CI/CD 集成](#5-cicd-集成)
6. [国际化工作流](#6-国际化工作流)
7. [维护指南](#7-维护指南)
8. [最佳实践](#8-最佳实?

---

## 1. 生态概?
BakeTool 拥有一套完整的开发工具链，包括：

```
baketool/
├── automation/           # 自动化工??  ├── cli_runner.py           # 统一 CLI 测试入口
?  ├── comprehensive_verification.py  # 综合验证脚本
?  ├── multi_version_test.py   # 跨版本测??  ├── headless_bake.py        # 无头烘焙 CLI
?  └── env_setup.py            # 环境配置
├── test_cases/          # 测试套件
?  ├── helpers.py              # 测试辅助工具
?  ├── suite_unit.py           # 单元测试
?  ├── suite_memory.py         # 内存测试
?  ├── suite_export.py         # 导出测试
?  ├── suite_api.py            # API 测试
?  └── ... (15+ 测试套件)
├── dev_tools/
?  └── extract_translations.py  # 翻译提取工具
└── docs/dev/
    ├── DEVELOPER_GUIDE.md      # 开发者指?    └── STANDARDIZATION_GUIDE.md # 标准化指?```

---

## 2. Blender 测试生?
### 2.1 Blender 官方测试方式

Blender 插件开发主要有以下测试方式?
| 方式 | 描述 | 适用场景 |
|------|------|----------|
| **unittest (内置)** | Blender 内置 `unittest` 模块 | 基础单元测试 |
| **pytest-blender** | pytest 插件 | 高级测试框架 |
| **Headless CLI** | `blender -b --python` | CI/CD 自动?|
| **Manual Testing** | Blender GUI | 手动验收测试 |

### 2.2 Blender 测试最佳实?
```python
# 标准 Blender 测试模板
import bpy
import unittest

class TestMyAddon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Blender 环境初始?        bpy.ops.mesh.primitive_cube_add()

    def setUp(self):
        # 每个测试前清?        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()

    def tearDown(self):
        # 测试后清?        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()

    def test_example(self):
        self.assertIsNotNone(bpy.context.object)
```

### 2.3 Blender 版本兼容性策?
```python
# core/compat.py 示例
import bpy

# 版本检?IS_BLENDER_5 = bpy.app.version >= (5, 0, 0)
IS_BLENDER_4 = bpy.app.version >= (4, 0, 0)
IS_BLENDER_3 = bpy.app.version >= (3, 0, 0)

def get_bake_settings(scene):
    """统一访问烘焙设置（兼?3.3 - 5.0+?""
    if IS_BLENDER_5:
        return scene.render.bake
    return scene.render
```

---

## 3. BakeTool 测试框架

### 3.1 框架架构

```
┌─────────────────────────────────────────────────────────────??                   CLI 入口?                                ?? automation/cli_runner.py                                    ?? - --suite, --category, --json, --list                     ?└─────────────────────────────────────────────────────────────?                              ?                              ?┌─────────────────────────────────────────────────────────────??                   测试套件?                                ?? test_cases/suite_*.py                                      ?? - suite_unit.py      # 核心逻辑                            ?? - suite_memory.py    # 内存泄漏检?                       ?? - suite_export.py    # 导出安全?                         ?? - suite_api.py       # API 稳定?                         ?? - ...                                                  ?└─────────────────────────────────────────────────────────────?                              ?                              ?┌─────────────────────────────────────────────────────────────??                   辅助工具?                                ?? test_cases/helpers.py                                      ?? - DataLeakChecker    # 数据泄漏检?                       ?? - JobBuilder         # 流畅 API 构建测试任务               ?? - MockSetting        # Mock 对象                           ?? - cleanup_scene()     # 场景清理                           ?└─────────────────────────────────────────────────────────────?```

### 3.2 核心组件详解

#### 3.2.1 DataLeakChecker

检?Blender 数据块泄漏：

```python
from test_cases.helpers import DataLeakChecker, assert_no_leak

class TestMemoryLeaks(unittest.TestCase):
    def test_no_image_leak(self):
        checker = DataLeakChecker()

        # 执行操作
        img = bpy.data.images.new("TestImg", 64, 64)

        # 检查泄?        leaks = checker.check()
        self.assertEqual(len(leaks), 0, f"Leaks detected: {leaks}")
```

#### 3.2.2 assert_no_leak (上下文管理器)

```python
from test_cases.helpers import assert_no_leak

def test_operations(self):
    with assert_no_leak(self, aggressive=True):
        # 执行可能泄漏的操?        create_bake_result()
        apply_baked_result()
    # 自动检测泄?```

#### 3.2.3 JobBuilder (流畅 API)

```python
from test_cases.helpers import JobBuilder

job = (JobBuilder("TestJob")
    .mode("SINGLE_OBJECT")
    .type("BSDF")
    .resolution(512)
    .add_objects([obj1, obj2])
    .enable_channel("color")
    .build())
```

### 3.3 测试套件清单

| 套件 | 文件 | 描述 | 分类 |
|------|------|------|------|
| 单元测试 | `suite_unit.py` | 核心组件逻辑测试 | core |
| 内存测试 | `suite_memory.py` | 内存泄漏检?| memory |
| 导出测试 | `suite_export.py` | 导出安全?| export |
| API 测试 | `suite_api.py` | 公共 API 稳定?| core |
| UI 测试 | `suite_ui_logic.py` | 面板绘制逻辑 | ui |
| 预设测试 | `suite_preset.py` | 序列化与迁移 | core |
| 负面测试 | `suite_negative.py` | 边界条件 | core |
| 降噪测试 | `suite_denoise.py` | 降噪器集?| core |
| 生产流测?| `suite_production_workflow.py` | 端到端流?| integration |
| 上下文生命周?| `suite_context_lifecycle.py` | 上下文管?| integration |
| 清理测试 | `suite_cleanup.py` | 资源清理 | core |
| 兼容性测?| `suite_compat.py` | 版本兼容?| core |
| 参数矩阵 | `suite_parameter_matrix.py` | 参数组合测试 | core |
| UDIM 高级 | `suite_udim_advanced.py` | UDIM 功能 | core |
| 着色测?| `suite_shading.py` | 着色器逻辑 | core |
| 代码审查 | `suite_code_review.py` | 静态检?| core |

### 3.4 运行测试

#### 3.4.1 Blender UI 运行

```
Blender ?N 面板 ?Baking ?Debug Mode ?Run Test Suite
```

#### 3.4.2 CLI 运行

```bash
# 单个测试套件
blender -b --python automation/cli_runner.py -- --suite unit

# 所有测试套?blender -b --python automation/cli_runner.py -- --suite all

# 按类别运?blender -b --python automation/cli_runner.py -- --category memory

# 列出所有套?blender -b --python automation/cli_runner.py -- --list

# 输出 JSON 报告
blender -b --python automation/cli_runner.py -- --json report.json
```

#### 3.4.3 跨版本测?
```bash
python automation/multi_version_test.py --verification

# 指定类别
python automation/multi_version_test.py --category memory
```

---

## 4. 自动化工具链

### 4.1 工具清单

| 工具 | 路径 | 用?|
|------|------|------|
| **cli_runner.py** | `automation/` | 统一测试入口 |
| **multi_version_test.py** | `automation/` | ?Blender 版本测试 |
| **comprehensive_verification.py** | `automation/` | 修复验证 |
| **headless_bake.py** | `automation/` | 无头烘焙 CLI |
| **extract_translations.py** | `dev_tools/` | 翻译提取与同?|

### 4.2 CLI Runner 详解

```bash
# 基本用法
blender -b --python automation/cli_runner.py [选项]

# 选项
--suite {unit|shading|negative|memory|export|api|all}
    指定运行的测试套?
--category {all|core|memory|export|ui|integration}
    按类别运行测?
--test <test_name>
    运行指定测试用例

--discover
    自动发现所?suite_*.py 文件

--json <path>
    保存 JSON 格式报告

--list
    列出所有可用测试套?```

### 4.3 综合验证脚本

用于验证代码审查中识别的修复?
```bash
# 运行验证
blender -b --python automation/comprehensive_verification.py

# 多版本验?python automation/multi_version_test.py --verification
```

**验证覆盖?*
1. 内存泄漏修复 (`use_fake_user`)
2. 图像清理修复 (`DeleteResult`)
3. NumPy 内存优化 (`_physical_clear_pixels`)
4. 导出安全?(`hidden_object_export`)
5. UI 安全 (`space_data` 访问)
6. 网格清理 (`do_unlink=True`)

### 4.4 无头烘焙

```bash
# 基本用法
blender -b scene.blend -P automation/headless_bake.py -- --job "JobName" --output "C:/output"

# 无参数（运行所有启用的任务?blender -b scene.blend -P automation/headless_bake.py
```

---

## 5. CI/CD 集成

### 5.1 GitHub Actions 示例

```yaml
# .github/workflows/test.yml
name: BakeTool Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        blender-version: ['3.3.21', '3.6.23', '4.2.14', '4.5.3', '5.0.1']

    container:
      image: user/blender:${{ matrix.blender-version }}

    steps:
      - uses: actions/checkout@v4

      - name: Run Tests
        run: |
          blender -b --python automation/cli_runner.py -- --json test_report.json

      - name: Upload Report
        uses: actions/upload-artifact@v4
        with:
          name: test-report-${{ matrix.blender-version }}
          path: test_report.json

  verify:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Verification
        run: python automation/multi_version_test.py --verification
```

### 5.2 预提交钩?
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml

  - repo: local
    hooks:
      - id: blender-lint
        name: Blender Python Syntax
        entry: blender -b --python-expr "exec(open('tests/lint_check.py').read())"
        language: system
        files: \.py$
```

### 5.3 本地开发工作流

```bash
# 1. 安装 pre-commit
pip install pre-commit
pre-commit install

# 2. 运行所有测?make test

# 3. 运行跨版本测?make test-multi-version

# 4. 生成翻译
python dev_tools/extract_translations.py --mode sync
```

---

## 6. 国际化工作流

### 6.1 翻译提取工具

```bash
# 扫描代码，提取需要翻译的字符?python dev_tools/extract_translations.py --mode update

# 同步：删除未使用?key
python dev_tools/extract_translations.py --mode sync

# 清理：重置所有翻?python dev_tools/extract_translations.py --mode clean
```

### 6.2 工具特点

**SmartFilter 智能过滤?*
- ?保留：用户可见文?(`"Bake"`, `"Select Object"`)
- ?忽略：内?ID (`"BAKETOOL_OT_Bake"`)
- ?忽略：数?(`"1024"`, `"3.14"`)
- ?忽略：单字符 (`"X"`, `"Y"`, `"Z"`)

### 6.3 Blender i18n 集成

BakeTool 使用 Blender 内置的翻译系统：

```python
# 注册翻译
bpy.app.translations.register(__name__, translations.translation_dict)

# 使用翻译
layout.label(text=bpy.app.translations.pgettext("Bake"))

# 注销
bpy.app.translations.unregister(__name__)
```

### 6.4 添加新语言

1. 编辑 `translations.py`
2. 添加语言代码?`translation_dict`
3. 翻译所有字符串

---

## 7. 维护指南

### 7.1 发布检查清?
- [ ] 运行所有测试套?(`--suite all`)
- [ ] 运行跨版本测?(`--verification`)
- [ ] 检查内存泄?(`suite_memory.py`)
- [ ] 验证导出安全?(`suite_export.py`)
- [ ] 更新 `bl_info` 版本?- [ ] 更新 CHANGELOG
- [ ] 运行翻译同步 (`--mode sync`)

### 7.2 回归防御

每当修改以下内容时，必须运行相应测试?
| 修改内容 | 必须运行的测?|
|----------|----------------|
| `core/engine.py` | `suite_unit.py`, `suite_production_workflow.py` |
| `core/image_manager.py` | `suite_memory.py`, `suite_unit.py` |
| `core/node_manager.py` | `suite_shading.py`, `suite_unit.py` |
| `ui.py` | `suite_ui_logic.py` |
| `property.py` | `suite_parameter_matrix.py`, `suite_preset.py` |
| 任何核心模块 | `suite_compat.py` (跨版本测? |

### 7.3 性能基准

```bash
# 运行性能测试
blender -b --python automation/cli_runner.py -- --suite unit --test test_performance
```

### 7.4 调试技?
```python
# 在测试中添加断点
import code; code.interact(local=dict(globals(), **locals()))

# 打印场景状?print(f"Objects: {len(bpy.data.objects)}")
print(f"Images: {len(bpy.data.images)}")
print(f"Materials: {len(bpy.data.materials)}")
```

---

## 8. 最佳实?
### 8.1 测试命名规范

```python
# 命名模式: test_<feature>_<scenario>_<expected>
def test_image_manager_creates_with_correct_resolution(self):
    pass

def test_export_hidden_object_no_crash(self):
    pass

def test_memory_leak_no_accumulation_after_bake(self):
    pass
```

### 8.2 测试隔离

```python
def setUp(self):
    cleanup_scene()  # 确保干净的环?
def tearDown(self):
    cleanup_scene()  # 清理测试产物
```

### 8.3 Mock 对象策略

```python
# 优先使用 helpers.py 中的 MockSetting
from test_cases.helpers import MockSetting

setting = MockSetting(
    res_x=512,
    res_y=512,
    bake_type="BSDF"
)
```

### 8.4 持续改进

1. **TDD 开?*: 新功能先写测?2. **测试覆盖?*: 目标 >80%
3. **自动?*: 所有测试在 CI/CD 中运?4. **文档同步**: 测试即文?
---

## 附录 A: Blender 测试资源

- [Blender Python API Docs](https://docs.blender.org/api/current/)
- [Blender Stack Exchange](https://blender.stackexchange.com/)
- [Blender Development Forum](https://developer.blender.org/)

## 附录 B: 相关工具

| 工具 | 用?|
|------|------|
| [pytest-blender](https://github.com/puckow/pytest-blender) | pytest 插件 |
| [blender-addon-tests](https://github.com/p2or/blender-addon-tests) | 测试模板 |
| [pre-commit-blender](https://github.com/scientific-assets/pre-commit-blender) | pre-commit 钩子 |

---

*本指南由 BakeTool 团队维护 - 最后更? 2026-04-17*
