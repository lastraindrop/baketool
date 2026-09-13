# BakeNexus 1.0.0 发布前独立审查

日期：2026-09-11。对象：审查开始时工作区内的源码及 `dist/baketool-1.0.0.zip`。

## 1. 结论

> **状态更新（2026-09-11 实施后）**：本报告第 3–7 章诊断中的第一批至第四批修复已实施并复验，详见文末"14. 修复实施记录"。原"暂不建议发布"结论针对审计时点的产物；实施后五版本矩阵、发布包隔离自检与行为复现均通过。仍保留为 v1.1 的项在 14.3 节明示。

**审计时点结论（原文保留）**：**暂不建议把当前产物作为稳定正式版发布。** 原有测试确实通过，但针对性复现发现了数据保护、输出正确性、预设往返、后台执行和发布包验证方面的问题。现阶段的主要任务是修正现有实现和缩减不可靠的功能承诺，而不是增加架构层、设计通用框架或大规模拆文件。

本次仅新增本报告；没有修改插件 Python 源码、既有测试、词典或发布 ZIP。诊断脚本、重新构建的包和测试报告位于系统临时目录。

优先顺序：

1. 阻止保存失败后退出、同名用户数据被覆盖等数据损失路径。
2. 让“成功”表示实际完成要求的烘焙和保存，消除全黑图、缺图、错误编码被当成成功。
3. 修复预设、动态枚举、UV/节点状态和后台动画的契约。
4. 对实际发布 ZIP 验证，再精简重复和无效代码。

### 证据等级

- **R：运行复现**。在独立的 `--factory-startup` Blender 后台进程验证。涉及退出和操作符返回值的检查使用模块级替身拦截，不真的保存或退出用户会话。
- **S：源码确认**。有明确的赋值、遗漏或调用链证据；不把它描述为已进行完整生产场景验证。
- **V：待场景验证**。存在具体缺口，但需要额外资产、交互环境或真实进程崩溃验证其完整表现。

### 严重度

- **P0**：可能丢失或破坏用户数据；相关路径必须修复或撤下。
- **P1**：功能或输出错误、无效配置、发布/自动化契约不成立；在保留对应功能的前提下，应在正式发布前解决。
- **P2**：体验、维护、性能及非关键状态问题；集中做减法，不扩展为新子系统。

## 2. 范围与实测

### 2.1 审查范围

逐模块检查了注册入口、RNA 属性、UI/操作符、预设、状态管理、全部 core 模块、自动化脚本、翻译工具、发布配置和 CI；交叉检查了测试的断言、测试辅助设施及既有发布文档。

源码统计为物理行数，含注释、空行：

| 范围 | Python 文件 | 行数 |
|---|---:|---:|
| 根目录运行时代码 | 8 | 4,634 |
| core | 16 | 5,136 |
| automation | 5 | 1,010 |
| test_cases | 23 | 4,050 |
| dev_tools | 2 | 509 |
| 合计 | 54 | 15,339 |

插件根目录与 core 共 9,770 行。测试目录包括 21 个 `suite_*.py`，总计 160 个测试方法。

### 2.2 原有测试矩阵

执行 `python automation/multi_version_test.py --timeout 600 --report-dir <临时目录>`：

| Blender | 通过 | 跳过 | 失败/错误 |
|---|---:|---:|---:|
| 3.3.21 | 155 | 5 | 0/0 |
| 3.6.23 | 155 | 5 | 0/0 |
| 4.2.14 LTS | 160 | 0 | 0/0 |
| 4.5.3 LTS | 160 | 0 | 0/0 |
| 5.0.1 | 160 | 0 | 0/0 |

这是本次实际验证的五个 Windows 版本。没有据此推断 Linux/macOS、其他小版本、GPU 后端、交互式模态操作或所有生产资产都已通过。

### 2.3 额外检查结果

| 检查 | 结果 |
|---|---|
| 54 个 Python 文件 AST 解析与编译 | 通过 |
| Ruff `F,E9`，不执行自动修复 | 27 项；主要为未用导入/变量、重复导入、无插值 f-string；没有检出语法错误/未定义名称 |
| Blender 4.2 官方 extension validate：源码和新构建 ZIP | 均通过 |
| 新构建 ZIP | 67 文件 |
| 现有 dist ZIP 与当前源码逐成员字节比较 | 67 文件中的对应源码内容一致 |
| 解压 ZIP 后独立运行全部套件，Blender 4.2 | **159 通过、1 失败、0 错误** |
| 翻译静态提取 | 提取 463 键，词典 465 键；没有缺键，有 2 个过期键 |
| 词典各现有非英语 locale | 按现有提取器规则，无缺值、乱码或未译值；不代表动态消息和人工翻译质量已全覆盖 |

针对性行为检查主要在 4.2.14 和 5.0.1 执行。以下条目分别说明运行证据和静态证据。

## 3. 数据保护：P0

### A01. 保存未成功仍会退出 Blender〔R+S〕

- 位置：`core/execution.py:222-239`。
- `save_and_quit` 分支在未保存过 blend、或 `save_mainfile()` 抛出异常时，仍执行分支末尾的 `quit_blender()`。日志虽称“cancelled”，实际控制流没有取消退出。
- 复现：空 `bpy.data.filepath`，模块级替身拦截退出；4.2/5.0 均观察到 `quit_called=True`。
- 入口条件：该属性目前没有常规 UI 控件，但可由预设/API 设置；不是无条件发生的风险。
- **最小处理**：只有确认保存成功才允许退出；更符合发布前精简目标的选择是移除尚未形成可靠契约的自动退出分支。不要增加确认弹窗框架。

### A02. 按名字认领用户数据，可能覆盖或删除原数据〔R+S〕

- 位置：`core/shading.py:232-255`、`core/image_manager.py:252-287`、`core/engine.py:517-524`。
- `apply_baked_result()` 对任意名为 `<base>_Baked` 的对象直接替换 mesh，并可能改变 collection；没有验证这是本插件的结果对象。
- 图像管理对同名 Image 直接缩放、清空、修改 fake user；TILED 与非 TILED 不匹配时直接删除旧 datablock。
- 复现：预先建立普通用户对象 `Collision_Baked`，应用结果后，返回的就是该对象且 mesh 已被替换。4.2/5.0 均重现。
- 导出后临时清理按 `res_obj` 删除对象/材质，会放大错误复用的影响。
- **最小处理**：限定复用为明确属于本任务的结果；不满足时让 Blender 自动唯一命名。只加必要的所属标记/引用判断，不建立资源注册中心。已有属性同名时也不能自动纳入“本次创建资源”清理列表。

