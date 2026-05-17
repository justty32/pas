# AI 專題 1：核心決策引擎與宏觀調控 (源碼剖析)

Freeciv AI 的全局策略由「國庫管理」與「科技路徑」兩大支柱組成。本文件深入剖析其底層實作邏輯。

## 1. 宏觀經濟調控：`dai_manage_taxes()`
位於 `ai/default/daihand.c`。這是 AI 每個回合調整稅率（金錢、科研、奢華度）的決策中樞。

### 1.1 決策流水線
1.  **數據聚合**: 呼叫 `dai_calc_data()` 統計全帝國的總貿易額、總支出與目前收入。
2.  **生存底線 (Bankruptcy Check)**:
    *   計算 `rate_tax_min`: 確保金錢收入足以覆蓋單位維護費與建築支出。
    *   AI 會考慮目前存款：如果存款豐富，可以容忍短期的赤字（`AI_GOLD_RESERVE_MIN_TURNS`）。
3.  **科研底線**: 如果規則集啟用了科技維護費，則計算 `rate_sci_min` 避免科技倒退。
4.  **增長路徑 (Celebration/Rapture)**:
    *   如果具備「慶典成長」獎勵，AI 會模擬將所有剩餘貿易額投入「奢華度 (Luxury)」。
    *   使用 `cm_query_result()` (城市管理查詢) 評估在此稅率下，有多少城市能進入「慶典」狀態。
    *   如果預期收益夠高，AI 會切換到慶典模式，犧牲科研換取人口爆發。
5.  **平衡平衡**: 若非慶典模式，則根據性格權重分配剩餘貿易額至科研。

### 1.2 核心公式 (偽代碼)
```python
def dai_manage_taxes(player):
    trade, expenses, income = calc_empire_data(player)
    
    # 尋找不破產的最小稅率
    rate_tax_min = find_min_tax(expenses, player.gold_reserves)
    
    # 尋找維持科研的最小稅率
    rate_sci_min = find_min_sci(tech_upkeep, player.bulb_reserves)
    
    if player.can_celebrate():
        # 測試極限奢華度
        success_count = simulate_rapture(luxury = 100 - min_tax - min_sci)
        if success_count > threshold:
            apply_rates(tax=min_tax, sci=min_sci, lux=max_lux)
            return

    # 預設模式：優先科研
    apply_rates(tax=min_tax, sci=(100-min_tax), lux=0)
```

## 2. 科技策略引擎：`dai_manage_tech()`
位於 `ai/default/daitech.c`。Freeciv AI 使用動態權重系統來決定研究路徑。

### 2.1 效用評估機制 (`dai_tech_effect_values`)
AI 會掃描所有尚未習得的技術，並計算其「需求值 (Want)」：
- **效果價值**: 遍歷該技術啟動的所有 `EFT_` (Effects)。例如增加產量、降低污染。
- **單位/建築啟動**: 呼叫 `want_tech_for_improvement_effect()`。如果該技術能解鎖 AI 渴望的建築，則按比例增加權重。
- **魔術轉換因子**: 程式碼中使用 `v * 14 / 8` 將建築的需求值轉換為科技的需求值。這是一個經過實驗微調的經驗係數。

### 2.2 政府與體制誘因 (`dai_manage_government`)
AI 會特別標記某些關鍵技術：
- 如果當前體制是初期的落後體制（如專制 Despotism），AI 會大幅提升通往先進體制（如共和國、民主）的技術權重。
- **體制加成公式**: `want = base_govt_val + 25 * current_turn`。這保證了隨著回合數增加，AI 換代體制的慾望會指數級增長。

### 2.3 決策與切換懲罰
在 `dai_select_tech()` 中：
- AI 會將總權重除以城市數量，平衡大帝國與小國家的研究需求。
- **切換懲罰**: 如果 AI 想要更換目前正在研究的技術，新技術的 `want` 必須比當前高出 `penalty`（已投入的燒瓶量），避免資源浪費。

## 3. 工程見解
- **線性簡化**: `dai_manage_taxes` 假設全帝國是一個巨大的單一城市進行初步計算，這大大節省了計算稅率時的 CPU 消耗。
- **解耦設計**: 科技權重的計算 (`daitech.c`) 與具體的軍事/城市決策解耦。軍事模組只需要提高某種單位的「Want」，科技引擎就會自動反應在相關技術的優先級上。
- **前瞻性**: `turns_for_rapture` 參數顯示 AI 在做決策時會預留約 10 回合的經濟緩衝，展現了具備深度的策略規劃能力。
