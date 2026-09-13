# 更新日志 /Changelog

本文件记录 BakeNexus 在正式发布前的主要版本变化。/This file records major version changes before official release.

## 1.0.0 - 2026-09-11
### 发布前独立审计修复：数据保护、输出正确性与入口一致性 / Pre-release Independent Audit Fixes: Data Protection, Output Correctness & Entry Consistency

依据 `docs/RELEASE_AUDIT_2026-09-11.md`（30 组诊断）实施第一至第四批修复。

#### 数据保护 / Data Protection
- **保存失败不再退出 Blender**：`save_and_quit` 在 blend 未保存或 `save_mainfile()` 失败时不再调用 `quit_blender()`（A01）。
- **同名用户数据保护**：图像与烘焙结果对象仅复用带 `is_bt_result` 标记的自有 datablock；用户同名对象/图像不再被替换、清空或删除（A02）。
- **恢复索引钳制**：崩溃续跑的 `current_queue_idx` 限制在重建队列范围内，避免越界跳步。

#### 输出正确性 / Output Correctness
- **假成功消除**：`bpy.ops.object.bake()` 返回非 `FINISHED` 视为失败；外部保存失败抛错不再产生"成功"结果条目；模态结束后状态如实显示 `Finished (N step errors)`；导出失败不再打印 Exported 日志（A03/A30）。
- **节点烘焙修复**：目标图像绑定并激活临时 Texture 节点，红色常量节点实际输出红色；图像所有权在创建前判定（A05）。
- **ID 图崩溃修复**：`ID_ele` / `ID_UVI` / `ID_seam` 的 `len(bm.loops)` TypeError 修复（A04）。
- **图像保存真实编码**：`save_image` 改用 `save_render`，PNG 位深与 RGB/BW 颜色模式实际写入文件头；通道顺序不再污染材质输出（每个 pass 从用户原始输出连接开始）；float/色彩空间契约在复用时强制兑现，不匹配即重建（A06/A10/A11）。
- **4.x 光照 pass 开关生效**：`SceneSettingsContext("bake")` 统一走 `compat.get_bake_settings()`，`use_pass_*` 在 Blender 4.x 实际生效（A08）。
- **Normal 标准与 AO 参数接线**：OPENGL/DIRECTX/CUSTOM 映射到 `normal_r/g/b`；AO 的 Only Local 写入 `only_local`；移除无消费者的通道 Export Mode 控件（A09）。
- **降噪诚实化**：后台模式明确跳过（不再静默假装处理）；临时场景按图像尺寸渲染；清理限定本次创建的场景并连带删除自有相机；临时图未按分辨率渲染的问题修复（A12）。

#### 入口与状态一致性 / Entry & State Consistency
- **Quick Bake 复用验证**：runtime proxy 经 `validate_job` 校验后再构建队列，与普通烘焙同规则；Auto Smart UV 启用时不再因"无 UV"误拒；SELECT_ACTIVE 的目标低模一并纳入 UV 管理（A14）。
- **动画帧统一**：`frame_set` 移入 `BakeStepRunner.run`，API/headless/modual 三入口都真实切换场景帧（A15）。
- **UV 回滚**：`UVLayoutManager.__enter__` 失败自动还原已建临时层；按 mesh 数据去重，共享 mesh 不再重复创建（A13）。
- **预设往返保真**：迁移仅作用于确属旧键的字段；集合始终序列化、加载先集合后标量；空集合/空指针可清空（A20）。
- **动态枚举稳定**：来源枚举恒含 NONE、编号全局唯一且跨通道启用状态稳定（A21）。
- **Custom 通道命名**：图像名包含自定义通道名，不同 custom 不再互相覆盖；新增 custom 通道 alpha 默认 1.0（A22）。
- **预览安全化**：重复应用不再从预览自身重建而丢失源逻辑；烘焙前自动还原预览材质，预览不再污染烘焙输入（A23）。
- **UDIM 打包透传**：UDIM 模式下打包结果以 TILED 图像输出（A17 局部）。
- **模态与导出细节**：Quick Bake poll 增加 is_baking 守卫；Delete All 重置索引；强制单采样通道的结果元数据如实记录 samples=1（A16/A30）。

#### 资源与发布 / Resources & Release
- **降噪/临时资源**：临时场景清理不再误删其他同前缀场景（A12/A29 局部）。
- **图像编辑器上下文**：`robust_image_editor_context` 不再吞掉调用体异常，并恢复编辑器原图像引用（A28）。
- **缩略图降级修正**：显式导入 `bpy.utils.previews`，移除基于"4.2 移除 API"错误前提的占位降级（A27）。
- **发布包自检闭环**：`build_release_zip.py` 随包分发，解压 ZIP 后 Run Safety Audit 162/162 通过（A24）。
- **CI 加固**：Blender 步骤加 `--python-exit-code 1`；artifact 不再互相覆盖；汇总校验遍历全部报告且要求 total>0（A26）。
- **词典与静态检查**：清除 3 个过期翻译键（0 缺失 0 过期）；运行时文件 Ruff F/E9 全清（A25/A24 局部）。

#### 新增回归测试 / New Regression Tests
- `test_uv_manager_rolls_back_partial_setup_failure`（UV 进入失败回滚）
- `test_preset_keeps_extension_channel_and_empty_collections`（扩展通道与空集合往返）
- 预览幂等测试加强为校验源节点存活；降噪测试改为 float 基线并区分后台跳过契约。

