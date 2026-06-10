# colony-archival-outpost · TODO（近期工作）

> 本檔只放 v1 現有 mod 的近期工作：🔴 需要 Fix、🟡 可以完善。
> **未來新功能／擴展（🟢 N1–N7、🔵 E1–E4）已拆到 [`IDEAS.md`](./IDEAS.md)。**
> 源碼核對基準日：2026-06-10。

---

## 🔴 需要 Fix（確認是缺陷／壞行為）

### ~~F1. 消耗端與產出端脫鉤—— 已關閉（設計特性）~~
> **這是特性，不是 bug，玩得開心！**
> 負成長視為象徵性維護費，與正成長獨立；料盡不停產為設計本意。
> 全有全無邏輯已實作並注解於 `Source/Outpost_Sampled.cs` `Produce()` block，日後若想啟用直接取消注解即可。

### F2. 採樣時長過短／速率溢位防護（使用者提案，源碼核對後拆兩件）
> ⚠ 使用者原始擔心「短採樣 → 產出超過 int64 → 出錯」。源碼核對（2026-06-10）後修正：
> 該溢位**已被部分擋住**，且型別是 **int32+float，非 int64**。拆成兩件性質不同的事：

- ~~**F2a 殘留溢位點 — 已修**~~：`Mathf.RoundToInt` 全數改為私有 helper `RateToInt(float, float)`，
  以 `double` 計算 + `int.MaxValue` clamp，消除 float→int 轉換溢位。build 0/0。
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

### ~~P1. 投遞失敗——已查證，VOE 有安全 fallback~~
- **查證結論（2026-06-10，Outposts.decompiled.cs:1444）**：
  `map = deliveryMap ?? (最近 IsPlayerHome 地圖)`；若 map == null →
  `Log.Warning("...storing instead")` + 物品存回 `containedItems`，直接 return。
  **不崩、不丟物，完全安全。不需我方額外處理。**

### ~~P2. pawn 轉入哨站相容性——已查證，AddPawn 不清除 pawn 狀態~~
- **查證結論（2026-06-10，Outposts.decompiled.cs:1022）**：
  我方路徑（DeSpawn 後呼叫）只走：CanAddPawn（恆過）→ holdingOwner?.Remove（null → skip）→
  WorldPawns 檢查（不在 → skip）→ `occupants.Add(pawn)` + `RecachePawnTraits()`。
  **完全不觸碰 hediffs / traits / relations / comps，疑慮消除。**
- **殘留已知限制（非 bug）**：
  1. `DeSpawn()` 觸發 `PostDeSpawn`——與商隊/任務帶走相同，非本 mod 獨有。
  2. 地圖銷毀後 MapComponent 資料消失——屬地圖資料非 pawn 資料，符合預期。
  3. 哨站期間依賴「pawn 在真實地圖」才 tick 的 mod 效果暫停——設計本意。
