# 城市地圖程序生成流程（核心子系統）

> 主檔：`projects/rimworld_mods/rimcities/decompiled/RimCities.decompiled.cs`
> 主 XML：`1.6/Defs/MapGeneration.xml`、`1.6/Defs/MapGeneration_Citadel.xml`

這是 RimCities 最核心也最值得做衍生的子系統。要回答的問題：**城市地圖是程序化（演算法）還是資料驅動（佈局）？** 答案：**程序化演算法為主幹，XML 提供「該放什麼/多少/多大」的參數，但沒有逐格佈局藍圖。**

## 一、觸發與前置（Harmony 接管 mapSize 與派系）

城市 WorldObject 進入時走原版 `MapGenerator.GenerateMap`，但被 Harmony Prefix 攔截：

- `MapGenerator_GenerateMap.Prefix`（`:2172`）：若 `parent is City`，呼叫 `city.ChooseMapSize(mapSize)` 改地圖尺寸，並掛 `city.PreMapGenerate(map)` 到 `extraInitBeforeContentGen`。
  - `City.ChooseMapSize`（`:5622`）：若 `Config_Cities.customCitySize` 為真，用 `citySizeScale`（預設 200×200）。
  - `Citadel.ChooseMapSize`（`:5437`）：硬寫 `120×625`（狹長攻城走廊）。
  - `City.PreMapGenerate`（`:5592`）：把地圖派系設成 `inhabitantFaction`（廢墟則隨機選一個敵對派系）。

之後執行 `MapGeneratorDef.genSteps` 清單（XML 定義，見下）。

## 二、genStep 管線（XML 定義順序，C# 實作邏輯）

`MapGeneration.xml` 用抽象繼承組裝管線：`Cities_MapCommonBase`（原版地形步驟）→ `Cities_Base`（城市步驟）→ 各 `City_*` 具體 def 追加差異步驟。城市核心步驟順序：

| order | GenStepDef | C# class | 職責 |
|---|---|---|---|
| 250 | City_Walls | `GenStep_Walls` (`:1728`) | 外圍城牆 + 城門 |
| 251 | City_Streets | `GenStep_Streets` (`:1596`) | 主幹道 + 側路網（核心街道演算法） |
| 260 | City_Docks | `GenStep_Docks` (`:1254`) | 水邊碼頭/橋 |
| 270 | City_Bazaars | `GenStep_Bazaars` (`:974`) | 露天市集（攤位+貨物） |
| 301-303 | City_Prison/Hospital/Freezer | `GenStep_Buildings` (`:1026`) | 固定數量功能建築（用不同 roomDecorators） |
| 310-311 | City_ProductionBuildings/MainBuildings/Houses | `GenStep_Buildings` | 按密度散佈的一般建築 |
| 312 | City_ThingGroups | `GenStep_ThingGroups` (`:1670`) | 太陽能陣列/墓園/發射台等成組物件 |
| 313 | City_Emplacements | `GenStep_Emplacements` (`:1282`) | 砲塔/迫擊砲工事 |
| 320-321 | City_Fields/Orchards | `GenStep_Fields` (`:1362`) | 農田/果園 |
| 330 | City_Sidewalks | `GenStep_Sidewalks` (`:1558`) | 人行道 |
| 690 | City_Post | `GenStep_Post` (`:1423`) | 收尾：清屋頂外物件的屋頂、清散落銀 |
| 691 | City_Abandoned_Post 等 | `GenStep_Abandoned/Ghost/Compromised_Post` | 廢墟衰變/鬼城/幫派化後處理 |

> 注意：**居民生成不是獨立 genStep**，而是散落在各 `RoomDecorator`（如 `RoomDecorator_Bedroom.Decorate` `:179` 呼叫 `GenCity.SpawnInhabitant`）以及攻城/任務邏輯中。

## 三、Stencil —— 佈局 DSL（演算法的真正核心）

所有 genStep 的幾何操作都建立在 `Stencil` struct（`:4796`）上。它是一個帶「位置 `pos` + 旋轉 `rot` + 邊界 `bounds`」的游標，提供鏈式 API：

- 移動/旋轉：`Move / MoveTo / Rotate / RotateRand / Left / Right / Center`
- 邊界：`Bound / Expand / BoundTo / ExpandRegion`（`ExpandRegion` 是 flood-fill 找連通可用區域，建築選址用）
- 寫地圖：`SetTerrain / FillTerrain / BorderTerrain / Spawn / Fill / ClearThingsInBounds / FillRoof / ClearRoof`
- 隨機：`RandX / RandZ / Chance / RandInclusive`

例：`GenStep_Streets.GenMainRoad`（`:1633`）就是在 Stencil 上鋪人行道→鋪路面→架橋→隔島→以 `roadSpacing` 間隔遞迴生側路。這是**演算法**，不是讀佈局表。

`GenStep_Buildings.GenRooms`（`:1079`）是建築內部佈局的核心：**遞迴二分切房間**（BSP 式）——若面積 > 選中 roomDecorator 的 `maxArea`，就沿長邊切一刀（依 `wallChance` 決定是否築牆+門），遞迴；否則停下鋪地、加燈、呼叫 `roomDecorator.Decorate(s)` 填內容。

## 四、選址：GenStep_RectScatterer

大多數建築 genStep 繼承 `GenStep_RectScatterer`（`:1447`）。選址邏輯：

- `GetStencil`（`:1519`）：從候選格用 `ExpandRegion(IsValidTile, areaConstraints.max)` 長出一塊連通矩形區域，檢查 `areaConstraints.min` 與長寬比 `maxRatio`，通過才回傳。
- `IsValidTile` 預設只認「自然地形（排除岩石）」(`TerrainUtility.IsNaturalExcludingRock`)，所以建築會避開已鋪的街道。
- 子類只需實作 `GenerateRect(Stencil s)`。

## 五、資料驅動 vs 演算法的界線（重點）

| 由 XML 控制（資料驅動的部分） | 由 C# 控制（寫死的演算法） |
|---|---|
| 管線中**有哪些步驟、順序**（MapGeneratorDef.genSteps） | 每個步驟**怎麼擺**（街道遞迴、房間 BSP 切分、選址 flood-fill） |
| 各步驟**數量/密度**（`count`、`countPer10kCellsRange`） | Stencil 幾何運算與隨機決策 |
| 建築**面積/長寬比**（`areaConstraints`、`maxRatio`） | `GenRooms` 切房規則、牆/門生成規則 |
| 房間**裝飾器組合與權重**（`roomDecorators` + `weight`/`maxArea`） | 每種 RoomDecorator 的擺放邏輯 |
| 傢俱/砲塔/作物**候選清單**（`options`、`floorOptions`、`excludePlants`、`weaponDef`…） | 物件擺放座標、品質指派(`GenCity.AssignQuality`) |
| 街道/人行道**地形候選**（`roadTerrains`、`sidewalkTerrains`、`divTerrains`） | 道路網拓樸 |
| 工事**武器/彈藥/是否有頂**（EmplacementOption） | 工事擺放 |

**結論**：城市生成是 **資料驅動參數化的程序生成**。你能用純 XML 大幅改變「城市長什麼樣」（更多砲塔、不同傢俱、更大建築、改密度、換地形），但**新的擺放規則或新的建築結構**必須寫 C# `GenStep` / `Decorator`。