#### 验证 / Verification
- 5 版本（3.3.21 / 3.6.23 / 4.2.14 / 4.5.3 / 5.0.1）：162 项测试，0 失败 0 错误（3.3/3.6 各 5 项预期跳过）。
- 行为复现确认：节点红色常量输出正确、PNG 文件头与设置一致、预设扩展字段保真、同名对象不受影响、4.x pass 开关生效、后台不退出、无临时 UV/节点/相机残留。
- 发布 ZIP（70 文件，含两份审查报告归档）通过官方 extension validate；解压后独立运行全套测试 162/162。
- 已知保留项（记录于审计报告）：UDIM 边界检测与逐 tile 后处理、崩溃记录跨进程归属、COMBINE/SPLIT 自动应用范围——均为文档明示的 v1.1 范围，不在本次静默承诺。

## 1.0.0 - 2026-09-10
### 发布候选清理：死链修复与死代码移除 / Release-Candidate Cleanup: Dead-Wire Fixes & Dead-Code Removal

#### 功能性修复 / Functional Fixes
- **预设库缩略图链路接通**：`thumbnail_manager.load_preset_thumbnails()` 是唯一调用 `pcoll.load` 的函数，但此前从未被任何代码调用，导致 Visual Preset Gallery 的 `get_icon_id()` 恒返回 0（图库静默降级为纯文字）。现已由 `property.get_library_preset_items()` 接线调用，并将加载改为幂等（已加载条目跳过）——动态枚举回调在每次重绘都会触发，重复加载同名条目会被 Blender previews API 拒绝。
- **Normal 通道 UI 去重**：`CHANNEL_UI_LAYOUT["normal"]` 中的 `prefix/suffix` 布局项与 `draw_active_channel_properties` 对所有通道统一绘制的 Naming 行重复，导致 Normal 通道的前后缀输入框出现两次；已从布局配置移除。

#### 死代码移除 / Dead-Code Removal（净 -153 行）
- `BAKETOOL_OT_TogglePreview` operator：22 个 operator 中唯一无任何 UI/菜单/快捷键引用者（UI 直接绑定 `use_preview` 属性）。
- `manage_objects_logic` 的 `"SET"` 分支：无调用方。
- Texel 死链整链移除：`texel_density` RNA 属性（引擎从未读取）、UI 字段、`TexelDensityCalculator`、对应存在性测试与 Mock 字段——用户不再能看到一个无任何效果的参数。
- `compat.is_extension()` / `compat.get_version_string()` / 恒等函数 `compat.get_bake_operator_type()`（engine.py 调用点直接使用 `bake_type`）。
- `save_image` 的 `reload` 形参（无调用方传入）与 `_resolve_color_space_name` 未使用的 `image` 形参。
- 翻译词典同步清除 3 个死键（`Texel` / `Target Density` / 其描述），468 → 465 词条。

#### 验证 / Verification
- 5 版本（3.3.21 / 3.6.23 / 4.2.14 / 4.5.3 / 5.0.1）160 项测试：0 失败、0 错误（3.3/3.6 各 5 项 tomllib 缺失的预期跳过）。
- 静态审计：已删符号 0 残留、孤儿 operator 0、i18n 全部 pgettext 字面量覆盖且 0 空值、register/unregister 12/12 对称、全项目 `py_compile` 0 错误。
- 旧预设兼容无损：`PropertyIO.from_dict` 本就优雅跳过未知键。

## 1.0.0 - 2026-08-17
### 发布收尾：一致性固化与防护性测试 / Wrap-up: Consistency Hardening & Regression Guards

#### 冗余清理 / Redundancy Cleanup
- **翻译词典治理**：以官方工具 `dev_tools/extract_translations.py --sync --prune` 清理 19 个死键（旧品牌 "Bake Nexus" 标签、已删除的 denoise/UV 功能枚举、已移除通道的显示名），补齐 6 个缺失键（品牌更新后的导入导出标签与操作提示）的 5 语言翻译——词典收敛至 468 词条、0 空值。
- **仓库清理**：移除全部 `__pycache__/` 与 `test_output/` 临时产物；发布 ZIP 在全部文档定稿后重新生成。

#### 一致性固化 / Consistency Hardening
- **`property.py`**：`BakeMeshSettings.contrast/direction/invert` 标注为 v1.1 通道重实装的预留字段（防止被后续清理误删，旧预设继续可加载）。
- **文档与实际行为对齐**：修正 `ECOSYSTEM_GUIDE`（§5.1/§7.4 曾错误声称 `dev_tools/automation/test_cases` 不随包分发）；`RELEASE_CHECKLIST` 新增"manifest id == ZIP 目录名"与"简体中文界面抽查"核对项；`USER_MANUAL` 更新 Mesh 通道清单、已移除通道说明、PID 会话文件名与 `Clean Up Bake Junk` 入口。

#### 防护性测试 / Regression Guards（158 → 161 项）
- **`test_channel_pipeline_alignment`**（suite_code_review）：通道列表、元数据、UI 布局与引擎可达性四层的一致性机器化——任何"UI 列出但引擎无路径"的通道（B-03 失效模式）将直接导致 CI 失败。
- **`test_manifest_id_matches_addon_directory`**（suite_extension_validation）：扩展 ID 与打包目录名强制一致（B-01 防复发）。
- **`test_release_zip_includes_audit_dependencies`**（suite_extension_validation）：打包脚本必须收录 `dev_tools/`（B-04 防复发）。

