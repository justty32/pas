# LOD 渲染、尋路避障與光照時序深度分析 (Analysis)

## 1. 遠景 LOD 地形渲染架構 (`voxygen/src/render/pipelines/lod_terrain.rs`)
Veloren 透過層級化的渲染管線實現超大視距。

### 核心代碼標註：
- **全局數據同步**：[voxygen/src/render/pipelines/mod.rs:133] 將 `view_distance` 與 `tgt_detail` 注入渲染全局狀態，控制 LOD 切換閾值。
- **地理邊界限定**：透過 `map_bounds` [Line 133] 確保 LOD 渲染器不會計算無效區域，優化顯存利用率。

## 2. NPC 尋路的可通行性與物理保護 (`common/src/path.rs`)
寻路系統具備高度的立體空間感知能力。

### 關鍵機制：
- **垂直淨空校驗 (`fn walkable`)**：[Line 521] 系統在判定一個體素是否可通行時，會遞歸檢查上方空間是否全為 `Air`，確保實體不會發生頭部卡死。
- **立體路徑加權**：[Line 502] 針對飛行生物 (`can_fly`)，系統會放寬 Z 軸的歐幾里得距離權重，使其更傾向於採取高低俯衝的立體戰術。
- **墜落預防邏輯**：[Line 503] `walking_towards_edge` 的判定是 NPC 生存率的關鍵，防止非飛行生物採取自殺式的最短路徑。

## 3. 動態晝夜光照系統 (`voxygen/src/render/pipelines/mod.rs`)
環境光感是由伺服器時間驅動的動態矩陣。

### 核心機制：
- **天體方向向量**：[Line 147-148] `sun_dir` 與 `moon_dir` 是實時計算的單位向量，決定了 Shader 中陰影投射的夾角。
- **週期性光照修正**：[Line 143] 透過 `time_of_day` 的長週期取模運算，系統模擬了季節性的光照長度變化，這些參數最終影響了 `terrain-frag.glsl` 中的環境光係數。

---
*本文件由分析任務自動生成預定留檔。*
