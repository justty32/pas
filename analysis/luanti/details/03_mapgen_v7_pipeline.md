# 模組深度分析 3：地圖生成引擎流水線 (Mapgen V7)

## 流程概述
在 Luanti 中，世界是無限延伸的，因此地圖是依照區塊（MapChunk，通常為 80x80x80 的節點空間）動態生成的。`MapgenV7` 是功能最完整的生成器，其生成邏輯完全封裝在 `MapgenV7::makeChunk` 函數中。

## 階段 1：準備與基礎地形生成
**原始碼位置：** `src/mapgen/mapgen_v7.cpp` (約 299 行，`MapgenV7::makeChunk`)

1. **空間劃分**：設定 `node_min` 到 `node_max` 的範圍，並綁定 `VoxelManipulator` (這是一個暫存的體素操作空間，用於在寫入資料庫前進行高速修改)。
2. **基底地形計算 (`generateTerrain`)**：
    - 依據 2D 與 3D Perlin 噪聲 (NoiseFractal)，生成最底層的岩石骨架 (Stone) 與山脈形狀。
    - 回傳 `stone_surface_max_y`，作為後續生成步驟的高度參考基準。
3. **更新高度圖 (`updateHeightmap`)**：計算出目前區域的地表最高點，用於光照與生物群系判定。

## 階段 2：地表修飾與空洞化
依據設定旗標 (`flags`)，依序執行：
1. **生物群系 (`MG_BIOMES`)**：
    - 呼叫 `generateBiomes()`。
    - 根據溫度與濕度的噪聲分布，將表層的岩石替換為對應的泥土、沙子、草地或冰雪。
2. **洞穴與地下洞穴 (`MG_CAVES`)**：
    - **3D 噪聲交集 (`generateCavesNoiseIntersection`)**：產生狹長且複雜的隧道網路。
    - **巨型地下洞穴 (`generateCavernsNoise`)**：生成寬廣的地下空間。
    - **隨機漫步洞穴 (`generateCavesRandomWalk`)**：模擬水流侵蝕的隨機洞穴。

## 階段 3：資源與結構點綴
地形與洞穴完成後，開始注入資源與預製結構：
1. **礦脈生成 (`MG_ORES`)**：
    - 交由 `OreManager` (`m_emerge->oremgr->placeAllOres`) 處理。根據設定的深度與機率，將部分岩石替換為煤礦、鐵礦等。
2. **地牢生成 (`MG_DUNGEONS`)**：
    - 在地底生成由鵝卵石與青苔石構成的隨機迷宮結構 (`generateDungeons`)。
3. **地表裝飾 (`MG_DECORATIONS`)**：
    - 交由 `DecorationManager` (`m_emerge->decomgr->placeAllDecos`) 處理。
    - 生成樹木、草叢、仙人掌等植物結構。

## 階段 4：物理與光照結算
在所有固體與結構都放置完畢後，進行最後的結算：
1. **粉塵覆蓋 (`dustTopNodes`)**：在表面鋪上一層薄薄的物質（如降雪）。
2. **流體更新 (`updateLiquid`)**：處理生成過程中被破壞或改變的水/岩漿的流動狀態。
3. **光照計算 (`calcLighting`)**：
    - 根據陽光直射與方塊透光率 (`paramtype = "light"`) 計算整個 Chunk 的光照陰影。
    - 這是整個生成過程中最耗費 CPU 資源的步驟之一。

## 結論
`MapgenV7` 展現了典型的**管線化 (Pipeline) 生成模式**：從底層拓樸、表層材質、內部掏空，一路到點綴與光照結算。這種嚴格的先後順序確保了樹木不會生成在半空中，且礦石不會覆蓋掉地牢的牆壁。
