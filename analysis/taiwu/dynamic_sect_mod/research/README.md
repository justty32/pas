# 中小門派 mod — experiment #1 接點調查批次（research/）

> 建立：2026-05-24。為「中小門派」mod **正式開工（起手 experiment #1 收徒與傳授）** 打底，一批 **5 個 subagent 平行調查**，全部對實裝版 **0.0.79.60** DLL 逐字核對。
> 唯一事實來源＝實裝 DLL（`Backend/GameData.dll`、`GameData.Shared.dll`、前端 `Assembly-CSharp.dll`，`ilspycmd -t`）＋ `~/dev/taiwu-src/`（較舊、僅供 grep 定位）。**本資料夾為調查留檔、非權威**。接續 [`../design_vision.md`](../design_vision.md)。

## 五份調查（檔 ↔ 涵蓋）

| 檔 | 涵蓋 | 對應實驗 |
|---|---|---|
| [`01_mentor_discipline_relation.md`](./01_mentor_discipline_relation.md) | 師徒關係資料模型、收徒（NPC＋太吾） | #1A |
| [`02_teach_combat_skill.md`](./02_teach_combat_skill.md) | 傳授武功 API、有無現成「傳授」語義 | #1B |
| [`03_combat_skill_mutation.md`](./03_combat_skill_mutation.md) | 武功複製＋變異（威力/五行/階位/美術） | #6 |
| [`04_taiwu_interaction_options.md`](./04_taiwu_interaction_options.md) | 太吾與 NPC 對話注入自訂選項、條件式選項 | 跨功能 |
| [`05_dynamic_sect_creation_and_promotion.md`](./05_dynamic_sect_creation_and_promotion.md) | 門派動態誕生與升格 | #5 核心機制 |

---

## 綜述（5 份完成後彙整）

### 一條主軸：關係 bitflag ＋ EventHelper 封裝 ＋ 過月主執行緒鉤

整批調查最大的共同結論是——**experiment #1 不需要門派、不需要 Harmony、不需要新美術**：

- **師徒是一條獨立的雙向關係 bitflag**（`Mentor=2048` / `Mentee=4096`），與門派（`OrganizationInfo`）完全解耦。建立只需一個後端呼叫 `DomainManager.Character.AddRelation(ctx, 弟子id, 師父id, 2048)`（自動回寫反向 bit、無紀錄時自動 `CreateRelation`）。這正好對應 design_vision「**小型門派＝只是師徒、還沒 sect**」那一階。
- **收徒／傳授都有現成的 `EventHelper` API**：收徒＝`ApplyRelationBecomeMentor(弟子, 師父)`（`:6234`，含雙向好感 +3000、心情、生平）；傳授＝`CharacterDomain.LearnCombatSkill(ctx, charId, skillTemplateId, readingState)`（`:4248`，通用任意 charId、無祕笈/造詣門檻）。**NPC 版與太吾版共用同一批後端 API**。
- **所有寫入動作都放進主執行緒過月鉤**（`RegisterHandler_AdvanceMonthBegin/Finish`）即可避開過月平行段執行緒雷——這與既有筆記一致。

### experiment #1 的最小 mod 形狀（可直接開工）

**後端 plugin**（net6，沿用 `MySwordArt.Backend` / `ChenJiaBao.Backend` 設定）：

- **NPC 版收徒/傳授**：在 `AdvanceMonthBegin` 主執行緒鉤裡，依「好感＋年紀差距＋立場相近＋雙方關係」（§六拍板的簡化契機）挑出師徒對 → `ApplyRelationBecomeMentor(弟子, 師父)` → 視需要 `LearnCombatSkill` 把師傅會的某武功傳給弟子。（NPC 不會自發收徒，必須 mod 驅動。）
- **太吾版收徒/傳授**：用官方事件系統 `EEventType.NpcInteractEvent`（`TriggerType=CharacterClicked`）掛兩個互動選項——「收某 NPC 為徒」（條件 `FavorAtLeast` ＋ NOT 已是師徒）、「傳授武功」（條件 對方是太吾弟子）——按下後後端呼 `ApplyRelationBecomeMentor` / `LearnCombatSkill`。

### 跨功能接點（哪些實驗彼此咬合）

