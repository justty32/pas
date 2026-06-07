# Rim War 擴充接點（extension_points）

> 為 create（擴充/衍生）盤點接點。分 **A 純資料（XML/設定，無需編譯）** 與 **B 改碼（C#/Harmony，需對 v1.6 編譯）**。行號指 `projects/rimworld_mods/rim-war/decompiled/RimWar.decompiled.cs`。前提：純 DLL 無源碼，B 類等於從外部寫獨立 patch DLL（Harmony）或 detour，風險高。

## A. 純資料接點（最省力，PatchOperation / 新 Def / 設定）

| 接點 | 怎麼做 | 影響 | 風險 |
|---|---|---|---|
| **派系行為傾向＋戰力係數** | 對 `RimWarDef RimWar_FactionBehavior`（`Defs/RimWarDefs/RimWarDef.xml`）用 `PatchOperationAdd/Replace` 改/增 `defDatas` 條目：`behavior`、`movementBonus`、`combatBonus`、`growthBonus`、`createsSettlements`、`hatesPlayer`、`movesAtNight` | 直接改 AI 派系的動作偏好與成長/戰鬥強度 | **低**。`GenerateFactionBehavior`（`:17731`）以 `factionDefname` 字串比對；新 mod 派系只要加一筆即被 Rim War 接管 |
| **新派系自動納入** | 任何 vanilla 風格 Faction 都會被 `AddRimWarFaction`（`:17696`）/`CheckForNewFactions`（`:17302`）自動建 `RimWarData`；無 RimWarDef 條目時走預設 behavior | 你的 mod 派系自動參戰 | 低。未在 XML 指定 behavior 則行為由預設邏輯決定（可能不理想）→ 建議補一筆 |
| **讓自訂聚落類型參戰** | 仿 `Patches/RimWarCompsx.xml`：把 `RimWar.Planet.WorldObjectCompProperties_RimWarSettlement` 用 `PatchOperationAdd` 注入你的 `WorldObjectDef[worldObjectClass=...]/comps`（已內建 Cities.City / FactionColonies 範例） | 自訂聚落獲得 RimWarPoints、可被攻佔/成長 | 中。需確認你的 WorldObjectClass 繼承 Settlement 行為；comp tick 假設是 Settlement |
| **戰鬥傷害** | `Defs/RimWarDefs/RW_Damages_Combat.xml`（DamageDef）可調 | 抽象戰/襲擊傷害數值 | 低 |
| **生態圈/科技乘數間接** | 無直接 XML，但 `GetBiomeMultiplier`/`GetFactionTechLevelMultiplier` 吃 vanilla BiomeDef/techLevel | 改派系 techLevel 會連動 `CanLaunch`（≥4）與成長/初始 points | 低（但屬改派系本體） |
| **模擬節奏/規模（玩家設定）** | 透過 `Settings`（`SettingsRef` 欄位）：`averageEventFrequency`、`rwdUpdateFrequency`、`settlementGrowthRate`、`maxFactionSettlements`、`settlementEventDelay`、`heatFrequency`、`useRimWarVictory`、`playerVS`、`createDiplomats`、`randomizeFactionBehavior`、`threadingEnabled` | 全域調快/慢、上限聚落數、勝利模式 | 低，但**屬玩家可調的 ModSettings，非 Def**，不能用 PatchOperation 預設（只能引導玩家或寫 patch 改預設值 `:7445+`） |
| **新信件/事件外觀** | `RW_Letters.xml` / `RW_HistoryEventDefs.xml` 可增 LetterDef/HistoryEventDef | 自訂事件呈現 | 低 |
| **新 WarObject 貼圖/圖示** | `RW_WorldObjects.xml` 的 `texture`/`expandingIconTexture` 可換；或新增 `WorldObjectDef` 指到既有 RimWar class | 視覺客製 | 低（不改邏輯） |

> A 類結論：**派系行為、戰力係數、哪些聚落參戰、模擬節奏幾乎全可資料化調整**，這是擴充最省力的路徑。

## B. 改碼接點（C# / Harmony，需對 v1.6 編譯，高風險）

> 全為硬編，要改必須寫獨立 Harmony patch DLL 攔截 Rim War 的方法（Rim War 自身無公開 API、無事件鉤）。

