# Level 10: Shader 架構與自定義渲染深度分析

## 1. Shader 生命週期與加載
Luanti 的 Shader 管理由 `ShaderSource` 類別 (`src/client/shader.cpp`) 負責。其流程如下：
1. **路徑匹配**：優先從 `shader_path` 設定中尋找，若無則回退至 `client/shaders/` 目錄。
2. **動態拼接**：
    - 引擎會讀取 `.glsl` 原始檔案（通常包含頂點著色器 `.vert` 與片段著色器 `.frag`）。
    - 根據驅動程式版本插入對應的 `#version` 聲明。
    - 將 `ShaderConstants` (由 C++ 定義的 `int` 或 `float`) 轉換為 `#define` 語句插入原始碼最前端。
3. **編譯與快取**：透過 Irrlicht 的 `IGPUProgrammingServices` 進行編譯，並將編譯後的 Material ID 快取在 `m_shaderinfo_cache` 中。

## 2. 數據傳遞：Uniforms 與 Attributes
為了讓 Shader 產生動態效果，C++ 會每幀傳送數據給 GPU：
- **全域 Uniforms** (`MainShaderConstantSetter`)：
    - `mWorldViewProj`: 投影矩陣。
    - `dayNightRatio`: 晝夜比例，用於動態切換色彩。
    - `mTime`: 遊戲時間，用於波浪或閃爍特效。
- **光照數據**：包含太陽位置、陰影貼圖矩陣以及光照等級 (`uLightLevel`)。

## 3. 節點著色器 (Nodes Shader)
這是體素方塊渲染的核心：
- **位置**：`client/shaders/nodes_shader/`
- **邏輯**：負責計算體素方塊的光照、法線貼圖 (Normal Maps) 以及環境光遮蔽 (AO)。
- **變體**：支援 `ndt_allfaces_optional` (如葉子) 與 `ndt_liquid` (如水) 的特殊處理。

## 4. 後處理管線 (Post-Processing)
Luanti 支援多階段後處理：
- **第一階段**：渲染場景到 FBO (Frame Buffer Object)。
- **第二階段**：套用 FXAA, Bloom, Volumetric Light 等效果。
- **最後階段**：色彩校正與色調映射 (Tonemapping)。