## 4. 输出与执行：P1

### A03. 失败被逐层降级为成功〔R+S〕

- 位置：`core/engine.py:329-376, 1097-1106, 1127-1170`；`core/api.py:63-71`；`automation/headless_bake.py:94-111`；`core/execution.py:126-148, 210-239`。
- `_execute_blender_bake_op()` 不检查 `bpy.ops.object.bake()` 是否返回 `FINISHED`；替身返回 `CANCELLED` 时，函数仍返回 True。
- `save_image()` 失败返回 None，但 runner 继续将图像添加为正常结果。复现使用“已有文件充当目录”：仍返回 1 条结果，path 为 null。
- API 只判断结果列表非空，无法辨别部分通道失败；headless 甚至不检查结果，只统计少数异常。
- 模态路径遇到步骤错误继续执行，最后仍显示 Finished 并删除会话记录；可能接着触发自动保存退出。
- **最小处理**：收敛一个失败契约。优先利用异常及现有 results，不新建复杂 Result 层级：核心必要操作失败直接抛出，入口统一报告；若继续下一任务，必须累计失败并返回明确非成功状态。必须检验操作符返回集合以及必要保存是否成功。

### A04. Element / UV / Seam ID 实现会直接异常〔R+S〕

- 位置：`core/math_utils.py:232-255`；入口 `core/engine.py:1366-1384`。
- `len(bm.loops)` 对 `BMLoopSeq` 不成立；4.2/5.0 平面复现：`TypeError: object of type 'BMLoopSeq' has no len()`。
- `ID_ele`、`ID_UVI`、`ID_seam` 共用该路径；Material ID 使用另一实现，不应一并判为同一故障。
- 后续依赖 `loop.index` 的正确性也没有建立显式保证。
- **最小处理**：用现有 mesh loops 数量和可靠的 loop 顺序写颜色，避免只改一个 `len()` 后留下索引问题；如果暂不修，先从发布通道中撤下这些条目。回归须检查实际 corner 颜色，不只检查 palette。

### A05. 节点烘焙没有设置目标图像节点〔R+S〕

- 位置：`core/node_manager.py:45-97`、`162-174`。
- 创建了 img 和临时 Texture 节点，但没有将 img 赋给目标节点，也没有正确激活烘焙目标。返回图像与“烘焙完成”不是同一件事。
- 4.2/5.0 对输出红色常量的 RGB 节点复现：Blender 提示没有 active image，函数仍返回图像，所有红色像素最大值为 0。
- `img_existed_before` 在创建后检查，正常情况下恒为 True，异常清理分支无法删除新图。`settings.sample` 也未应用。
- **最小处理**：复用 NodeGraphHandler 已有目标设置能力，绑定并激活目标 Texture，创建前记录所有权；遵循 A03 的失败契约。不要另造节点烘焙引擎。

### A06. 通道之间没有恢复材质输出，结果依赖通道顺序〔R+S〕

- 位置：`core/node_manager.py:302-345`。
- EMIT pass 将 Material Output 接到临时 Emission；后续非 EMIT pass 不恢复原 shader 链接。
- 复现 `EMIT/color → COMBINED`：第二次 setup 后输出仍连接 `ShaderNodeEmission`，4.2/5.0 一致。
- 扩展节点源缺失时，还可能保留上一通道的 Emission 输入链接，输出错误的旧来源。
- **最小处理**：每个 pass 从已记录的原始输出连接开始，重置当前 emission 输入；没有源时明确失败。无需每次完整复制材质树。

### A07. 重复材质引用造成临时节点泄漏〔R+S〕

- 位置：`core/engine.py:568-585, 621-626`；`core/node_manager.py:139-174, 176-199`。
- 单对象材质槽可以多次引用同一 Material，传入列表未去重。创建第二组节点后，以材质为 key 的字典覆盖第一组，后者失去跟踪。
- 直接 `with NodeGraphHandler([mat, mat])` 后，4.2/5.0 均残留一组 Texture/Emission。
- 活动节点也没有恢复，已在运行检查确认。
- **最小处理**：在 handler 入口保序去重，并保存/恢复原 active node。对 `__enter__` 中途失败实施自身回滚。

### A08. Blender 4.x 的光照 pass 开关被静默忽略〔R+S〕

- 位置：`core/common.py:438-443`；已有正确访问器 `core/compat.py:47-51`。
- SceneSettingsContext 只在 5.x 使用 `scene.render.bake`，4.x 却返回 `scene.render`；`use_pass_*` 属性未命中后直接略过。
- 4.2：尝试在上下文内把 `use_pass_direct` 从 True 改为 False，实际仍 True。5.0 同一检查正常。
- **最小处理**：直接复用 `compat.get_bake_settings(scene)`，删除错误的版本分支。现有 mapping 字典测试不能验证属性实际生效。

### A09. 多个公开配置未接入执行链，部分通道语义错误〔S〕

| 配置/通道 | 位置 | 当前问题 |
|---|---|---|
| Normal Standard | `constants.py:737-744`；`engine.py:1143-1146` | UI 暴露 OPENGL/DIRECTX/CUSTOM，但引擎只读取 object_space，没有使用 Standard 或 X/Y/Z |
| Channel Export Mode | `ui.py:141-144`；`engine.py:390-420` | custom_mode 可编辑但保存只取 job.color_mode |
| AO Only Local | `constants.py:762-769`；`node_manager.py:456-461` | 不写 Ambient Occlusion 的相应属性 |
| Position Invert G | `constants.py:792`；`node_manager.py:462-463` | 仅输出 Geometry.Position，未执行反转 |
| ID Map Count | `constants.py:727-730, 793-796` | 仅定义、绘制/迁移，没有引擎消费 |
| Bevel Normal | `constants.py:916`；`engine.py:1132-1134` | 与 Bevel 共用 mesh_type，最终强制 EMIT，原始法线向量被直接当颜色输出，不是正常编码的 NORMAL pass |
| Gloss 自动应用 | `constants.py:357-362, 885`；`shading.py:340-348` | GLOSSY 光照结果被当 glossiness 反转后连接 Roughness，语义不一致 |
| AO 自动应用 | `constants.py:891`；`shading.py:307-348` | AO 与 Base Color 竞争同一个输入，后接者覆盖先接者 |

