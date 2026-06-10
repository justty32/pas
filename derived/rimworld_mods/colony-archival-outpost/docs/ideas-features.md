# colony-archival-outpost · 🟢 未來新想法（增強／新功能）

> 由 `IDEAS.md` 拆出（2026-06-10）。索引見 [`IDEAS.md`](./IDEAS.md)；🔵 擴展見 [`ideas-expansions.md`](./ideas-expansions.md)；🔴🟡 近期工作見 [`TODO.md`](./TODO.md)。
> 源碼核對基準日：2026-06-10。

---

### N1. 封存前確認視窗（產出/消耗預覽 + 命名 + 確定/取消）
- **流程**：按「結束封存」後，不立即執行 `ArchivalService.Archive()`，先跳一個 `Window`/`Dialog`：
  - **預覽區**：列出 `ComputeSnapshot()` 算出的各資源每日有號淨流——正成長(產出)與負成長(消耗)分區顯示，
    讓玩家封存前看清楚這座哨站之後會產什麼、耗什麼。
  - **命名輸入欄**：讓玩家替 outpost 取名（目前用 def 預設 label）。
  - **按鈕**：「確定」→ 執行 Archive 並套用名稱；「先等等」→ 關閉視窗、不封存、繼續採樣。
  - **不足一天警告（軟提醒，取代 F2b 硬擋）**：若 `elapsedTicks < 60000`（不到 1 遊戲天），
    視窗內顯示黃字警告：「採樣時間不到一天，產出/消耗速率已強制以一天計算」，
    對應 `ArchivalService.cs:36` 的 `Mathf.Max(elapsedTicks, 60000)` 數學下限。玩家知情後仍可按「確定」。
- **技術點**：
  - 自訂 `Verse.Window`（`DoWindowContents` 畫預覽表 + `Widgets.TextField` 命名欄 + 兩顆 `Widgets.ButtonText`）。
  - 預覽需在「確定」前就算 snapshot → 把 `ComputeSnapshot()` 抽出供 UI 預覽，確定後再用同一份結果 Archive
    （避免算兩次或不一致）。
  - 命名：`Outpost.Name` 欄位（VOE/RimWorld WorldObject 命名 API，回家查 `Outpost` 是否有 Name 欄或走 `WorldObject.LabelCap` override）。
- **與 F2b 的協同**：採樣不足一天時於視窗黃字軟提醒（見 TODO.md F2b），玩家知情後仍可確定。

### N2. 採樣中查看狀況的 gizmo（即時預覽當前採樣結果）
- **流程**：採樣進行中（封存前），於 Settlement 的 gizmo 列加一顆「查看採樣狀況」按鈕，開視窗顯示：
  - **目前採到的有號淨流**：用「當下 `AllCountedAmounts` − `tracker.startCounts`」即時算（同 `ComputeSnapshot` 邏輯，
    但用當前 tick 而非封存 tick），分產出(正)/消耗(負)顯示。
  - **換算後的具體產量**：把當前速率乘 `daysPerCycle`(=15) 預估「封存後每生產週期會產/耗多少」，
    讓玩家在封存前就評估這座哨站划不划算。
  - **採樣已歷時**：顯示 `elapsedTicks` 換算的天/時，並在不足 1 天時同樣黃字提醒（與 N1 一致）。
- **技術點**：
  - **與 N1、F1 共用**：把「依 start/end counts + elapsed 算 snapshot」與「snapshot → 每週期具體產量」
    兩段邏輯各抽成可重用方法（`ArchivalService.ComputeSnapshot` 已是靜態，可直接餵「當前 tick」版；
    具體產量換算現散在 `Outpost_Sampled.ResultOptions`/`Produce`，建議抽共用 helper 供 gizmo/N1 預覽/實際產出三處共用，避免三套算式不一致）。
  - gizmo 僅在 `tracker.isSampling` 為真時出現（比照 `Settlement_GetGizmos_Patch.cs` 既有條件顯示）。
- **與 N1 關係**：N2 是「採樣中隨時看」，N1 是「結束封存前最終確認」；兩者畫面/算法高度重疊，可共用同一 UI 元件 + 計算 helper。

### N3. 封存視窗可選大地圖圖標（世界物件 icon 由玩家挑選）
> 使用者歸「可以完善」；功能上是 N1 視窗內新增的選擇項，故與 N1 綁一起實作。
- **現況**：圖標寫死在 def——`Defs/WorldObjectDefs/Outpost_Sampled.xml` 的
  `<expandingIconTexture>WorldObjects/OutpostFarming</expandingIconTexture>`（借 VOE 既有貼圖）。所有哨站長一樣。
