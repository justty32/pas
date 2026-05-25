# Level 6 Analysis: 視覺、動畫與特效

> 核對於 2026-05-25（Claude Code, Opus 4.7）：轉場流程、殘影、Shader 特效皆與源碼一致；本次補上路徑/行號，修正殘影驅動方式（AnimationPlayer）與 dust shader 實際檔名。

## 1. 高級場景切換技術
專案棄用了簡單的黑屏過渡，轉而採用基於 Shader 的截圖溶解技術（`addons/top_down/scripts/game/TransitionManager.gd`，autoload `Transition`）。

### 1.1 流程分解
1. **觸發**: `change_scene(path)` 先把 `bool_resource` 設 true，並掛一次性 `RenderingServer.frame_post_draw` 回呼，等本幀畫完（`TransitionManager.gd:17-20`）。
2. **捕捉**: `_post_draw()` 執行 `get_viewport().get_texture().get_image()` 取得當前畫面，並依視窗/內容縮放比設定 shader 的 `scale` 參數（`:22-37`）。
3. **覆蓋**: 將截圖建為 `ImageTexture` 賦予覆蓋全螢幕的 `TextureRect`，隱藏 `current_scene` 後顯示轉場層（`:37-42`）。
4. **載入與動畫**: 以 `ThreadUtility.load_resource(path, scene_loaded)` 異步載入（`:45`）；載入完成後 `change_scene_to_packed()` 並用 Tween 把 shader 參數 `progress` 從 0→1（`EASE_IN`/`TRANS_CUBIC`）播放溶解（`scene_loaded()`，`:48-57`）。著色器：`addons/top_down/scripts/shaders/transition.gdshader`。

## 2. 動效與回饋機制
為了提升俯視角射擊的爽快感，專案整合了多種視覺技巧。

### 2.1 殘影效果 (After-Image)
- **檔案路徑**: `addons/top_down/scripts/vfx/AfterImageVFX.gd`（場景 `scenes/vfx/after_image_vfx.tscn`，資源 `resources/InstanceResources/vfx/after_image_vfx.tres`）。
- **實作**: `setup()` 複製來源 `Sprite2D` 的 `texture` / `hframes` / `vframes` / `frame` / `centered` / `offset` 與位置（`AfterImageVFX.gd:12-20`），再由 `AnimationPlayer` 播放淡出動畫，播完於 `animation_finished` 觸發 `pool_node.pool_return()` 回收（`:22-29`）——淡出由 AnimationPlayer 驅動，而非腳本逐幀計算。
- **應用**: 通常與角色衝刺 (Dash, `scripts/actor/DashAbility.gd`) 或高速移動掛鉤。
- **效能**: 透過 `PoolNode` 快速回收，不產生額外開銷。

### 2.2 著色器特效 (VFX Shaders)
（著色器集中於 `addons/top_down/scripts/shaders/`）
- **Color Flash**: 角色受傷時瞬間閃白，由 `color_flash.gdshader` 實作（搭配 `resources/CommandNodeResource/color_flash.tres`）。
- **Dust Particles**: Shader 驅動的粒子效果，實際檔名為 `dust_partickle.gdshader`（原拼字，搭配 `resources/materials/dust_particle_material.tres`），比傳統粒子系統更輕量。
- **其他**: `spawn_ring.gdshader`（敵人生成環）、`progress_bar.gdshader` / `progress_fill.gdshader`（UI 進度條）、`control_shader.gdshader`、`h_separator_line.gdshader`。

## 3. 視覺總結
Godot Game Template 展現了 Godot 4 在視覺處理上的靈活性：
- 強調**非同步加載**（`ThreadUtility`）與**視覺掩護**（截圖溶解）的結合。
- 大量使用 **Shader** 處理 UI 與環境特效，並在 `BootPreloader`/`PreloadResource` 啟動時預先觸發編譯以避免執行期卡頓。
- 透過**對象池**（`PoolNode`）保證了在高密度彈幕下的畫面流暢度。
