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

### 8. 外部审计修复与发布收尾 (2026-08-17) ✅
- [x] **B-01** manifest `id` 统一为 `baketool`（== ZIP 目录名 == `import baketool`），修复 4.2+ 扩展安装失败；产物更名为 `baketool-1.0.0.zip`。
- [x] **B-02** 翻译 locale `zh_CN` → `zh_HANS` 全链路替换（481 词条）；`translations.py` 注册期派生 `zh_CN` 别名兼容 ≤4.1；工具与测试同步。
- [x] **B-03** 移除 5 个无引擎实现的 Mesh 通道（Vertex Color/Curvature/Slope/Thickness/Select）与 `height` 孤岛元数据；`mesh_settings.contrast/direction/invert` 按 v1.1 预留并注释保护。
- [x] **B-04** 发布包收录 `dev_tools/`，随包 Run Safety Audit 导入链闭合。
- [x] **H-03** 崩溃会话文件按 PID 隔离 + glob 检测（新者优先）；`finish_session` 只清本实例，`clear_state` 清全部。
- [x] **H-04** `Clean Up Bake Junk` 按钮进入 Baked Results 面板。
- [x] **防护性测试**：`test_channel_pipeline_alignment`、`test_manifest_id_matches_addon_directory`、`test_release_zip_includes_audit_dependencies`——测试数 158 → 161。
- [x] **词典治理**：`--sync --prune` 清理 19 个死键、补齐 6 个新键的 5 语言 → 468 词条、0 空值。
- [x] **打磨**：`context.copy()` 弃用 API 移除、预览材质名改用 `SYSTEM_NAMES`、Quick Bake 补 poll、README 引用块修复、CI 官方源回退。
- [x] **文档一致化**：USER_MANUAL（通道清单/状态文件名/清理入口）、ECOSYSTEM_GUIDE（dev_tools 分发策略修正）、RELEASE_CHECKLIST（id==目录名与 zh 抽查项）、TECHNICAL_GUIDE（新增 §5.4 通道管线与引擎可达性、§9.7 本轮产物）、ROADMAP/task.md/CHANGELOG 同步。
- [x] **验证**：5 版本 161 项测试 0 失败 0 错误（3.3/3.6 各 4 项 tomllib 预期跳过）；发布 ZIP（67 文件，根目录==id、dev_tools 随包、zh_HANS 生效、无 pycache 泄漏）全项通过；全项目 `py_compile` 0 错误。

## [v1.1.x] 后续排队功能
- [ ] **通道实装补齐（外部审计立项，最高优先）**：Vertex Color / Curvature / Slope / Thickness / Select 重实装并挂回通道列表（走 TECHNICAL_GUIDE §5.4.5 检查单）；Normal X/Y/Z 轴向分量实装或删除属性，二选一。
- [ ] **崩溃记录归属细化**：会话记录结合 blend 文件名哈希，恢复 UI 仅提示本场景的崩溃记录。
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
- [x] CM.2: `core/common.py` 职责拆分（材质结果函数 → `shading.py`，保留 `common.py` facade 重导出）。

### 7. 维护执行状态 (2026-07-12)
- [x] P0: `BakeModalOperator` 对运行中队列漂移进行受控错误处理；补齐 Quick Bake、Reset、导出预检的用户反馈；统一两处 BakeNexus 品牌标签。
- [x] 架构前置: 新建 `core/bake_types.py` 作为 `BakeStep` / `BakeTask` 的中立契约模块，避免后续 `engine.py` → `job_prep.py` 提取形成循环导入。
- [x] 依赖清理: 新建 `core/udim_utils.py` 并使 `common.py` 依赖该叶模块，消除 `common.py` 到 `uv_manager.py` 的反向依赖；`UVLayoutManager` 支持显式 context 注入。
- [x] DRY/KISS: 合并重复 UI 通道布局配置；统一 Operator 的活动 Job 报告守卫；清理预览材质代码中的对话式实现注释与闭包内重复常量。
- [x] Blender 运行时门禁: Blender 3.3.21、3.6.23、4.2.14、4.5.3、5.0.1 的 `unit` 跨版本矩阵 5/5 通过；4.2 的 `verification` 6/6、注册循环和 facade 导入通过；5.0 的 `production_workflow` 10/10 通过。

### 6. 发布前最终清理与 DRY 重构 (2026-07-02) ✅
- [x] **Phase 10 — 死代码与死导入清理**：constants.py 删除 12 个零引用常量 (JOB_TYPES, ATLAS_PACK_METHODS, DENOISE_METHODS 等)；__init__.py/ui.py/ops.py 删除 7 个未用导入；property.py 删除 `use_antialiasing` 死属性；MANIFEST.in 删除（与 build_release_zip.py 冲突的死文档）。
- [x] **Phase 11 — 静默 CANCELLED 修复**：ops.py 全部 9 处无反馈的 `return {"CANCELLED"}` 添加 `self.report()`，用户点按钮无响应 → 有明确弹窗提示。
- [x] **Phase 12 — DRY 重构**：`core/common.py` 新增 `get_active_job()` 和 `tag_redraw_view3d()` 两个辅助函数，消除 12+3=15 处重复模式。`constants.py` 新增 `EXTENSION_TO_FORMAT` 从 `FORMAT_SETTINGS` 自动计算，消除 `ops.py` 的 `_get_format_from_path` 双重事实源。预览切换逻辑统一由 `update_preview` 回调处理。
- [x] **Phase 13 — 魔法字符串集中化**：`BT_Denoise_Temp`、`BT_Denoise_Camera`、`BT_Packing_Preview` 纳入 `SYSTEM_NAMES`，`constants.py` 成为 Blender 命名的事实源。
- [x] **Phase 14 — 品牌文档修正**：task.md 和 ROADMAP.md 更正"BakeTool 残留为 0"为如实描述（bl_idname 已统一但类名保留 BAKETOOL 前缀）。
- [x] **验证**：22/22 运行时源文件 `py_compile` 全过；0 lsp error。