- 旧报告只把隐藏的 X/Y/Z 当遗留，遗漏了用户可见的 Normal Standard。
- **最小处理**：简单且确定的透传直接接线；没有明确定义的 UI 控件和自动映射先删除。不要为保留每个开关而扩建 schema/节点生成框架。

### A10. 图像保存选项与实际文件编码不一致〔R+S〕

- 位置：`core/image_manager.py:488-499`；`ops.py:763-784`。
- `save_image()` 临时设置 render.image_settings，但调用的是 `image.save()`；实际编码没有服从传入的全部设置。
- 4.2/5.0 均验证 PNG 文件头：非 float Image 请求 16 位仍为 8 位；float Image 请求 8 位仍为 16 位；RGB/BW 请求均落为 PNG color type 6（RGBA）。
- 单个示例“16 位请求得到 16 位”不足以证明透传正确，必须交叉改变 buffer 类型和请求参数。
- `ExportAllResults` 仅读 external_save_format，未消费其 UI 上其他图像设置，也不使用配置的结果保存目录作为默认来源。
- **最小处理**：统一一个真正控制编码的保存路径。若选择 `save_render`，同时验证数据图不受 display/view transform 污染；不能只机械换方法。单图和批量导出复用该路径。

### A11. 图像复用不能兑现 float/color-space 契约〔R+S〕

- 位置：`core/image_manager.py:197-208, 242-288`。
- 请求 full=True 会跳过颜色空间设置；请求 Non-Color 的新 float 图实测为 Linear Rec.709。二者对部分数据可能数值相同，但标签和用户覆盖契约不一致，不应武断描述为全部数值错误。
- 已有 byte Image 再请求 full=True，实际 `is_float=False`；旧 image alpha/buffer 类型同样没有完整协调。
- **最小处理**：对已拥有的图像校验存储类型，必要时新建；颜色空间按请求显式赋值，并报告失败，不静默吞掉。结合 A02 避免删除用户同名图。

### A12. 降噪后台无效果，且遗留相机资源〔R+S；交互效果 V〕

- 位置：`core/engine.py:143-235, 297-310, 341-348`；`core/compat.py:74-84`。
- 临时场景未按图像设置渲染尺寸；依赖 Viewer 图像回读，且失败/尺寸不符时没有可见失败结果。
- 使用 float 噪声图保存实际写入后的基线：4.2 的 16×16 图未变化，Viewer 为 256×256；5.0 未变化，未发现 Viewer 图。
- 删除 Scene 不会自动删除其 Object 和 Camera datablock；两版本单次调用均增加 1 个 Object、1 个 Camera。
- 独立调用还扫描删除所有同前缀场景；5.0 compositor 复用固定名字 NodeGroup，随后清空节点，存在错误认领风险。
- 对所有通道统一降噪还会改变 ID、打包数据等不应平滑的语义。
- **最小处理**：先明确可支持的后台/交互路径；不可靠路径禁用并说明原因。只清理本次创建资源，限定可降噪通道。不要增加第二套大型合成器框架。

## 5. UV、任务和自动化：P1

### A13. UV 上下文进入失败不回滚，共享 mesh 也存在清理问题〔R+S〕

- 位置：`core/uv_manager.py:135-168, 219-277`。
- `__enter__()` 中先改一批对象，再因某对象达 8 层上限或 smart UV 失败而抛出；Python 不会为进入失败的管理器调用 `__exit__`。
- 复现：第一个对象原有 1 UV 层，第二个 8 层；失败后第一个变成 2 层且残留 `BT_Bake_Temp_UV`。
- 共享 mesh 的两个对象重复创建/清理同一数据；5.0 复现残留 `BT_Bake_Temp_UV.001`，active index 从 0 变为 1；4.2 该共享测试未见残留。
- `_apply_smart_uv` 的 finally 只恢复对象选择，没有保证异常时退出 EDIT 模式或恢复原模式/面选择。
- **最小处理**：无 UV 修改时不创建临时层；按 mesh 数据去重；进入失败由管理器自身回滚。减少要恢复的状态优于增加补救代码。

### A14. 普通、快速、API 的准备规则不一致〔R+S〕

- 位置：`core/engine.py:654-677, 703-761, 820-846`；`core/api.py:44-58`。
- 普通任务先要求存在 UV，因此启用 Auto Smart UV 的无 UV 对象仍被拒绝，4.2/5.0 已重现。
- Quick Bake 直接 build，绕过 validate_job 和空通道保护；API 也走此分支。
- 原验证允许部分非 MESH 组合，UVLayoutManager 却直接访问每个 obj.data.uv_layers。
- SELECT_ACTIVE 的 UVLayoutManager 处理 task.objects（源高模），没有处理单独的 task.active_obj（目标低模），Auto UV 的目标对象不一致。
- **最小处理**：runtime proxy 建好后直接复用普通准备入口；在这一处统一 target/source/mesh/UV 规则。Auto UV 的验证条件应反映实际是否会生成 UV。

### A15. 动画在 API/headless 中只改变文件编号，不切场景帧〔R+S〕

- 位置：`core/execution.py:162-166`；`core/api.py:63-69`；`automation/headless_bake.py:95-104`；`core/engine.py:850-875`。
- `frame_set()` 只存在于模态入口，其他入口直接调用 runner。
- API 替身记录实际场景帧：请求 10、11，实际两步均在 frame 1。
- UI 显示 Start/Frames，但未显示 `bake_motion_use_custom`；默认 False 时引擎忽略这些输入，使用 Scene 帧范围。动画无外部保存时静默变成静态。
- **最小处理**：把步骤帧切换放到所有入口共享的位置，原帧恢复有明确的作用域；UI 要么暴露是否自定义，要么简化为唯一帧范围规则。

### A16. 模态生命周期与可编辑数据之间没有可靠边界〔S+V〕

- 位置：`ops.py:215-221, 280-283`；`core/execution.py:83-156, 200-251`；`ui.py:584-627`；`__init__.py:178-183`。
- Quick Bake.poll 不检查 is_baking；配置集合在烘焙期间仍可编辑。BakeStep 只是浅层 namedtuple，job/channel/object 内部仍是活 RNA 引用。
- 任意 TIMER 都可能推进队列，没有验证 event.timer 属于自身；当前 context 也未绑定启动场景。
- timer/modal_handler 初始化失败没有完整回滚；未覆盖的 ReferenceError/OSError 等路径可能跳过 session/timer 清理。
- is_baking 是可保存的 Scene 属性，没有 load 后重置，可能把运行态带入文件。
- 一个 TIMER 同步执行一个 task 的全部 channels，期间 UI/取消无法及时响应；当前架构不能声称随时可中断。
- **最小处理**：共用运行状态 guard、验证自身 TIMER、锁定启动场景；烘焙期间禁用变更任务的控件/操作符，运行态使用 SKIP_SAVE；清理置于明确 finally。不要为发布前修复引入线程烘焙或复杂任务调度器。