- **目標**：在 N1 確認視窗放一排可選圖標（縮圖 gallery），玩家挑一個當這座 outpost 在世界地圖上的圖標。
- **技術點**：
  1. **存選擇**：`Outpost_Sampled` 加欄位 `string chosenIconPath`，`ExposeData` 用 `Scribe_Values` 存讀
     （與 `snapshot` 一起）。
  2. **覆寫渲染**：override 世界物件的圖標來源——RimWorld `WorldObject.ExpandingIcon`/`ExpandingIconMaterial`
     讀的是 `def.ExpandingIconTexture`；需 override getter 改回傳 `ContentFinder<Texture2D>.Get(chosenIconPath)`
     （回家確認 VOE `Outpost` 有無已 override 此處、以及正確的覆寫點）。
  3. **可選圖標清單**：先用內建/VOE 既有幾張 WorldObjects 貼圖當選項；未來可加自製貼圖（放 `Textures/`）。
  4. UI：`Widgets` 畫縮圖按鈕格，選中高亮；預設值＝目前 def 的 `OutpostFarming`。
- **相依**：需 N1 視窗先存在（此為其中一個輸入欄，與命名欄並列）。

### N4. 速率隨殖民者數量縮放（per-pawn 速率 + 封存視窗開關）
> 使用者 2026-06-10 提出。影響核心採樣/產出語意，且為 E1 正確復刻的前提。
- **目標**：產出/消耗速率不再是固定絕對值，而是「**以採樣期平均殖民者數為基準的 per-pawn 速率**」；
  哨站日後增減殖民者時，速率隨之等比增減。是否啟用此縮放，由封存視窗（N1）一個**開關**決定。
- **VOE 原生支援（關鍵，省工）**：`ResultOption` 有 `AmountPerPawn` 欄位，目前我們在
  `Source/Outpost_Sampled.cs:30` 寫死 `AmountPerPawn = 0`。啟用縮放時改為餵 per-pawn 值即可，不必自造。
  - 待確認（需 VOE 源碼）：VOE `ResultOption.Amount`（設計文件 `:2061`）對 `BaseAmount`/`AmountPerPawn`/
    occupants.Count 的確切計算公式；負成長（消耗）走我方 `Produce()` override，需自行比照乘 pawn 數。
- **採樣端改動**：`ColonyArchivalTracker` 需在採樣期間記錄**平均殖民者數**（目前只在 startTick 記資源 startCounts）。
  作法：定期累加 colonist count / 或積分後除以 elapsedTicks。封存時 `ComputeSnapshot` 把總速率除以平均 pawn 數
  得 per-pawn 基準。
- **封存視窗開關（N1 內）**：「產出/消耗速率是否受殖民者數量影響」勾選框。
  - 開：存 per-pawn 速率，正成長走 `AmountPerPawn`、負成長 `Produce()` 乘當前 occupants 數。
  - 關：維持現行固定絕對速率（`BaseAmount` 全量、`AmountPerPawn=0`）。
- **存檔**：開關狀態與 per-pawn 基準需隨 `ProductivitySnapshot`/`Outpost_Sampled` 一起 `ExposeData`。
- **相依/關聯**：N1（開關 UI 載體）；F1（消耗端語意，乘 pawn 數時一併處理）；E1（模板存 per-pawn 基準）。

### N5. 把電量（電力流）納入採樣與產出/消耗
> 使用者 2026-06-10 提出。目標：封存採樣時也把**電量產出/消耗**算進去，封存後哨站反映電力盈虧。
> 需結合兩個 mod 的 code（回家後提供）：一個 **VOE 電力輸送哨站擴展**；一個**分層 mod**
> （其 A 建築接電 → 把電量輸送到另一地圖的 B 建築，使 B 成為「發電站」＝跨地圖電力傳輸）。
- ⚠ **技術現實（與現有採樣不同路徑）**：
  - 現採樣靠 `ArchivalService.cs:34` `resourceCounter.AllCountedAmounts`（數**物品 Thing**，期末−期初）。
  - **電量是「流(瓦特)」不是庫存物品**：不在 resourceCounter；`ProductivitySnapshot.dailyRates` 的 key 是
    `ThingDef`，電量**無 ThingDef**。
  - 故電量採樣須另走：取樣 `PowerNet` 即時淨功率（產電−耗電），採樣期間累積取平均 → 轉每週期電量/特殊速率欄位。
    `ProductivitySnapshot` 需加一個**非 ThingDef 的電量欄位**（或特殊 pseudo-key）。
- **產出/消耗去向**：
  - 負電量（淨耗）：類比負成長，從緩衝扣（但電量無實體可存——需設計「電量緩衝」抽象）。
  - 正電量（淨產）：要「送回主基地」須借**跨地圖電力傳輸**機制（即上述分層 mod 的 A→B 概念，
    或 VOE 電力輸送哨站擴展）——這部分較大，屬整合工作。
- **相依/關聯**：F1（產出/消耗語意一致性）；結合兩參考 mod 的 code（待提供）。
- **狀態**：構想＋技術勘查；正電量送回家的整合是重點難點，待兩 mod code 到位後評估。

### N6. 採樣殖民者 hediff/狀態變化（封存後套用於佔位符殖民者）
> 使用者 2026-06-10 提出。把殖民者的傷勢/狀態變化納入採樣，封存後哨站每週期對佔位符殖民者施加這些變化。
- ⚠ **概念釐清（第三種運作模式）**：這**不是**「送回主基地」或「從緩衝扣物品」，而是
  **每生產週期對 occupants 本身施加 hediff 變化**（治療/惡化/加狀態）。
  - `ProductivitySnapshot` 需新增**獨立「狀態變化」區段**（與物品 `dailyRates`、電量 N5 分開）。
  - `Outpost_Sampled.Produce()` 需新增邏輯：每週期遍歷 occupants，按採樣速率改 hediff。
