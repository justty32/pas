# 教學：實作「原神風格」渲染 (Anime / Cel-Shading)

「原神」風格的核心在於 **Cel-Shading (三渲二)**、**Outline (描邊)** 以及 **Stylized Environment (風格化環境)**。以下是在 Godot 4 中達成此風格的具體步驟。

## 1. 核心：三渲二材質 (Cel-Shading Shader)

原神不使用真實的光影漸層，而是階梯狀的明暗色塊。

### 實作步驟
1. 建立一個 `ShaderMaterial`。
2. 編寫或導入 Toon Shader。關鍵邏輯在於 `light()` 函數：
   ```glsl
   void light() {
       float diffuse = dot(NORMAL, LIGHT);
       // 將連續的漫反射值轉為 0 或 1 (或多個階梯)
       float ramp = smoothstep(0.45, 0.55, diffuse);
       DIFFUSE_LIGHT += LIGHT_COLOR * ATTENUATION * ramp * ALBEDO;
   }
   ```
3. **Rim Light (邊緣光)**：在頂部加上一層淡淡的發光，增加角色層次感。

---

## 2. 角色描邊 (Outline)

原神角色邊緣有一圈黑色的描邊。
- **方法：背面擴張法 (Backface Expansion)**
  1. 在 `MeshInstance3D` 的 `Material` 中增加一個 **Next Pass**。
  2. 新增一個 `ShaderMaterial`。
  3. Shader 邏輯：將頂點沿著法線方向稍微移動，並只渲染背面 (Cull Front)，顏色設為純黑。
   ```glsl
   void vertex() {
       VERTEX += NORMAL * outline_width;
   }
   ```

---

## 3. 色彩與紋理 (Textures)

- **無 PBR 貼圖**：關閉 `Specular` 與 `Roughness` 的細節，主要依賴 `Albedo` (底色)。
- **SDF 面部陰影**：原神的面部陰影是特殊的，通常需要額外的貼圖來控制陰影在臉上的形狀，確保在任何角度看起來都美觀。

---

## 4. 風格化環境 (Environment)

- **天空**：使用 `ProceduralSkyMaterial`，將顏色設定為鮮豔的淺藍與淺紫。
- **雲朵**：不要使用體積雲，建議使用帶有動畫 Shader 的平面 Mesh (Stylized Clouds)。
- **草地**：使用大量簡單的平面 Mesh，並套用 **Wind Sway Shader**（讓草隨風搖擺）與 **Slope Coloring**（山坡處顏色變深）。

---

## 5. 渲染選項微調

1. **關閉 SSAO**：風格化渲染不需要過於真實的遮蔽陰影。
2. **開啟抗鋸齒 (MSAA)**：二次元風格對鋸齒非常敏感，建議至少開啟 `4x MSAA`。
3. **Tonemapping**: 選擇 `Linear` 或自訂色彩曲線，保持色彩飽和度。

## 驗證方式
1. 觀察角色在旋轉光源時，陰影是否呈現銳利的塊狀切換（而非柔和漸層）。
2. 檢查遠處物件的描邊是否清晰，且不會隨距離過度閃爍。
3. 比較原畫與遊戲畫面的色彩飽和度，調整 `Vibrance` 參數。