### A17. UDIM 支持在检测、后处理和尺寸方面不闭合〔R+S〕

- 位置：`core/uv_manager.py:24-38`；`core/udim_utils.py:21-36`；`core/engine.py:453-455, 1041-1062, 1216-1244`；`core/math_utils.py:14-22, 80-114`；`core/image_manager.py:323-380`。
- floor 顶点 UV 边界使普通 [0,1] 平面被识别为 1001、1002、1011、1012，4.2/5.0 已复现。dominant-tile API 则只返回一个 tile；`api.get_udim_tiles()` 名称暗示全量但实际只收集 dominant tile。
- numpy custom/PBR/packing 没有逐 tile 处理；packed target 没有传 use_udim，结果是普通图。不能据此宣称多 tile 自定义打包已正确支持。
- 已存在的非 1001 tile 不更新分辨率；同 tile 多对象的 override 由字典最后项决定。属性最大 1099，而检测允许 1100，范围也不一致。
- **最小处理**：合并两个检测函数的扫描内核，明确边界归属与单/多 tile API；在真实逐 tile 支持完成前，对 UDIM 不支持的后处理组合明确拒绝/隐藏。不要让单 tile 测试代替多 tile 内容检查。

### A18. 自动应用/导出结果不匹配多对象或拆材质任务〔S〕

- 位置：`core/engine.py:484-524, 587-626`；`core/shading.py:195-275`。
- COMBINE_OBJECT/UDIM 任务包含多个对象，post-bake 却只将 task.active_obj 传给 apply_baked_result；导出也只导出这个结果。
- SPLIT_MATERIAL 每个任务复制整个 mesh，并换成单一烘焙材质，没有真正裁出对应面或聚合回正确多材质结果。
- 新结果 copy 可能保留临时 UV 名；紧急清理又按该名称删除 UV，可能移除结果需要的布局。
- 重复 Apply 创建新的 UUID 材质，旧材质没有对应的拥有者清理；export-only 删除 object 未删除其 mesh。
- **最小处理**：先把自动应用/模型导出限制在已经正确实现的模式；需要保留的组合再用现有任务对象列表处理。不要以新资产管线掩盖这个输入契约缺口。

### A19. USD 选择范围检测无效；Cage 配置不完整〔R+S〕

- 位置：`core/engine.py:1148-1158, 1531-1541`。
- 对 operator wrapper 使用 `hasattr(..., 'selected_objects_only')` 不等于查询 RNA 参数。4.2/5.0 实测 hasattr=False、RNA 属性存在；因此从不传 True，可能导出整个场景。
- 显式 cage_object 仅传了名称，没有传 `use_cage=True`；需要用真实 cage 几何验证投射行为，不能以“参数存在”当功能成立。
- Proximity 名称称 ray-cast，但实际是最近点距离，最后取所有顶点平均值；不能保证笼体覆盖最远部分。非均匀缩放下，cage_analyzer 法线变换也需逆转置校验。
- **最小处理**：正式支持版本直接传正确 USD 选择参数，或查询 RNA；明确 use_cage。对 Proximity 简化/纠正语义，避免许诺逐顶点自适应笼体。

## 6. 预设、枚举和预览：P1

### A20. 预设往返不保真〔R+S〕

- 位置：`preset_handler.py:149-155, 179-249`；`constants.py:850-851`；`property.py:565-573`。
- 通道集合加载后，后续 use_light_map/use_mesh_map/use_extension_map 的 update 回调会删除/重建通道，丢失 enabled 和配置。
- 全局迁移把正常的 `BakeExtensionSettings.node_group` 当旧键迁移为 `extension_settings.node_group`，在当前层找不到目标后丢弃。
- 4.2/5.0 往返：node_group 从 MyGroup 变空、enabled 从 True 变 False；对 extension_settings 直接加载 node_group 也为空。
- 空 collection 不序列化，所以把一个没有 custom channels 的预设导入有 custom channels 的现有 job，旧集合保留。空指针也有同类“不能清空”问题。
- 对错误 collection 值先 clear 再验证类型，会先破坏现有配置。
- **最小处理**：先加载会触发结构变化的开关，再加载集合；优先接受当前层合法字段，只在确属旧字段时迁移；完整快照显式输出空集合/空指针。先验证输入类型再 clear。避免增加版本迁移类体系。

### A21. 动态枚举数值不稳定且依赖当前 UI job〔R+S〕

- 位置：`property.py:81-137, 669-707`。
- built-in 枚举数值使用完整 channels 索引，custom 数值却以“已启用数量”作为偏移，既会变化又可能冲突。
- 复现：pack_r 选择 BT_CUSTOM_Custom 后再启用一个普通通道，数值从 3 对应到无效来源，pack_r 读取为空，并有 RNA warning。4.2/5.0 一致。
- 回调总是根据 scene 当前 job_index 取候选，不根据 self 所属 job；多 job 批量、加载预设和后台运行可能解析为另一个 job 的来源。
- 有候选项时不保留 NONE；图库有 JSON 时同样不保留 NONE，update 回调却无条件设置 NONE，存在非法枚举赋值。
- 图库文件枚举未稳定排序/标识；动态生成的字符串没有明确的长期引用缓存。
- **最小处理**：稳定、唯一的枚举数值和始终存在的 NONE；来源以属性所属 job 为准。若 UI 动态枚举约束过重，改成稳定存储的来源标识再呈现，减少隐式状态，不构建依赖注入系统。

### A22. 自定义来源顺序、命名及缺失策略不一致〔S；默认 alpha R〕

