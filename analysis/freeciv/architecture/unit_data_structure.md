# Freeciv 單位資料結構極致深度分析 (源碼剖析)

Freeciv 的單位系統 (`struct unit`) 是遊戲中動態性最強、互動最頻繁的實體。它不僅承載了戰鬥與移動數據，還具備複雜的任務狀態機與運輸同步邏輯。

## 1. 核心實體：`struct unit`
定義於 `common/unit.h`。此結構體設計精巧，區分了靜態規則（Type）與動態實例（Instance）。

### 1.1 基本身分與歸屬
| 欄位 | 說明 |
| :--- | :--- |
| `int id` | 全域唯一 ID。 |
| `struct player *owner` | 所屬玩家指標。 |
| `struct tile *tile` | 目前所在物理位置。 |
| `int homecity` | 家鄉城市 ID。影響維護費（Upkeep）的扣除來源。 |

### 1.2 狀態與屬性 (Dynamic Stats)
- **`hp` (Hit Points)**: 目前生命值。當歸零時單位被摧毀。
- **`moves_left`**: 本回合剩餘移動力（乘以 `SINGLE_MOVE` 因子進行整數運算）。
- **`fuel`**: 燃料（主要用於飛機），歸零且未返航則墜毀。
- **`veteran`**: 經驗等級。越高則戰鬥力加成越大。

---

## 2. 任務與活動系統 (Activity System)
這是單位的「行為大腦」，決定了單位目前正在執行什麼長效任務。

### 2.1 狀態欄位
- **`activity` (`enum unit_activity`)**: 
    - `ACTIVITY_IDLE`: 待命。
    - `ACTIVITY_IRRIGATE`: 正在灌溉（工人）。
    - `ACTIVITY_FORTIFIED`: 已駐防（獲得防禦加成）。
    - `ACTIVITY_GOTO`: 正在執行尋路移動。
- **`activity_count`**: 
    - 關鍵欄位！記錄任務已完成的工作量。乘以 `ACTIVITY_FACTOR` 以支援非整數進度。
- **`goto_tile`**: 遠期目標座標，PF (Path-Finding) 引擎的終點。

---

## 3. 運輸與裝載邏輯 (Transport & Cargo)
Freeciv 支援極其精細的裝載系統，允許單位「巢狀」重疊。

### 3.1 關聯模型
- **`struct unit *transporter`**: 如果此單位在船上或飛機上，此指針指向載具實體。
- **`struct unit_list *transporting`**: 載具專屬。這是一個鏈結串列，儲存了所有目前承載的乘客單位。
- **`carried`**: 被承載的貨物或戰略物資。

---

## 4. 自動化與訂單 (Automation & Orders)
為了減輕玩家負擔，單位具備自動化控制層。

- **`ssa_controller`**: 伺服器代理（Server Side Agent）。標記單位是否由「自動工人」或「自動探索者」邏輯接管。
- **`orders` 結構**: 
    - 儲存一系列有序的指令序列（List of `unit_order`）。
    - 支援 `repeat`（循環執行）與 `vigilant`（遇敵報警並終止）。

---

## 5. 聯集擴充：Server vs Client
Freeciv 透過 `union` 在兩端儲存完全不同的上下文資訊。

### Server 端特有 (AI 與 邏輯核心)
- **`adv`**: 指向 `struct unit_adv`。這是 AI 專屬的決策緩衝區，儲存了該單位在 AI 心中的「戰略價值分」。
- **`upkeep_paid`**: 實際支付的維護費，用於解決複雜體制（如專制 vs 民主）下的資源扣除。
- **`removal_callback`**: 單位移除時的勾子函數。

### Client 端特有 (視角與 UI)
- **`focus_status`**: 標記該單位是否為目前 UI 的焦點（閃爍效果）。
- **`act_prob_cache`**: 戰鬥勝率預測快取，讓玩家在滑鼠懸停時能即時看到攻擊成功率。
- **`asking_city_name`**: 處理開拓者建立新城市時的彈出對話框狀態。

---

## 6. 規則集分離：`struct unit_class` & `struct unit_type`
定義於 `common/unittype.h`。這是單位的「基因」。

### 單位類別 (`unit_class`)
定義了兵種的大類特性：
- **`move_type`**: 陸、海、空、或兩棲。
- **`hp_loss_pct`**: 某些單位（如核潛艇或遠程轟炸機）在野外每回合會自動扣血。
- **`flags`**: 如 `UCF_ZOC`（是否受控制區影響）、`UCF_CAN_OCCUPY_CITY`（是否能佔領城市）。

### 單位類型 (`unit_type`)
定義了具體兵種的數值：
- **`attack_strength`**, **`defense_strength`**, **`firepower`**。
- **`build_cost`**: 生產所需的產能。
- **`tech_reqs`**: 研發所需科技。

---

## 7. 工程見解
1.  **高度狀態化**:
    `struct unit` 不僅僅是數據，它更像一個小型的狀態機。`activity` 與 `activity_count` 的配合，使得遊戲可以處理「需要多個回合才能完成的工程任務」。
2.  **鏈結串列 vs 陣列**:
    地圖方格上的單位使用鏈結串列 (`unit_list`)，這讓方格能容納無限數量的單位堆疊，展現了 C 語言處理動態實體的靈活性。
3.  **異構聯集優化**:
    Server 側需要 AI 戰略分 (`adv`)，Client 側需要 UI 快取 (`act_prob_cache`)。透過 `union` 共享同一塊記憶體，既區分了權責，又維持了記憶體的高效利用。
4.  **規則數據化**:
    所有的戰鬥力與特性都分離到 `unit_type`。這意味著要新增一個「星際戰艦」，只需修改 ruleset，而底層的 `struct unit` 行為邏輯完全不需要變更。
