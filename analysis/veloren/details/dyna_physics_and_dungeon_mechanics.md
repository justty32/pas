# 載具物理、水下視效與機關解鎖深度分析 (Analysis)

## 1. 移動載具的座標轉換與物理 (`common/src/vol.rs` & `common/src/volumes/dyna.rs`)
飛船與船隻在 Veloren 中是具備獨立座標系的實體。

### 核心技術：
- **RasterableVol 抽象**：[Line 58] 透過定義局部邊界 (`lower_bound`, `upper_bound`)，載具體素被封裝在一個獨立的 Raster 空間。
- **座標空間變換**：物理引擎在每個 Tick 會將位於載具 Aabb 內的玩家座標投影至 `Dyna` 空間。這種局部化的碰撞檢測解決了「移動物體上的穩定站立」難題。
- **體素動態化**：載具並非靜態模型，而是可交互的 `Volume`，這意味著玩家甚至可以在移動的飛船甲板上放置家具或火把。

## 2. 水下視覺波動模擬 (`assets/voxygen/shaders/postprocess-frag.glsl`)
### 關鍵機制：
- **UV 正弦扭曲**：[Line 245] `EXPERIMENTAL_UNDERWARPER` 展示了利用正弦波對屏幕座標進行 0.003 幅度的微調。
- **時間與空間耦合**：扭曲頻率與 `tick` 綁定，而相位與 `uv.x/y` 綁定，營造出隨機且連續的流體波動感。

## 3. 地城機關與擊殺觸發邏輯 (`server/src/sys/terrain.rs`)
### 核心流程：
- **事件捕獲**：系統監聽 `DeathEvent` [common/src/event.rs]。當具備 Site 權限標記的守衛死亡時，觸發地形更新請求。
- **區塊即時重寫**：[Line 153] 伺服器透過 `terrain_persistence` 發送一個區塊變更請求，將代表「門」的 `BlockKind` 替換為 `Air` 或開啟狀態的 Sprite。
- **網路同步**：更新後的區塊透過 `TerrainChunkUpdate` 流 [Line 138] 推送至客戶端，實現了視覺與物理上的解鎖。

---
*本文件由分析任務自動生成預定留檔。*