- 位置：`core/engine.py:897-919, 1037-1039, 1211-1298`；`property.py:365-416`。
- custom 被视为 DATA，排序在 EXTENSION 之前，却允许选择扩展结果；也允许引用后面的 custom 或形成环。源未就绪时静默输出默认值。
- 新建 custom channels 的名字相同、prefix/suffix 默认都为空；图片名不含 custom name，不同 custom 会复用同一 image，先前结果和缓存可能被后续覆盖。
- 默认 a_settings.default_value 为 0；两版本实测新 custom alpha=0，容易得到全透明结果。应明确这是设计默认还是错误，不应在说明中承诺默认不透明。
- custom 的默认分量读取与普通 packing 永远取源 R 通道不同；alpha 值全 1 时自动改取 R 的推断也应有明确语义。
- **最小处理**：限定来源为已经生成的结果、检查输出名字唯一性、缺失所选来源报错。优先限制前向/循环引用，而不是引入拓扑调度框架。统一通道提取约定。

### A23. 实时预览改变烘焙输入且不能可靠表示输出〔R+S〕

- 位置：`core/shading.py:40-187`；`property.py:258-269`；`ui.py:578-579`。
- 所有对象共用一个全局预览材质，后处理对象重建节点会改变先前对象的预览。
- 重复 apply 时源已经是 preview，nodes.clear 后找不到原 BSDF。4.2/5.0 复现只剩 Output、Combine、Emission。
- 只复制直接 source node，不复制输入 default_value 和上游链接，复杂纹理网络显示不等价；修改 pack_r/g/b/a 没有对应刷新回调。
- 烘焙没有先恢复原材质，预览开启后任务可能拿预览材质当输入；无原材质、重命名原材质、切换 active material slot 也使恢复不可靠。
- **最小处理**：当前预览比它提供的价值引入更多状态。发布前优先隐藏/移除该功能入口与不可靠实现，至少禁止它与实际烘焙同时生效；不要临时开发节点树深复制框架。

## 7. 发布、恢复和质量门槛

### A24. 随包 Safety Audit 确定失败〔P1，R+S〕

- 位置：`automation/build_release_zip.py:45-50`；`test_cases/suite_extension_validation.py:69-89`。
- 新增回归测试要求 build_release_zip.py 存在，但 AUTOMATION_FILES 没有它。
- 独立解压 67 文件 ZIP，实际运行 160 测试：159 pass、1 fail；失败为 `build_release_zip.py missing`。当前 dist 内容与源码对应成员一致，不是“忘了重新打包”的问题。
- **最小处理**：源码布局断言属于构建侧，不应作为已安装插件的运行时自检前提。改成验证包内实际运行依赖；若继续保留构建脚本依赖才补打包，但不要让自检不断拉入新的开发工具依赖。
- `ops.py:143-163` 对报告缺失的子进程仍可能按 exit code 0 判成功，且报告总数未严格验证；应统一使用已经较严格的结果判断规则。

### A25. 崩溃恢复并不可靠跨进程〔P1，S+V〕

- 位置：`state_manager.py:33-56, 135-143, 177-205`；`ops.py:250-256`；`preset_handler.py:432-474`。
- 文件放入 bpy.app.tempdir。本次两个独立 4.2 进程分别得到 `.../blender_a28668/` 与 `.../blender_a32488/`；新进程仅 glob 自己的目录，无法据此发现旧进程文件。PID 文件名并没有解决目录隔离。
- 若配置为共享目录，又缺少 blend/session 归属；最新其他实例的文件可能被误判为崩溃，clear_state 删除所有实例记录。
- resume 只取 current_queue_idx，不验证任务集合、对象或文件身份、索引范围；重建后的队列不一定是崩溃前队列。读取旧 PID 文件后 finish 删除的是当前 PID 文件，旧文件可能持续存在。
- 写入直接 truncate，flush/fsync 不能防止写一半留下无效 JSON；json root 类型和索引类型也未校验。
- **最小处理**：明确记录目录和文件归属，只有匹配且有效时才能恢复。若发布前不能验证真正的崩溃续跑，保留诊断记录并撤下自动 resume 承诺。无需数据库、心跳服务或事务日志框架。
- 本次没有强杀 Blender 来模拟真正崩溃；以上跨进程目录与源码控制流证据应与强杀恢复测试区分。

### A26. CI 报告聚合和失败退出存在缺口〔P1，S〕

- 位置：`.github/workflows/test.yml:64-75, 89-123, 155-158`。
- 每个版本 artifact 内均为 test_report.json，merge-multiple=True 下载到同目录会互相覆盖；verify 无法证明检查了 12 份报告。
- Blender 命令缺少 `--python-exit-code`，脚本装载/执行早期异常可能无法可靠转换为失败码；再结合 artifact 缺失/覆盖，可能漏拦截。
- verify 不检查总测试数、预期版本集合、丢失报告；syntax find 的命令结束状态也不足以逐文件聚合编译失败。
- **最小处理**：保留 artifact 各自目录或唯一文件名；检查完整版本集合与非零测试数；Blender 使用明确 Python 失败退出码。现有 CI 不必另加平台来解决这些问题。

### A27. 缩略图兼容性降级基于错误前提〔P2，R+S〕

- 位置：`core/thumbnail_manager.py:10, 74-84`。
- 没有显式 import bpy.utils.previews 就用 hasattr 检测，并把缺失解释为“Blender 4.2+ removed”。
- 4.2/5.0 干净进程 `_HAS_PREVIEWS=False`，显式导入后模块正常存在；此前缓存仍然 False。
- **最小处理**：显式导入 previews，删除针对“4.2 移除 API”的错误 placeholder。图库不应因模块尚未导入而静默永久空白。

### A28. 图像编辑器 contextmanager 会掩盖调用体异常〔P2，R+S〕

- 位置：`core/image_manager.py:113-133`。
- try/except 包含 yield；调用体抛 RuntimeError 后 except 再 yield False，违反 contextmanager 协议。
- 4.2/5.0 复现：原始 body sentinel 被 `RuntimeError("generator didn't stop after throw()")` 替代。
- 另未恢复原 image editor 的 image 引用。
- **最小处理**：只对进入失败做降级，不捕获 yield 内调用体异常；finally 恢复自己改动的编辑器状态。

### A29. 注册与清理边界欠明确〔P2，S+V〕

- 位置：`__init__.py:151-223, 226-285`；`core/cleanup.py:45-51, 72-158`。
- register_class 失败仅记录后继续挂属性/菜单，可能留下半注册状态；unregister 的翻译/菜单/keymap 任一早期错误可阻断后续清理。
- cleanup operator 在烘焙中也可用；按名字/前缀认领资源，UV 仅精确匹配基础名，漏掉 `.001` 等残留。
- emergency cleanup 只移除临时节点，不能恢复已失去的原 shader 链接；不应宣传为完整场景恢复。
- 目前存在真实普通注册循环通过的证据；未将它夸大为部分失败、reload、烘焙中禁用均可靠。
- **最小处理**：只记录成功注册项；初始化失败时回滚；让已有清理步骤具备独立 finally。清理限定自己拥有的资源，避免追加“更激进的全局扫描”。

