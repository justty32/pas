# 擴充接點清單（核心交付物）

> 使用者目標：在 SpeakUp 基礎上做擴充（新對話來源／新觸發／改顯示）。
> 每項標 path:line、註明「擴充方式＝純資料 / 需改碼」與風險。

## 先讀懂兩條軸線

擴充 SpeakUp 有兩個獨立維度，先對號入座：

1. **要新增「對話句子／情境分支」** → 多半是**純資料（XML）**，不用編譯。
2. **要新增「可判斷的情境變數」「新觸發來源」「改泡泡顯示」** → 多半**需改碼**（C# + Harmony，要重編譯 `SpeakUp.dll` 或另開外掛 mod）。

---

## A. 純資料擴充（不需編譯，最低風險）— 首選

### A1. 為既有原版互動加對話（Chitchat / Insult / Romance…）
- 接點：`PatchOperation` 注入到原版 `InteractionDef`，xpath 鎖 `logRulesInitiator/rulesStrings`。
- 範例：`1.6/Patches/z_add_chitchat_weather.xml:3`（`PatchOperationAdd`）、`1.6/Patches/Patches.xml:3`（`PatchOperationReplace` 整段換 Chitchat）。
- 寫法：`<li>r_logentry(條件...)->句子 [子關鍵字]</li>`，條件用 SpeakUp 已提供的關鍵字（見 D 區清單）。
- **擴充方式＝純資料**。新增一個 `1.6/Patches/zz_my_xxx.xml`（檔名排序影響套用順序，`z_` 前綴是慣例）即可。
- 風險：低。若 xpath 寫錯只會 patch 失敗報 log；要避免和既有 `PatchOperationReplace`（如 `Patches.xml`）衝突——Replace 會覆蓋整段 rulesStrings，後載入者贏。

### A2. 新增一種全新對話主題（自訂 InteractionDef）
- 接點：在 `1.6/Defs/` 加 `InteractionDef`，`ParentName="SpeakUpReply"`（抽象父定義在 `1.6/Defs/Interactions.xml:3`）。
- 範例：`1.6/Defs/chitchat_weather.xml:5` `StuckIndoors`。
- 重點：根規則關鍵字必須是 `r_logentry`（`GrammarResolver_Resolve.cs:17` 只對它注入情境；其他 root 不會有 WEATHER 等變數）。
- 若要讓它能被當成「回話」串接，在規則上加 `tag=<某InteractionDefName>`，`Ensue→Reply` 會用該 tag 去 `DefDatabase<InteractionDef>.GetNamed(tag)` 找下一句（`Talk.cs:51`）。
- **擴充方式＝純資料**（前提：用到的關鍵字都已存在）。
- 風險：低～中。新 InteractionDef 要被原版排程選中，得有對應的 `Pawn_InteractionsTracker` 觸發條件；最穩做法是把規則「掛進」既有的 `Chitchat`（走 A1）而非新建一個無人觸發的 InteractionDef。

### A3. 調行為參數（不改碼，玩家可調）
- 接點：`SpeakUp/Settings.cs:56`（`SpeakUpSettings`）。`linesPerConversation`、`ticksBetweenLines`、`sameRegionRestriction`、`forceNoTranslate`。
- **擴充方式＝純資料/設定**（遊戲內 mod 設定面板，`Settings.cs:20`）。

---

## B. 需改碼擴充（重編譯 SpeakUp 或另開外掛 mod）

### B1.（最關鍵）新增一種「情境變數」讓 XML 能判斷 — 改 ExtraGrammarUtility
- 接點：`SpeakUp/ExtraGrammarUtility.cs::ExtraRules`（`:54`），實作在 `ExtraRulesForPawn`(`:80`)/`ExtraRulesForMap`(`:246`)/`ExtraRulesForTime`(`:269`)。
- 做法：在對應方法裡多一行 `MakeRule(symbol + "myVar", 值)`（`MakeRule` 定義 `:282`），之後 XML 就能寫 `r_logentry(INITIATOR_myVar==...)`。
- 範例可仿：天氣 `MakeRule("WEATHER", ...)`（`:253`）、心情 `MakeRule(symbol+"mood", ...)`（`:85`）。
- 若新變數要做**數值比較**，無需再動約束碼——`RuleEntry_ValidateConstantConstraints.cs:43` 已支援數值；只要 `MakeRule` 餵的是可 parse 的數字字串。
- **擴充方式＝需改碼**（C#，重編 DLL）。風險：中。`ExtraRulesForPawn` 限定 humanlike（`IsValid` `:275`），動物/機械對話需放寬此限。注意 try/catch 包住整段（`:60`），單一變數 throw 會吞掉**整批**規則→建議自己做 null 防護。