- **收徒(01) × 互動選項(04)**：太吾版選項按下即呼 `ApplyRelationBecomeMentor`——兩支調查直接咬合。
- **動態誕生(05) 依賴 收徒(01)**：先用師徒關係長出一個師徒群 → 「創派宣告」→ 認領一個預生佔位 sect → `JoinSect` 把眾人塞進去。
- **武功變異(03) × 傳授(02)**：師傅把變異武功（如「五虎斷魂槍－水」）用 `LearnCombatSkill` 傳給弟子——變異產物直接走傳授管線。
- **太吾差遣門派 NPC**（experiment #2）＝既有 `TakeRevenge` 引擎（[`../../player_faction_research/03_npc_directed_action.md`](../../player_faction_research/03_npc_directed_action.md)）＋ 互動選項(04)＋ 關係查詢 `GetRelatedCharIds(發令者, 關係bit)`（「權力使喚」延伸的資料驅動原語）。**「委託請師傅派人」是承載動作裡最大的新造缺口**（門派 NPC 自由差遣原版無入口）。

---

## 訂正既有調查的漂移（重要，後續實作以此為準）

| 項目 | 舊記 | 實裝 0.0.79.60 |
|---|---|---|
| `LearnCombatSkill` 行號 | `:3984` | **`:4248`** |
| 前端學武類名/methodId | `CharacterDomainHelper.MethodCall`、methodId 92 | **`CharacterDomainMethod.Call`、methodId 91** |
| 關係增刪查 API 歸屬 | `RelationType.AllowAdding*` / `AddRelation` | **`RelationTypeHelper`（GameData.dll）**；`RelationType`（Shared）只剩常數＋位元工具 |
| 武功 config 型別歸屬 | `GameData.Domains.CombatSkill.CombatSkillItem` | **`Config.CombatSkillItem`（GameData.Shared.dll，實裝無前者）** |
| `design_vision §六` 接點表「據點」 | `_taiwuBuildingAreas` + `AddTaiwuBuildingArea` | **那是太吾家園專屬軌，不適合小派**；小派據點歸屬改用 mod 私有表 ＋ `BuildingDomain.GetBuildingBlockList` 驗 |

---

## 共同未實機／待釐清（開工前先知道風險在哪）

- **運行期動態 `AddExtraItem` 注入**安全性 ＋ mod 變異武功**跨存檔持久化**（03）——MySwordArt 是載入期固定批次，動態注入未實證，是 #6 最大風險。
- **佔位 sect（`AreaId=-1`）跑多月**對 NPC AI／過月供應是否走異常路徑（05）——`player_faction_research` 老懸案，仍未實機。
- `CharacterInSect`(21) 對「克隆世俗派佔位 sect」是否回 true（04／05 共同）。
- `CharacterIsCastellan`(33) 寫死 org 區間 21–35，mod 新城鎮 org 超界即失效（04）。
- mod 私有表（師徒群歸屬／據點歸屬／升格狀態）的**持久化機制**（05）——遊戲無現成委託/門派表可掛。
- 標準交談事件 `567d1caf…` 的選項結構／注入時機（本體在 `Event/EventLib`，未反編譯，04）。

---

## 各 experiment 的備料狀態

| 實驗 | 狀態 | 依據 |
|---|---|---|
| #1 收徒與傳授 | ✅ **可開工** | 01 ＋ 02 ＋ 04 |
| #2 師傅命弟子（含權力使喚延伸） | ✅ 引擎現成 | `TakeRevenge`（player_faction_research/03）＋ 04 ＋ `GetRelatedCharIds` 原語（01） |
| #5 創派契機＋升格 | ✅ 機制備齊 | 05（預生池+認領、過月升格）＋ 04（契機 condition 原語） |
| #6 武功進化變異 | ✅ 路徑清楚 | 03；待解運行期注入＋持久化風險 |
| #3 外交／階級制度 | ⏳ 尚未開 | 依賴 sect 成立後；偏設計階段 |
| #4 自製 UI | 🔁 MVP 用聊天選項替代 | §四#4 拍板；`UI_CombatSkillTree` 已調查（details/sect_skill_favor_ui.md）待用 |
