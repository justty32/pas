# AI 專題 2：城市管理與產能分配 (源碼剖析)

Freeciv AI 的城市管理核心在於平衡「立即生存」與「長期發展」。這透過一個精密的效用評估系統 (Want Evaluation) 來達成。

## 1. 城市決策流程：`dai_manage_cities()`
位於 `ai/default/daicity.c`。這是 AI 管理所有城市的頂層循環。

### 1.1 核心決策階段
1.  **緊急狀態檢測 (`CITY_EMERGENCY`)**: 檢查城市是否面臨叛亂 (Unhappy)、飢荒 (Food < 0) 或產能負值。
2.  **解救緊急狀態 (`resolve_city_emergency`)**:
    *   **土地接管**: 嘗試從鄰近的己方城市中奪取資源格。
    *   **解散單位**: 如果城市不快樂且支持著攻擊性單位，AI 會果斷解散這些單位以減輕維護負擔與不滿。
3.  **生產選擇 (`dai_city_choose_build`)**: 這是最核心的邏輯，決定城市目前的建造目標。

## 2. 生產價值評估：`base_want()` 與效用函數
AI 透過計算 `adv_want` (數值化的渴望度) 來決定建造什麼。

### 2.1 建築價值模擬 (`base_want`)
Freeciv AI 採用了一種「虛擬實驗」的方法來評估建築：
- **實作邏輯**:
    1.  暫時將該建築加入城市 (`city_add_improvement`)。
    2.  計算城市在擁有該建築後的「總價值」(`dai_city_want`)。
    3.  減去未建造前的價值 (`acity->worth`)，得到純粹的收益。
    4.  **擴展範圍**: 對於奇觀 (Wonders)，模擬範圍會擴展到全帝國的所有城市 (`city_range_iterate`)，加總所有城市從該奇觀獲得的增益。
    5.  實驗結束後將建築移除，恢復原狀。

### 2.2 城市價值計算 (`dai_city_want`)
這是一個多維權重公式，反映了 AI 對各種資源的重視程度：
```python
# 偽代碼：城市總價值模型
def dai_city_want(city, player):
    want = 0
    # 資源產出加權
    want += city.food_surplus * player.food_priority
    want += city.shield_surplus * player.shield_priority
    want += city.science_output * player.science_priority
    
    # 特殊邏輯：金錢溢價
    if player.tax_rate > 50:
        # 當稅率極高時，暗示國庫空虛，金錢的權重會額外放大
        want += city.gold_output * player.gold_priority * (tax - 40) / 14.0
    else:
        want += city.gold_output * player.gold_priority
        
    return want
```

## 3. 奇觀與技術聯動
- **技術前瞻性**: 在 `adjust_improvement_wants_by_effects` 中，即便目前不能建造某個強力建築，AI 也會計算其潛在收益。
- **渴望轉移**: 如果一個尚未解鎖的技術能開啟高收益建築，AI 會將該收益按比例（實驗常數如 `5/4`）轉移給科技樹研究路徑，這解釋了為何 AI 會為了某個奇觀而瘋狂衝刺特定科技。

## 4. 資源變現 (`dai_city_sell_noncritical`)
AI 會在急需現金時出售非關鍵建築。
- **關鍵建築定義**: 包含城牆 (`EFT_DEFEND_BONUS`) 或能產生實際收益的生產設施。
- **冗餘清理**: AI 會偵測因技術進步而失效的建築並將其售出換取金錢。

## 5. 工程見解
- **試錯法 (Simulation-based Evaluation)**: AI 不依賴寫死的規則，而是透過「試蓋」來評估收益。這種設計使其能自動適應任何複雜的 ruleset（Mod），因為它始終是在測量真實的數值變化。
- **非線性權重**: 金錢權重隨著稅率非線性增長的設計（`tax - 40 / 14.0`），使 AI 在經濟崩潰邊緣表現出極強的求生欲。
- **解耦的顧問**: 建築價值計算獨立於軍事需求。如果軍事顧問提高了城市對「防守」的渴望，城牆的 `base_want` 自然會提升，不需要在建築邏輯中寫死戰爭檢查。
