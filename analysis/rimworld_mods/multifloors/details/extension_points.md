# MultiFloors 擴充接點（純 XML vs 必須 C#）

> 技術型大 mod，引擎全在 C#。但兩個面向對下游友善：①新星球層支援、②新樓梯／電梯建築外觀，多可純 XML。

## 純 XML vs 必須 C# 二分表

| 需求 | 純 XML？ | 接點 / 說明 |
|---|---|---|
| 支援新星球層 mod 的上層地形/生成 | ✅ 純 XML | `MultiFloors.UpperLevelSettingsDef` 加一組 `layers`(PlanetLayerDef)+`settings`(mapGenerator/defaultTerrain/deckTerrain/voidTerrain) 配對，用 `MayRequire` gate |
| 新地基/虛空地形 | ✅ 純 XML | `TerrainDefs/`（如 `MF_SurfaceVoid`）；新 MapGeneratorDef（`MapGeneration/`） |
| 新「外觀變體」樓梯／電梯 | ✅ 純 XML | 新 `ThingDef`（建築），`thingClass` 沿用既有 `MultiFloors.StairEntrance`/`StairExit`/`WoodenElevator`/`ModernElevator`/`FreightElevator`，掛 `StairsModExtension` 設 `stairsSettings`(isUpstairs/upstairsEntranceDef/downstairsEntranceDef/connectedToExitDef) 或 `elevatorSettings`，再配 graphic/cost/research |
| 教學頁 | ✅ 純 XML | `MultiFloors.TutorDef`（`TutorDefs/`） |
| 跨層傳輸/輸電「行為」 | ❌ C# | `TransferPolicy`/`AutoTransferWorker`/`ITab_PowerTransmission` 邏輯寫死 |
| 樓層＝PocketMap 的生成/堆疊/存讀 | ❌ C# | `MF_*MapComp`、`MultiFloorManager`、PocketMap 整合全硬編 |
| 全新樓梯／電梯**機制**（非外觀） | ❌ C# | 須新 `Stair`/`Elevator` 子類（C#），因傳送邏輯在類別內 |
| 與某第三方 mod 跨樓層相容 | ❌ C#（gated 子模組） | 仿 `1.6/ModCompat/<mod>/`：寫一個 compat DLL，LoadFolders `IfModActive` 條件載入。已有 9 例（PRF/Vehicle/Dubs×2/VEF/Rimefeller/ResearchReinvented/Hospitality/SmarterConstruction）可照抄 |
| 在原版型別上掛新欄位 | ❌ C#（Prepatcher） | `PrepatcherFields:5704`——本 mod 用 Prepatcher 注入欄位，非一般 mod 技巧 |

## StairsModExtension 結構（純 XML 可填）

```
StairsModExtension
├─ stairsSettings (StairsSettings)
│   ├─ isUpstairs (bool)                上樓還下樓
│   ├─ connectedToExitDef (ThingDef)    對應出口建築
│   ├─ upstairsEntranceDef / downstairsEntranceDef (ThingDef)
│   ├─ oppositeRotWithEntrance (bool)
│   └─ useSelfGraphicData (bool)
└─ elevatorSettings (ElevatorSettings)  電梯專用
```

## 結論導向

- **最划算純 XML 衍生**：①為某個新「星球層／天空島」mod 加一條 `UpperLevelSettingsDef` 支援；②做一套新美術風格的樓梯/電梯建築（沿用既有 thingClass + `StairsModExtension`）。
- **要動樓層生成、傳輸、或加全新通行機制 → C#**，且涉及 PocketMap/MapPortal 與 Prepatcher，門檻高。
- **跨第三方 mod 相容 → 照抄 ModCompat 的 gated DLL 模式**（本 mod 是這套模式的優良範本，已 9 例）。
