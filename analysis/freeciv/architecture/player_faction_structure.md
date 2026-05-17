# Freeciv 玩家與勢力資料結構深度分析 (源碼剖析)

Freeciv 的勢力系統由 **玩家 (Player)**、**民族 (Nation)** 與 **隊伍 (Team)** 三層結構交疊而成。本文件解構了這些實體在底層如何定義以及彼此間的關聯。

## 1. 核心決策實體：`struct player`
定義於 `common/player.h`。這是遊戲中具備主動權的邏輯主體，無論是由人類還是 AI 控制。

### 1.1 玩家身分與屬性
| 欄位 | 說明 |
| :--- | :--- |
| `char name[MAX_LEN_NAME]` | 領袖名稱。 |
| `char username[MAX_LEN_NAME]` | 登入此玩家的使用者帳號名稱。 |
| `struct government *government` | 目前的政府體制指標（如：民主、專制）。 |
| `struct team *team` | 所屬隊伍指標，處理跨玩家的盟友關係。 |
| `struct nation_type *nation` | 所選民族的靜態模板（如：中國、美國）。 |
| `bv_plr_flags flags` | 位元向量，包含 `PLRF_AI`（標記是否為 AI）。 |

### 1.2 外交關係：`diplstates`
這是 Freeciv 最精密的系統之一。
```c
const struct player_diplstate **diplstates;
```
- **結構**: 這是一個二維動態陣列，存儲了對全體玩家的外交狀態 (`struct player_diplstate`)。
- **狀態枚舉 (`diplstate_type`)**: 包含 `DS_WAR`, `DS_CEASEFIRE`, `DS_PEACE`, `DS_ALLIANCE`, `DS_TEAM` 等。
- **情感屬性**: 包含 `first_contact_turn` (首觸回合) 與 `love` (AI 好感度分值)。

### 1.3 經濟與統計
- **`economic`**: 儲存存款 (`gold`) 與三項稅率 (`tax`, `science`, `luxury`)。
- **`score`**: 即時統計數值，包含殺敵數 (`units_killed`)、損失數 (`units_lost`)、文化值與總分。
- **`tile_known`**: 採用 **動態位元向量 (DBV)** 儲存該玩家已探索的地圖區域。這保證了極高的戰爭迷霧處理效能。

---

## 2. 民族基因：`struct nation_type`
定義於 `common/nation.h`。這代表了在 ruleset 中定義的「文明」模板。

### 2.1 文明特性與初始條件
- **`adjective`, `noun_plural`**: 語言翻譯名稱（如：Chinese, Chinese）。
- **`init_techs`, `init_units`**: 遊戲開始時賦予的科技與單位。
- **`leaders`**: 該文明可選的領袖清單鏈結串列。
- **`civilwar_nations`**: 觸發內戰時可能分裂出的新民族列表。這體現了 Freeciv 對歷史動態性的模擬。

---

## 3. 集體協同：`struct team`
定義於 `common/team.h`。用於處理多人遊戲中的正式結盟。

- **`team_members`**: 所屬玩家的清單。
- **效應共享**: 隊伍成員間通常預設開啟 **共享視覺 (Shared Vision)** 與 **科技研發共享**。
- **外交連動**: 在某些 ruleset 設定下，隊伍的外交狀態是連動的（一人宣戰，全隊宣戰）。

---

## 4. 聯集擴充：Server vs Client

### Server 端特有 (模擬核心)
- **`private_map`**: 伺服器為每個玩家維護的「私有地圖」，用於處理視距（Vision）與雷達。
- **`adv`**: 指向 `struct adv_data`，儲存 AI 顧問對整個國家的宏觀策略規劃（如：擴張傾向、戰爭準備度）。
- **`really_gives_vision`**: 考慮了間接視覺共享的複雜位元向量。

### Client 端特有 (呈現層)
- **`mood`**: `MOOD_PEACEFUL` 或 `MOOD_COMBAT`，用於在 UI 上顯示不同的表情或背景音樂。
- **`tile_vision[V_COUNT]`**: 客戶端專用的視覺圖層快取（主圖層、隱形圖層、水下圖層）。

---

## 5. 工程見解：權責劃分模型
1.  **享元模式 (Nation -> Player)**:
    `struct nation_type` 是靜態的唯讀數據，而 `struct player` 是動態的實例。這使得一個「羅馬民族」模板可以同時被多個不同帳號（如：不同顏色的隊伍）實例化。
2.  **外交的獨立性**:
    Freeciv 的外交並非對稱的。玩家 A 對玩家 B 的 `diplstates` 與 B 對 A 的 `diplstates` 是獨立儲存的。這允許了「A 視 B 為盟友，但 B 密謀背叛 A」的不對稱局勢。
3.  **效能導向的迷霧系統 (`dbv tile_known`)**:
    使用動態位元向量而非 `bool` 陣列，大幅縮減了大型地圖（500x500）下每回合封包同步的資料量。
4.  **AI 的宏觀大腦 (`adv`)**:
    與單位的微觀戰術不同，玩家層級的 `adv` 處理的是「國家發展」的靈魂。它決定了科研經費的百分比，這正是 AI 表現出不同性格（科研瘋子 vs 戰爭販子）的資料來源。
临
