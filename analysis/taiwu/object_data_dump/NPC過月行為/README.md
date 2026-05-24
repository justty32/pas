# 太吾繪卷 NPC 過月行為 資料抽取

> 日期：2026-05-24
> 範圍：把《太吾繪卷》「NPC 在月份更替/過月時會做的各種行動，及其 AI 決策設定」相關的 config 資料表整批抽出留檔（行為清單＋說明）。
> 全程對遊戲與反編譯源唯讀，僅在本資料夾寫輸出。

本批是**資料抽取**（行為清單＋欄位說明），與既有**機制研究** `../../details/npc_ai_and_advance_month.md`（過月主管線、Harmony/事件切入點）互補。讀本檔可知「有哪些行為、各自的名稱與設定」；讀那份可知「這些行為如何被過月迴圈呼叫、要怎麼 mod」。

---

## 檔案

| 檔案 | 內容 |
|---|---|
| `extract_npc_month_behavior.py` | 抽取腳本，複用上層 `../extract_objects.py` 的 helper（`split_top`/`iter_new_calls`/`parse_ctor`/`load_ref`/`load_lang`/`lang_get`/`parse_int`），輸出 JSON |
| `npc_month_behavior.json` | 12 張表的結構化抽取結果（每表含 count/unresolved/name_from_ref/rows） |
| `npc_month_behavior_分類清單.md` | 分類 Markdown：以主題分節，每筆列名稱＋說明 |
| `README.md` | 本檔 |

### 重現方式

```bash
cd /home/lorkhan/repo/pas/analysis/taiwu/object_data_dump/NPC過月行為
python3 extract_npc_month_behavior.py     # 重生 npc_month_behavior.json 並印統計
# 重生分類 Markdown：見腳本註解，或直接讀 JSON 自行渲染
```

---

## 資料來源（唯讀）

- **schema（欄位→argN）**：反編譯 `~/dev/taiwu-src/Assembly-CSharp/Config/<Table>Item.cs` 建構子本體。
- **資料列**：`~/dev/taiwu-src/Assembly-CSharp/Config/<Table>.cs` 的每個 `new <Table>Item(...)`。
- **名稱（權威）**：`<遊戲>/The Scroll of Taiwu_Data/StreamingAssets/ConfigRefNameMapping/<Table>.ref.txt`（name 偶數行 / id 奇數行，id==TemplateId，與安裝版同步）。本批 12 張表 ref 皆齊全，名稱 **100% 由 ref 解出**（僅 AiGroup id=2 在 ref 無名，見「資料坑」）。
- **說明 Desc / 台詞**：`<遊戲>/.../StreamingAssets/Language_CN/<Pack>_language.txt` 第 argN 行（0-based）。

---

## 各表覆蓋與欄位含義

| 表 | 筆數 | 主題 | Name 來源 | Desc | 語言 pack | schema 出處 |
|---|---:|---|---|:---:|---|---|
| **MonthlyActions** | 84 | NPC 每月可執行行動清單（核心；奇遇/招親/劇情/妖魔巢穴等場景型） | ref | — | MonthlyActions_language | `MonthlyActionsItem.cs:54` |
| **AiAction** | 59 | AI 行動定義（主為戰鬥行為樹，含說明） | ref | ✔ | AiAction_language | `AiActionItem.cs:32` |
| **BehaviorType** | 5 | 行為大類（道德傾向：刚正/仁善/中庸/叛逆/唯我） | ref | ✔ | BehaviorType_language | `BehaviorTypeItem.cs:20` |
| **PrioritizedActions** | 23 | 優先級行動設定（過月每月先挑的高優先行為） | ref（無 Name 欄位） | — | PrioritizedActions_language（拒約台詞） | `PrioritizedActionsItem.cs:42` |
| **VillagerRoleArrangement** | 13 | 村民職務安排（太吾村村民過月自動執行的職務） | ref | ✔ | VillagerRoleArrangement_language | `VillagerRoleArrangementItem.cs:22` |
| **VillagerRole** | 7 | 村民角色母類（農戶/匠人/大夫…） | ref（無單一 Name） | — | VillagerRole_language（效果標籤） | `VillagerRoleItem.cs:27` |
| **AiNode** | 3 | AI 決策樹節點種類（順序/分支/行為） | ref | ✔ | AiNode_language | `AiNodeItem.cs:27` |
| **AiCondition** | 114 | AI 決策樹條件原語 | ref | ✔ | AiCondition_language | `AiConditionItem.cs:32` |
| **AiParam** | 25 | AI 參數型別 | ref | ✔ | AiParam_language | `AiParamItem.cs:20` |
| **AiData** | 25 | 具名 AI 藍圖（角色/劇情→行為樹 Path） | ref | — | —（Path 為字串字面） | `AiDataItem.cs:14` |
| **AiGroup** | 3 | AI 分組（通用/戰鬥…，聚合 GroupId） | ref | — | — | `AiGroupItem.cs:13` |
| **AiRelations** | 13 | 關係觸發 AI（互動後好感/仇怨變化） | ref | — | — | `AiRelationsItem.cs:27` |

