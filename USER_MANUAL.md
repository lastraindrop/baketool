# Simple Bake Tool (SBT) - 用户参考手册

**版本**: 0.9.4 (Robustness Update)
**分类**: 3D VIEW > N Panel > Baking

> **📢 项目状态声明**: 本插件已通过涵盖 56 项测试的跨版本（Blender 3.6 - 5.0）自动化测试套件验证。重构后的架构大幅提升了在复杂着色器和极端 UDIM 布局下的稳定性。

Simple Bake Tool (SBT) 是一套专为 Blender 设计的非破坏性、全自动纹理烘焙解决方案。它接管了繁琐的节点连接、图像创建和保存工作，让您专注于参数设置。

---

## 1. 界面概览与基础设置

### 1.1 Job Management (任务管理)
面板顶部是任务列表。你可以创建多个不同的烘焙预设（例如“角色烘焙”、“场景烘焙”）。
*   **Add/Remove**: 添加或删除任务。
*   **Save/Load Preset**: 将当前的所有设置保存为 `.json` 文件，方便在不同工程间共享配置。

### 1.2 Input Settings (输入设置)
定义“谁来烘焙”以及“怎么烘焙”。

*   **Resolution (X/Y)**: 烘焙贴图的分辨率。对于 UDIM，这是每个 Tile 的分辨率。
*   **Bake Type**:
    *   `BSDF Bake`: 自动分析物体的材质节点（Principled BSDF），烘焙固有色、粗糙度、法线等。
    *   `Basic Bake`: Blender 原生的烘焙模式（AO, Shadow 等）。
*   **Bake Mode (核心模式)**:
    *   `Single Object`: 每个选中的物体单独烘焙一张图。
    *   `Multi Objects`: 所有选中物体合并烘焙到同一张图（需要它们在同一个 UV 空间）。
    *   `Active Bake`: **高模烘低模**。将选中的物体（高模）烘焙到 Active 物体（低模）。
    *   `Split Material`: 如果一个物体有多个材质槽，会为每个材质生成独立的贴图。
    *   `UDIM Bake` *[New]*: 专为 UDIM 流程设计，支持多象限烘焙。

*   **Targets (目标物体)**:
    *   列表显示当前将要参与烘焙的物体。
    *   **Smart Set (Active Bake 专用)**: 一键将当前选中的物体设为高模，最后选中的设为低模（Active），自动配置列表。

### 1.3 UDIM Workflow (UDIM 工作流)
*   **智能检测 (Robust Detect)**: *[Improved]* 现在的检测算法支持非标准 UV 范围过滤。即使 UV 坐标超出了 0-10 的标准 UDIM 范围，插件也会智能过滤掉干扰点，准确识别主象限。
*   **硬件限制保护**: *[New]* 针对 Blender 每个物体最多 8 个 UV 层的硬件限制，插件增加了前置检查。如果层数已满，插件会记录错误并提示用户，防止崩溃。

*   **Method (处理方式)**:
    *   `Use Existing UVs (Detect)`: 默认模式。插件会自动检测每个物体 UV 所在的象限（如 1001, 1002），并烘焙到对应的 Tile 上。**前提**: 你已经手动分好了 UV。
    *   `Auto Repack 0-1`: 自动打包模式。如果你的物体 UV 都在 0-1 (1001) 空间重叠，选择此模式会自动将它们分配到 1001, 1002, 1003... 等空闲 Tile 上。
    *   `Custom List`: 手动模式。你可以在上方的物体列表中，手动指定每个物体应该去哪个 Tile (1001-1099)。
*   **Output**: 烘焙结果会自动保存为带 `<UDIM>` 标记的文件序列（如 `Color.1001.png`, `Color.1002.png`）。

---

## 2. Channel List (通道列表)

这是 SBT 的核心。在这里勾选你需要输出的贴图类型。

### 2.1 PBR Data (物理属性)
*   **高级着色器支持**: *[New]* 除了标准 `Principled BSDF`，现在支持直接使用 `Emission` 或其他基础着色器节点。如果检测不到物理着色器，插件会自动向上寻找发射信息或回退到材质基础色。

基于 Principled BSDF 的输入。
*   `Base Color`, `Metallic`, `Roughness`, `Normal`, `Emission`, `Alpha` 等。
*   **注意**: 如果你的材质没有连接某个属性（如 Metallic），插件会自动给出一个默认值（如纯黑）。

### 2.2 Light / Render (光照结果)
需要 Cycles 渲染计算。
*   `Diffuse`, `Glossy`, `Transmission`: 包含光照影响的最终渲染结果。
*   `AO (Ambient Occlusion)`: 环境光遮蔽。
*   `Shadow`: 阴影通道。