### B2. 改「觸發來源 / 對話節奏」— 改排程邏輯
- 接點：續話排程 `SpeakUp/DialogManager.cs::Ensue`(`:16`)/`Talk.cs`(`MakeReply :29` / `Reply :45`)；發射時機 `Pawn_InteractionsTracker_InteractionsTrackerTick.cs:12`。
- 例：想讓特定情境**主動發起**對話（而非等原版排程），需新增一個 tick patch 自己呼叫 `TryInteractWith`（仿 `FireStatement` `DialogManager.cs:36`）。
- **擴充方式＝需改碼**。風險：中～高。`DialogManager` 全是 static 狀態、非 thread-safe；`talkBack`/`Initiator`/`Recipient` 在 `ToGameStringFromPOV_Worker` 前後 set/clear（`PlayLogEntry_Interaction_ToGameStringFromPOV_Worker.cs:16,24`），時序敏感，亂插容易污染他人對話。`FireStatement` 還臨時改了 `intDef.ignoreTimeSinceLastInteraction`（`DialogManager.cs:39`，作者註明是 workaround），擴充時注意副作用。

### B3.（外掛式，不改原 mod）自己寫一個 patch 同樣注入 r_logentry 規則
- 接點：仿 `GrammarResolver_Resolve.cs:15` 做自己的 Prefix，或仿 `RandomPossiblyResolvableEntry` 注入規則。
- **擴充方式＝需改碼**，但**獨立成新 mod、loadAfter SpeakUp**，不動原始檔——最乾淨的擴充路線。風險：中。要小心和 SpeakUp 的 `r_logentry` Prefix 競合（兩個 Prefix 都改同一 request.rules，順序由 Harmony priority 決定）。

---

## C. 顯示端擴充（屬於 Bubbles，不在 SpeakUp）

### C1. 改泡泡外觀 / 過濾 / 文字處理
- 接點（反編譯）：抓文字 `Bubbler.Add`（`interaction-bubbles/decompiled/Bubbles.decompiled.cs:529`）、取文字 `Bubble.GetText`（`:444`）、繪製 `Bubbler.Draw`（`:638`）、設定 `Bubbles.Settings`（`:146`，字級/顏色/淡出/聽力範圍等大量可調）。
- 注意：Bubbles **無原始碼**（只有 DLL），且 SpeakUp 不引用它。改顯示要嘛調 Bubbles 內建設定（玩家層級，無需碼），要嘛另寫 Harmony patch hook `PlayLog.Add`/`Bubbler` 做二次處理。
- **擴充方式**：調設定＝純資料；改邏輯＝需改碼（且是對第三方 DLL，升級易壞）。風險：高（無源碼、版本相依）。

---

## D. XML 可用的情境關鍵字清單（給 A 區資料擴充用）

來源全在 `ExtraGrammarUtility.cs`。前綴 `INITIATOR_` / `RECIPIENT_`（`:14-15`）。

| 關鍵字 | 來源 path:line | 型別/值 |
|---|---|---|
| `{P}_mood` | `:85` | 0–1 數值 |
| `{P}_thoughtDefName` / `{P}_thoughtLabel` / `{P}_thoughtText` | `:93,96,100` | 字串 |
| `{P}_opinion` | `:106` | 數值 |
| `{P}_relationship` | `:115,124,132` | 關係 defName / `None` |
| `{P}_trait` | `:141` | 特質 Label（多筆） |
| `{P}_bestSkill`/`worstSkill`/`higherPassion` | `:145,148,151` | 技能 label |
| `{P}_<skill>_level` / `{P}_<skill>_passion` | `:156,157` | 數值 / passion enum |
| `{P}_childhood` / `{P}_adulthood` | `:161,164` | 背景 title |
| `{P}_moving` / `{P}_seated` | `:169,179` | 是/否 |
| `{P}_jobDefName` / `{P}_jobText` | `:174,175` | 字串 |
| `{P}_inventory_item` / `{P}_wearing` | `:186,195` | defName / label |
| `{P}_needs_tending` | `:205` | 是/否 |
| `{P}_injury` / `{P}_missing_part` / `{P}_ailment` | `:215,220,227` | 部位+label |
| `WEATHER` | `:253` | 天氣 label（中文，如 晴/雾/雨） |
| `TEMPERATURE` | `:256` | 數值 |
| `OUTDOORS` | `:259` | 是/否 |
| `NEAREST_art` / `NEAREST_plant` | `:265` | label（5 格內） |
| `HOUR` | `:271` | 0–23 |
| `DAYPERIOD` | `:272` | morning/afternoon/evening/night |

> 注意：是/否、特質/天氣 label 在**中文版**會是中文字串（XML 已用中文比對，如 `WEATHER==晴`、`INITIATOR_trait==穴居者`）。新增資料時請對齊中文 label。

---

## 推薦擴充路徑（依風險）

1. **只想加更多對話**：走 A1（新 `1.6/Patches/zz_*.xml` 注入 Chitchat）→ 零編譯、零相依風險。
2. **要依新情境變數分支**（變數已存在 D 表）：仍是 A1/A2 純資料。
3. **要全新情境變數**：B1 改 `ExtraGrammarUtility.cs` 加 `MakeRule`，重編 DLL。
4. **要新觸發/主動發話**：B2（高風險，碰 static 狀態機），或 B3 另開外掛 mod 較安全。
5. **要改泡泡顯示**：先試 Bubbles 內建設定（C1）；非不得已才 patch 第三方 DLL。