- **分階段範圍**：
  - **階段 A（先做）傷勢**：記錄殖民者**傷勢恢復速率**（=產出/正向）與**傷勢添加速率**（=消耗/負向）。
  - **階段 B 其他 hediff**：特殊狀況（嘔吐等）、靈能等級之類。
  - **階段 C 其他 mod 掛在 pawn 上的額外 component**：另做 patch mod，或**軟支援**——
    **僅在偵測到相關 mod 已載入時才作用**（`ModsConfig.IsActive`/反射偵測型別）。
- **UI 流程（新增兩處互動）**：
  1. **開始 sampling 時跳視窗**（⚠ 新 UI 面，現「開始採樣」可能只是 gizmo 直接設 `isSampling`）：
     玩家勾選「**記錄殖民者狀態變化**」→ 跳列表，選**要記錄哪些殖民者**的變化。
     **同一視窗設定採樣粒度**——勾選要記錄哪幾類：
     - **血量（HP）** ← 先做這個（最普通）
     - **肢體缺損狀態**（記錄哪些部位被重生/毀損；對應「斷肢重生」）
     - **特定狀態**（狀態的添加/加重/減少/失去；勾此再跳**另一個 list** 讓玩家選具體哪些狀態；具體清單之後參考 mod 再定）
  2. **結束 sampling（=N1 封存視窗）**：勾選「**人數是否影響狀態變化速率**」（per-pawn 類比 N4，但作用於狀態變化）。
- **套用對象**：封存後狀態變化作用於**所有佔位符殖民者**。
- **進階：分組套用**（待參考）：可分組施加（如「教師/學生」——用教師技能等級決定學生技能提升速率）。
  待使用者提供某 **VOE 擴展 mod**（回家後給看）。見 N7（技能訓練）。
- **技術現實/風險**：
  1. 粒度**已定為玩家可選**（開始採樣視窗勾血量/肢體缺損/特定狀態），分階段先做血量(HP)。
     實作上：血量＝整體傷勢嚴重度；肢體缺損＝記錄部位 missing/regen；特定狀態＝逐選定 hediff def 的 severity。
  2. 採樣需在開始/結束記錄每位被選殖民者的 hediff 狀態，算 delta/時間 → 比物品淨流複雜得多。
  3. ✅ **套用方式定案：直接按速率調整 severity**，**不**模擬地圖相關邏輯（治療品質/環境）——
     使用者明示那些「應該不會正常作用、也不在考慮範圍」。佔位符 pawn 直接套數值即可。
- **相依/關聯**：N1（結束視窗開關）；N4（per-pawn 語意一致）；F1（產出/消耗框架）；N7（同屬狀態變化家族）；需新增「開始採樣視窗」。
- **狀態**：構想＋技術勘查；先做階段 A 傷勢。分組與其他 mod component 待參考 mod 到位。

### N7. 採樣技能訓練程度（封存後套用於佔位符殖民者）
> 使用者 2026-06-10 補充。與 N6 同屬「對 occupants 施加狀態變化」家族，且是 N6 分組（教師/學生）的數值基礎。
- **目標**：採樣期間記錄殖民者**技能訓練速率**（XP 增長／等級變化），封存後每週期施加到佔位符殖民者的
  `Pawn_SkillTracker`。
- **運作模式**：同 N6 第三種模式（**作用於 occupants 本身**，非投遞、非扣物品）；併入 N6 的「狀態變化」區段。
- **採樣**：開始/結束記錄各 `SkillRecord` 的 `Level` + `xpSinceLastLevel`（或累積 XP），算 XP/時間速率。
- **套用**：每週期給 occupants 對應技能加 XP（`SkillRecord.Learn`）。
- **UI**：併入 N6 開始採樣視窗的粒度勾選（新增一項「**技能訓練程度**」）；結束視窗共用「人數是否影響速率」開關。
- **與分組（教師/學生）連動**：N6 提到的 VOE 教師/學生擴展正是技能機制——學生技能提升速率由教師技能等級決定；
  N7 是該分組的基礎數值來源。
- **技術點（兩項已定案 2026-06-10）**：`SkillRecord.Level` 上限 20。
  - **rust（技能衰退）**：✅ **由玩家勾選決定是否記錄**——在開始採樣視窗的粒度清單再加一個勾選項
    （與血量/肢體缺損/特定狀態並列）；勾了才把 rust 衰退納入採樣與套用。
  - **passion 倍率**：✅ **採樣時不重現**原 pawn 的 passion 倍率（採基礎技能速率）。
    套用時改依**各佔位符 pawn 自己的熱情程度**做加成——即哨站建立後，每週期 `Learn` 的 XP 依該 occupant 自身
    passion（無/有興趣/燃燒）即時計算倍率，而非沿用採樣來源的 passion。
- **相依/關聯**：N6（共用區段與 UI）；N4（per-pawn）；E1（模板存技能配方）。
