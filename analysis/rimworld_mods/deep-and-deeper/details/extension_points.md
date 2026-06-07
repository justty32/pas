# Deep And Deeper 擴充接點（純 XML vs 必須 C#）

> 結論：洞窟層的「組成與調校」高度資料驅動，純 XML 能做很多；只有「全新洞窟機制/興趣點類型」才需 C#。

## 純 XML vs 必須 C# 二分表

| 需求 | 純 XML？ | 接點 / 說明 |
|---|---|---|
| 新增一層洞窟 / 重排既有層內容 | ✅ 純 XML | 新 `MapGeneratorDef`（`ParentName="ShashlichnikUndergroundBase"`），`genSteps` 列要跑的 `GenStepDef` |
| 調某層的礦量/獎勵/危險強度 | ✅ 純 XML | 改 `GenStepDef` 餵給 worker 的參數：`mineableModifier`、`reward`/`countOfRewards`、`countChances`、`MinDistApart`、`mutant` 等 |
| 用既有興趣點類型佈置（屍堆/蟲巢/菌/變異體/低溫艙…） | ✅ 純 XML | `GenStepDef` 指 `genStep Class="Shashlichnik.GenStep_CaveInterest_*"`，DLC 內容用 `MayRequire` gate |
| 洞窟入口 Site | ✅ 純 XML | `SitePartDef` + `GenStepDef`（`linkWithSite`），見 `Defs/Sites/Sites.xml` |
| Deep Diver 兵種 / 地下物品 / 建築 | ✅ 純 XML | `PawnKindDef`（`PawnKind_DeepDiver`）、`ThingDefs_Items`、`ThingDefs_Buildings` |
| 讓建築能穩定洞窟（延緩崩塌） | ✅ 純 XML | 在 ThingDef 掛 `DefModExtension_CaveStabilizer`（`effectiveRadius`，預設 4.9） |
| 全新「興趣點類型」 | ❌ C# | 須繼承 `GenStep_CaveInterest`（抽象）寫新 worker，再用 GenStepDef 掛上 |
| 進出洞窟/崩塌/挖掘 AI 機制 | ❌ C# | `CaveEntrance:MapPortal`、`CaveMapComponent`、`JobDriver_Dig`、`JobGiver_*` 全硬編 |
| 洞窟基底地形演算法 | ❌ C# | `GenStep_Caves`/`GenStep_UndergroundLakes`/`GenStep_RocksFromGrid`（參數可 XML 調，演算法 C#） |

## 最省力衍生（純 XML）

1. **加新主題洞窟層**：複製 `CaveMapGeneratorLvl2.xml`，換 `genSteps` 組合（例如全菌類＋多寶箱的「蘑菇林層」），調 reward。
2. **改危險曲線**：調各 `GenStep_CaveInterest_*` 的 `countChances`（出現數量機率分佈）。
3. **接其他內容 mod 的怪**：若想塞別 mod 的生物進洞窟，多半要新 worker（C#）；但若該怪是 vanilla `mutant`/`pawnKind`，可直接餵既有 worker 的參數（純 XML）。

## 與本群組其他 mod 的關係

- **PocketMap/MapPortal 家族第三例**（前有 MultiFloors 樓層、RV-with-PD/SimplePortal）。三者都用原版口袋地圖＋傳送門做「另一個地圖空間」，做相容或衍生時可互相參照進出地圖的 patch 慣例。
