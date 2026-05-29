# 教學：畫面表現設定（天空盒、光影、Shader 與渲染選項）

本教學說明在 Godot 4 + COGITO 中設定高品質視覺效果的具體步驟，包括環境設定、光影調整、後處理效果以及效能開關的正確位置。

## 前置知識
- 了解 Godot 4 節點系統基礎。
- COGITO 使用 Forward+ 渲染器（Jolt 物理，`project.godot:238`）。

---

## 一、WorldEnvironment 設定

每個場景應有一個 `WorldEnvironment` 節點，掛載一個 `Environment` 資源。

### 天空盒

**全景 HDR 天空（推薦用於寫實場景）**：
1. 下載 .hdr 或 .exr 格式的 360° 全景圖（Polyhaven 等免費資源）。
2. 匯入時在匯入設定中確認 `Detect 3D` 不干擾。
3. `WorldEnvironment → Environment → Background → Mode: Sky`。
4. `Sky Material: PanoramaSkyMaterial → Panorama: [放入 HDR 貼圖]`。

**程序化天空（快速設定）**：
- Sky Material: ProceduralSkyMaterial
  - Sky Top Color: (0.1, 0.3, 0.8) — 高空顏色
  - Sky Horizon Color: (0.6, 0.75, 0.9) — 地平線
  - Sky Curve: 0.15 — 天頂到地平線的漸層曲線
  - Ground Bottom Color: (0.2, 0.15, 0.1)
  - Sun Angle Max: 30 — 太陽光暈的大小

---

## 二、光影設定

### DirectionalLight3D（太陽/月亮）

必要設定：
- DirectionalLight3D
  - Enabled: true
  - Shadow: true（必須開啟才有陰影）
  - Directional Shadow
    - Mode: PSSM 4 Splits（戶外大場景）／ Orthogonal（室內小場景）
    - Max Distance: 150（陰影最遠繪製距離）
    - Split 1~4 Bias: 0.1（避免 shadow acne，若有條紋請調高）

**Soft Shadows 設定位置**：
- Project Settings → Rendering → Lights and Shadows
  - Directional Shadow → Soft Shadow Filter Quality: Medium 或 High

### 局部光源最佳化

- OmniLight3D / SpotLight3D
  - Shadow: 通常關閉（貴！只給關鍵光源開）
  - Distance Fade
    - Enabled: true
    - Begin: 30, Length: 10 — 30m 外開始淡出，40m 完全消失
  - Light Bake Mode: Dynamic（動態）或 Static（烘焙，效能最佳）

---

## 三、渲染特效（環境效果）

以下設定位於 `Environment` 資源中，或 `Project Settings → Rendering`：

### SSAO（螢幕空間環境光遮蔽）
- **作用**：物件交界處出現細微陰影，增加立體感。
- **位置**：`Environment → SSAO → Enabled`
- **建議**：室內場景開啟（Radius: 1.0, Intensity: 0.8），大型開放世界可關閉。

### SSR（螢幕空間反射）
- **作用**：水面、金屬地板的反射。
- **位置**：`Environment → SSR → Enabled`
- **注意**：效能消耗高；只對有反射材質的場景開啟。

### FSR 2.2（超取樣）
- **作用**：以較低解析度渲染後放大，維持畫質同時大幅提升 FPS。
- **位置**：`Project Settings → Rendering → Anti Aliasing → Quality → Screen Space AA`
- **建議**：設為 `FSR 2.2`，Mip Bias 設 -0.5（減少鋸齒）。

---

## 四、後處理（Tonemap + 色彩校正）

### Tonemapping

- Environment → Tonemap
  - Mode:
    - Linear: 色彩最鮮艷（動漫風、卡通風推薦）
    - Reinhard: 柔和過曝（較自然）
    - Filmic: 電影感（中等飽和度）
    - ACES: 電影標準（高對比，暗部較深）
  - Exposure: 1.0（正常曝光）
  - White: 1.0（白點位置，調低讓畫面更亮）

### Glow（泛光）

- Environment → Glow
  - Enabled: true
  - Intensity: 0.8
  - Bloom: 0.2 — 高亮部分的光暈強度
  - Blend Mode: Additive（標準發光）
  - HDR Threshold: 1.0 — 只有超過此亮度的部分才發光

讓發光效果生效，發光物件的材質需啟用 `Emission`，且 Emission Energy 要超過 `HDR Threshold`。

### Color Correction（LUT）

```
Environment → Color Correction → Texture: [3D LUT 圖片]
```

LUT（Look Up Table）是預先計算好的色彩映射表。可以從 DaVinci Resolve 或 Photoshop 匯出 `.cube` 格式，再轉換為 Godot 接受的 `Image Texture 3D`。

---

## 五、Shader 基礎套用

在 COGITO 中所有物件最終都是 `MeshInstance3D`。套用自訂 Shader：
1. 選取 `MeshInstance3D` → `Surface Material Override`（或 `Mesh → Surface Materials` 中的 Surface 0）。
2. 新建 `ShaderMaterial`。
3. `Shader` 欄位 → 新建 `.gdshader` 或指向現有檔案。

**Shader 類型選擇**：
- `shader_type spatial;`：3D 物件表面（大多數情況）
- `shader_type canvas_item;`：2D 控制節點 / HUD 特效
- `shader_type sky;`：自訂天空（搭配 `ShaderSkyMaterial`）

---

## 六、COGITO 專案現有設定

根據 `project.godot`，COGITO v1.1.5 的渲染配置：
- **Physics Engine**: Jolt（高效能物理）
- **Renderer**: Forward+（啟用全部高品質特效）
- **Layers**: Layer 1 = Environment，Layer 2 = Interactables

---

## 七、驗證清單

| 測試步驟 | 預期結果 |
|---|---|
| 切換 `Environment → Background Mode` | 環境光立即改變（天空顏色影響全場景 GI）|
| 放置 `DirectionalLight3D` 且開啟陰影 | 物件投影陰影在地面 |
| Glow 啟用後放置高 Emission 物件 | 物件周圍出現泛光光暈 |
| 切換 Tonemapping Mode | 整體色調明顯變化 |
| 使用 Rendering → Debug Draw → Overdraw | 紅色越深表示過度繪製越多 |
| FSR 啟用後 | FPS 提升，畫質接近原始解析度 |