| 接點 | 目標 | 想擴充什麼 | 風險 |
|---|---|---|---|
| **新增 RimWarAction 類型** | enum `RimWarAction`（`:1082`）、`GetWeightedSettlementAction`（`:1688`）、`WorldComponentTick` 的 if-else 分派（`:17144`） | 加新世界動作（如「攻城器」「劫掠隊」） | **極高**。enum 與分派、機率歸一化（`:15980`）散落多處，需同時 transpile/prefix 多方法 |
| **新增 behavior 類型** | enum `RimWarBehavior`（`:1092`）+ 全檔 ~10 處 `behavior ==` 分支（`GenerateActionWeights` `:15987`、`GetEngagementRange` `:1718`、成長 `:17585`、戰鬥修正 `:11136`） | 自訂派系 AI 性格 | 極高，散布太廣 |
| **改戰鬥結算公式** | `IncidentUtility.ResolveRimWarBattle`（`:10274`）、聚落抽象戰（`:11130`+）、`ResolveRimWarTrade`（`:10350`） | 改勝負判定、捕獲機率、損耗 | 高。`static` 方法可 prefix/postfix，但內部用 `Rand.Value` 與多個私有欄位 |
| **改戰力公式** | `WorldUtility.Calculate*`（`:15840`–`:15913`）、`RimWarData.PointsFrom*`（`:1333`+）、成長 `IncrementSettlementGrowth`（`:17567`） | 換算法、加新 points 來源 | 中高。Calculate* 是 `public static`，相對好攔 |
| **改易主行為** | `WorldUtility.ConvertSettlement`（`:15289`） | 佔領時保留建物/改派系/觸發劇情 | 中。`public static`，prefix 可改參數或 skip |
| **改玩家互動選項** | `FactionDialogReMaker`（`:2530`）、`CommsConsole_RimWarOptions_Patch`（`:5876`） | 新增通訊台請求類型 | 中。本身就是 patch，可再 postfix 它的 `__result.options` |
| **玩家面板擴充** | `MainTabWindow_RimWar`（`:688`） | 新分頁/資訊 | 中。可 Harmony 加分頁，但 UI 私有欄位多 |
| **掛勾模擬 tick** | `WorldComponent_PowerTracker.WorldComponentTick`（`:17030`） | 在每次評估前後插自訂邏輯 | 中。postfix 可讀 `RimWarData` 公開 list（`RimWarData`/`AllWarObjects` 有 public getter） |

### B 類可利用的公開面（降低風險的著力點）
- `WorldComponent_PowerTracker` 的 `RimWarData`（list）、`AllWarObjects`、`AllRimWarSettlements`、`WorldObjects` 皆 **public getter** → 外部 mod 可讀取整盤戰局狀態做 UI/統計，不需反射。
- `RimWarData` 的戰力 getter、`WorldSettlements`、`WarFactions`/`AllianceFactions`、`GetCapitol`、`TotalFactionPoints` 皆 public。
- `WorldUtility.Create*` / `Calculate*` / `ConvertSettlement` 皆 `public static` → 衍生 mod 可**直接呼叫**生成自己的 WarObject 或觸發易主（最乾淨的程式化擴充方式）。
- `RimWarSettlementComp.RimWarPoints` 有 public setter → 可程式調整任一聚落戰力。

## 建議的擴充策略（依省力排序）
1. **純 XML**：增/改 `RimWarDef.xml` 派系條目 + 用 `RimWarCompsx` 風格 patch 把自訂聚落納管 → 不寫一行 C#，即可讓新派系/聚落完整參戰。
2. **薄 C# 呼叫層**：寫一個小 mod，透過 `WorldComponent_PowerTracker` 的 public getter 讀盤、用 `WorldUtility.Create*`/`ConvertSettlement` 主動製造事件（劇情、任務、自訂勢力行動），**不攔截 Rim War 內部**。
3. **Harmony patch**：僅在需要改判定公式/新動作時才動，且優先 postfix `public static` 方法。
4. 避免動 enum / behavior 分支（散布過廣，維護成本高）。

## 待驗證
- B 類所有「可 prefix/postfix」假設未實機驗證（純讀反編譯）。
- `WorldObjectCompProperties_RimWarSettlement` 注入非 Settlement 子類時的相容性未驗證。
- 設定預設值若用 patch 改 `Settings` 預設（`:7445+`）是否安全，未驗證。