### 2.3 Mesh Maps (网格数据)
不依赖材质，只依赖模型几何结构。常用于贴图制作软件（如 Substance Painter）。

*   **Curvature (曲率图)**:
    *   检测模型的边缘和缝隙。
    *   **Samples**: 采样数。越高越平滑，噪点越少（推荐 6-12）。
    *   **Radius**: 边缘检测范围。值越大，白边越宽。
    *   **Contrast**: 对比度。值越大，边缘越锐利。
*   **ID Map (蒙版图)**:
    *   用于区分模型的不同部分。
    *   **Type**: 可按 Material（材质）、Element（独立的网格块）、UV Island（UV 岛）或 Seam（缝合线）着色。
    *   **Random Seed (随机种子)**: *[重要]* 指定一个整数。**只要种子不变，生成的 ID 颜色永远固定**。建议设置为非 0 值以保证流程可复现。
*   **Thickness**: 厚度图（基于 SSS 原理）。
*   **Bevel**: 仅烘焙倒角法线。

### 2.4 Extension Maps (PBR 流程转换)
用于将 **Specular/Glossiness** 流程的材质转换为 **Metal/Roughness** 流程。

*   `Conv: Metallic`: 从 Specular 贴图计算金属度。
*   `Conv: Base Color`: 混合 Diffuse 和 Specular。
*   **F0 Threshold (介电阈值)**:
    *   默认 `0.04`。
    *   用于区分“非金属”和“金属”。如果你的金属贴图出来太黑，尝试降低此值；如果塑料变成了金属，尝试提高此值。
*   **Numpy 加速**: 如果你同时烘焙了源通道（Color + Specular）和转换通道，插件会使用内存计算，**速度提升 100 倍**。

---

## 3. Save & Export (保存与输出)

*   **Save Output**: 勾选后，烘焙结果会自动保存到磁盘。如果不勾选，结果只保存在 Blender 内部内存中（未打包，关闭软件会丢失）。
*   **Path**: 输出目录。支持相对路径 `//`。
*   **Format**: 支持 PNG, JPG, EXR (32bit), TIFF 等。
*   **Folder Naming**: 自动创建子文件夹的规则（如按材质名建文件夹）。
*   **Base Name**: 文件名规则。
    *   例如选 `Object_Mat`，输出文件名为 `Cube_MaterialA_BaseColor.png`。
    *   你可以在通道设置中自定义每个通道的后缀（Suffix）。

---

## 4. 故障排查 (Troubleshooting)

### 4.1 崩溃恢复 (Crash Recovery)
如果 Blender 在烘焙过程中意外关闭或崩溃：
1.  **不要惊慌**。数据已经实时记录。
2.  重新打开 Blender，加载工程。
3.  SBT 面板顶部会出现一个**红色警告框**。
4.  查看警告信息：它会精确告诉你是在处理**哪个物体**的**哪个通道**时崩溃的。
    *   *案例*: 如果卡在 `Curvature`，可能是 `Samples` 设置过高导致内存溢出。
    *   *案例*: 如果卡在 `ID Map`，可能是模型拓扑有严重错误导致死循环。
5.  解决模型问题后，点击红色框的 `X` 按钮清除记录，重新开始烘焙。

### 4.2 紧急清理 (Emergency Cleanup)
*   **清理审计日志**: *[New]* 现在执行 `Clean Up Bake Junk` 不仅会重置 UI，还会在插件目录下的 `logs/cleanup_history.log` 中生成详细的审计清单。你可以查看具体哪个物体被删除了哪些临时层或节点。

如果崩溃后，你发现场景中出现了奇怪的紫色 UV 层（名为 `BT_Bake_Temp_UV`）或无法删除的白色贴图：
*   这是插件为了保护原始数据创建的临时文件，本应在烘焙结束后自动删除。
*   **解决方法**:
    1.  按 `F3` (搜索)。
    2.  输入 `Clean Up Bake Junk` 并回车。
    3.  插件会自动扫描并删除所有残留的临时数据。

### 4.3 常见问题
*   **法线贴图有奇怪的接缝**: 确保 `Image Settings` 中的 `Color Space` 设为 `Non-Color`（插件会自动设置，但请勿手动更改）。
*   **ID Map 颜色每次都不一样**: 请在 ID Map 设置中将 `Random Seed` 从 0 改为任意固定整数（如 1）。
*   **PBR 转换无效**: 确保你的材质中有连接 Specular 相关的节点或属性。