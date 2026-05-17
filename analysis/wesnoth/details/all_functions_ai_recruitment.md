# Wesnoth 全函數工程解析：AI 招募與經濟模型 (`recruitment.cpp`)

本文件窮舉並解析了 `src/ai/default/recruitment.cpp` 中的所有函數。此模組構成了一個具備經濟預測與對手分析能力的資源排程引擎。

---

## 1. 核心生命週期與 RCA 介面

### 1.1 `recruitment(...)` (建構子)
- **工程語義**：初始化招募模組。綁定 RCA 上下文與 WML 配置設定。

### 1.2 `to_config()`
- **工程語義**：物件序列化 (Serialization)。將 AI 的內部狀態（如預期招募清單）轉為 WML 格式以利存檔。

### 1.3 `evaluate()`
- **工程語義**：RCA 框架的評估子。
- **演算法細節**：
  - 檢查當前黃金是否小於最便宜單位的成本。若是，回傳 $0$ 分。
  - 若處於 `SAVE_GOLD` 狀態且未達解鎖回合，回傳極低分。
  - 若領袖處於被攻擊範圍，回傳高分（強制觸發防禦招募）。
  - 一般情況下回傳標準權重，與其他 RCA 任務（如攻擊、移動）競爭執行權。

### 1.4 `execute()`
- **工程語義**：RCA 框架的執行子。
- **演算法細節**：
  - 內部執行一個 `do...while` 迴圈。
  - 呼叫 `get_most_important_job()` 取得最優先招募指令。
  - 比較「召回老兵 (`execute_recall`)」與「招募新兵 (`execute_recruit`)」的效益。
  - 執行後，若遊戲狀態改變（招募成功），觸發重新評估。

---

## 2. 行動執行與評估

### 2.1 `execute_recall(...)` & `execute_recruit(...)`
- **工程語義**：實際對遊戲引擎發出召回或招募指令。
- **演算法細節**：呼叫 `check_recall_action` 等模擬函數，確認地形合法、空間未被佔用後，正式扣除金幣並生成單位實體。

### 2.2 `recall_unit_value(...)`
- **工程語義**：老兵殘值評估。
- **演算法細節**：計算老兵的經驗值比例與自帶的特質 (Traits)。若該綜合價值低於召回所需的固定金幣（通常為 20G），則判定召回不划算。

### 2.3 `get_average_defense(u_type)`
- **工程語義**：計算防禦力期望值。
- **演算法細節**：遍歷 `important_hexes_`（前線），根據該兵種在這些地形上的迴避率，求出加權平均防禦力。這讓 AI 能判斷該兵種是否適應當前戰場。

### 2.4 `get_cost_map_of_side(side)`
- **工程語義**：取得特定陣營的移動力成本圖（用於計算支援速度）。

---

## 3. 戰場熱圖與統計 (Heuristics Data Gathering)

### 3.1 `update_important_hexes()`
- **工程語義**：空間特徵點採樣。
- **演算法細節**：將地圖上的村莊、雙方領袖、敵軍集群所在位置標記為「重要座標」。這些座標的地形將主導後續的兵種選擇。

### 3.2 `show_important_hexes()`
- **工程語義**：除錯渲染 (Debug Overlay)，在 UI 上畫出上述採樣點。

### 3.3 `update_average_lawful_bonus()`
- **工程語義**：時間變量聚合。計算晝夜變化帶來的平均陣營傷害修正。

### 3.4 `update_average_local_cost()`
- **工程語義**：計算招募清單中所有單位的價格中位數/平均值，用於評估購買力。

### 3.5 `update_own_units_count()` & `update_scouts_wanted()`
- **工程語義**：狀態統計。計算己方陣容比例，判斷是否缺乏高機動單位以探索未解鎖地圖 (Fog)。

---

## 4. 戰鬥相剋矩陣 (Counter-Matrix Analysis)

### 4.1 `do_combat_analysis(leader_data)`
- **工程語義**：構建兵種優勢權重圖。
- **演算法細節**：掃描所有已知敵軍，對每一個己方可招募單位，累加其對抗所有敵軍的 `compare_unit_types` 分數。總分越高，代表該單位對敵方陣容的整體壓制力越強。

### 4.2 `compare_unit_types(a, b)`
- **工程語義**：一對一決鬥期望值。
- **演算法細節**：模擬兵種 A 攻擊兵種 B，計算 $(P_{kill\_A} \cdot Value_B) - (P_{kill\_B} \cdot Value_A)$。

### 4.3 `do_similarity_penalty(...)`
- **工程語義**：邊際效用遞減 (Diminishing Marginal Utility) 計算。
- **演算法細節**：若己方已存在大量單位 A，則在最終矩陣中，單位 A 的招募分數會被減去一個懲罰項。這保證了 AI 會建立多樣化的混合兵種陣容。

### 4.4 `do_randomness(...)`
- **工程語義**：引入高斯/均勻分佈的白噪聲，防止 AI 行為被玩家輕易預測。

---

## 5. 經濟預測與狀態機 (Economic Forecasting & FSM)

### 5.1 `get_estimated_income(turns)`
- **工程語義**：現金流量預測模型。
- **演算法細節**：計算 $Income = (Villages \cdot Village\_Income - Upkeep) \cdot turns$。

### 5.2 `get_estimated_unit_gain()` & `get_estimated_village_gain()`
- **工程語義**：基於歷史斜率的線性預測，猜測未來兵力與資源的成長率。

### 5.3 `update_state()`
- **工程語義**：有限狀態機 (FSM) 狀態轉移。
- **演算法細節**：
  - 讀取 `get_estimated_income(5)`。
  - 若未來 5 回合收益小於 0 且當前金幣不足，切換狀態至 `SAVE_GOLD`。
  - 若金幣溢出上限，切換至 `SPEND_ALL_GOLD`。

---

## 6. 任務管理與介面過濾 (Job Management)

下列函數處理 WML 中預設的招募指令（例如：強制 AI 開局先招募兩個弓箭手）。

- `get_most_important_job()`：優先權佇列 (Priority Queue) 頂部彈出。
- `integrate_recruitment_pattern_in_recruitment_instructions()`：解析正則表達式或列表，合併任務。
- `leader_matches_job(...)` / `recruit_matches_job(...)` / `recruit_matches_type(...)`：屬性交集檢查 (Intersection Check)。
- `limit_ok(...)`：檢查全域計數器，確認招募量是否達到硬上限。
- `remove_job_if_no_blocker(...)`：垃圾回收 (Garbage Collection)，清除過期任務。
- `get_cheapest_unit_cost_for_leader(...)` / `handle_recruitment_more(...)` / `is_enemy_in_radius(...)`：提供給決策樹的邊界檢查輔助函數。

### 6.1 監聽器與切面 (Observers & Aspects)
- `recruit_situation_change_observer` 系列：採用觀察者模式 (Observer Pattern)。當 WML 腳本強制修改招募清單，或發生事件導致金幣改變時，觸發 dirty flag，通知 RCA 重新計算。
- `recruitment_aspect` 系列：處理 `[aspect]` WML 節點，負責建立招募數量限制 (`create_limit`) 與任務佇列 (`create_job`) 的實體化。
