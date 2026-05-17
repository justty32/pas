# Freeciv 城市資料結構極致深度分析 (源碼剖析)

Freeciv 的城市系統 (`struct city`) 是整個遊戲中最複雜、承載資料量最大的結構實體。它不僅是經濟產出的中心，也是人口管理、基建開發與軍事後勤的樞紐。

## 1. 核心實體：`struct city`
定義於 `common/city.h`。此結構體採用了高度緊湊且區分 Server/Client 側的設計。

### 1.1 基本身分與定位
| 欄位 | 說明 |
| :--- | :--- |
| `char *name` | 城市名稱（動態分配）。 |
| `struct tile *tile` | 城市所在的物理座標指針。 |
| `struct player *owner` | 目前的擁有者玩家。 |
| `int id` | 全域唯一 ID，用於 C/S 封包識別。 |
| `enum capital_type capital` | 標記是否為首都（Primary/Secondary/Not）。 |

---

## 2. 人口與情感系統 (The People)
Freeciv 使用了一個多維矩陣來管理公民狀態，這在同類遊戲中是非常精確的設計。

### 2.1 公民狀態矩陣
```c
citizens size;
citizens feel[CITIZEN_LAST][FEELING_LAST];
```
- **`size`**: 城市人口等級。
- **`feel` 矩陣**: 這是一個「情感演變記錄表」。
    - **第一維 (`CITIZEN_LAST`)**: 類別（Happy, Content, Unhappy, Angry）。
    - **第二維 (`FEELING_LAST`)**: 階段（Base -> Luxury -> Building Effects -> Nationality -> Martial Law -> Final）。
    - **意義**: 系統可以精確追溯為什麼某個公民不快樂（是因為國籍衝突還是因為缺乏奢華度？）。

### 2.2 專家與特殊人口
- **`specialists[SP_MAX]`**: 儲存各類專家（科學家、稅務官、演藝人員）的數量。
- **`nationality`**: 動態陣列，追溯城市內每個公民的原始國籍。這影響了城市在被征服後的忠誠度與動亂機率。
- **`martial_law`**: 被軍事單位（戒嚴）壓制而暫時「平靜」的人口數。

---

## 3. 資源生產與負擔 (Productions & Upkeep)
城市透過 `O_LAST` (食物、產能、貿易等) 枚舉進行精密的資源結算。

### 3.1 產出流水線快照
- **`citizen_base[O_LAST]`**: 公民在地圖格上勞動產生的原始數值。
- **`usage[O_LAST]`**: 帝國整體的資源調用。
- **`waste[O_LAST]`**: 腐敗與浪費。
- **`unhappy_penalty[O_LAST]`**: 因暴動（Unhappy）而造成的產能損失。
- **`prod[O_LAST]`**: 最終可用於建造的淨產量。
- **`surplus[O_LAST]`**: 結算完所有維護費後的純剩餘。

### 3.2 物理存量
- **`food_stock`**: 糧倉內累積的食物。
- **`shield_stock`**: 目前生產項目的進度累積值。

---

## 4. 基建與生產佇列 (Infrastructure)

### 4.1 建築狀態：`built_status`
```c
struct built_status built[B_LAST];
```
- **`B_LAST`**: 由 ruleset 定義的所有可能建築上限。
- **`turn`**: 記錄該建築是在哪一回合蓋好的。
    - `-1` (`I_NEVER`): 從未建造。
    - `-2` (`I_DESTROYED`): 曾建造但已被摧毀（例如戰爭或地震）。

### 4.2 生產目標：`production`
採用 `struct universal` 聯集結構，這是一個極其優雅的抽象，允許城市生產任何東西：
- **`production.kind`**: 決定生產的是 `Kind_Unit`, `Kind_Building`, 或 `Kind_Wonder`。
- **`production.value`**: 指向具體類型的指針。

### 4.3 工作清單：`struct worklist`
儲存了後續的生產計畫，實現自動化建造。

---

## 5. 聯集擴充：Server vs Client
Freeciv 透過 `union` 針對執行環境優化記憶體：

### Server 端特有欄位
- **`workers_frozen`**: AI 暫時鎖定工人，防止在複雜計算中發生震盪。
- **`adv`**: 指向 `struct adv_city`，儲存 AI 顧問對該城市的專屬評估數據（如：發展潛力分）。
- **`access_area`**: 處理戰爭迷霧下的城市可見度。

### Client 端特有欄位
- **`city_image`**: 圖形顯示緩存。
- **`buy_cost`**: 幫玩家預計算好的「立即買斷」金錢成本。
- **`need_updates`**: 位元遮罩，標記 UI 視窗是否需要重繪。

---

## 6. 工程見解：為什麼這樣設計？
1.  **高度快取化 (`tile_cache`)**:
    為了避免每回合都重新走訪周邊 21 格來計算產出，城市維護了一個 `tile_cache`。只有當地圖發生變化（蓋路、灌溉）時，才會局部更新快取。
2.  **情感階段追溯**:
    透過 `feel[category][stage]` 矩陣，Freeciv 解決了「規則交疊」的難題。開發者可以輕鬆判斷「如果我賣掉這座神廟，城市會不會立刻陷入混亂」。
3.  **通用的生產抽象 (`struct universal`)**:
    這種設計讓遊戲核心邏輯不需要知道它正在蓋的是「弓箭手」還是「長城」，只需操作 `universal` 的接口即可，極大簡化了程式碼複雜度。
4.  **國籍系統的細緻化**:
    `nationality` 公民系統是 Freeciv 真實感的來源，它讓城市在被佔領後需要數十回合才能真正同化，而非瞬間轉換立場。
