# 勢力架構深化：非對稱外交狀態機與情感演變 (源碼剖析)

Freeciv 的外交系統是其最精緻的設計之一。不同於多數遊戲採用對稱的「A 與 B 是盟友」關係，Freeciv 實作了一套**非對稱外交狀態機**。本文件深入剖析 `common/player.h` 與 `server/plrhand.c`，解構其信任度演變與條約效力。

## 1. 核心資料結構：非對稱狀態機
在 `struct player` 中，外交關係並非全域變數，而是每個玩家對其他玩家的獨立處置：
```c
const struct player_diplstate **diplstates;
```
- **物理佈局**: 這是一個指標陣列，索引為玩家 ID。
- **非對稱性**: 玩家 A 的 `diplstates[B]->type` 可能為 `DS_ALLIANCE` (盟友)，但玩家 B 的 `diplstates[A]->type` 卻可能同時被 AI 修改為 `DS_WAR` (戰爭)。
- **同步機制**: 雖然資料結構允許非對稱，但遊戲規則（Ruleset）通常會強制在「簽訂條約」時同步雙方的狀態。然而，在「密謀背叛」或「失去聯繫」的瞬間，這種非對稱性提供了極高的策略模擬深度。

---

## 2. 外交狀態枚舉 (`diplstate_type`)
系統定義了以下核心狀態，每一種狀態都具備特定的位元遮罩權限：

| 狀態 | 名稱 | 核心邏輯限制 |
| :--- | :--- | :--- |
| `DS_NO_CONTACT` | 未接觸 | 無法進行任何交易，黑幕對其完全封鎖。 |
| `DS_WAR` | 戰爭 | 單位可自由攻擊，進入領土不視為侵犯（Casus Belli 豁免）。 |
| `DS_CEASEFIRE` | 停火 | 具備 `turns_left` 倒數。強制禁止攻擊，時間到後自動轉為停戰或和平。 |
| `DS_PEACE` | 和平 | 長期狀態。攻擊將導致嚴重的名聲 (Reputation) 損失與參議院阻礙。 |
| `DS_ALLIANCE` | 盟友 | 開啟共享視覺，單位可以重疊（Stack）而不觸發衝突。 |
| `DS_TEAM` | 隊伍 | 最高層級。通常預設研究共享，無法單方面解除。 |

---

## 3. 情感演變系統：信任度 (`Love`) 的物理模型
AI 的外交決策不僅基於條約，更基於 `player_ai.love` 這個數值。

### 3.1 信任度更新公式
在每回合結算時，系統會掃描玩家行為並套用以下演算法（參考 `dai_diplomacy_begin_new_phase`）：

1.  **歷史遺忘 (Decay)**:
    信任度具有回歸中值的特性：
    `love = love - (love * love_coeff / 100)`
    這模擬了歷史仇恨或恩情隨時間淡化的過程。

2.  **領土侵犯懲罰**:
    如果玩家單位出現在 AI 領土內且無通行證：
    `love -= units_in_territory * (MAX_AI_LOVE / 200)`
    這解釋了為什麼玩家只是路過，AI 就會發出警告並降低好感。

3.  **共同敵人獎勵**:
    如果玩家正在攻擊 AI 的宿敵，AI 會產生共鳴：
    `love += damage_dealt_to_enemy * conversion_factor`

---

## 4. 外交行為的權限校驗流水線
當一個單位嘗試進入他國城市或攻擊他國單位時，系統會啟動以下檢查（參考 `pplayer_can_make_treaty`）：

### 4.1 法律校驗 (Legality Check)
1. **是否存在 Casus Belli (戰爭藉口)?**
   - 檢查 `DRO_HAS_CASUS_BELLI` 位元。
   - 若無藉口而宣戰，玩家的名聲 (`reputation`) 會大幅下跌。
2. **參議院阻礙 (Senate Blocking)**:
   - 在「共和」或「民主」體制下，系統會呼叫 `is_senate_blocking()`。
   - 如果民眾渴望和平，系統會直接拒絕玩家的宣戰請求（除非被偷襲）。

### 4.2 間諜活動後果
當間諜被捕（如 `diplomat_get_tech` 失敗），會立即觸發 `action_consequence_caught`：
- 強制降低雙方玩家的 `love` 值。
- 將外交狀態從 `DS_PEACE` 降級為 `DS_CEASEFIRE`（外交危機）。

---

## 5. 工程見解
- **位元遮罩權限 (Bitmask Permissions)**: 
    Freeciv 不使用大量的 `if (state == DS_WAR || state == DS_PEACE)`。相反，它為每個外交狀態定義了一組行為能力位元（如：`can_attack`, `can_trade`, `can_see_city`）。這使得新增一個外交狀態（如「冷戰」）只需定義新的位元遮罩，無需改動核心攻擊代碼。
- **分散式一致性**:
    雖然 `diplstates` 是非對稱的，但透過 C/S 封包 `PACKET_PLAYER_DIPLSTATE` 的強制廣播，保證了玩家在操作介面上看到的外交狀態始終與伺服器邏輯同步。
- **情感與規則的分離**: 
    `type` 決定了「能不能做」，`love` 決定了 AI「想不想做」。這種分離讓 Freeciv 的 AI 表現得既遵守規則又具備情緒化的不可預測性。