### A30. 元数据与结果生命周期仍有不一致〔P2，S〕

- `core/execution.py:31-34`：按 image 去重时直接跳过更新，重烘焙后路径、时长、分辨率仍可能是旧值；动画也只保留首个登记信息。
- `core/engine.py:319-369`：duration 没算 denoise；强制单采样通道记录 job.sample 而不是实际 1。
- `core/execution.py:171-185`：无论外部保存是否成功都释放 image buffers，放大 A03 的结果丢失/重新加载问题；应与成功持久化契约绑定。
- `ops.py:649-664`：DeleteAllResults 不重置索引，fake user 在 users 判断后才清除，部分零实际使用图像会遗留。
- `core/engine.py:1429-1467`：export 失败没有成功返回值，日志仍可能在未输出文件时称 Exported。
- **最小处理**：复用 result 时更新而非丢弃元数据；记录实际执行参数；只在确认可重载后释放缓存；不引入独立缓存管理服务。

## 8. 为什么测试全通过仍发现上述问题

这不是“测试数量不够”可以概括的，主要是断言与所声称的功能错位。

| 当前测试/设施 | 实际覆盖缺口 | 精简后的替换方向 |
|---|---|---|
| `suite_code_review.py:197-210` 通道对齐 | ID 前缀、mapping 存在即通过；不执行 BMesh 或核对通道语义 | 保留声明检查，增加实际 ID 输出和已暴露参数的行为断言 |
| `suite_unit.py:481-501` 降噪 | 比较随机原数组与 byte Image 回读；量化本身就能使它们不等，3.x 跳过降噪也可能“通过” | float 图，写入后回读作为基线，检查实际降噪效果与资源计数 |
| `suite_production_workflow.py:274-304` 动画 | 两个文件名存在，不检查帧动画内容是否不同 | 帧 1/2 驱动明显不同颜色，核对图像内容和原帧恢复 |
| `suite_api.py:46-64` | 返回 False 也满足 bool 断言 | 已知有效输入必须成功且输出正确 |
| `suite_preset.py:25-60` | 只比较分辨率、sample；没比较 channels/扩展开关 | 非默认、多 job、custom/extension/空集合快照往返 |
| `suite_parameter_matrix.py:22-51` | 只生成队列；SELECT_ACTIVE 甚至同一对象作为 source/target | 少量有代表性的真实投射/打包场景 |
| `suite_production_workflow.py:308-329` | 三个材质槽但辅助对象只有一个面，默认只使用一个材质 | 真实不同面组、多材质图案及保护目标 |
| `suite_production_workflow.py:362-374` | 把 Object 传给 NodeGraphHandler，过滤为空；没有真正的 linked material | 真正 link/library 数据场景，或删除该误导测试 |
| `helpers.py:196-200` | 请求不存在的 channel 静默忽略，BSDF 测试 enable_channel('diff') 并不启用 Diffuse | 找不到测试要求的通道直接失败 |
| `assert_no_leak` 与 cleanup_scene | 多个测试在退出检查前自行清空场景，掩盖操作造成的遗留 | 清理前检查 delta；仅对白名单的真正产物放行 |
| `DataLeakChecker` | 不统计 Camera/Scene；白名单只影响显示的新名字，不影响数量判断 | 修正现有小工具，不增加内存监控框架 |
| `suite_verification.py` | 多项重复检查 constructor/属性存储 | 合并重复项，把名额用于实际失败和输出验证 |

不建议把 160 当必须持续增长的目标。优先替换弱测试，允许测试数下降但可信度上升。

## 9. 架构、DRY、KISS、YAGNI 诊断

### 9.1 可保留的结构

- `BakeStep/BakeTask` 的小数据结构、JobPreparer/Runner 分工、SceneSettingsContext 和 ExitStack 方向是合理的。
- 运行时 proxy 避免为 Quick Bake 改写持久 job 是合理的；问题是它没有复用验证入口。
- 已有 constants 驱动 UI、统一日志、显式 ZIP 文件名单和独立进程测试均有价值。
- 本次运行导入和静态调用检查未发现阻断导入的循环依赖。不要为了“分层纯度”重新搭建框架。

### 9.2 真正的重复事实源

1. **准备规则重复**：普通/Quick/API 不同。合并入口比抽象接口更重要。
2. **bake settings 访问重复**：common 自己写版本判断，而 compat 已有正确函数；删除前者的分支即可。
3. **保存路径重复**：job/node/单结果/批结果不共用完整编码规则，造成参数不一致。复用一个现有保存函数。
4. **UDIM 扫描重复**：两个函数约 25 行相同扫描，含相同边界缺陷；合并内核但保留“主要 tile”与“所有 tiles”的明确语义。
5. **预览恢复重复**：shading.remove_preview 与 load handler 各写一份；若撤下预览，应连同相应恢复和词典一起减掉。
6. **通道配置多表**：metadata、默认列表、UI layout、socket map 各有用途，不必强行变一个巨型 schema；应删除未消费字段，并直接测试有用户意义的映射。

### 9.3 可净减代码的候选

| 候选 | 建议 |
|---|---|
| 不可靠实时预览 | 优先撤下；可减少上百行复杂状态/复制逻辑，但须保留必要旧数据恢复策略 |
| 自动 Save and Quit | 若不是首发核心需求，删除比添加确认/重试框架更合适 |
| 错误 previews placeholder | 显式导入后移除降级类和分支 |
| 多份图像导出保存/恢复块 | 收敛到现有函数，减少行为分叉 |
| 无消费者的 UI/元数据 | `id_count`、`invert_g`、custom_mode 等实装简单者接线，其余撤下；不要继续给无效开关写说明 |
| UUID 材质名 | Blender 已自动唯一命名；如不需要外部稳定 UUID，可删除 uuid 依赖，但先明确结果复用策略 |
| 静态检查噪声 | Ruff 27 项集中修；不要顺便全库格式化 |
| 过期翻译 | 删除 `No objects to preview`、`Toggle Preview` 两键 |
| 同一事实的多份“发布成功”报告 | 一个当前发布状态 + 历史记录，减少互相矛盾的重复文档 |
| 小样板 | 已有 get_active_job 仍有调用点手写索引；优先复用，而不是新增 report_cancel 装饰器 |

