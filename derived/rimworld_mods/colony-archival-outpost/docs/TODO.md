# colony-archival-outpost · TODO（近期工作）

> 本檔只放 v1 現有 mod 的近期工作：🔴 需要 Fix、🟡 可以完善。
> **未來新功能／擴展（🟢 N1–N7、🔵 E1–E4）已拆到 [`IDEAS.md`](./IDEAS.md)。**
> 源碼核對基準日：2026-06-10。

---

## 🔴 需要 Fix（確認是缺陷／壞行為）

### F1. 消耗端與產出端脫鉤——負成長料盡仍照產正成長
- **現象**：用黃金產出食物的情境，黃金歸零後食物仍無條件產出（變「免費」）。
- **位置**：`Source/Outpost_Sampled.cs:36-54` `Produce()`：先 `TakeItems` 扣負成長（不足扣到 0），
  再 **無條件** `base.Produce()` 產正成長，兩者無耦合判斷。
- **根因**：`ProductivitySnapshot.dailyRates` 把每資源記成獨立有號淨流，沒有「料↔產物」關聯。
- **詳見**：`docs/2026-06-10-todo-consume-produce-decoupling.md`（含 3 個修法選項）。
- **動工前**：先確認設計意圖（黃金是否為食物原料）。

### F2. 採樣時長過短／速率溢位防護（使用者提案，源碼核對後拆兩件）
> ⚠ 使用者原始擔心「短採樣 → 產出超過 int64 → 出錯」。源碼核對（2026-06-10）後修正：
> 該溢位**已被部分擋住**，且型別是 **int32+float，非 int64**。拆成兩件性質不同的事：

- **F2a 殘留溢位點（真，機率極低）**：`Source/Outpost_Sampled.cs:28` 與 `:44`
  `Mathf.RoundToInt(kv.Value * daysPerCycle)`（daysPerCycle = 900000/60000 = 15）。
  僅當某資源 `delta` 逼近 int32 上限（約 21 億）時，`rate×15` 在 float→int 轉換溢位。
  - 對策：用 `long`/`checked` 計算 + 上限 clamp，或 try/catch 包住封存流程（出錯即中止、不破壞存檔）。
- **F2b 採樣不足一天的處置（⚠ 使用者已改為「軟提醒」，不再硬擋——詳見 IDEAS.md N1）**：
  > 原構想是「不足門檻 → 按鈕變灰硬擋」；使用者後決定改為「照樣可封存，於確認視窗黃字提醒
  > 『不足一天，已強制以一天計算』」。實作併入 N1。若日後想改回硬擋或做兩段式（極短硬擋+其餘軟提醒），再議。
  > 以下為原硬擋構想，保留備查：
  - 現況：`ArchivalService.cs:36` `Mathf.Max(elapsedTicks, 60000)` 已把分母下限鎖 **1 遊戲天**，
    所以短採樣**不會**爆大速率（分母≥1），反而被稀釋、不具代表性。
  - 因此「採樣太短就把『結束封存』按鈕變灰」應以 **資料品質** 為由實作。
  - **門檻取值要對齊**：使用者初想「1 遊戲小時 = 2500 ticks」，但數學下限是 **1 天 = 60000 ticks**；
    門檻設在 1 小時仍落在被稀釋區間內 → 建議門檻直接取 **≥ 1 遊戲天（60000 ticks）** 與數學下限一致，
    否則速率會被低估。回家後定案門檻值。
  - 實作點：gizmo disable + tooltip 說明（比照唯一基地防呆 `Settlement_GetGizmos_Patch.cs` 既有 disable 模式）。

---

## 🟡 可以完善（健壯性／邊界，未必是 bug，待查證或加固）

### P1. 投遞失敗／找不到殖民地——無任何保險，且失敗路徑未驗證
- **現象**：正成長產出的投遞 100% 委派 VOE `base.Produce()`（`Source/Outpost_Sampled.cs:53`），
  我方無 try/catch、不檢查投遞結果。
- **未知數**：VOE `Deliver()`（設計文件記為 `:1409`）對「無主基地可投遞／投遞失敗」如何處理，**尚未查證**
  （VOE 反編譯源碼未 clone 進工作區）；設計文件 `docs/2026-06-09-design.md:145` 當初即標「待驗」，
  Task9 實機只驗正常路徑。
- **待辦**：
  1. 取得並閱讀 VOE `Outposts.decompiled.cs` 的 `Deliver()`（:1409）行為。
  2. 釐清「玩家此刻沒有任何家園地圖」時 outpost 產出會怎樣（憑空消失？卡住？報錯？）。
  3. 若 VOE 無妥善處理 → 決定我方對策（暫存回 containedItems？暫停產出？提示玩家？）。
  - 視查證結果，本項可能升級為 🔴 Fix。

### P2. pawn 轉入哨站的相容性查證（mod 掛在 pawn 上的額外資料是否保全）
> 使用者疑慮：封存時殖民者「被 remove → 變 VOE 佔位符」會不會丟失其他 mod 掛在 pawn 上的資料。
> 源碼核對（2026-06-10）後初步結論：**疑慮前提多半不成立**，但 VOE `AddPawn` 內部行為待源碼坐實。
- **我方流程（已核對）**：`ArchivalService.cs:75-82` 不走原版商隊（無 `Caravan`/`CaravanFormingUtility`），
  而是 `pawn.DeSpawn()`（從地圖移除，不 Destroy/不丟棄）+ `outpost.AddPawn(pawn)`（存進 `occupants`）。
- **關鍵**：搬的是**原本那個 Pawn 物件本身**，非新建佔位符 → comps/hediffs/traits/關係/他 mod 額外資料
  都隨同一物件一起進 occupants，理論上不會漏搬（沒「複製到新物件」這一步就不會漏）。
- **待查證（需 VOE 源碼，未 clone）**：VOE `AddPawn`（設計文件記 `:1022`，`CanAddPawn:1033`）內部除
  `occupants.Add` + `RecachePawnTraits` 外，是否還清除/重置 pawn 任何狀態。
- **殘留真實風險（非「資料沒搬」）**：
  1. `DeSpawn()` 觸發 comps `PostDeSpawn`——假設 pawn 恆在地圖的 mod 可能誤判（同商隊/任務帶走，非獨有）。
  2. 地圖被銷毀（`ArchivalService.cs:95` `DeinitAndRemoveMap`）——存於 MapComponent/地圖綁定物件的 pawn 相關
     資料會隨地圖消失（屬地圖資料非 pawn 資料）。
  3. 哨站期間 VOE 用自身邏輯餵 occupants，依賴「pawn 在真實地圖」才 tick 的 mod 效果暫停作用。
