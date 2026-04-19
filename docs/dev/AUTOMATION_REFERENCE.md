# BakeTool 自动化工具参�?## Automation Tools Reference

**版本:** 1.0.0

---

## 快速参�?
### 测试命令

```bash
# Blender UI
N 面板 �?Baking �?Debug Mode �?Run Test Suite

# CLI
blender -b --python automation/cli_runner.py -- --suite all

# 跨版本测�?python automation/multi_version_test.py --verification
```

---

## 1. CLI Runner (`cli_runner.py`)

统一测试入口点�?
### 基本用法

```bash
blender -b --python automation/cli_runner.py [选项]
```

### 选项

| 选项 | 描述 | 示例 |
|------|------|------|
| `--suite` | 指定测试套件 | `--suite unit` |
| `--category` | 按类别运�?| `--category memory` |
| `--test` | 运行单个测试 | `--test suite_api.SuiteAPI.test_example` |
| `--discover` | 自动发现所有测�?| `--discover` |
| `--json` | 输出 JSON 报告 | `--json report.json` |
| `--list` | 列出所有套�?| `--list` |

### 可用套件

| 套件 | 描述 |
|------|------|
| `unit` | 核心单元测试 |
| `shading` | 着色逻辑测试 |
| `negative` | 负面/边界测试 |
| `memory` | 内存泄漏检�?|
| `export` | 导出安全性测�?|
| `api` | API 稳定性测�?|
| `context_lifecycle` | 上下文生命周�?|
| `cleanup` | 资源清理测试 |
| `denoise` | 降噪器测�?|
| `parameter_matrix` | 参数矩阵测试 |
| `preset` | 预设功能测试 |
| `production_workflow` | 端到端流�?|
| `udim_advanced` | UDIM 高级功能 |
| `ui_logic` | UI 逻辑测试 |
| `code_review` | 代码审查 |
| `all` | 所有套�?|

### 可用类别

| 类别 | 包含的套�?|
|------|------------|
| `core` | unit, negative, api, cleanup, compat, parameter_matrix |
| `memory` | memory |
| `export` | export |
| `ui` | ui_logic |
| `integration` | production_workflow, context_lifecycle |

### 示例

```bash
# 运行单个套件
blender -b --python automation/cli_runner.py -- --suite unit

# 运行多个类别
blender -b --python automation/cli_runner.py -- --category memory

# 发现并运行所有测�?blender -b --python automation/cli_runner.py -- --discover

# 生成 JSON 报告
blender -b --python automation/cli_runner.py -- --json test_report.json --suite all

# 列出所有可用套�?blender -b --python automation/cli_runner.py -- --list
```

---

## 2. Multi-Version Test (`multi_version_test.py`)

�?Blender 版本测试运行器�?
### 基本用法

```bash
python automation/multi_version_test.py [选项]
```

### 选项

| 选项 | 描述 |
|------|------|
| `--verification` | 运行综合验证脚本 |
| `--suite` | 指定测试套件 |
| `--category` | 按类别运�?|
| `--list` | 列出可用�?Blender 版本 |
| `--json` | 保存详细 JSON 报告 |

### 环境变量

```bash
# 自定�?Blender 路径
export BLENDER_PATHS="D:\Blender\3.6\blender.exe;D:\Blender\4.2\blender.exe"
python automation/multi_version_test.py
```

### 默认测试版本

- Blender 3.3.21
- Blender 3.6.23
- Blender 4.2.14 LTS
- Blender 4.5.3 LTS
- Blender 5.0.1

### 示例

```bash
# 完整验证
python automation/multi_version_test.py --verification

# 运行单元测试
python automation/multi_version_test.py --suite unit

# 内存测试
python automation/multi_version_test.py --category memory

# 列出可用版本
python automation/multi_version_test.py --list

# JSON 输出
python automation/multi_version_test.py --json cross_version_report.json
```

---

## 3. Comprehensive Verification (`comprehensive_verification.py`)

**状态**: 规划中 - 尚未实现

此脚本旨在运行完整的代码审查验证。当前可通过测试套件覆盖：
```bash
blender -b --python automation/cli_runner.py -- --suite all
```

### 验证项目

| 编号 | 验证�?| 描述 |
|------|--------|------|
| FIX-1 | Memory Leak | `use_fake_user` 默认行为 |
| FIX-2 | Image Cleanup | `DeleteResult` 移除数据�?|
| FIX-3 | NumPy Memory | `_physical_clear_pixels` 内存优化 |
| FIX-4 | Export Safety | 隐藏对象导出安全 |
| FIX-5 | UI Poll Safety | `context.space_data` 安全访问 |
| FIX-6 | Mesh Cleanup | `do_unlink=True` 正确清理 |

### 输出示例

