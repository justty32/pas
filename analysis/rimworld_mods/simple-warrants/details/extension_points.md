# Simple Warrants 擴充接點（純 XML vs 必須 C#）

> 結論：懸賞「目標種類」是封閉 C# 階層（加新種類需 C#）；但風味資料、通緝理由、接單後的任務/地圖生成走純 XML（原版 QuestScript DSL），調平衡與擴內容多可零 C#。

## 純 XML vs 必須 C# 二分表

| 需求 | 純 XML？ | 接點 / 說明 |
|---|---|---|
| 加新的「通緝理由」風味文字 | ✅ 純 XML | `RulePackDef`（`Defs/RulePackDefs/WantedReasons.xml`），quest 描述用 `[reason]` 取 |
| 調懸賞任務的點數/獎勵文字/門檻 | ✅ 純 XML | 改 `Defs/QuestScriptDefs/Script_Warrant*.xml`（`rootMinPoints`、`questDescriptionRules`、`autoAccept`…） |
| 改接單後生成的目標營地/地點 | ✅ 純 XML | `Sites/*`＋`SitePartDef`（tag 如 `SW_Camp`），QuestScript 以 `QuestNode_GetSitePartDefsByTagsAndFaction` 按 tag 抓——加同 tag 的新 SitePart 即進池 |
| 用原版 QuestNode 重組懸賞任務流程 | ✅ 純 XML | QuestScriptDef 走 vanilla DSL（`QuestNode_Sequence`/`QuestNode_GetSiteTile`/`QuestNode_SubScript`…），僅一個自訂節點 `QuestNode_WarrantFailed` |
| 佈告欄出現位置 | ✅ 純 XML | `MainButtonDef`（`Defs/MainButtonDefs/MainButtons.xml`） |
| 賞金上限/頻率等平衡 | ✅（非 XML，設定 UI） | `SimpleWarrantsSettings`（`warrantRewardMax` 等），SimpleSettings 框架，玩家在設定調 |
| 加全新「懸賞目標種類」（如摧毀建築、運送物資） | ❌ C# | 須新增 `Warrant` 子類＋擴 `TargetType` enum＋`WarrantsManager` 生成/結算接線＋UI 繪製＋對應 QuestScriptDef |
| 改接單/結算/付款/送回領賞邏輯 | ❌ C# | `Warrant` 基類、`WarrantsManager`、`TransportersArrivalAction_ReturnWarrant` |
| 改「擊殺/被襲擊判定」行為 | ❌ C# | `HarmonyPatches/`（Pawn_Kill / Raid / JobGiver_AIFightEnemy 等） |
| 佈告欄 UI | ❌ C# | `MainTabWindow_Warrants`（695 行） |

## 最省力衍生（純 XML）

1. **擴充通緝理由庫**：往 `WantedReasons` RulePackDef 加 `[reason]` 候選句 → 懸賞描述更多樣，零 C#。
2. **加新目標營地風貌**：做一個帶 `SW_Camp` tag 的 `SitePartDef`（＋GenStep 沿用既有），接 pawn 懸賞時就可能抽到 → 純 XML。
3. **調平衡**：改 Script_Warrant* 的 `rootMinPoints`、獎勵文字、`autoAccept`。

## 對 Create 的意義

- Simple Warrants 是**「封閉核心＋資料化外圍」**的典型：核心懸賞型別與結算寫死 C#，但風味/任務/地點層用原版 QuestScript DSL 完全開放。
- 若衍生目標是「新一類懸賞玩法」→ 必須 fork C#（有 .sln 與完整源碼，門檻不高）。
- 若只是「更多懸賞理由/更多目標營地/調平衡」→ 純 XML。
- `SimpleSettings.cs` 是 Taranchuk 系 mod 通用的反射式設定框架，可單獨當參考。
