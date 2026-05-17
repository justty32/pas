# 教學：畫面表現設定 (天空盒、光影、Shader 與渲染選項)

本教學將引導您如何在 Godot 4 / COGITO 中設定高品質的視覺畫面，涵蓋基礎環境設定與進階渲染優化。

## 1. 設定天空盒 (Skybox)

天空盒決定了場景的環境光與背景。
1. **建立環境資源**：在場景中添加 `WorldEnvironment` 節點。
2. **新增 Environment**：新建一個 `Environment` 資源。
3. **設定背景**：
   - `Background -> Mode`: 選擇 `Sky`。
   - `Sky -> Sky Material`: 
     - **全景圖**：選擇 `PanoramaSkyMaterial` 並放入 360 度 HDR/EXR 貼圖。
     - **程序化**：選擇 `ProceduralSkyMaterial`（可自訂天空、地平線與地面顏色）。

---

## 2. 光影設定 (Lighting & Shadows)

### DirectionalLight3D (太陽光)
- **Shadows**: 勾選 `Enabled`。
- **Directional Shadow -> Mode**: 建議選擇 `Orthogonal` (室內) 或 `PSSM 4 Splits` (大型室外場景)。
- **Soft Shadows**: 在 `Project Settings -> Rendering -> Lights and Shadows` 中調整品質。

### 局部光源 (OmniLight / SpotLight)
- 善用 **Distance Fade**：對於遠處的小燈泡，設定隱藏距離以節省效能。
- **Shadow Casting**: 僅對關鍵光源開啟投影，避免過度消耗。

---

## 3. 各類渲染選項 (Forward+ 特性)

前往 `Project Settings -> Rendering`：
- **SSAO (螢幕空間環境光遮蔽)**：增加物件交界處的陰影細節，提升立體感。
- **SSIL (螢幕空間間接光)**：模擬光線反彈，讓暗部色彩更自然。
- **SSR (螢幕空間反射)**：用於金屬或積水地面的反射效果。
- **FSR 2.2**: 開啟超取樣 (Upscaling)，在維持畫質的前提下大幅提升 FPS。

---

## 4. Shader 的基本應用

在 Godot 中，Shader 透過 `ShaderMaterial` 運作。
- **套用 Shader**：在 `MeshInstance3D` 的 `Material` 屬性中，新建一個 `ShaderMaterial`，並建立新的 `Shader`。
- **常用 Shader 類型**：
  - **Spatial**: 處理 3D 物件表面。
  - **Fog**: 用於自訂體積雲或迷霧。
  - **Sky**: 用於自訂動態天空（如極光、動態雲）。

---

## 5. 後處理 (Post-Processing)

在 `WorldEnvironment` 的屬性中調整：
- **Tonemap**: 建議選擇 `Filmic` 或 `ACES` 以獲得電影級的色彩範圍。
- **Glow**: 讓發光物體有光暈效果。
- **Color Correction**: 放入一個 3D LUT 圖示來進行整體色調映射（冷色調、暖色調等）。

## 驗證方式
1. 切換 `WorldEnvironment` 的 `Background Mode`，觀察環境光的即時變化。
2. 在 `Debug Draw` 選單中選擇 `Overdraw` 或 `Lighting` 模式，檢查過度繪製與光影分佈。
3. 切換渲染器模式（Forward+ vs Mobile），確保 Shader 在不同平台下的相容性。
