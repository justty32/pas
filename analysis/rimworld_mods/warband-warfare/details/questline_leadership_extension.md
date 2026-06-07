# Questline / Leadership 兩個擴充 DLL 的「純 XML vs 必須 C#」與擴充接點

> 供核心 agent 的 `details/extension_points.md` 收錄。涵蓋 `WarbandWarfareQuestline.dll` 與 `WAWLeadership.dll`。
> 源碼位置同 `architecture/02_questline_and_leadership.md`。

## 一、可純 XML 擴充的接點

| 接點 | Def 類別 | 來源行 | 純 XML 能做什麼 | 範例 XML 位置 |
|---|---|---|---|---|
| **政策（資料部分）** | `WarbandWarfareQuestline.League.Policies.PolicyDef`（`:2354`） | — | 新增政策節點：`prerequisite`(接到既有樹)、`category`(Economy/Warfare)、`taxBonus`、`cost`、`equipmentBudgetLimitOffset`。`PolicyTree.Refresh()`(`:2437`) 自動從 DefDatabase 讀並建樹，**不改 C#** | `Defs/Policies/PolicyDefs.xml` |
| **政策分類** | `PolicyCategoryDef`（`:2351`，空 Def） | — | 新增政策分類（但派系 trait 的 `dislikedCategory` 才有投票意義；新分類沒派系討厭就無投票阻力） | `Defs/Policies/PolicyCategoryDefs.xml` |
| **派系特質** | `WarbandWarfareQuestline.FactionTraitDef`（`:54`） | — | 新增小派系特質：`commonality`、`supplyBonus`、`dislikedCategory`、`hatedTrait`。`GenerateRandomMinorFaction`(`:3140`) 用 `GetRandom()` 隨機抽，**純 XML 即生效** | `Defs/FactoinTraitDefs/TraitDefs.xml` |

### 純 XML 的限制 / 陷阱
- `FactionTraitDef.commonality` 存在，但 `DefDatabase.GetRandom()` 是**均勻隨機**，不讀 commonality 權重。
- `FactionTraitDef.supplyBonus` 在反編譯碼內**未見被讀取**（疑死欄位）。
- `FactionTraitDefOf.WAW_Cautious`(`:64`) 與 `PolicyDefOf.{TaxReform,TradeAgreement,ResourceOptimization}`(`:2404`) 是 `[DefOf]` 硬引用，**這些 defName 不可改名/刪除**，否則核心反射綁定報錯。
- `QuestScriptDef WAW_SaveVillage` 是**空殼**，純 XML **無法**用標準 QuestNode DSL 擴充救援村莊任務（見下）。

## 二、必須寫 C# 的接點

| 想做的事 | 為何必須 C# | 關鍵型別/行 |
|---|---|---|
| **新的救援村莊類任務** | 任務不是 QuestScriptDef DSL，而是 `Quests.GiveVillageQuest()`(`:115`) 手動 `new Quest` + `AddPart` 三個自訂 QuestPart 硬編；`WAW_SaveVillage` 只當佔位 `root` def 引用 | `Quests`(`:87`)、`QuestPart_VillageLooted`(`:162`)、`Reward_MinorFactionJoin`(`:281`) |
| **政策的特殊副作用** | `taxBonus/cost` 等純數值欄位可 XML，但任何「解鎖功能/改遊戲狀態」都要寫 `PolicyWorker` 子類別並在 XML 用 `<workerClass>` 指定 | `PolicyWorker`(`:2523`) 及其 8 個子類別(`:2541`–`:2633`) |
| **新領導力屬性** | 六種屬性是 `AttributeSet.InitAttributes()`(`:1958`) 寫死的六個 `new`，**無 Def、無註冊表**；新增屬性必須改這份 C# + 新增 `LeadershipAttribute` 子類別 | `LeadershipAttribute`(`:754`)、各 `Attribute_*`(`:2052`+) |
| **改屬性曲線/上限** | `maxLevel=3`(`:758`)、`SkillBonusCurve`、各屬性 `*Curve()` 全部硬編在方法內，無 XML | 同上 |
| **新的世界地圖指揮官互動** | `InteractionUtility.TryToInteract`(`:397`) 用 `switch (GetType().Name)` 硬編目標型別分派，門檻 `ValidateLeader<T>` 寫死 | `InteractionUtility`(`:393`) |
| **新 warband 升級項** | `Window_UpgradeWarband` 的五個升級是 `new` 出來的清單(`:1730`)，門檻 `switch` 硬編(`:1841`)（升級型別本身屬核心 DLL） | `Window_UpgradeWarband`(`:1645`) |
| **交易價格改動** | 走 Harmony patch | `HarmonyPatches_League`(`:452`) |

## 三、給冷啟動 agent 的一句話結論
- **Questline**：劇情/任務是**硬編 C#**（QuestScriptDef 是空殼，不可純 XML 擴任務）；但**政策樹與派系特質是真資料驅動**，加數值型政策/特質可純 XML，加新行為要寫 `PolicyWorker` 子類別。
- **Leadership**：**完全 C# 硬編，零 Def**——屬性、曲線、互動、UI 全寫死，任何擴充都要改 C#。
