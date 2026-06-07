# Faction Territories 擴充接點（純 XML vs 必須 C#）

> 結論：這是**重 C# mod**。可純 XML 擴充的只有兩處 Def 系統；領土演算法、附庸、入侵、建城建路全鎖在 C#。

## 純 XML vs 必須 C# 二分表

| 需求 | 純 XML？ | 接點 / 說明 |
|---|---|---|
| 新增「領土感知商隊事件」 | ✅ 純 XML | `FactionTerritories.CaravanIncidentEntryDef`（`Def` 子類，`:55`）。把任一 `IncidentDef` 對應到關係/科技旗標＋權重，商隊穿越某派領土時依旗標抽事件 |
| 調整商隊事件權重 / 條件 | ✅ 純 XML | 改既有 `CaravanIncidentEntryDef` 的 `defaultWeight` / `orFlags` / `andFlags`（見下旗標表） |
| 領土地圖模式的繪製參數 | ✅ 純 XML | `Defs/Regions.xml` 的 `MapModeFramework.MapModeDef`（含 `RegionProperties.doBorders/borderWidth`、`displayLabels`、`canCache`…）——屬 Map Mode Framework 的 Def |
| 新增入侵 / 建城 / 藩屬前哨「物件種類」 | ⚠️ 半 | `WorldObjectDef`（`Invasions.xml` / `VassalOutposts.xml`）可純 XML 加新 def，但 `worldObjectClass` 指向的行為類別在本 mod C# 內，新行為需寫 C# |
| 領土計算規則（半徑/權重/錨點/爭議） | ❌ C# | `TerritoryOwnershipCache:4384`、`FactionTerritoriesUtility` 的 `TileBaseMovementDifficulty/RoadMultiplier/HillinessMovementDifficultyOffset`——數值含義寫死，僅部分經 `FactionTerritoriesSettings` 暴露給玩家設定 UI（非 def） |
| 派系顏色 / 遭遇 / 科技倍率 | ❌ C#（玩家設定） | `FactionColorOverride:4296` / `FactionEncounterOverride:4312` / `TechLevelMultiplier:4327` 是 `IExposable` 存檔設定，由 `Dialog_FactionTerritoryColor:284` 在遊戲內調，**不是 def、無法靠 mod XML 預設** |
| 附庸化 / 割讓 / 藩屬點數規則 | ❌ C# | `VassaliseUtility:10628`、`VassalagePointsComponent:8496` 全硬編 |
| 強制伏擊派系 / 改 raid 派系挑選 | ❌ C# | `Patch_FactionManager_RandomEnemyFaction_ForceAmbushFaction:604` 等一組 Harmony patch |

## CaravanIncidentEntryDef 旗標表（純 XML 可填）

`orFlags`（命中任一即符合）/ `andFlags`（須全部符合），值取自 `CaravanIncidentFilterFlag`（`:39`）：

- 關係：`Hostile` / `Neutral` / `NeutralAndAllied` / `Allied` / `Royalty`
- 生物：`Animal`
- 科技等級：`Neolithic` / `Medieval` / `Industrial` / `Spacer` / `Ultra` / `Archotech`

範例（`Defs/CaravanIncidents.xml`）：`Ambush` 設 `orFlags=[Hostile]` 權重 15；`CaravanMeeting` 設 `orFlags=[Neolithic,Medieval,Industrial]` 權重 10。

### 最省力衍生：純 XML 加一條領土事件

```xml
<FactionTerritories.CaravanIncidentEntryDef>
  <defName>MyTraderInAlliedLand</defName>
  <incident>TraderCaravanArrival</incident>   <!-- 任一既有/自製 IncidentDef -->
  <defaultWeight>12</defaultWeight>
  <orFlags><li>Allied</li></orFlags>           <!-- 穿越盟友領土時較易遇到 -->
</FactionTerritories.CaravanIncidentEntryDef>
```

## 結論導向

- **想做 data-driven 衍生 → 只有「商隊穿越領土時的事件表」這條路純 XML 可行**（搭配自製 `IncidentDef`/`IncidentWorker`，後者若要全新效果仍需 C#）。
- **想動領土邊界演算法、附庸外交、入侵/建城 → 必須改 C#**（且 fork 本 mod）；多數玩家可調項已開在遊戲內設定 UI（`FactionTerritoriesSettings`），不需改碼。
- 繪製外觀（邊框寬/標籤/顏色透明度）部分經 `MapModeDef` 純 XML、部分經設定 UI。
