# Freeciv AI 系統深度分析：總綱分析報告

Freeciv 的 AI 系統是一個複雜的、多層次的決策引擎，旨在模擬人類玩家在策略遊戲中的各種行為。它採用了模組化架構，將決策邏輯拆分為多個專門的顧問 (Advisors) 與控制模組。

## 1. AI 系統架構概觀

Freeciv AI 的核心邏輯主要分佈在兩個目錄：
- `freeciv/ai/`: 包含具體的 AI 實作邏輯。
    - `default/`: 目前最成熟的預設 AI 實作（DAI - Default AI）。
    - `classic/`: 較舊、更接近原始 Civilization 邏輯的實作。
- `freeciv/server/advisors/`: 包含「顧問系統」，這些模組提供中立的建議，不僅供 AI 使用，有時也協助人類玩家（如自動單位探索、自動工人）。

## 2. 核心組件與職責

### 2.1 決策控制層 (Decision Handlers)
以 `ai/default/daihand.c` 為核心，負責：
- **回合管理**: 處理回合開始與結束的宏觀操作。
- **資源分配**: 計算金錢 (Gold)、科研 (Science) 與奢華度 (Luxury) 的稅率。
- **太空競賽管理**: 決定何時建造與發射太空船。

### 2.2 城市與經濟顧問 (Domestic & City Advisors)
- `ai/default/daicity.c`: 決定城市要建造什麼（單位、建築或奇觀）。
- `ai/default/daidomestic.c`: 管理城市的內政需求。

### 2.3 軍事與戰術引擎 (Military & Tactical AI)
- `ai/default/daimilitary.c`: 全局軍事策略，包含威脅評估與進攻目標選擇。
- `ai/default/daiunit.c`: 具體單位的行動邏輯（移動、攻擊、撤退）。
- `ai/default/daiferry.c`: 複雜的海運邏輯，處理單位過海的調度。

### 2.4 外交與科研 (Diplomacy & Tech)
- `ai/default/daidiplomacy.c`: 與其他玩家簽訂條約、宣戰或貿易。
- `ai/default/daitech.c`: 決定技術樹的研究路徑。

## 3. 運作哲學：基於權重的效用評估 (Weight-based Evaluation)

Freeciv AI 並非基於簡單的 IF-THEN 規則，而是大量使用 **效用函數 (Utility Functions)**。對於每一項候選行動（如建造某個建築、攻擊某個城市），AI 會計算一個數值化的權重，並選擇權重最高（最符合當前利益）的行動。這種設計使其具備極強的擴展性。

## 4. 數據流向 (Data Flow)

1. **感測 (Perception)**: 透過 `daidata.c` 掃描地圖，獲取資源、敵人分佈等情報。
2. **評估 (Evaluation)**: 顧問系統針對感測數據計算各種行動的權重。
3. **執行 (Action)**: 單位控制層根據最高權重目標呼叫 `unithand.c` 執行具體操作。
