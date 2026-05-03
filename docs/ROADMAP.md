# BakeNexus 路线图 / Roadmap

## 1. 当前版本 (v1.0.0) - 稳定发布
- **核心定位**：从实验性脚本转向工业级稳定的 Blender 插件。
- **完成项**：
  - 全面品牌重塑 (BakeTool -> BakeNexus)。
  - 完善的自动化验证套件（150+ 测试用例）。
  - 支持 UDIM、Selected-to-Active、自定义通道打包。
  - 修复了渲染参数透传、可见性污染和内存泄露问题。

## 2. 短期计划 (v1.1.x) - 生产力增强
- **AI 辅助功能**：集成简单的 AI 降噪预设建议。
- **UV 优化联动**：烘焙前自动检测 UV 重叠并提供修复建议。
- **预设库扩展**：内置更多行业标准的 PBR 导出预设（UE5, Unity, Substance 风格）。
- **性能监控**：增加烘焙过程中的显存占用预警。

## 3. 长期愿景 (v2.x) - 智能烘焙生态
- **跨软件联动**：支持一键导出到外部渲染引擎的着色器配置。
- **云端验证**：支持在远程计算节点执行超大规模场景烘焙。
- **全自动化资产处理**：从原始高模到优化后的 LOD 资产实现一键全流程自动化。

---

# 技术原理概要 / Technical Principles

### 1. 非破坏式执行管道 (Non-Destructive Pipeline)
BakeNexus 不直接修改用户的场景数据。在烘焙开始前，`BakeContextManager` 会通过 `common.py` 中的 `safe_context_override` 保存当前视图、选择、渲染设置和节点树状态。在烘焙结束后，无论成功与否，系统都会通过 `finally` 块强制还原状态，确保用户的编辑流程不被打断。

### 2. 动态参数对齐 (Dynamic Parameter Alignment)
为了避免 UI 与引擎逻辑的脱节，我们引入了“单一事实源”机制：
- `property.py` 定义 RNA 属性。
- `constants.py` 定义底层引擎所需的映射。
- 自动化测试通过 `SuiteCodeReview` 强制验证 UI 标签与内部键的一致性。

### 3. 资源生命周期管理 (Resource Lifecycle)
所有的临时图像和中间节点均带有 `BT_TEMP_` 前缀。执行引擎在完成后会自动调用清理脚本，根据引用计数和标记识别并移除不再需要的 datablocks，防止 `.blend` 文件体积膨胀。
