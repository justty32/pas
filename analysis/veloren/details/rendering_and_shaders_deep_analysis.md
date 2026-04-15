# 渲染架構與 Shader 技術深度分析 (Analysis)

## 1. 角色渲染管線 (`voxygen/src/render/pipelines/figure.rs`)
Voxel 角色的渲染需要同時兼顧效能與靈活性。

### 核心技術拆解：
- **數據壓縮 (`make_greedy`)**：
    - **位置**：`voxygen/src/render/pipelines/figure.rs` (約 85 行)
    - **邏輯**：為了將骨骼 ID 塞入每個頂點，系統壓縮了 `atlas_offs` 的位元。這是在 GPU 記憶體頻寬與視覺細節之間的平衡。
- **骨骼數據同步 (`FigureLayout`)**：
    - **位置**：`voxygen/src/render/pipelines/figure.rs` (約 125 行)
    - **邏輯**：每個角色實例都擁有一個 `Locals` 與 `BoneData` 的 Uniform Buffer。Shader 透過 `bone_mat` 對體素頂點進行實時偏移，實現動畫。

## 2. 後處理著色器 (`assets/voxygen/shaders/postprocess-frag.glsl`)
### 核心技術拆解：
- **HDR 與色調映射 (`_illuminate`)**：
    - **位置**：`assets/voxygen/shaders/postprocess-frag.glsl` (約 105-175 行)
    - **邏輯**：使用指數衰減公式 `1.0 - exp(-alpha * lum)` 進行 Tone-mapping。這保證了在強光（陽光直射）與暗部（深夜森林）中，畫面細節都能正確呈現。

---
*本文件由分析任務自動生成。*
