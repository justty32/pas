# CQF：流民商隊的償還（cqf-caravan-redemption）

## 衍生目標
在 **Custom Quest Framework（CQF，`HaiLuan.CustomQuestFramework`）** 基礎上，做一個**最小可行**的純 XML 子 mod，唯一目的是**證明「CQF 純 XML 自訂任務真的能被 RimWorld 載入並觸發」**。內容刻意保持最小，「能不能跑起來」優先於豐富度。

## 任務本體（做了什麼）
一個 `QuestScriptDef`（defName `CQFCaravanRedemption`），`root` 為原版 `QuestNode_Sequence`，依序三個節點：

1. **CQF 證明點** — `QuestEditor_Library.QuestNode_DoCQFActions`（`inSignal` 留空＝吃任務 initiate 信號、生成時立即執行），裝兩個 CQFAction：
   - `QuestEditor_Library.CQFAction_Message`：跳一則「流民商隊的償還」開場白（走翻譯 key `CQF_CaravanRedemption_OpeningMessage`，`type=PositiveEvent`）。
   - `QuestEditor_Library.CQFAction_SentSignal`：發信號 `CaravanArrived`（`addQuestPrefix=true`），純示範 CQF 信號總線可被觸發。
2. **生成獎勵** — 原版 `QuestNode_GenerateThingSet`，引用本 mod 的 `ThingSetMakerDef`（`CQFCaravanRedemption_RewardSilver`，`ThingSetMaker_StackCount` 固定 `Silver` `200~400`），存進 slate 變數 `cqfCaravanRewardThings`。
3. **發放獎勵** — 原版 `QuestNode_DropPods`，`contents=$cqfCaravanRewardThings`，投放白銀到殖民地並寄標準信件。

### 獎勵為何走原版節點（取捨說明）
CQF 的 `CQFAction_Spawn`（`decompiled.cs:1473`）的 `RealWork` 會遍歷傳入的 `targets` 找有效地圖格才生成；但 `QuestPart_DoCQFActions.Notify_QuestSignalReceived`（`decompiled.cs:32827`）呼叫 `action.Work(new Dictionary<>(), quest)` **傳入空 targets**，任務生成階段沒有 `Position`/地圖目標，故 `CQFAction_Spawn` 在此情境下不會生成任何東西。
另外 `QuestNode_DropPods.contents` 是 `SlateRef<IEnumerable<Thing>>`，而 `SlateRef<T>` 內部只存字串（`Assembly-CSharp` 反組譯確認），**不能在 XML 直接寫字面 `<li>` 清單**，必須由 slate 變數提供——這正是中間插入 `QuestNode_GenerateThingSet` 的原因。
因此採「CQFAction 只負責跳訊息/發信號，獎勵交給原版 `GenerateThingSet → DropPods`」，以**最穩定可載入**為最高原則。此模式直接抄自原版 `Core/Defs/QuestScriptDefs/Scripts_Utility_RewardsCore.xml`。

## 參照素材（權威來源）
- 教學：`analysis/rimworld_mods/custom-quest-framework/tutorial/01_add_custom_quest.md`（路徑 A）。
- 作者一手 schema：CQF mod 內 `.QuestEditor_Library/Skill/{cqf-action-condition-dev,cqf-def-catalog,cqf-map-dev,cqf-overview}/SKILL.md`。
- 反編譯欄位真名：`projects/rimworld_mods/custom-quest-framework/decompiled/QuestEditor_Library/QuestEditor_Library.decompiled.cs`
  - `CQFAction_Message`:618、`CQFAction_SentSignal`:447、`QuestNode_DoCQFActions`:32791、`QuestPart_DoCQFActions`:32821、`CQFAction_Spawn`:1473。
- 原版節點 schema：`RimWorld/RimWorldWin64_Data/Managed/Assembly-CSharp.dll`（`QuestNode_DropPods`、`QuestNode_GenerateThingSet`、`SlateRef<T>`、`ThingDefCountClass`、`ThingSetMaker_StackCount`）。
- 原版任務參照：`RimWorld/Data/Core/Defs/QuestScriptDefs/Scripts_Utility_RewardsCore.xml`、`.../ThingSetMakerDefs/ThingSetMakers_Misc.xml`。

## 技術棧
- 純 XML mod（無 C#、無組件編譯）。
- RimWorld 1.6（實機版本 `1.6.4633 rev1261`，全 DLC）。
- 硬相依 Harmony + CQF；`loadAfter` CQF。
- 健檢腳本：Python 3 + `monodis`（`tests/healthcheck.py`）。

## 完成定義與驗證狀態（如實）
- [x] 所有 `Class` 型別存在於 CQF 反編譯或原版 Assembly-CSharp（靜態健檢通過）。
- [x] CQF 型別的子欄位（`message`/`type`/`signal`/`addQuestPrefix`/`actions`）皆為真實 public 成員（靜態健檢逐欄位驗證通過）。
- [x] 引用的 `Silver`、`PositiveEvent`、`ThingSetMaker_StackCount`、本 mod `ThingSetMakerDef` cross-ref 皆解析成功。
- [x] `IntRange/FloatRange` 用 `min~max`；所有 XML well-formed。
- [ ] **遊戲內實際載入/觸發：尚未驗證（僅完成靜態健檢）。**
  - 原因：驗證當下 RimWorld 正由使用者開啟運行中（PID 94638，Proton/Win64），且現役 `ModsConfig.xml` 未啟用 CQF 與本 mod。為不干擾使用者運行中的遊戲，未強制改 ModsConfig 或重啟遊戲。
  - **要真正跑起來，需人工**：
    1. 把本資料夾連結/複製到 RimWorld 的 Mods 目錄（或 workshop 同層 local mods）。
    2. 在遊戲 Mod 列表啟用 Harmony → Custom Quest Framework → 本 mod（順序）。
    3. 開一局，開發者模式用「Debug actions → Quests → Execute quest / Force quest」選 `CQFCaravanRedemption` 手動觸發。
    4. 觀察：左上是否跳出綠色訊息「流民商隊的償還…」、是否收到白銀投放艙信件；掃 `Player.log` 確認無 `Could not find type QuestEditor_Library.*` / `def-linked` 紅字。
  - Player.log 路徑：`~/.local/share/Steam/steamapps/compatdata/294100/pfx/drive_c/users/steamuser/AppData/LocalLow/Ludeon Studios/RimWorld by Ludeon Studios/Player.log`

## 之後如何長成四章故事（備註）
見 `docs/structure.md`。