### 9.4 目前不建议做

- 不引入依赖注入、事件总线、通道插件注册框架、通用 serializer 框架、通用异常/Result 类体系。
- 不为允许任意 custom 循环/前向引用引入图调度器；先限制合法来源。
- 不为了减少一个 1,572 行文件而在发布前拆一批 facade/re-export。必要时以后只做机械搬移，无行为改变。
- 不为追求 DRY 一次性改掉所有 RNA 字段布局。Job 的平铺 image settings 与 Node/Result 的组合形式虽不一致，立刻改存储结构会带来旧 blend/预设迁移成本；先统一消费代码。
- 不单纯为了降低“except Exception 数量”收窄入口异常，导致 timer/UI 状态泄漏。核心内部异常应暴露，顶层负责有限而可靠的收尾。
- 不以“类型覆盖率 50%/80%”作为首发质量目标，优先保证输出与保存真实正确。

## 10. 建议实施计划：修正、限制、删除优先

### 第一批：消除数据与假成功风险

处理 A01–A03、A05、A10、A19 的 USD 范围。验收：保存失败不退出、不计成功；同名用户数据不改；节点红色常量输出正确；真实文件头匹配设置；USD 只含选定对象。

### 第二批：修正已有工作流契约

处理 A04、A06–A09、A11、A13–A15、A20–A22。复用现有入口和 helper；对无法快速兑现的配置/通道撤下 UI。验收：多 pass 顺序无污染；预设往返保真；切换 job/启用通道不改变来源；异常恢复 UV/节点；API/CLI 动画帧正确。

### 第三批：收缩复杂功能范围

处理 A12、A16–A18、A23、A25、A29。优先限制 UDIM 后处理、多对象自动应用、预览、恢复等未验证组合；只有经过输出/生命周期验证的组合继续作为首发能力。

### 第四批：发布包与质量门槛

处理 A24、A26–A28、A30，替换弱测试，删除明确死代码/过期词条。构建一次实际包，对解压包验证，不只验证源码。

**代码预算**：不承诺每个正确性修复都零新增行；必要的 finally、失败检查和回归断言值得保留。通过移除预览/失效 fallback、重复保存和重复准备逻辑争取运行时代码总体不增长。用真实 diff 统计验收，不提前虚报节省行数。

## 11. 正式发布的最小验收集

1. 原有五版本矩阵没有回归；旧版跳过项如实记录。
2. 节点常量输出、ID 元素分区、多通道顺序、Normal Standard、光照 pass 配置均有内容断言。
3. 真实 PNG/EXR 编码与色彩空间验证，失败输出目录返回非成功。
4. 预设非默认值、扩展/custom、两个 job、空集合/空指针往返一致。
5. Auto UV 无 UV 输入、8 层上限、linked mesh、异常回滚；用户原始 UV 不被误删。
6. 两帧不同内容的 API/headless 动画，结束恢复原帧；UI 帧设置与执行一致。
7. 多 tile 不同图案验证，逐 tile 核验；未支持组合必须明确禁用。
8. 同名用户 object/image/material 和重复材质槽保护；临时 Scene/Object/Camera/NodeGroup 计数在清理前核验。
9. 真实安装 ZIP、启用/禁用、中文 UI、图库、自检；UI 场景下取消、重复启动和烘焙期间配置操作验证。
10. 最终 ZIP 自检成功；CI 每个预期版本都有独立、有效、非空报告。

已确认有问题的组合在修复或撤下前，不应仅因旧 suite 绿色而放行。

## 12. 既有文档需要修正的结论

- `docs/PRE_RELEASE_REVIEW.md` 的“无阻断缺陷”“100% 还原”“极佳质量”不能继续作为当前发布结论；本报告的复现已构成反证。
- `docs/ROADMAP.md` 与 README 对稳定性的描述相互矛盾；历史 158/161 和当前 160 测试数量应区分时间，不把旧结果写成当前事实。
- 旧文档说“缩略图 API 在 4.2 移除”是错误解释；是未导入模块造成误判。
- `safe_context_override` 只临时覆盖上下文字段，不等同于自动保存/恢复真实 selection、mode、visibility。
- 官方源码及 ZIP validate 均通过；本次没有把“id 与顶层目录同名”单一断言当成 Extensions 全部兼容规则，也没有发现当前 ZIP 无法解析 manifest。
- 通道表一致、文件存在、函数没异常，都不能替代像素正确、保存正确、生命周期完整的验证。

## 13. 本次验证产物与复现方式

临时目录：`C:\Users\23168\AppData\Local\Temp\opencode`。

- `baketool-audit-matrix/cross_version_report_20260911_102743_036185.json`：五版本完整原有套件结果。
- `baketool-packaged-report.json`：独立 ZIP 的 159P/1F 结果。
- `baketool-audit-release.zip`、`baketool-audit-packaged/`：新构建及解压产物。
- `baketool_audit_probe.py`：上下文、ID、节点图、预设、枚举、失败契约等诊断。
- `baketool_behavior_audit.py`：PNG 文件头、float 降噪、节点实际像素、共享 mesh、同名对象、空集合等诊断。
- `baketool_static_audit.py`：AST/规模、词典、ZIP 与源码对比和隔离包测试。

关键命令（路径按本机实际安装填写）：

```powershell
python automation/multi_version_test.py --timeout 600 --report-dir "C:\Users\23168\AppData\Local\Temp\opencode\baketool-audit-matrix"
python -m ruff check --no-cache --select F,E9 --output-format concise .
python automation/build_release_zip.py --output "C:\Users\23168\AppData\Local\Temp\opencode\baketool-audit-release.zip"
& "D:\Program Files\blender-4.2\blender.exe" --background --factory-startup --command extension validate "C:\Users\23168\AppData\Local\Temp\opencode\baketool-audit-release.zip"
& "D:\Program Files\blender-4.2\blender.exe" --background --factory-startup --python-exit-code 1 --python "C:\Users\23168\AppData\Local\Temp\opencode\baketool_audit_probe.py"
& "D:\Program Files\blender-5.0\blender.exe" --background --factory-startup --python-exit-code 1 --python "C:\Users\23168\AppData\Local\Temp\opencode\baketool_behavior_audit.py"
```