#### 技术指南完善 / Technical Guide
- `TECHNICAL_GUIDE.md` 新增 **§5.4 通道管线与引擎可达性**：完整叙述通道从 UI 勾选到像素落盘的四层数据结构与执行流水线、引擎可达性判定规则、B-03 案例复盘，以及"新增通道强制检查单"；§6.1 更新 PID 会话文件机制；§9.7 记录本轮工程产物。

#### 验证 / Verification
- 5 版本（3.3.21 / 3.6.23 / 4.2.14 / 4.5.3 / 5.0.1）161 项测试：0 失败、0 错误（3.3/3.6 各 4 项 tomllib 缺失的预期跳过）。
- 发布 ZIP `dist/baketool-1.0.0.zip`（67 文件）：根目录 == manifest id、dev_tools 随包、`zh_HANS` 生效、无 `__pycache__` 泄漏；翻译审计 0 死键 0 缺失。

## 1.0.0 - 2026-08-16
### 发布前外部审计修复 / Pre-release External Audit Fixes

#### 阻断级修复 / Blocker Fixes
- **扩展 ID 统一 (B-01)**：`blender_manifest.toml` 的 `id` 从 `bakenexus` 改为 `baketool`，与发布 ZIP 内目录名一致，修复 Blender 4.2+ 从磁盘安装扩展必然失败的问题；发布产物更名为 `baketool-1.0.0.zip`。
- **中文翻译 locale 修正 (B-02)**：`translations.json` 全部 481 词条 `zh_CN` → `zh_HANS`（Blender 4.2+ 使用的简体中文 locale 代码）；`translations.py` 注册时自动附加 `zh_CN` 别名，保持 ≤4.1 legacy 源码安装的兼容；同步更新提取工具与 `suite_localization` 测试。
- **移除无实现 Mesh 通道 (B-03)**：`Vertex Color / Curvature / Slope / Thickness / Select` 五个通道在引擎中无生成路径（静默产出全黑贴图），从 `BAKE_CHANNEL_INFO["MESH"]` 移除并列入 ROADMAP v1.1；连带清理 `CHANNEL_BAKE_INFO` / `CHANNEL_UI_LAYOUT` / `DATA_BAKE_FORCE_SINGLE_SAMPLE` / `CHANNEL_MESH_TYPE_MAP` 残留及 `height` 孤岛元数据、`engine.py` 的 `displacement` 死键。
- **发布包补齐 dev_tools (B-04)**：`build_release_zip.py` 收录 `dev_tools/*.py`，修复打包后 `Run Safety Audit` 因 `suite_localization` 导入 `..dev_tools` 必然报错的问题（67 文件）。

#### 高优先级修复 / High-priority Fixes
- **崩溃记录多实例隔离 (H-03)**：`state_manager.py` 会话文件改为 `sbt_last_session_<PID>.json`，检测/读取/清理改为 glob 前缀匹配（按 mtime 新者优先），并行 Blender 实例不再互相覆盖崩溃记录。
- **紧急清理 UI 入口 (H-04)**：`Baked Results` 面板新增 `Clean Up Bake Junk` 按钮（原先仅 F3 可达）。

#### 打磨项 / Polish
- `engine.py` 降噪管线移除已弃用的 `context.copy()`，改用纯 `temp_override(scene=...)`。
- `preset_handler.py` 预览材质恢复改用 `SYSTEM_NAMES["PREVIEW_MAT"]` 常量（消除硬编码）。
- `Quick Bake` 添加 `poll`（无 Mesh 选择时右键菜单置灰）。
- README 顶部 CAUTION 引用块断裂修复；CI Blender 下载增加官方源回退（镜像单点依赖）。

#### 验证 / Verification
- 5 版本全量套件：Blender 3.3.21 / 3.6.23（154 passed + 4 skipped，tomllib 缺失的预期跳过）、4.2.14 / 4.5.3 / 5.0.1（158/158）——0 失败 0 错误。
- 发布 ZIP 结构验证：根目录 == manifest id == `baketool`；dev_tools 随包；`zh_HANS` 生效且无 `zh_CN` 残留；无 `__pycache__` 泄漏。

## Unreleased
### 架构一致性、运行时安全与文档同步 / Architecture Consistency, Runtime Safety & Documentation
- **执行安全**：modal 烘焙队列长度变化转为受控错误；cage 视口切换失败时恢复选择状态；补齐 Quick Bake、Reset 与导出预检的用户反馈。
- **依赖边界**：新增 `core/bake_types.py` 承载 `BakeStep` / `BakeTask`；新增 `core/udim_utils.py` 作为 UDIM 检测叶模块，消除 `common.py` 对 `uv_manager.py` 的反向依赖。
- **职责分离**：将 `apply_baked_result` 与 `create_simple_baked_material` 从 `core/common.py` 移至 `core/shading.py`；旧导入路径保留 facade 重导出，避免破坏外部脚本。
- **DRY/KISS**：合并重复的 Light Path / ID 通道 UI 配置；统一活动 Job 报告守卫；移除预览代码中的对话式注释和闭包内重复常量。
- **验证**：跨 Blender 3.3.21、3.6.23、4.2.14、4.5.3、5.0.1 的 `unit` 矩阵 5/5 通过；4.2 的 `verification`、注册循环与公开 facade 检查通过；5.0 的 `production_workflow` 10/10 通过。
- **文档与发布**：同步技术、开发、自动化、生态、标准化、路线图、任务板和发布清单；构建脚本生成 65 文件发布 ZIP 并确认包含新核心模块。

