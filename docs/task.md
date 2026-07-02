# BakeNexus 任务看板 / Task Board

## [v1.0.0] 发布收尾状态 (Final Check)

### 1. 核心链路状态
- **UI 对齐**：已完成。所有 RNA 属性均已同步至烘焙引擎。
- **品牌一致性**：已完成。代码、文档、Manifest 全部迁移至 BakeNexus。
- **清理机制**：已完成。验证了在异常中断下的资源回收逻辑。

### 2. 最终验证清单 (Release Checklist)
- [x] 跨版本验证 (Blender 3.3 - 5.1) 全部通过；正式 Extension 发布包最低版本为 4.2。
- [x] 品牌清理 (bl_idname 全部统一为 baketool.*；类名 BAKETOOL_OT_* 保留以维持内部一致性；文档/Manifest/README 全部 ~BakeNexus)。
- [x] 物理打包脚本一致性检查。
- [x] 文档与代码行为 100% 同步。
- [x] 动态 Enum 默认值、`--test` 单测入口、跨版本报告命名和 denoise 临时场景清理完成发布前回归修复。

### 3. v1.0.0 发布前关键修复 (Pre-release Critical Fixes)
- [x] **C-01** `core/node_manager.py` `_find_socket_source` — 新增 `is_bt_temp` 过滤，防止临时 Emission 节点被误判为用户材质节点导致黑图。
- [x] **C-02** `core/engine.py` `BakeContextManager` — 用 `ExitStack.pop_all()` 重写为原子上下文模式；`ExitStack` 提升至模块级导入避免 `NameError`。
- [x] **C-03** 项目全线 LF 换行统一 (68 files)，`.gitattributes` 配置校验通过。
- [x] **C-04** `automation/headless_bake.py` — `main()` 返回 `bool`，`__main__` 使用 `sys.exit(0 if main() else 1)` 支持 CI/CD 退出码检测。
- [x] 清理 `__pycache__`/`dist/`/`test_output/`/`reports/`/根级报告文件。
- [x] `ops.py` 未使用导入清理（BakeStep, BakeTask, TaskBuilder, BakeContextManager, BakePassExecutor, ModelExporter, BakeStepRunner, pack_channels_numpy, UVLayoutManager, set_image, save_image, compat）。
- [x] 52 个 `.py` 文件全部通过 `py_compile` 语法检查。
- [x] `CHANGELOG.md` 更新 2026-05-08 条目。
- [x] `ROADMAP.md` 更新 v1.0.0 完成状态、短期计划和技术原则章节。
- [x] `DEVELOPER_GUIDE.md` 新增 BakeContextManager 原子模式和临时节点隔离文档。

### 4. 发布前代码风格整肃 (2026-05-14) ✅
- [x] **Phase 1**: 空白字符清除 + 40 个未使用 import 删除 + 修复 2 个潜伏 bug。
- [x] **Phase 2**: E741 (ambiguous `l`) 全清除 + E701/E702 全清除。
- [x] **Phase 3**: 34 模块 docstring + 关键类/函数 docstring 补全。
- [x] **Phase 4**: 公共 API 类型化 + operator 返回类型验证。
- [x] pycodestyle 385 → 97（-75%）；跨版本 5/5 全部通过。

### 5. 发布前审计与测试优化 (2026-06-06) ✅
- [x] **Phase 6 关键修复**: UNDO 支持 (12 operator)、draw_env_status 性能优化、headless context 安全、图像泄漏修复、属性边界约束。
- [x] **Phase 7 基础设施**: CI BLENDER_DIR 修复、multi_version_test 环境变量、state_manager 回退、headless_bake 路径验证。
- [x] **Phase 8 代码质量**: 异常处理升级、register/unregister 安全、Handler 独立错误处理、属性完整性、代码风格。
- [x] **Phase 9 测试优化**: 去重 1 测试、MockSetting +27 属性、category_map 覆盖 22 suite、新增 COMBINE_OBJECT E2E。
- [x] **验证**: 158/158 测试通过、16 文件 lsp_diagnostics 通过、5/5 BAKE_MODES 全覆盖。
- [x] `CHANGELOG.md` 更新 2026-06-06 条目、`ROADMAP.md` 更新 Phase 6-9、`.gitignore` 增强。

## [v1.1.x] 后续排队功能
- [ ] Phase 5: 函数拆分（`BakeStepRunner.run` 129 行、`BakePassExecutor._run_blender_bake_pipeline`）。
- [ ] Phase 6: CI 集成（`isort` + `ruff` + `mypy` incremental）。
- [ ] 类型覆盖率目标 50%+（`core/common.py` + `core/engine.py`）。
- [ ] 异步烘焙进度条改进。
- [ ] 自动 UDIM 分页优化。
- [ ] 更加智能的导出文件重命名规则。
- [ ] 参数 schema 化：将 `property.py`、`constants.py`、UI 布局和执行读取路径纳入可自动审计的统一协议。
- [ ] 动态枚举专项测试扩展：覆盖默认值、5 元组返回、旧预设迁移和跨版本注册。
- [ ] i18n 全量翻译覆盖：`ops.py` self.report 与 `ui.py` 面板标签走 `pgettext` 或 `UI_MESSAGES`。
- [ ] CM.1: `core/engine.py` 拆分 (`ModelExporter` → `exporter.py`, `TaskBuilder+JobPreparer` → `job_prep.py`)。
- [ ] CM.2: `core/common.py` 职责拆分 (材质函数 → `shading.py`)。

### 6. 发布前最终清理与 DRY 重构 (2026-07-02) ✅
- [x] **Phase 10 — 死代码与死导入清理**：constants.py 删除 12 个零引用常量 (JOB_TYPES, ATLAS_PACK_METHODS, DENOISE_METHODS 等)；__init__.py/ui.py/ops.py 删除 7 个未用导入；property.py 删除 `use_antialiasing` 死属性；MANIFEST.in 删除（与 build_release_zip.py 冲突的死文档）。
- [x] **Phase 11 — 静默 CANCELLED 修复**：ops.py 全部 9 处无反馈的 `return {"CANCELLED"}` 添加 `self.report()`，用户点按钮无响应 → 有明确弹窗提示。
- [x] **Phase 12 — DRY 重构**：`core/common.py` 新增 `get_active_job()` 和 `tag_redraw_view3d()` 两个辅助函数，消除 12+3=15 处重复模式。`constants.py` 新增 `EXTENSION_TO_FORMAT` 从 `FORMAT_SETTINGS` 自动计算，消除 `ops.py` 的 `_get_format_from_path` 双重事实源。预览切换逻辑统一由 `update_preview` 回调处理。
- [x] **Phase 13 — 魔法字符串集中化**：`BT_Denoise_Temp`、`BT_Denoise_Camera`、`BT_Packing_Preview` 纳入 `SYSTEM_NAMES`，`constants.py` 成为 Blender 命名的事实源。
- [x] **Phase 14 — 品牌文档修正**：task.md 和 ROADMAP.md 更正"BakeTool 残留为 0"为如实描述（bl_idname 已统一但类名保留 BAKETOOL 前缀）。
- [x] **验证**：22/22 运行时源文件 `py_compile` 全过；0 lsp error。