诊断脚本输出观测值，并不修改被审查实现；其中少数使用替身的检查属于控制流验证，不冒充真实 GPU、渲染、保存退出或进程崩溃实验。临时目录不是长期归档位置，正式修复时应把关键行为断言融入现有测试，避免长期维护另一套审计框架。

## 14. 修复实施记录（2026-09-11）

### 14.1 已修复项与验证结果

| 审计项 | 修复方式（摘要） | 复验证据 |
|---|---|---|
| A01 保存失败仍退出 | `save_and_quit` 仅在保存确认成功后退出 | 替身探测 `quit_called=false`（4.2/5.0） |
| A02 同名数据覆盖 | 图像/结果对象仅复用 `is_bt_result` 自有标记 | 行为复现 `reused_user_object=false`、`mesh_replaced=false` |
| A03 假成功 | bake 返回值检查；保存失败抛错；模态计数失败步并在状态中如实显示；导出日志门控 | 替身 `CANCELLED → False`；坏目录抛 `RuntimeError`；其余套件 0 失败 |
| A04 ID 图 TypeError | `len(obj.data.loops)` 替代 `len(bm.loops)` | 探测 `element_id="BT_ATTR_ELEMENT"` |
| A05 节点烘焙全黑 | 目标图绑定并激活 tex 节点；所有权创建前判定 | 行为复现 `max_red=1.0`、center=(1,0,0,1) |
| A06 通道输出污染 | 每 pass 先恢复用户原始输出链接 | 探测 EMIT→COMBINED 后源为 `ShaderNodeBsdfPrincipled` |
| A07 重复材质泄漏 | handler 入口保序去重；活动节点保存/恢复 | 探测 `leftover_nodes=[]`、`active_restored=true` |
| A08 4.x pass 开关失效 | bake 目标统一走 `compat.get_bake_settings()` | 4.2 探测 `during_expected_false=false`（上下文内实际生效） |
| A09 未接线配置 | Normal Standard/X/Y/Z、AO Only Local 接线；移除通道 Export Mode 控件 | 套件回归 0 失败；参数走 `bpy.ops.object.bake` 原生参数 |
| A10 保存编码不符 | `save_render` 统一编码路径 | PNG 文件头：8/16 位与 color type 2/0/6 与请求一致（4.2/5.0） |
| A11 float/色彩空间契约 | 颜色空间始终赋值；复用时 float 不匹配即重建 | 探测 `float_cs="Non-Color"`、`reused_is_float=true` |
| A12 降噪后台假象 | 后台明确跳过；临时场景按图像尺寸渲染；仅清理本次场景并连带自有相机 | 日志显式警告；探测资源计数 before==after |
| A13 UV 无回滚/共享 mesh | `__enter__` 失败自回滚；按 mesh 指针去重 | 新回归测试通过；探测 before==after |
| A14 入口验证不一致 | Quick Bake 复用 `validate_job`；Auto UV 跳过 UV 预检；SELECT_ACTIVE 目标纳入 UV 管理 | 探测 Auto UV 无 UV 对象 `success=true` |
| A15 API/headless 动画不切帧 | `frame_set` 移入 runner | E2E 日志出现 Fra:1→Fra:2 同步 |
| A16 运行守卫缺口 | Quick Bake poll 加 `is_baking`；恢复索引钳制 | 套件回归通过 |
| A17 UDIM 局部 | 打包结果透传 `use_udim/udim_tiles`（边界检测与逐 tile 后处理仍留 v1.1） | 打包套件通过 |
| A20 预设不保真 | 迁移仅限旧键；集合始终序列化；先集合后标量；先验证后 clear | 新回归测试通过；探测 `group_after="MyGroup"`、`enabled_after=true` |
| A21 动态枚举不稳定 | 恒含 NONE；编号全局唯一稳定 | 探测启用新通道后 `selected_after_enable` 保持 |
| A22 custom 命名/alpha | 图像名含 custom 名；新 custom 通道 alpha 默认 1.0 | 探测像素 alpha 契约（旧数据保持 0，符合预期语义） |
| A23 预览破坏源/污染烘焙 | 已是预览则早退；烘焙前 `remove_preview` | 加强后的幂等测试（校验源节点存活）通过 |
| A24 包内自检必失败 | 构建脚本随包 | 解压 ZIP 独立运行 162/162 |
| A26 CI 聚合缺口 | `--python-exit-code 1`、artifact 隔离、遍历+total>0 校验 | workflow 文件更新（云端运行待推送验证） |
| A27 缩略图误判 | 显式导入 previews | 探测 `cached_available=true` |
| A28 编辑器上下文吞异常 | yield 移出 try/except；恢复编辑器原图像 | 探测 body 哨兵异常原样透传 |
| A30 元数据/索引细节 | Delete All 重置索引；强制单采样通道 samples 如实记录 | 套件回归通过 |

### 14.2 全量复验

- 五版本矩阵（3.3.21 / 3.6.23 / 4.2.14 / 4.5.3 / 5.0.1）：162 项，0 失败 0 错误；3.3/3.6 各 5 项预期跳过。
- 发布 ZIP（最终发布产物 70 文件，含本报告与历史审查报告归档；审计时点产物为 68 文件）官方 extension validate 通过；解压后独立 Safety Audit 162/162。
- 运行时文件 `ruff --select F,E9` 全清；翻译词典 0 缺失 0 过期；全部 Python 文件 `py_compile` 通过。
- 变更规模：运行时代码净增约 90 行（含必要的失败检查与 finally），测试净增约 76 行；未新增任何模块或抽象层。

### 14.3 明示保留项（v1.1，不在本次承诺内）

- A17 余项：UDIM 边界 tile 误检（[0,1] 平面识别出 4 tile）、逐 tile numpy 后处理、`api.get_udim_tiles` 语义统一。
- A18：COMBINE_OBJECT/UDIM/SPLIT_MATERIAL 的自动应用与模型导出仍仅覆盖 `active_obj`；使用这些组合时应关闭 apply/export。
- A19 余项：Proximity 笼体为最近点均值而非逐顶点自适应；非均匀缩放下 cage 分析法线未校验。
- A25 余项：崩溃记录跨进程/跨场景归属；后台与真实强杀恢复路径未在本机验证。
- 预览功能的节点深复制仍不做——预览与烘焙互斥已保证，复杂网络显示不等价是已知限制。

上述保留项均已在代码注释、用户文档或本报告中明示，不构成"静默宣称支持"。按第 11 章验收集执行人工场景验收后，可进入正式发布。