## 1.0.0 - 2026-07-02
### 发布前最终清理与 DRY 重构 / Pre-release Final Cleanup & DRY Refactoring

#### 死代码与死导入清理 / Dead Code Removal
- **constants.py**：删除 12 个零引用常量（JOB_TYPES, ATLAS_PACK_METHODS, DENOISE_METHODS, DEFAULT_BAKE_TARGET, API_VERSION, SYSTEM_ID, UDIM_DEFAULT_TILE, UDIM_TILE_RANGE, GOLDEN_RATIO, MIN_THRESHOLD, DEFAULT_SMART_UV_ANGLE, DEFAULT_SMART_UV_MARGIN）。
- **property.py**：删除 `use_antialiasing` 死属性（声明但烘焙管线从未读取）。
- **死导入清理**：__init__.py（types, persistent, bpy.props.*, CHANNEL_BAKE_INFO）、ops.py（traceback）、ui.py（os, json）——共计 7 个未用导入删除。
- **MANIFEST.in**：删除——与 build_release_zip.py 冲突的死文档，打包已有独立的显式文件列表。

#### UX 修复 / UX Fixes
- **ops.py 静默 CANCELLED 修复**：全部 9 处无 `self.report()` 的 `return {"CANCELLED"}` 添加用户反馈（SetSaveLocal, RefreshUDIMLocations, TogglePreview, AnalyzeCage ×2, OneClickPBR, ManageObjects, SaveSetting, LoadSetting）。

#### DRY 重构 / DRY Refactoring
- **`get_active_job()` 辅助函数**（`core/common.py`）：消除 ops.py/ui.py/property.py/common.py 之间 12 处重复的 BakeJob 索引钳制模式，同时修正了缺少空 Job 集检查的潜在 IndexError。
- **`tag_redraw_view3d()` 辅助函数**（`core/common.py`）：消除 ops.py/property.py 之间 3 处重复的 View3D area redraw 循环。
- **`EXTENSION_TO_FORMAT` 映射**（`constants.py`）：从 FORMAT_SETTINGS 自动计算，消除 `ops.py` 的 `_get_format_from_path` 双重事实源。
- **预览路径统一**：TogglePreview.execute 简化为仅翻转标志，`update_preview` RNA 回调成为预览应用/移除/redraw 的唯一执行路径。
- **魔法字符串集中化**：`BT_Denoise_Temp/camera`、`BT_Packing_Preview` 纳入 `SYSTEM_NAMES`。

#### 文档修正 / Documentation Fixes
- **task.md / ROADMAP.md**：更正"BakeTool 残留为 0"为如实描述（bl_idname 已统一，类名保留 BAKETOOL 前缀）。
- **ROADMAP.md / task.md**：新增 Phase 10-14 完成记录。

## 1.0.0 - 2026-06-15
### 发布前最终审查、加固与收尾 / Pre-release Final Review, Hardening & Wrap-up

#### 审查与报告 / Review & Report
- **全维度代码审查**：架构、代码质量、Blender API、测试覆盖、安全性、发布配置 6 个维度全面审计，无阻断性缺陷。
- **审查报告**：`docs/PRE_RELEASE_REVIEW.md` 记录完整审查结果与 8 项人工验证清单。

#### 代码质量加固 / Code Quality Hardening
- **重复异常合并**：`core/node_manager.py` 中 `bake_node_to_image()` 两个连续 except 块（`AttributeError/KeyError/ReferenceError` 与 `RuntimeError`）合并为单一块，消除冗余代码。
- **I/O 性能优化**：`state_manager.py` 中 `BakeStateManager` 引入 `_cached_data` 内存缓存机制，`update_step()` 不再每次从磁盘读取 JSON，大批量烘焙时显著减少磁盘 I/O。
- **finish_session/clear_state**：增加 `_cached_data = None` 重置，确保缓存生命周期与磁盘状态同步。

#### 发布打包完善 / Release Packaging
- **文档完整**：`build_release_zip.py` 的 DOC_FILES 添加 `docs/dev/TECHNICAL_GUIDE.md`，确保技术指南随发布包分发。

#### 一致性验证 / Consistency Verification
- **全项目 py_compile**：所有源文件通过 Python 语法编译检查（0 错误）。
- **打包验证**：`build_release_zip.py` 成功生成 `dist/bakenexus-1.0.0.zip`（63 文件）。

#### 文档同步 / Documentation Sync
- **CHANGELOG**：补充 2026-06-15 发布前收尾记录。
- **ROADMAP**：将 engine.py 拆分推迟至 v1.1，更新短期计划反映当前状态。
- **TECHNICAL_GUIDE**：新增崩溃恢复与状态缓存章节，修复章节编号跳空与重复问题。
- **PRE_RELEASE_REVIEW**：新增完整发布前审查报告文档。

## 1.0.0 - 2026-06-06
### 发布前最终审计与加固 / Pre-release Final Audit & Hardening

