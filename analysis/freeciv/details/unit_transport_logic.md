# 單位架構深化：運輸裝載與級聯摧毀 (源碼剖析)

在 Freeciv 中，運輸系統（如船隻載運陸軍、潛艇載運導彈、航空母艦載運飛機）是戰略遊戲中最複雜的互動之一。這不僅涉及空間的重疊，更涉及當載具被摧毀時，乘客的生死存亡邏輯。

本文件深入剖析 `common/unit.c` 與 `server/unittools.c`，解構其巢狀運輸與「沉船求生」機制。

## 1. 裝載邏輯：`unit_transport_load`
這是在 `common/unit.c` 中定義的核心函數，負責建立單位間的父子關係。

### 1.1 巢狀指標鏈結
當陸軍 (Cargo) 登上船隻 (Transport) 時，系統會建立雙向連結：
```c
pcargo->transporter = ptrans;
unit_list_append(ptrans->transporting, pcargo);
```
- 這種設計使得查詢「這艘船載了誰」與「這個單位在哪艘船上」的時間複雜度都是 $O(1)$ 或極低。
- 由於使用的是 `unit_list` (鏈結串列)，理論上只要符合 Ruleset 的容量限制 (`get_transporter_capacity`)，裝載數量是動態的。

### 1.2 裝載規則驗證 (`can_unit_load`)
在正式連結前，系統會檢查：
1. **載具容量**: 是否還有剩餘空間。
2. **地形要求**: 通常只能在港口城市或相鄰的海岸方格進行裝卸。
3. **規則限制**: 某些單位只能被特定載具承載（例如：導彈只能上潛艇或巡洋艦，由 `unit_class` 中的 `ferry_types` 定義）。

---

## 2. 死亡的連鎖反應：`wipe_unit_full`
位於 `server/unittools.c`。當一個單位死亡（戰鬥失敗、缺油墜毀、被解散）時，如果它是一艘運輸船，會發生什麼事？

### 2.1 乘客分類 (Triage)
系統首先會強制將所有乘客（`pcargo`）卸載 (`unit_transport_unload`)，並根據其當前狀態分為三大類（Triage）：
1. **`helpless` (無助者)**:
   - 條件：無法卸載的單位 (`!can_unit_unload`)。例如，在深海中失去船隻的陸軍。
2. **`imperiled` (瀕危者)**:
   - 條件：可以卸載，但目前所在方格不允許其生存 (`!can_unit_exist_at_tile`)。例如，被卸載到海洋格上的步兵。
3. **Healthy (健康者)**:
   - 條件：剛好在港口內船隻被擊沉，乘客可以直接在陸地上存活。這些單位會被安全釋放並發送網路封包通知。

### 2.2 搶救機制 (`try_to_save_unit`)
Freeciv 並不是殘酷地直接秒殺所有落水者，而是給予一線生機。系統會依序對 `helpless` 與 `imperiled` 陣列執行搶救：
- **尋找替代船隻**: 如果同一個方格內剛好有另一艘友軍船隻，且有空位，落水者會瞬間自動登船（`unit_transport_load_tp_status`）。
- **緊急傳送 (Teleport)**: 如果設定允許 (`teleporting`)，系統會呼叫 `find_closest_city` 尋找最近的己方城市，並將乘客瞬間傳送回城！
    - *UI 提示*: `"XXX escaped the destruction of YYY, and fled to ZZZ."*

### 2.3 優先救援權重
在災難發生時，誰先上救生艇？
```c
if (unit_has_type_flag(pcargo, UTYF_EVAC_FIRST) || unit_has_type_flag(pcargo, UTYF_GAMELOSS)) {
    // 優先搶救
}
```
- **`UTYF_GAMELOSS`**: 死亡即遊戲結束的單位（如護送模式的國王、VIP）。
- **`UTYF_EVAC_FIRST`**: ruleset 標記為優先疏散的高價值單位。
系統會先將有限的救生資源（如同格的其他船隻空位）分配給這些單位，一般步兵只能排在後面。

### 2.4 級聯摧毀 (Cascading Death)
對於既找不到其他船，也無法傳送回城的單位，它們會被放入 `unsaved` 清單，並最終呼叫 `unit_lost_with_transport` 執行銷毀，完成悲慘的級聯死亡。

## 3. 工程見解
- **雙向鏈結的安全性**: 在 `wipe_unit_full` 中，作者特別使用了 `unit_list_iterate_safe` 來遍歷乘客。這是因為卸載動作 (`unit_transport_unload`) 會即時修改 `ptrans->transporting` 鏈結串列。如果使用一般的迴圈，會導致 Pointer 崩潰。
- **解耦的死亡結算**: 透過 `unit_loss_reason` (如 `ULR_TRANSPORT_LOST`)，計分系統 (`score.units_lost`) 與外交系統能精確知道單位的死因，而非籠統的「消失」。
- **容錯與柔性設計 (Soft Failure)**: 「沉船傳送」機制 (`try_to_save_unit`) 展現了遊戲設計的柔性。在某些非寫實的 Ruleset 或特定難度下，不至於讓玩家因為一次海戰失誤就損失整支遠征軍，提升了遊戲的容錯體驗。
