# Unciv AI 戰略全景深度剖析：全方位決策架構

Unciv 的 AI 是一套高度模組化且基於權重評分 (Weight-based Scoring) 的系統。它透過 `PersonalityValue`（領袖性格）來驅動所有的決策邏輯，從宏觀的勝利路徑選擇到微觀的地塊改良。

---

## 1. 戰略指揮中心：`NextTurnAutomation`

AI 的回合邏輯由 `automateCivMoves` 統一管理，執行順序如下：
1.  **外交應對**：處理玩家或其他 AI 的請求（貿易、宣戰、友誼）。
2.  **外交提案**：主動發起貿易、大使館、開放邊境或研究協議。
3.  **科技與政策**：決定本回合的研究目標。
4.  **金錢分配**：調用 `UseGoldAutomation` 買地、買建築或買單位。
5.  **單位行動**：執行最消耗效能的尋路與戰鬥邏輯。
6.  **城市管理**：決定生產項目。
7.  **擴張決策**：訓練開拓者 (Settler) 並尋找新城市選址。

---

## 2. 建設決策邏輯：權重與動機 (`ConstructionAutomation`)

AI 透過「候選清單評分」來決定生產什麼。
- **基礎評分**：計算建築產出的數值（糧、錘、金、瓶、琴）並結合領袖性格。例如：愛好科學的領袖會給予瓶子產出更高的權重。
- **勝利導向**：如果啟用特定勝利，AI 會給予「勝利里程碑建築」極高的額外加成 (+20)。
- **軍事平衡**：如果正在開戰或力量不足，AI 會動態提升軍事單位的產權重。
- **補給限制**：如果單位補給超過上限，AI 會停止生產軍事單位以防經濟崩潰。

---

## 3. 外交心理與博弈 (`DiplomacyAutomation`)

AI 的外交並非隨機，而是基於「好感度 (Opinion)」與「威脅評估 (Threat Assessment)」。
- **友誼宣告 (DoF)**：AI 會計算動機分數。如果朋友太多或即將計劃攻擊對方，AI 會拒絕友誼。
- **大使館與邊境**：AI 明白「開邊」可能被對方用來偵查或突襲。如果對方很強大或我方打算攻擊對方，會拒絕開放邊境。
- **軍事Ultimatum**：AI 會偵測國境邊緣的敵軍密度。如果人類玩家在邊境集結超過 10 個單位且力量佔優，AI 會發出警告。

---

## 4. 擴張與城市選址 (`CityLocationTileRanker`)

AI 如何選擇新城市的位置？
- **資源優先**：**唯一奢侈資源**是最高權重 (+10)。AI 為了快樂度會不惜遠行去圈佔新資源。
- **地形加成**：
    - **河流 (+20)**：極高權重，為了早期的水車與貿易加成。
    - **沿海 (+3)** & **丘陵 (+14)**：為了防禦與產能。
    - **山脈 (+5)**：為了天文台。
- **距離懲罰**：AI 偏好距離首都 4-6 格的位置。距離 3 格以內會受到巨大懲罰（-25），以避免城市間的格子重疊與產能損耗。

---

## 5. 工人自動化與地塊改良 (`WorkerAutomation`)

工人 AI 的目標是「產能最大化與資源解鎖」。
- **奢侈品優先**：為了維持帝國快樂度，工人會優先前往改良奢侈資源。
- **節奏 (Tempo) 優化**：AI 懂得「砍樹」 (Forest Chopping) 來獲取即時的產能加成，這在早期衝刺奇觀或單位時非常關鍵。
- **道路網絡**：AI 會使用 `RoadBetweenCitiesAutomation` 規劃城市間的最短路徑，並優先連接首都與分城以獲取貿易路線金錢。

---

## 6. 總結：AI 的行為邏輯圖

| 決策層級 | 核心考量 | 驅動機制 |
| :--- | :--- | :--- |
| **戰略 (Strategic)** | 勝利條件、帝國規模 | `PersonalityValue` 權重 |
| **經濟 (Economic)** | 資源解鎖、城市產能 | `rankStatsValue` 評分函數 |
| **外交 (Diplomatic)** | 力量平衡、歷史恩怨 | `Opinion` 衰減與事件紀錄 |
| **擴張 (Expansion)** | 奢侈資源、領土完整 | 地塊價值分析 (Ranking Map) |

---
*原始碼位置參考：*
- `com.unciv.logic.automation.city.ConstructionAutomation`
- `com.unciv.logic.automation.civilization.NextTurnAutomation`
- `com.unciv.logic.automation.unit.CityLocationTileRanker`
- `com.unciv.logic.automation.unit.WorkerAutomation`