#### Phase 6: 关键缺陷修复 / Critical Bug Fixes
- **UNDO 支持 (C-1)**：为 12 个修改场景的 Operator 添加 `bl_options = {"REGISTER", "UNDO"}`，6 个文件/导出/只读操作保持不加。
- **Draw 性能 (C-2)**：将 `draw_env_status()` 中每帧 `os.path.exists()` 移出到 `update_save_path_validity` 属性回调，消除 UI 绘制中的文件 I/O。
- **Headless 安全 (C-3)**：为 `preset_handler.py` 中 `load_default_preset()` 和 `update_crash_cache()` 添加 `bpy.context` 空值守卫。
- **图像泄漏 (C-4)**：`bake_node_to_image` 烘焙失败时自动清理已创建的 Image datablock。
- **属性边界 (H-1)**：`quality` 添加 min=0/max=100；`res_x/res_y` min 降至 1；`radius`/`distance`/`id_count` 添加 min 边界；7 个 `bake_motion_*` 属性添加 min/max 约束。

#### Phase 7: 基础设施修复 / Infrastructure Fixes
- **CI 路径 (H-8)**：`test.yml` 中 BLENDER_DIR 使用 `find` 精确定位 Blender 二进制文件。
- **构建打包 (H-9)**：`build_release_zip.py` 的 AUTOMATION_FILES 添加 `multi_version_test.py`。
- **跨版本测试**：`multi_version_test.py` 添加 `BAKE_TOOL_BLENDER_PATHS` 环境变量支持。
- **临时目录容错**：`state_manager.py` 中 `bpy.app.tempdir` 为空时回退至 `$TEMP` 或 `/tmp`。
- **路径安全**：`headless_bake.py` 中 `sys.path` 修改前添加 `os.path.isdir()` 验证。

#### Phase 8: 代码质量强化 / Code Quality Hardening
- **异常处理**：`DeleteResult`/`DeleteAllResults` 静默异常改为 logger.warning。
- **注册/注销安全**：`__init__.py` 中 `register()`/`unregister()` 循环添加 try/except。
- **Handler 注册**：AutoLoadHandler/UpdateCrashCacheHandler/RestorePreviewMaterialsHandler 注册添加独立错误处理。
- **属性完整性**：`BakedImageResult.filepath` 添加 `subtype="FILE_PATH"`。
- **代码风格**：`ui.py` 中 `import json` 从函数内部提升至模块顶层。

#### Phase 9: 测试套件优化 / Test Suite Optimization
- **去重**：移除 `suite_negative.py` 中与 `suite_unit.py` 重复的 `test_context_manager_exception_restores_state`。
- **MockSetting 对齐**：添加 27 个新属性（udim_mode、auto_cage_mode、extrusion、texel_density、use_*_map、name_setting 等），与 UI 引用的属性保持一致。
- **category_map 完善**：`cli_runner.py` 的 `_load_category` 覆盖全部 22 个 suite。
- **新增 COMBINE_OBJECT E2E 测试**：`suite_production_workflow.py` 添加 `test_combine_objects_2_objs_e2e`，补齐唯一未测试的架构模式。

#### 验证结果 / Verification
- **158/158 测试通过**（Blender 4.2.14，0 失败）。
- 全部 16 个修改文件的 `lsp_diagnostics` 通过。
- 5/5 BAKE_MODES 全覆盖，MockSetting 缺口缩减 43%。

---

## 1.0.0 - 2026-05-14
### 正式发布前代码风格系统整肃 / Pre-release Code Style Overhaul

#### Phase 1: 自动修复与 import 清理 / Automated Cleanup & Import Sanitation
- **空白字符批量清除**：修复 196 处空白行空格 (W293)、23 处行末空格 (W291)、2 处缺失 EOF 换行 (W292)、10 处缩进错误 (E111/E117)。
- **40 个未使用 import 删除**：涵盖全部生产代码 (`ops.py`、`core/*.py`、`automation/*.py`) 和测试代码。
- **发现并修复两个潜伏 Bug**：`core/common.py` 中 `reset_channels_logic` 依赖未导入的 `BAKE_CHANNEL_INFO`；`core/thumbnail_manager.py` 中 Blender 4.2+ 已移除的 `bpy.utils.previews` API 增加降级守卫。

#### Phase 2: 命名规范与多语句修复 / Naming & Multi-Statement Fixes
- **E741 (ambiguous `l` 变量) 全清除**：`ui.py` 中 5 处 `l = self.layout` → `layout`；`node_manager.py` `l` → `link`；`suite_api.py` `l` → `loop`；`suite_code_review.py` `l` → `line`；`suite_memory.py` `l` → `entry`。
- **E701/E702 全清除**：`headless_bake.py`、`suite_api.py`、`suite_parameter_matrix.py`、`suite_verification.py` 中的 6 处单行多语句拆分为多行。

#### Phase 3: 文档补全 / Documentation Completion
- **34 个模块 docstring 全部补全**：覆盖 `core/*.py`、`automation/*.py`、`dev_tools/*.py`、`test_cases/suite_*.py` 和 `property.py`/`preset_handler.py` 等关键文件。
- **关键类/函数 docstring 补全**：`BakeJobs`、`BakeJobSetting`、`TranslationExtractor`、`build_release_zip.py` 全部函数、`multi_version_test.py` 核心函数、`BakeModalOperator`、`BakePassExecutor` 等。

#### Phase 4: 类型标注强化 / Type Annotation Hardening
- **公共 API 完整类型化**：`core/api.py`（`bake`、`get_udim_tiles`、`validate_settings`）、`core/execution.py`（`add_bake_result_to_ui`、`BakeModalOperator` 全部方法）。
- **所有 Operator `execute()`/`invoke()` 返回类型验证**：全部已标注 `-> Set[str]`。
- 类型覆盖率从 25% → 30.8%。