```
======================================================================
      BAKETOOL v1.0.0 VERIFICATION SUITE
======================================================================
  Blender Version: 4.2.14 LTS
  Python Version:  3.11.7
======================================================================

[FIX-1] Memory Leak Fix: use_fake_user
  [PASS] use_fake_user_not_default
  [PASS] use_fake_user_with_setting

[FIX-2] Image Cleanup Fix: DeleteResult
  [PASS] delete_result_removes_datablock
  [PASS] no_accumulation

...

======================================================================
      COMPREHENSIVE VERIFICATION SUMMARY
======================================================================
  Total Tests:  15
  Passed:      15
  Failed:      0
----------------------------------------------------------------------

>>> ALL VERIFICATIONS PASSED!
```

---

## 4. Headless Bake (`headless_bake.py`)

无头模式烘焙 CLI 工具�?
### 基本用法

```bash
blender -b scene.blend -P automation/headless_bake.py -- [选项]
```

### 选项

| 选项 | 描述 | 示例 |
|------|------|------|
| `--job` | 指定任务名称 | `--job "MainBake"` |
| `--output` | 输出目录 | `--output "C:/baked/"` |

### 示例

```bash
# 运行所有启用的任务
blender -b scene.blend -P automation/headless_bake.py

# 指定任务
blender -b scene.blend -P automation/headless_bake.py -- --job "PBR_Job"

# 指定输出目录
blender -b scene.blend -P automation/headless_bake.py -- --output "C:/output/"

# 组合
blender -b scene.blend -P automation/headless_bake.py -- --job "PBR" --output "C:/baked/"
```

---

## 5. Environment Setup (`env_setup.py`)

**状态**: 规划中 - 尚未实现

测试环境初始化模块 (规划中)。

### 当前替代方案

直接使用 CLI Runner 加载测试环境：
```bash
blender -b --python automation/cli_runner.py -- --suite all
```

---

## 6. Translation Extractor (`dev_tools/extract_translations.py`)

翻译字符串提取与同步工具�?
### 基本用法

```bash
python dev_tools/extract_translations.py [选项]
```

### 选项

| 选项 | 描述 |
|------|------|
| `--mode` | 同步模式 |
| `--path` | 扫描根目�?|

### 模式

| 模式 | 描述 |
|------|------|
| `update` | 添加�?key，保留旧 key (默认) |
| `sync` | 删除未使用的 key |
| `clean` | 删除所�?key 并重置翻�?|

### 示例

```bash
# 扫描并更新翻译文�?python dev_tools/extract_translations.py

# 同步：删除未使用�?key
python dev_tools/extract_translations.py --mode sync

# 清理：重置所有翻�?python dev_tools/extract_translations.py --mode clean

# 指定路径
python dev_tools/extract_translations.py --path /path/to/addon
```

### 输出

```json
{
    "header": {
        "system": "Extracted by Universal Tool"
    },
    "data": {
        "Bake": {
            "zh_CN": "烘焙",
            "fr_FR": "Cuire"
        }
    }
}
```

---

## 7. 测试辅助工具 (`test_cases/helpers.py`)

### DataLeakChecker

检�?Blender 数据块泄漏：

```python
from test_cases.helpers import DataLeakChecker

checker = DataLeakChecker()
# ... 执行操作 ...
leaks = checker.check()
if leaks:
    print(f"Leaks: {leaks}")
```

### assert_no_leak

上下文管理器检测泄漏：

```python
from test_cases.helpers import assert_no_leak

def test_example(self):
    with assert_no_leak(self):
        create_images()
        create_meshes()
```

### JobBuilder

流畅 API 构建测试任务�?
```python
from test_cases.helpers import JobBuilder

job = (JobBuilder("TestJob")
    .mode("SINGLE_OBJECT")
    .type("BSDF")
    .resolution(256)
    .add_objects([obj])
    .enable_channel("color")
    .build())
```

### cleanup_scene

深度清理场景�?
```python
from test_cases.helpers import cleanup_scene

cleanup_scene()  # 清理所有测试数?```

### create_test_object

创建标准测试对象?
```python
from test_cases.helpers import create_test_object

obj = create_test_object(
    name="TestCube",
    location=(0, 0, 0),
    color=(0.8, 0.2, 0.2, 1.0),
    metal=0.5,
    rough=0.3,
    mat_count=1
)
```

### MockSetting

Mock 设置对象�?
```python
from test_cases.helpers import MockSetting

setting = MockSetting(
    res_x=512,
    res_y=512,
    bake_type="BSDF",
    use_external_save=True,
    external_save_path="/tmp/baked"
)
```

---

## 8. 环境变量

| 变量 | 描述 | 示例 |
|------|------|------|
| `BLENDER_PATHS` | 自定?Blender 路径 (分号分隔) | `D:\Blender\3.6\blender.exe;D:\Blender\4.2\blender.exe` |
| `PYTHONIOENCODING` | Python 输出编码 | `utf-8` |

---

## 9. 退出码

| 退出码 | 描述 |
|--------|------|
| 0 | 所有测?验证通过 |
| 1 | 有测试失败或错误 |

---