> 「Ai* 各表能否解出名稱」：**全部能**。即使 `AiData`/`AiGroup`/`AiRelations`/`PrioritizedActions`/`VillagerRole` 的 `Item.cs` **沒有 Name 欄位**，其 `.ref.txt` 仍按 TemplateId 提供顯示名（如 AiRelations「结下仇怨/爱慕」、AiData「太吾/莫女」、PrioritizedActions「拜师学艺/寻仇报复」）。

### 重點欄位細節

- **MonthlyActions**：`CharacterSearchRange`(arg6 搜尋目標範圍)、`IsEnemyNest`(arg12 妖魔巢穴)、`CanActionBeforehand`(arg17)、`PreparationDuration`(arg18 準備月數)、`PreannouncingTime`(arg19 預告月數)、`MinInterval`(arg20)、`MinFailureInterval`(arg21)。另有 `MajorTargetFilterList`/`ParticipateTargetFilterList`（`CharacterFilterRequirement[]`，目標篩選器）未展開。
- **AiAction / AiCondition / AiNode / AiParam**：皆有 `Type`（對應 `EAiActionType`/`EAiConditionType`/`EAiNodeType`/`EAiParamType` enum，資料列以 `EXxxType.Yyy` 字面寫入，腳本擷取後綴）。
- **BehaviorType**：5 種道德型，`Desc`=型格描述，另有 `BetrayTips`（3 句「道不合/志不同」台詞）。**這 5 型的順序即 PrioritizedActions.MoralityPriority 陣列的 5 個權重順序**。
- **PrioritizedActions**：`BasePriority`(arg5 基礎優先級)+`MoralityPriority[5]`(arg6 各道德型加權)決定選擇傾向；`ActionCoolDown`(arg3)、`Duration`(arg4)、`IsAdultOnly/IsNonLeader/IsNonMonk`(arg8/9/11 門檻)、`RefuseAppointment`(arg16 因執行此行動而拒絕太吾召喚的台詞)。TemplateId 與後端 `Character/Ai/PrioritizedActionType.cs` switch 一一對應。
- **VillagerRoleArrangement**：`VillagerRole`(arg1 所屬角色)、`Desc`(arg6 產出說明)。`ShortName`(arg2) 在反編譯語言檔多為空白行（版本漂移，見下）。
- **AiData**：`Path`(arg1) 是行為樹藍圖相對路徑（如 `taiwu`、`sect-story/baihua-anonym-escape`、`sword-tomb/monv`）。
- **AiRelations**：以 `PersonalityType`(arg1) 為鍵；`Noncontradictory*Adjust`/`EnemySectMemberAdjust`/`FriendlySectMemberAdjust` 為關係/名望調整量。過月「關係更新」階段使用。

---

## 這些行為如何接入過月迴圈

（詳見 `../../details/npc_ai_and_advance_month.md`，此處只給速覽）