#### 累计效果 / Cumulative Impact
- pycodestyle 违规总数从 385 降至 97（-75%）。
- bare `except` 子句清零（17→0）。
- 全部 4 个 Phase 通过跨版本回归验证（5 个 Blender 版本，各 158 测试）。

#### Phase 5: 发布前最终加固 / Pre-release Final Hardening
- **异常安全大幅提升**：全项目 18 处 `except Exception` 收紧为具体异常类型，覆盖 `core/engine.py`、`core/execution.py`、`ops.py`、`property.py`、`automation/*.py` 等 9 个文件。
- **全局状态封装**：`__init__.py` 引入 `_RegistryState` 类封装模块级可变状态；`thumbnail_manager.py` 的 `preview_collections` 改为模块私有 `_preview_collections`。
- **上下文管理统一**：`save_image` 和 `bake_node_to_image` 改用 `SceneSettingsContext` 管理场景设置，消除手动恢复。
- **CI 修复**：verify job 改用 heredoc 避免 YAML 缩进歧义。
- **类型标注**：`api.validate_settings` 返回类型 `Any` → `ValidationResult`；`compat.get_bake_settings` 返回类型 `Optional[Any]` → `object`。
- **命名一致性**：`cleanup.py` operator 前缀统一为 `baketool.`。
- **代码清理**：重复 import 删除、CHANGELOG 格式修复、translations.py 模块 docstring 补全、constants.py license 占位符替换。
- **文档同步**：更新 ROADMAP.md、TECHNICAL_GUIDE.md、DEVELOPER_GUIDE.md、STYLE_GUIDE_ANALYSIS.md，确保发布前文档一致。

---

## 1.0.0 - 2026-05-13
### 发布前最终 Code Review 加固 / Pre-release Code Review Hardening

#### 核心执行引擎修复 / Engine Fixes
- **降噪安全增强**：`apply_denoise` 注入 `context` 参数替代全局 `bpy.context`；渲染失败时 `try/finally` 确保 `BT_Denoise_Temp` 清理。
- **Depsgraph 性能优化**：`calculate_cage_proximity` 将 `evaluated_depsgraph_get()` 移出循环（N 次→1 次）。
- **预览材质崩溃恢复**：新增 `RestorePreviewMaterialsHandler`，`load_post` 时自动恢复原始材质。
- **Bake Target 统一管理**：通过 `compat.get_bake_target()` 集中管控，`engine.py` 和 `node_manager.py` 统一调用。
- **纹素密度参数化**：`TexelDensityCalculator.get_mesh_density` 新增 `resolution` 参数，消除 1024 硬编码。
- **场景上下文容错**：`SceneSettingsContext.__enter__` except 收紧为具体异常（AttributeError/TypeError/ValueError/RuntimeError）。
- **错误日志防膨胀**：`bake_error_log` 添加 8000 字符滚动窗口。

#### API 与自动化修复 / API & Automation Fixes
- **API 上下文注入**：`api.bake()` 和 `api.validate_settings()` 新增可选的 `context` 参数，headless 模式安全调用。
- **模块加载优化**：`cli_runner.py` 使用 `importlib.reload()` 替代 `del sys.modules` 暴力删除。
- **路径分隔符跨平台**：`multi_version_test.py` 使用 `os.pathsep` 替代硬编码分号。
- **测试签名同步**：更新 `suite_unit.py` 和 `suite_denoise.py` 中 `apply_denoise` 的三处旧签名调用。
- **CI 管道加固**：verify job 解析 JSON 报告验证测试结果；lint 移除 `|| true` 使其生效。
- **导入性测试补全**：`suite_code_review.test_all_test_suites_importable` 补充 `suite_custom_channel_hardened`。

#### 资源与状态管理 / Resource & State Management
- **保护镜像 GC 预防**：`node_manager.py` 中 `DUMMY_IMG` 创建时设置 `use_fake_user = True`。
- **时间轴状态恢复**：`BakeModalOperator` 在 `init_modal` 保存 `_original_frame`，`_cleanup_state` 恢复。
- **无头模式崩溃修复**：`cage_analyzer.py` 添加 `context.screen` None 守卫。
- **缩略图 TOCTOU 修复**：`thumbnail_manager.get_icon_id` 缓存 `pcoll.get()` 结果。

#### 代码审查与文档 / Code Review & Documentation
- **全量两轮 Code Review**：审查 44 个源文件，修复 20 个 CRITICAL/HIGH/MEDIUM 问题。
- **完善技术指南**：新增上下文注入模式、Depsgraph 优化实践、错误日志治理、CI 有效性规则章节。
- **更新路线图**：同步 v1.0.0 最终修复记录，调整短期计划反映已完成优化。
- **更新开发者指南**：新增上下文注入模式、Compat Layer 函数表、API 上下文约定。

---

## 1.0.0 - 2026-05-05

### 本次发布前综合收尾 / Pre-Release Comprehensive Wrap-up

