# Freeciv AI 戰鬥策略與勝率評估 (源碼剖析)

Freeciv AI 的單位戰鬥策略並非隨機，而是一套嚴謹的機率預估與利益最大化模型。它結合了微觀的機率計算與宏觀的戰略攤銷。

## 1. 戰鬥評估的核心：勝率預測 (`unit_win_chance`)

在發動攻擊前，AI 必先呼叫 `common/combat.c` 中的 `unit_win_chance()`。
- **計算維度**: 考慮雙方的基礎攻擊/防禦、經驗等級（Veteran）、生命值（HP）、火力（Firepower）以及地形加成。
- **邏輯用途**: 在 `ai/default/daiunit.c` 中，AI 會走訪潛在目標，若勝率低於特定門檻（除非極度絕望），AI 會拒絕進攻。

## 2. 進攻決策模型：擊殺慾望 (`kill_desire`)

這是 AI 的「戰勝利潤表」。
```c
/* ai/default/daiunit.c:341 */
desire = (benefit * attack - loss * vuln) * victim_count 
         * SHIELD_WEIGHTING / (attack + vuln * victim_count);
```
- **參數深度解析**:
    - **`benefit` (利潤)**: 目標的價值（如城市、高價單位）。
    - **`attack` (優勢)**: 我方攻擊力（平方），代表我方輸出能力。
    - **`loss` (代價)**: 我方單位一旦被反擊摧毀所損失的生產力 (Shields)。
    - **`vuln` (風險)**: 敵方防禦力（平方），代表我方受傷的可能性。
- **博弈邏輯**: 如果 `benefit * attack` (預期收益) 小於 `loss * vuln` (預期損失)，`desire` 將變為負值。AI 將選擇原地待命或尋找下一個目標。

## 3. 兵種偏好與攻擊渴望 (`dai_unit_attack_desirability`)

在生產單位時，AI 透過一個啟發式公式評估哪種兵種最適合進攻：
```c
/* ai/default/daimilitary.c:1031 */
desire = punittype->hp * punittype->move_rate * punittype->firepower * punittype->attack_strength;
desire += punittype->defense_strength;
if (utype_has_flag(punittype, UTYF_IGTER)) desire *= 1.5; // 忽略地形移動加成
```
- **移動力優先**: AI 顯著偏好高移動力（`move_rate`）單位，因為它們能更快到達前線，且具備更高的戰術靈活性。
- **忽視地形 (IGTER)**: 具備忽略地形懲罰屬性的單位（如開拓者、特種部隊）會獲得 50% 的權重溢價。

## 4. 戰術執行：尋路與截擊邏輯

### 4.1 尋路與進攻同步 (`dai_unit_move_or_attack`)
在 `daitools.c` 中，移動與攻擊被封裝在一個原子操作中：
1. **路徑規劃**: 使用 PF (Path-Finding) 引擎規劃到達目標的路徑。
2. **最後一哩路**: 判斷當前步數是否為路徑終點：
    - **是**: 呼叫 `dai_unit_attack()` 發動攻擊。
    - **否**: 呼叫 `dai_unit_move()` 向前推進。

### 4.2 特殊戰術：狂暴與防空
- **狂暴模式 (`dai_military_rampage`)**: 單位在執行 GOTO 指令時，會自動掃描鄰近格。如果發現勝率近乎 100% 且能「順便」擊殺的敵人，它會偏離路徑進行斬首。
- **攔截與防空**: AI 會根據 `unittype->targets` 標籤，派遣具備防空能力的單位（如戰鬥機、防空砲）攔截敵方飛行單位。

## 5. 撤退與恢復 (`dai_unit_recovery`)
AI 單位不會戰死到最後一兵一卒：
- **生命值門檻**: 單位受傷後，AI 會計算其在下一格被擊殺的機率。
- **回港維修**: 受傷單位會暫時切換任務為 `AIUNIT_RECOVER`，優先尋找己方城市或要塞（Fortress）進行駐紮回血。

## 6. 工程見解
- **平方價值法則**: Freeciv 使用平方值（`attack^2` vs `defend^2`）來模擬戰鬥，這能更明顯地拉開科技落差，鼓勵 AI 使用先進武器碾壓低科技文明。
- **延遲獎勵與攤銷**: AI 在計算進攻慾望時，會將「移動到那裡所需的輪數」作為分母。這讓 AI 表現得非常現實：近處的敵軍威脅永遠高於遠方的肥肉。
