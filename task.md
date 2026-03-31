# BakeTool 研发攻坚行动看板 (Phase 4.3 & 4.5)

## [x] Phase 4.3: 跨版本端到端验证 (E2E Hardening)
- [x] 重构 `compat.set_bake_type` 以支持 B3.3/3.6 (Cycles 引擎强制锁定策略)
- [x] 修复 UDIM 初始化在 B3.3 Headless 模式下的缓冲分配问题 (像素触摸策略)
- [x] 优化 `suite_production_workflow.py` 的文件搜索逻辑，解决 `SPLIT_MATERIAL` 误报
- [x] 验证 Blender 3.6/4.2/4.5/5.0 达到 100% 通过率

## [/] Phase 4.5: 项目同步与文档对齐
- [x] 更新 `implementation_plan.md` 至 Phase 4.5 状态
- [x] 撰写 `version_analysis_33_36.md` 深度技术分析报告 (Artifact)
- [/] 同步更新 `ROADMAP.md` 里程碑状态
- [/] 同步更新 `DEVELOPER_GUIDE.md` 录入“三点对齐”与“跨版本避坑”规范
- [ ] 最终执行 `multi_version_test.py` 进行文档一致性后的全量回归

## [ ] 未来方略 (Future Roadmap)
- [ ] 调研 B3.3 极大贴图下的 OOM 保护机制
- [ ] 统一项目所有说明文件为全中文 (可选)
- [ ] 自动化测试环境静态化与容器化预研

## 🎯 优先战役 1: 零摩擦资产交付闭环 (USD/glTF Delivery Loop)
- `[x]` **`core/engine.py`**: 开发 `build_pbr_material` 函数。
  - 自动新建材质，创建 `Principled BSDF`，并将传入的 `baked_images`（BaseColor, Normal, MR 等）链接到对应的 Socket 上。
- `[x]` **`core/engine.py`**: 重构 `ModelExporter.export`。
  - 在原有的导出逻辑前，劫持并注入上述构建的材质。
  - 针对 GLB 格式，设置 `export_format='GLTF_SEPARATE'` 或打包模式，确保物理图片绑定成功。
- `[x]` **`property.py` & `ui.py`**: 配置专属开关。
  - 增加 `export_textures_with_model` (携带材质与贴图导出) 开关，默认激活。
- `[x]` **`test_cases/suite_production_workflow.py`**: 追加完整交付验证。
  - 新增 E2E 节点，读取导出的 GLB 测试其贴图包容量或材质属性节点存在性。

## 🛡️ 战役 2: 视觉包裹分析引擎基础 (Visual Cage Analysis)
- `[x]` **`core/cage_analyzer.py`**: 创建基础框架。
  - 实现射线数学计算模块 `run_raycast_analysis` 的骨骼架子（使用 BMesh 与 BVHTree）。
- `[x]` **`property.py`**: 注册界面属性。
  - 新增针对笼状容差的控制组，以及 `auto_switch_vertex_paint` (默认 False) 选项。
- `[x]` **`ops.py` & `ui.py`**: 加入呼出入口。
  - 添加 `BAKETOOL_OT_AnalyzeCage`，在 UI 面板“Smart Intelligence”中绘制 `Analyze Cage Overlap` 按钮。
- `[x]` **`test_cases/suite_unit.py`**: 部署基础的数学断言测试 (`TestCageAnalyzer`)。

## 🧹 战役 3: 激进垃圾回收防泄露基础 (Memory Safety Guard)
- `[x]` **`core/execution.py`**: 在模态操作周期的收尾点 (`_process_single_step` 结束后)，探查并引入 `img.gl_free()` 与主动内存收缩。
- `[x]` **`core/cleanup.py`**: 强化 Crash 和正常完成后的游离 `Image` 孤单节点强回收。