#### UI 架构审计与修复 / UI Audit & Fixes
- **参数暴露补全**：`draw_inputs` 补回了 `sample`、`margin`、`device`、`use_clear_image`、`color_base`；`draw_saves` 补回了 `use_denoise`、`create_new_folder`、`folder_name`、`pack_suffix`、`export_textures_with_model`。
- **数据驱动对齐**：`CHANNEL_UI_LAYOUT` 所有通道属性现已通过 `SuiteCodeReview` 自动验证存在于 `BakeChannel` 中。
- **空安全**：`BAKE_UL_BakedImageResults.draw_item` 增加 `item.image` 空值守卫，避免 NoneType 崩溃。
- **国际化**：`draw_active_channel_properties` 中硬编码 `"Naming:"` → `pgettext("Naming") + ":"`；结果列表空通道显示 `pgettext("(Empty)")`。
- **布局优化**：`draw_saves` 重构为 Common Settings / External Save / Animation / Smart Intelligence 四个功能区，减少认知负荷。

#### 单元测试体系优化 / Test Suite Optimization
- **Mock 同步**：`MockSetting` 补全 `color_base`、`create_new_folder`、`folder_name`；`JobBuilder` 新增 `.folder()`、`.packing()`、`.denoise()` 流式 API。
- **覆盖率提升**：新增 `test_denoise_integration_trigger`、`test_output_subfolder_creation`、`test_apply_baked_result_collection` 三个集成测试。
- **跨版本框架修复**：修正 `multi_version_test.py` 中 `stdout_tail` 缺失、`write_summary_reports` 键名不一致、`cli_runner.py` 引用不存在的 `suite_verification.py` 等问题。
- **最终验证**：5 个 Blender 版本（3.3 / 3.6 / 4.2 LTS / 4.5 LTS / 5.0）全部 158 测试 100% 通过。

#### 核心引擎一致性修复 / Engine Consistency Fixes
- **参数传递路径**：`_handle_save` 和 `ModelExporter.export` 中 `folder_name` 统一为 `s.folder_name if s.create_new_folder else task.folder_name`。
- **集合名称修正**：`test_apply_baked_result_mesh_cleanup` 中集合名从错误的 `"BakeResults"` 修正为 `SYSTEM_NAMES["RESULT_COLLECTION"]`（即 `"Baked_Results"`）。
- **API 健壮性**：`test_bake_trigger_api` 移除 `from .. import baketool` 的内部导入，改为直接检查 `scene.BakeJobs` 属性。

#### 文档与发布准备 / Documentation & Release Prep
- 更新 `ROADMAP.md`：补充参数动态对齐机制、资源生命周期管理、跨版本兼容性说明。
- 补充技术原理概要：参数传递路径、一致性保证、资源监控机制。
- 清理所有 `__pycache__` 目录，确保发布包干净。
- 发布前复核修复：补齐 `verification` 自动化入口、修正动态枚举默认值、统一发布 ZIP 顶层包名、收紧保存路径命名、补强 UDIM 多 tile 检测与 Selected-to-Active 上下文。
- 跨版本回归修复：恢复动态枚举回调的 Blender 兼容默认值、修复 `cli_runner.py --test` 被 discovery 覆盖的问题、避免 `multi_version_test.py` 并行报告文件名碰撞，并清理 denoise 临时场景删除时的 `lib_remap` 噪声。

---

## 1.0.0-p1 - 2026-04-23

### 核心修复与增强 /Core Fixes & Enhancements

- **自定义通道加固 /Custom Channel Hardening**:
  - 引入 `default_value` 属性，支持自定义通道默认值（如 AO/金属度默认为 1.0）/Introduced `default_value` property
  - 实现 **自我指涉过滤 /Self-Reference Filter**，自动排除当前通道/Automatically exclude current channel

- **导出质量优化 /Export Quality**:
  - 重构 `save_image()`，透传详细图像参数/Refactored to pass detailed image parameters
  - 实现场景设置临时覆盖与自动还原/Temporary override and auto-restore

### 稳定性与自动化 /Stability & Automation

- **全量回归验证 /Full Regression**: Blender 4.2 LTS 21 套件 100% 通过/21 test suites pass at 100%
- **新增专项测试 /New Tests**: `suite_custom_channel_hardened.py`
- **CI 稳定性 /CI Stability**: 修复 GitHub Actions 跨平台兼容性/Fixed cross-platform compatibility
- **测试覆盖 /Test Coverage**: 扩展到 12 个 Blender 版本/Expanded to 12 Blender versions

## 1.0.0 - 2026-04-22

这是发布前的关键收尾版本，重点是修复会直接影响发布质量和自动化可信度的缺陷。

### 补充

- 预设/属性保存链路现在支持常见 Blender ID 指针的稳定往返保存与恢复，包括 `Object`、`Material`、`Image` 等，缺失目标会安全跳过而不是破坏导入流程。
- 多版本测试脚本补齐了 `--blender`、`--paths-file`、`--timeout`、`--report-dir` 等入口，并改为优先读取 `cli_runner.py` 的 JSON 结果判断成功/失败，降低了仅靠控制台关键字判断的误报风险。
- 翻译提取脚本升级为 AST 级提取/审计/同步工具，补齐了 `AnnAssign` 属性声明、UI `text=`、`report()`、`pgettext()`、枚举项与消息字典等来源。
- 翻译审计现在会额外标记坏掉的 locale 值和“键存在但仍回落到英文原文”的条目，能直接拦截 `????`、乱码回写和覆盖不足问题。
- UI 中原本绕过词典的动态拼接文本已接入翻译系统，例如通道设置标题和结果面板元数据标签。
- `fr_FR`、`ja_JP`、`ru_RU`、`zh_CN` 四个 locale 现已全部达到 `missing=0 / broken=0 / untranslated=0`，并完成 Blender `3.3.21 / 3.4.1 / 3.5.1 / 3.6.23 / 4.0.2 / 4.1.1 / 4.2.14 / 4.3.2 / 4.4.3 / 4.5.3 / 5.0.1 / 5.1.0` 的本地化回归。
- 正式翻译表已清洗为 476 个当前有效键，移除了陈旧键和内部标识键，并补齐本轮新增键的 `zh_CN` 翻译；清洗后的翻译表在 Blender `3.3.21 / 3.4.1 / 3.5.1 / 3.6.23 / 4.0.2 / 4.1.1 / 4.2.14 / 4.3.2 / 4.4.3 / 4.5.3 / 5.0.1 / 5.1.0` 上完成了注册回归。

