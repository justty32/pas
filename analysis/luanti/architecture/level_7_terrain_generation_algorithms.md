# Level 7: 地形生成演算法深度分析 (Terrain Generation)

## 1. 核心數學原理：多層噪聲疊加
Luanti 的地形生成主要依賴於 **Perlin 噪聲 (Perlin Noise)**。為了產生自然的地形，引擎並非只使用單層噪聲，而是透過多層不同頻率與振幅的噪聲進行複合運算。

### A. 2D 基礎地形 (Base Terrain)
**原始碼位置：** `src/mapgen/mapgen_v7.cpp` (約 400-415 行, `baseTerrainLevelAtPoint`)

1. **雙重地貌切換**：
    - `height_base`: 產生較平緩的地形。
    - `height_alt`: 產生較崎嶇或海拔較高的地形。
    - `hselect`: 選擇器噪聲，決定在特定 (x, z) 座標點使用哪種地形，或如何進行線性插值。
2. **持久度調整 (Persist)**：透過 `noise_terrain_persist` 噪聲動態改變地形的複雜度（細碎程度）。

### B. 3D 山脈生成 (Mountain Terrain)
**原始碼位置：** `src/mapgen/mapgen_v7.cpp` (約 428-435 行, `getMountainTerrainAtPoint`)

這是 Luanti 能產生懸空島嶼與不規則山洞的關鍵。
- **公式：** `mnt_n + density_gradient >= 0`
- **mnt_n**: 3D 噪聲值。
- **density_gradient**: 垂直密度梯度。其公式為 `-((y - mount_zero_level) / mount_height)`。
- **物理意義**：隨著高度 (y) 增加，梯度值會變小（負值更大），抵消掉 3D 噪聲的正值，使得高處較難生成實體方塊。這保證了山脈有頂峰，而不會無限向天空延伸。

## 2. 特殊結構生成
- **河流 (Rivers/Ridges)**：使用 `noise_ridge` (3D) 與 `noise_ridge_uwater` (2D) 進行邏輯減法，在地表「挖出」河道。
- **浮空島 (Floatlands)**：在極高海拔 (預設 y=1280 以上) 啟動獨立的 3D 噪聲運算，並使用 **Tapering (漸變)** 演算法確保島嶼邊緣與上下方不會生硬地切斷。

## 3. 效能優化：MapChunk 緩存機制
為了避免對每個點進行重複的噪聲運算，`MapgenV7` 會在 `generateTerrain()` 階段預先計算整個 80x80 (2D) 或 80x80x80 (3D) 的噪聲矩陣 (`noiseMap2D` / `noiseMap3D`) 並儲存在 `result` 陣列中。後續的方塊填充僅需透過索引 (Index) 查表，極大地提升了速度。
