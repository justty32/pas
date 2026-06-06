# `Outposts.OutpostExtension` 完整欄位參照

> 逆推自 `projects/rimworld_mods/vanilla-outposts-expanded/decompiled-framework/Outposts.decompiled.cs:2014`（`OutpostExtension : DefModExtension`）
> 標 `[Setting]` 者可被玩家在 mod 設定覆寫（`PostToSetings` 屬性）。

## OutpostExtension
| XML 欄位 | C# 型別 | 預設 | 說明 |
|---|---|---|---|
| `AllowedBiomes` | `List<BiomeDef>` | 空 | 只允許這些生態域建立（白名單） |
| `DisallowedBiomes` | `List<BiomeDef>` | 空 | 禁止這些生態域（黑名單） |
| `CostToMake` | `List<ThingDefCountClass>` | 空 | 建立時消耗的物資（`:2018`，扣除邏輯 `:1062`） |
| `DisplaySkills` | `List<SkillDef>` | 空 | UI 顯示的相關技能（不影響產量，僅資訊/排序） |
| `Event` | `HistoryEventDef` | null | pawn 加入此 outpost 時觸發的 ideology 歷史事件 |
| `MinPawns` `[Setting 1–10]` | `int` | 0 | 建立/維持所需最少入駐 pawn |
| `ProvidedFood` | `ThingDef` | `MealSimple` | 餵養在營 pawn 的食物（`Outpost.ProvidedFood`，`:90`） |
| `Range` `[Setting 1–30]` | `int` | -1 | 作用半徑（服務型用，如砲擊/防禦，-1＝不適用） |
| `RequiredSkills` | `List<AmountBySkill>` | 空 | 建立門檻：某技能需達指定等級 |
| `RequiresGrowing` | `bool` | false | 需可耕作條件（季節/地形） |
| `ResultOptions` | `List<ResultOption>` | 空 | **每生產週期產出的物品清單（核心）** |
| `TicksPerProduction` `[Setting Time]` | `int` | 900000 | 生產週期 tick；**-1＝關閉預設生產**（服務型用 C# 自理） |
| `TicksToPack` `[Setting Time]` | `int` | 420000 | 拔營打包耗時；實際 `/occupants.Count`（`:781`） |
| `TicksToSetUp` | `int` | -1 | 建立後到開始運作的延遲（-1＝立即） |

> 衍生屬性 `RelevantSkills`（`:2040`）＝ `RequiredSkills ∪ ResultOptions 內所有技能 ∪ DisplaySkills`。用於判定哪些 pawn「有能力」入駐（`IsCapable`，`:1926`）。

## OutpostExtension_Choose（`:2574`，繼承上者）
| XML 欄位 | 型別 | 說明 |
|---|---|---|
| `ChooseLabel` | `string` | 「選產出」按鈕標籤，可含 `{0}` 佔位（顯示目前選擇） |
| `ChooseDesc` | `string` | 該按鈕的 tooltip |
> 搭配 `worldObjectClass="Outposts.Outpost_ChooseResult"` 使用。

## ResultOption（`:2050`）— 單一產出項
| XML 欄位 | C# 型別 | 說明 |
|---|---|---|
| `Thing` | `ThingDef` | 產出的物品 |
| `BaseAmount` | `int` | 固定基底量 |
| `AmountPerPawn` | `int` | 每位在營 pawn 追加量 |
| `AmountsPerSkills` | `List<AmountBySkill>` | 每技能：`Count × 全員該技能等級總和` |
| `MinSkills` | `List<AmountBySkill>` | 低於此門檻則此項**不產**（用於高階產物分級） |

**產量** `Amount(pawns)`（`:2058`）：
```
RoundToInt( (BaseAmount + AmountPerPawn*pawns.Count
            + Σ AmountsPerSkills.Amount) * Settings.ProductionMultiplier )
```

## AmountBySkill（`:2079`，自訂 XML 載入）
寫法是「技能名當 node 名、值當數量」，例：
```xml
<RequiredSkills>
  <Plants>10</Plants>     <!-- Skill=Plants, Count=10 -->
</RequiredSkills>
```
`Amount(pawns)`（`:2095`）＝ `Count × Σ pawns 該技能等級`。每個 `<RequiredSkills>`/`<AmountsPerSkills>`/`<MinSkills>` 內**只能有一個子節點**，否則框架報 `Misconfigured AmountBySkill`（`:2087`）。

## DeliveryMethod enum（`:2466`）
`Teleport` / `PackAnimal` / `Store` / `ForcePods` / `PackOrPods`。非單一 def 欄位，由 mod 設定與 outpost 實例狀態決定配送方式（`Deliver`，`:1409`）。