### 修复

- 统一了预设加载兼容策略，启动默认预设和库预设现在同时接受单 Job 导出与完整 `BakeJobs` 快照，避免导出的 JSON 在复用时被静默忽略。
- 补齐了 UI 已经引用但未注册的三个 operator：
  - `bake.set_save_local`
  - `bake.selected_node_bake`
  - `bake.refresh_udim_locations`
- 修复了 `automation/headless_bake.py` 在干净 Blender 背景会话中不能初始化插件属性的问题，脚本现在会先尝试注册 BakeNexus，再访问 `scene.BakeJobs`。
- 将自定义通道真正接入执行管线，不再在执行阶段退回默认黑色结果。
- 统一了自定义通道结果键命名，执行结果和通道打包统一使用 `BT_CUSTOM_<name>`，消除了自定义图可烘焙但不可打包的问题。
- 将 diffuse、glossy、transmission 和 combined 的 pass filter 选项实际映射到 Blender bake 设置，不再是“界面可改但执行不生效”的状态。
- 修复导出流程只恢复 `hide_set()` 不恢复 `hide_viewport` 的问题，避免导出后对象可见性被污染。
- 增加颜色空间枚举与 Blender 实际 colorspace 名称的映射，避免 `NONCOL`、`LINEAR` 等内部值直接写入 RNA 导致的异常。
- 将 View Layer 预检前移到 `JobPreparer`，对象、active object 或 cage object 不在当前 View Layer 时会明确跳过 Job，而不再等到 Blender 原生 bake 阶段才报运行时错误。
- 为失败 bake 增加新建图像回收逻辑，避免通道执行失败后在场景里残留无效 image datablock。
- 将 `Run Safety Audit` 改为启动独立 Blender 后台进程执行测试，并回填 JSON 摘要，避免在当前交互式会话里原地跑测试导致 RNA 路径解析崩溃。

### 自动化

- 重写 UI operator 完整性测试，改用 `get_rna_type()` 验证注册状态，避免 `hasattr(bpy.ops...)` 带来的假阳性。
- 新增和补强以下回归测试：
  - headless 初始化测试
  - 自定义通道结果键规范测试
  - 自定义通道 NumPy 组装测试
  - 自定义结果参与通道打包测试
  - pass filter 映射测试
  - 导出可见性恢复测试
- 新增 View Layer 预检回归、失败 bake 图像清理回归，以及开发调试测试隔离执行回归。
- 在 Blender 4.5.3 LTS 上通过了 `unit`、`export`、`ui_logic`、`verification` 和 `production_workflow` 关键套件。
- 通过了 `3.3.21`、`3.4.1`、`3.5.1`、`3.6.23`、`4.0.2`、`4.1.1`、`4.2.14`、`4.3.2`、`4.4.3`、`4.5.3`、`5.0.1`、`5.1.0` 的跨版本 verification 验证。
- 通过了 `3.3.21`、`3.4.1`、`3.5.1`、`3.6.23`、`4.0.2`、`4.1.1`、`4.2.14`、`4.3.2`、`4.4.3`、`4.5.3`、`5.0.1`、`5.1.0` 的跨版本 negative 验证。

### 文档与发布准备

- 更新 `__init__.py` 中的 `doc_url` 和 `tracker_url`，替换占位链接。
- 清理 `bl_info.warning` 的 Beta 提示，并修正 GitHub Actions 中未真正命中当前仓库源码的 lint/style 配置。
- 增加正式分发 ZIP 打包脚本，避免本地 `.venv/`、测试输出和历史资料被误带入发布包。
- 重写 `README.md`、用户手册、开发者文档和自动化说明，移除乱码与旧脚本引用。
- 增加发布检查清单，统一正式打包前需要执行的验证和人工验收动作。
- 修正 `MANIFEST.in`，使其与当前仓库布局一致。
- 补充参数一致化、动态 UI 对齐和交互式调试隔离的开发约束说明，并同步更新路线图与任务看板。

## 1.0.0-pre - 2026-04-17

这是 1.0 线的稳定化节点，主要目标是让插件在 Blender 3.3 到 5.x 范围内具备可持续验证和维护的基本条件。

### 变化

- 稳定化核心执行链与异常处理。
- 收敛 UI、属性和引擎参数映射。
- 清理部分未使用导入和维护性问题。
- 完成多份基础文档与测试脚本的初版整理。

## 0.9.5 - 2024-01-20

### 变化

- 增加 GLB/USD 导出联动支持。
- 增加降噪后处理相关流程。
- 持续调整执行引擎与资源清理逻辑。

## 0.9.0 - 2023-09-01

### 变化

- 将烘焙执行逻辑重构为更清晰的模块化核心组件。
- 引入更明确的 UI、operator、engine 分层。
- 开始形成自动化套件与开发规范。
