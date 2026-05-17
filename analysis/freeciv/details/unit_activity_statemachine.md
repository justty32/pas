# 單位架構深化：活動狀態機與工程進度 (源碼剖析)

Freeciv 中的單位不僅僅是移動與戰鬥的棋子，它們同時也是「工程節點」。工人在地圖上鋪設鐵路、農民開墾荒地、甚至士兵挖掘戰壕（駐防），在底層都由同一套**活動狀態機 (Activity State Machine)** 驅動。

本文件深入剖析 `server/unittools.c` 中的 `update_unit_activity()` 函數，解構單位如何透過「時間累積」完成改變地圖的壯舉。

## 1. 核心資料結構回顧
在 `struct unit` 中，有三個關鍵欄位支撐著狀態機：
```c
enum unit_activity activity;       /* 目前的任務 (如: ACTIVITY_IRRIGATE) */
struct extra_type *activity_target;/* 任務的具體目標 (如: 灌溉設施) */
int activity_count;                /* 已投入的勞動量 (Work done) */
```

## 2. 狀態機的推進：`update_unit_activity`
在伺服器每回合的結算階段 (`cityturn.c` 或 `srv_main.c` 的 `update_unit_activities`)，系統會遍歷所有單位的狀態。

### 2.1 勞動量累積
- **不累積的活動**: `IDLE` (待命), `EXPLORE` (探索), `GOTO` (尋路), `SENTRY` (警戒)。這些屬於即時動作或持續狀態，不需要進度條。
- **累積勞動量的活動**: `MINE` (挖礦), `IRRIGATE` (灌溉), `GEN_ROAD` (蓋路), `PILLAGE` (掠奪), `FORTIFYING` (正在駐防)。
    - 系統執行: `punit->activity_count += get_activity_rate_this_turn(punit);`
    - `get_activity_rate_this_turn` 會根據單位的類型（如：現代工程車的勞動率大於遠古工人）返回對應的數值。

### 2.2 經驗值獎勵
在累積勞動量後，系統有一個有趣的機制：
```c
if (maybe_become_veteran_real(punit, 100, TRUE)) {
    notify_unit_experience(punit);
}
```
這意味著工人單位在「做有用的事（蓋路、種田）」時，是有機率升級為「Veteran（老練）」狀態的，這會進一步提升他們的勞動效率！

---

## 3. 任務完成判定與協同作業
這是 Freeciv 引擎中非常優雅的設計：**多個單位可以合作完成同一項工程。**

### 3.1 總進度判定 (`total_activity_done`)
系統並不是單純檢查 `punit->activity_count >= required_time`，而是呼叫 `total_activity_done()`。
這個函數會**加總該方格上所有執行相同 `activity` 且指向相同 `target` 的單位的 `activity_count`**。
這就是在遊戲中「派三個工人一起蓋鐵路會比較快」的底層數學依據。

### 3.2 完工結算
一旦 `total_activity_done` 返回 True，系統會根據任務類型改變世界：
- **`ACTIVITY_PILLAGE` (掠奪)** / **`ACTIVITY_CLEAN` (清理)**: 呼叫 `destroy_extra()` 移除地圖上的道路或污染。
- **`ACTIVITY_GEN_ROAD` (蓋路)** / **`ACTIVITY_BASE` (蓋基地)**: 呼叫 `create_extra()` 將新的基礎設施寫入方格的位元向量 (`bv_extras`)。
- **地形改造 (如 `ACTIVITY_IRRIGATE`)**: 呼叫 `tile_apply_activity()`，這可能會觸發 `check_terrain_change()`（例如：將沼澤抽乾變成草原）。

### 3.3 狀態重置與防呆
當工程完成，系統必須防止其他參與的工人繼續執行「非法操作」（例如在已經有路的格子上繼續蓋路）：
```c
unit_list_iterate(ptile->units, punit2) {
    if (punit2->activity == activity && punit2->activity_target == act_tgt) {
        set_unit_activity(punit2, ACTIVITY_IDLE, ACTION_NONE);
    }
}
```
這段程式碼會將同一個格子上所有參與該工程的單位，瞬間重置為 `ACTIVITY_IDLE`。

---

## 4. 特殊活動：駐防 (`ACTIVITY_FORTIFYING`)
士兵駐紮並非瞬間完成，而是需要時間的。
- 當下達駐防指令時，士兵狀態變為 `ACTIVITY_FORTIFYING`。
- 系統會比較其 `activity_count` 與 `action_id_get_act_time(ACTION_FORTIFY)`。
- 只有當回合結束，時間達標後，狀態才會轉變為 `ACTIVITY_FORTIFIED`，此時士兵才真正獲得地形防禦加成。

## 5. 工程見解
- **乘數放大 (Activity Factor)**: 為了支援小數點級別的勞動效率差異，`activity_count` 與所需時間都被預先乘以一個常數（通常是 10）。這避免了浮點數運算，保證了網路同步的絕對確定性。
- **解耦的地圖改造**: 單位本身不直接操作 `tile` 的資料。單位只負責「累積時間」，當時間達到 ruleset 定義的門檻後，由統一的 API (`create_extra`, `destroy_extra`) 來修改地圖並觸發視覺更新。這確保了遊戲狀態的一致性。
