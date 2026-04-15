# 模塊分析：17_world_generation_mechanism (世界生成機制深度分析)

OpenStarbound 的世界生成是一個典型的 **分層過程生成 (Layered Procedural Generation)** 系統。它將複雜的地形、地質與結構拆分為多個獨立的生成階段。

## 1. 生成流水線的核心：WorldTemplate
生成的起點是 `WorldTemplate`。它根據 `WorldSeed` 定義了星球的全局屬性：
- **尺寸與拓撲：** 定義世界寬高與 Wrapping 屬性。
- **重力與威脅等級：** 影響模擬物理與生成怪物的強度。
- **主生物群落 (Main Biome) 與次生物群落：** 決定了地形生成器的基本配置。

## 2. 地形生成器 (Terrain Selectors)
引擎在 `source/game/terrain/` 中實現了一系列基於函數組合的選擇器（Selectors），用於計算任意點 $(x, y)$ 的材質密度。
- **PerlinSelector：** 使用分型柏林噪聲生成起伏的山脈。
- **WormCave / KarstCave：** 使用 3D 噪聲或隨機遊走算法生成蜿蜒的洞穴系統。
- **DisplacementSelector：** 對基礎地形進行擾動，增加視覺上的不規則感。
- **Max/Min/Mix Selectors：** 允許將多個地形特徵（如平原與高山）通過數學運算進行無縫融合。

## 3. 生物群落佈置 (Biome Placement)
生物群落不僅決定了地表的顏色，還決定了材質的組成與背景景觀。
- **分層映射：** 星球被劃分為多個垂直層（如 Space, Atmosphere, Surface, Subsurface, Underground, Core）。
- **水平分布：** 在同一層內，系統會根據種子計算出不同生物群落的邊界，並通過過渡函數進行材質混合。

## 4. 地牢與結構生成 (Dungeon Generation)
這是系統中最複雜的部分。地牢生成器（`DungeonGenerator`）負責將預定義的靜態或隨機結構嵌入到動態生成的地形中。
- **DungeonDefinition：** 基於 JSON 的規則集，定義了房間、走廊、物件分佈與接線邏輯。
- **Facade 模式：** `DungeonGeneratorWorldFacade` 提供了一個抽象接口，允許地牢生成器在不直接操作 `WorldServer` 的情況下，安全地修改瓦片、放置物件與生成 NPC。
- **地形標記 (Marking)：** 地牢生成時會「標記」區域，防止普通的地形生成算法覆蓋地牢結構，並確保地牢入口與地表平滑連接。

## 5. 植被與微觀結構 (Plants & Micro-Dungeons)
在地形成型後，系統執行最後的裝飾階段：
- **植物生成 (PlantDatabase)：** 根據生物群落配置，在適當的土壤瓦片上隨機生成樹木、草叢與作物。
- **微型地牢：** 散佈在世界各地的小型隨機物件組合（如露營火堆、箱子），用於增加探索的細節。

## 6. 初始化模擬 (Initial Simulation)
在世界對外開放前，會進行一次初步模擬：
- **流體填充：** 確保海洋、湖泊與熔岩池在初始時具有正確的壓力與水位。
- **實體生成 (Spawner)：** 在指定的區域生成初始的怪物與動物。
- **物理演化：** 處理初始時不穩定的方塊掉落（如碎石砂礫）。
