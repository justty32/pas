# AI 專題 3：軍事指揮與威脅評估 (源碼剖析)

Freeciv AI 的軍事邏輯是其最具侵略性的部分，結合了長期戰略評估（威脅）與短期戰術決策（擊殺慾望）。

## 1. 全局威脅評估：`assess_danger()`
位於 `ai/default/daimilitary.c`。AI 每個回合會掃描全地圖，偵測己方城市面臨的威脅。

### 1.1 評估機制
- **偵測範圍**: 預設掃描 40 格內的敵方單位 (`ASSESS_DANGER_MAX_DISTANCE`)。
- **脆弱度計算**: 統計能到達該城市的敵方單位總攻擊力，並考慮敵人的移動力。
- **反應行動**: 
    - 如果威脅值過高，AI 會將該城市的生產優先級強制切換為「防禦單位」。
    - 呼叫 `dai_choose_defender_versus()`：模擬與最強威脅單位戰鬥，選取預期損失（HP Loss）最小的兵種。

## 2. 擊殺慾望公式：`kill_desire()`
這是 AI 決定是否攻擊某個目標的數學核心，位於 `ai/default/daiunit.c`。

### 2.1 核心公式 (C 實作)
```c
desire = (benefit * attack - loss * vuln) * victim_count 
         * SHIELD_WEIGHTING / (attack + vuln * victim_count);
```
- **參數解析**:
    - `benefit`: 擊殺後的收益。對於城市，採用 `CITY_CONQUEST_WORTH` (城市價值 * 0.9 + 補償係數)。
    - `attack`: 我方攻擊力（通常是平方值）。
    - `loss`: 如果我方單位被摧毀，損失的產能 (Shields)。
    - `vuln`: 我方單位的脆弱性（敵方防禦力）。
    - `victim_count`: 目標格內的單位數量（AI 喜歡一石多鳥）。

### 2.2 邏輯意義
AI 不會盲目攻擊。只有當「預期收益 (`benefit * attack`)」遠大於「預期損失 (`loss * vuln`)」時，擊殺慾望才會為正值。這解釋了為什麼 AI 傾向於用高攻擊力單位（如大砲）攻擊，而非低勝算的自殺攻擊。

## 3. 戰略調度：攤銷與延遲 (`military_amortize`)
位於 `ai/default/daitools.c`。

AI 會考慮「時間成本」。如果一個目標非常誘人但距離太遠，其權重會被攤銷：
```python
def military_amortize(value, travel_delay, build_time):
    # 權重隨著到達時間的增加而指數級下降
    return amortize(value, travel_delay + build_time)
```
這保證了 AI 會優先處理眼前的威脅，而非為了遠方的利潤而讓後方空虛。

## 4. 戰術狀態：狂暴模式 (`dai_military_rampage`)
當一個軍事單位正在前往戰略目標的途中，它會進入「狂暴模式」：
- 如果路徑鄰近格出現敵方弱小單位（如工、探索者），且擊殺機率極高，單位會脫離原定路徑進行「順手一擊」。
- **門檻檢查**: 狂暴攻擊的期望收益必須大於 `BODYGUARD_RAMPAGE_THRESHOLD`。

## 5. 協同作業：保鏢系統 (`aiguard.c`)
- **請求機制**: 脆弱單位（如開拓者、外交官）在移動前會呼叫 `dai_gothere_bodyguard()`。
- **等待邏輯**: 如果目標區域危險，單位會原地待命，直到系統派遣的軍事單位（保鏢）到達同一格。
- **任務綁定**: 保鏢的任務會切換為 `AIUNIT_ESCORT`，其移動完全同步於被保護者。

## 6. 工程見解
- **平方價值模型**: 攻擊與防禦力的評估通常使用平方值，這與蘭徹斯特平方定律 (Lanchester's Square Law) 吻合，精確模擬了大規模軍隊對抗時的戰力差距。
- **死路預判**: AI 在規劃軍事路徑時具備初步的 Look-ahead，會避開死胡同。
- **角色分離**: AI 單位明確區分 `CT_ATTACKER` (攻擊者) 與 `CT_DEFENDER` (防守者)，這在 ruleset 解析時就已經完成。