過月總入口 `WorldDomain.AdvanceMonth`（`WorldDomain.cs:7067`）→ `PeriAdvanceMonth`（`:7214`）依地區平行逐角色跑各階段。本批資料表對應如下：

- **狀態碼 7 `_CharacterRelationsUpdate`**：關係/好感更新 → 用 **AiRelations**。
- **狀態碼 9 `_CharacterPrioritizedAction`**（A 層上半）：`Character.PeriAdvanceMonth_ExecutePrioritizedAction`（`Character.cs:16577`）遍歷 **PrioritizedActions** 表，按 `BasePriority + MoralityPriority[該 NPC 的 BehaviorType]` 擇優；NPC 的 `BehaviorType`（**BehaviorType** 表）即道德型，決定權重取哪一欄。各行動的成立條件由 `PrioritizedActionType.TryCreateAction_<名稱>` 硬編（id 對齊 PrioritizedActions.ref）。
- **狀態碼 11 `_CharacterFixedAction`**：固定行動，含「村民職務」——**VillagerRoleArrangement / VillagerRole** 在此驅動太吾村村民的自動產出（亦對應優先級行動 id=21「村民身份」`VillagerRoleArrangementAction`）。
- **MonthlyActions**：場景型/世界級月度行動（招親、妖魔巢穴等）的設定表，由過月尾段 `CheckMonthlyEvents` 與 `MonthlyEventActions/` 機制結算（含搜尋目標、準備/預告月數、最短間隔）。
- **AiAction / AiCondition / AiNode / AiParam / AiData / AiGroup**：AI **行為樹**的原語與藍圖（戰鬥 AI 為主，亦含通用），由遊戲內 `AiEditor` 視覺化編輯器產生。與「過月世界行為」是相鄰但不同的系統（戰鬥 AI 在進戰鬥時跑，B 層）；但同屬「NPC AI 決策設定」，故一併留檔以備完整。

> 改「某行為多/少發生」最省事＝改 PrioritizedActions 的 `BasePriority`/`MoralityPriority`（純資料 ConfigCell，免 Harmony）。詳見機制研究 §6 切入點總表。

---

## 資料坑（caveat）

1. **版本漂移（ref vs 反編譯語言檔）**：名稱取自**安裝版** ref，Desc 取自**反編譯版**語言檔，兩者版本可能不同步。最明顯例：AiAction id=1/2 在 ref 為「普攻1/普攻2」，但反編譯語言檔對應行寫「变招/变招破绽」。**以 ref 名稱為準**（per 既有方法論）。
2. **AiGroup id=2 ref 無名**：`AiGroup.ref.txt` 只含 id 0(通用)/1(战斗)，id=2（GroupIds=[2]）在安裝版 ref 無對應名稱，JSON 內 Name=null、`unresolved=1`。屬安裝版 ref 的真實缺漏，非解析錯誤。
3. **VillagerRole 效果標籤越界**：id=5(护冢)/6(村长) 的部分 `EffectTexts` 索引超出反編譯語言檔長度，顯示 `<VillagerRole_language_NN_invalid>`（版本漂移）；分類 Markdown 已過濾這些 invalid 標籤。
4. **VillagerRoleArrangement.ShortName 為空**：arg2 指向反編譯語言檔的空白行，故多數列 ShortName 為空字串（非缺漏；遊戲此欄本就可空）。
5. **任務原指定的 `VillagerRoleAutoAction.cs` 不存在**：反編譯源中無此表，村民過月自動行動實際由 **`VillagerRoleArrangement` + `VillagerRole`** 兩表承載，已改抽這兩張。
6. **未展開的複合欄位**：MonthlyActions 的 `MajorTargetFilterList`/`ParticipateTargetFilterList`（目標篩選器陣列）、AiRelations 的 `Probability`（觸發機率陣列）為巢狀結構，本批未逐項展開（保留名稱/數值級別即可滿足「行為清單＋說明」目標）。
