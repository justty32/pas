# Level 6 Analysis: 視覺、動畫與特效

## 1. 高級場景切換技術
專案棄用了簡單的黑屏過渡，轉而採用基於 Shader 的截圖溶解技術。

### 1.1 流程分解
1. **捕捉**: `TransitionManager` 在切換前執行 `get_viewport().get_texture().get_image()`。
2. **覆蓋**: 將截圖賦予一個覆蓋全螢幕的 `TextureRect`。
3. **特效**: 執行 `transition.gdshader` 中的 `progress` 動畫。
4. **載入**: 在特效遮蓋下，異步加載目標場景並完成切換。

## 2. 動效與回饋機制
為了提升俯視角射擊的爽快感，專案整合了多種視覺技巧。

### 2.1 殘影效果 (After-Image)
- **實作**: `AfterImageVFX.gd` 會複製 `Sprite2D` 的 `texture` 與 `frame`。
- **應用**: 通常與角色衝刺 (Dash) 或高速移動掛鉤。
- **效能**: 透過 `PoolNode` 快速回收，不產生額外開銷。

### 2.2 著色器特效 (VFX Shaders)
- **Color Flash**: 角色受傷時瞬間閃白，由 `color_flash.gdshader` 實作。
- **Dust Particles**: 使用 Shader 驅動的粒子效果，比傳統粒子系統更輕量。

## 3. 視覺總結
Godot Game Template 展現了 Godot 4 在視覺處理上的靈活性：
- 強調**非同步加載**與**視覺掩護**的結合。
- 大量使用 **Shader** 處理 UI 與環境特效。
- 透過**對象池**保證了在高密度彈幕下的畫面流暢度。
