# Simple Bake Tool (SBT) - 用户参考手册

**版本**: 1.1.0 (Production Stable - Architectural Refinement)
**分类**: 3D VIEW > N Panel > Baking

> **📢 项目状态声明**: 本插件已通过涵盖 19x5 (950+) 项测试用例的跨版本（Blender 3.3 - 5.0）自动化矩阵测试套件验证，通过率 100%。v1.1.5 引入了安全性加固引擎与数据驱动 UI。

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
    *   `BSDF Bake`: 自动分析物体的材质节点（Principled BSDF），支持金属度/粗糙度流烘焙。
    *   `Basic Bake`: 调用 Blender 原生烘焙模式（如 AO, Shadow）。

### 1.3 Smart Intelligence (高阶智能) [New]
*   **Auto-Cage 2.0**: 
    *   `Uniform`: 传统的统一挤出模式。
    *   `Proximity`: **[Roadmap 1.1]** 智能邻近度模式。系统会自动分析高模与低模的间距，动态调整每个顶点的挤出距离，防止交叉和裁剪。
*   **Texel Density (像素密度)**: 
    *   设定目标密度（px/unit），系统将根据物体的实际物理尺寸自动计算并建议最佳的烘焙分辨率，确保资产库中的所有模型质量一致。

### 1.3 核心烘焙方法 (Core Methods)

#### Quick Bake (快捷烘焙)
无需配置复杂的任务，直接在视图中选择物体并点击 **Quick Bake**。
*   **零副作用**: *[New]* 现在的 Quick Bake 使用内存代理执行，不会修改你当前面板上的 Job 设置或场景预设。

#### Select to Active (高模烘低模)
1.  首先选择一个或多个高模物体。
2.  按住 Shift 最后选择低模目标物体（保持为 Active）。
3.  设置 Bake Mode 为 `Select to Active`。
4.  烘焙！现在支持高模物体无需 UV 坐标即可参与烘焙。

#### UDIM Bake
专为 UDIM 流程设计，支持多象限并行烘焙与自动 Tile 识别。

#### Interactive Preview (实时预览) [New]
在 Channel 列表上方开启 **Preview Packing**。
*   **可视化反馈**: 在 3D 视图中实时查看 ORM（遮蔽/粗糙度/金属度）通道的打包效果，无需烘焙即可调整参数。
*   **自动恢复**: 关闭预览后，系统会自动恢复采集物体原有的材质。

---

## 2. Channel List (通道列表)

这是 SBT 的核心。在这里勾选你需要输出的贴图类型。支持 PBR 数据、光照结果、网格地图（Curvature, ID Map, Thickness 等）以及 PBR 流程转换。

---

## 3. Save & Export (保存与输出)

*   **Apply to Scene (应用到场景)**: 勾选后，插件会创建一个带有 `_Baked` 后缀的新物体并赋予烘焙好的材质。
    *   **智能更新**: *[New]* 如果场景中已经存在该结果物体，插件会直接更新其材质和网格，而不会重复创建新的物体，保持场景整洁并节省内存。
*   **External Save**: 勾选后，烘焙结果会自动保存到磁盘。支持 PNG, JPG, EXR, TIFF 等格式。
*   **Path**: 输出目录。支持相对路径 `//`。

---

## 4. CLI & API (开发者与自动化) [New]
SBT 现在支持完全脱离 UI 运行，适用于渲染农场或 CI 管道。

### 4.1 Headless CLI
使用命令行参数运行烘焙，无需打开 Blender 界面：
`blender -b project.blend -P automation/headless_bake.py -- --job "MyJob"`

### 4.2 Public API
在你的脚本中直接调用：
```python
from baketool.core import api
api.bake(objects=bpy.context.selected_objects, preset="C:/presets/unreal.json")
```

---

## 5. 故障排查 (Troubleshooting)

### 4.1 崩溃恢复 (Crash Recovery)
如果 Blender 在烘焙过程中意外关闭或崩溃，重新打开后 SBT 面板顶部会出现红色警告框，显示最后一次处理的物体和通道，帮助您排查模型问题。

### 4.2 紧急清理 (Emergency Cleanup)
如果发生异常，场景中出现了名为 `BT_Bake_Temp_UV` 的临时层或 `BT_Protection_Dummy` 贴图：
1.  按 `F3` (搜索)。
2.  输入 `Clean Up Bake Junk` 并回车。
3.  **审计日志**: *[New]* 清理过程会记录在插件目录或系统临时目录下的 `logs/cleanup_history.log` 中。

### 4.3 常见问题
*   **法线贴图有奇怪的接缝**: 确保 `Image Settings` 中的 `Color Space` 设为 `Non-Color`（插件会自动设置）。
*   **链接资产崩溃**: *[Fixed]* 插件现在会自动跳过 Library 链接材质的节点注入，确保处理外部资产时的稳定性。
