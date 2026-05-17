# Wesnoth 技術全典：Lua 腳本與 Micro AI 系統 (第十一卷)

Wesnoth 是一個高度資料驅動 (Data-Driven) 的引擎。雖然 C++ 提供了 RCA 框架（第五至第七卷所述），但真正讓 AI 行為豐富多變的，是實作在 `data/ai/` 目錄下的 **Lua AI** 與 **Micro AI** 系統。

本卷將解析 Wesnoth 腳本層如何利用 C++ 暴露的介面，實作出無數種專精的戰術行為。

---

## 1. Lua AI 基礎框架 (`data/ai/lua/`)

這些腳本直接繼承並實作了 RCA 框架的 `candidate_action` (CA)。

### 1.1 `ai_helper.lua` (腳本引擎工具箱)
這是所有 Lua AI 的基礎依賴函式庫。
- **`ai_helper.get_closest_enemy(loc)`**: 
  - **演算法**：封裝了 C++ 的路徑尋找，在腳本層提供 $O(N)$ 的最近敵軍空間搜尋。
- **`ai_helper.get_attack_combinations(...)`**: 
  - **組合數學**：窮舉目前所有可用的己方單位與敵方目標的配對，用於構建自訂的戰鬥評分矩陣。

### 1.2 `ca_village_hunt.lua` (村莊獵人 CA)
- **`evaluate()`**: 
  - 掃描全圖未佔領或敵方的村莊。根據村莊距離與單位移動力，算出一個 $Score \in [40, 60]$ 的分數（略低於進攻，略高於閒置）。
- **`execute()`**: 
  - 使用 C++ 暴露的 `ai.move_full(unit, best_village)` 執行移動。

### 1.3 `ca_retreat_injured.lua` (受傷撤退 CA)
- **觸發條件**：單位 HP < 50% 且周圍無醫療單位。
- **決策邏輯**：尋找最近的村莊或友方薩滿，並將沿途的敵方 ZOC (控制區) 代價設為無窮大，確保安全撤退。此 CA 的評分極高（通常設為 90），確保 AI 會優先保命。

---

## 2. 微型人工智慧系統 (Micro AIs)

Micro AIs 位於 `data/ai/micro_ais/cas/`。它們是高度專精、只負責**單一目標**的決策機器，通常被綁定在特定單位上（例如：一隻守門的狼、一個會打帶跑的刺客）。

### 2.1 守衛機制 (`ca_hang_out.lua`)
- **工程語義**：空間束縛系統 (Spatial Tethering)。
- **演算法**：
  - 給定一個錨點 (Anchor) 與半徑 $R$。
  - 單位若偵測到半徑 $R$ 內有敵軍，則啟動攻擊模式；若無敵軍或血量過低，則強制將尋路目標設為錨點，防止單位被玩家引誘 (Kiting) 離開防守位置。

### 2.2 刺客打帶跑 (`ca_assassin_move.lua`)
- **工程語義**：打了就跑 (Hit-and-Run) 狀態機。
- **邏輯設計**：
  - 攻擊後，不留在原地承受反擊。
  - `evaluate()` 會檢查該單位是否有剩餘移動力，並計算周圍能提供最高防禦或脫離敵人視野的坐標。
  - `execute()` 呼叫 `ai.move()` 將刺客隱藏回森林或村莊。

### 2.3 護衛任務 (`ca_protect_unit_*.lua`)
- **工程語義**：動態編隊演算法 (Dynamic Formation)。
- **核心機制**：
  - 一群單位被標記為「保鏢」，並設定一個「VIP 目標」。
  - 保鏢的 A* 尋路終點永遠被設定為 VIP 當前的坐標。
  - 透過 `ca_protect_unit_attack`，保鏢只會攻擊「能夠在下一回合打到 VIP」的敵軍，絕對不主動追擊其他無關目標。

### 2.4 動物本能 (`ca_forest_animals_*.lua`)
- **群集行為 (Swarm Logic)**：
  - 模擬如野豬 (Tuskers) 與幼豬 (Tusklets) 的行為。
  - 幼豬的尋路權重高度傾向於靠近母豬。若有玩家靠近幼豬，母豬的攻擊評分 (`aggression`) 會被強制拉到極大值，實現「保護幼崽」的生物學模擬。

---

## 3. C++ 與 Lua 的架構閉環

透過這十一卷的分析，我們看見了 Wesnoth 的技術全貌：
1. **底層 (C++)**：提供 A* 路徑搜尋、戰鬥機率分佈矩陣、地圖標量場生成等高效能的**物理原語 (Physical Primitives)**。
2. **中層 (C++ RCA)**：提供 `[candidate_action]` 競爭框架與基礎戰略（招募與推進）的**排程引擎 (Scheduling Engine)**。
3. **上層 (Lua/WML)**：利用 `Micro AI` 腳本，透過覆寫 `evaluate` 與 `execute`，實作了千變萬化的**具體行為 (Specific Behaviors)**。

這種**資料驅動 (Data-driven) 與腳本熱插拔 (Hot-pluggable)** 的架構，正是 Wesnoth 能夠維護 20 年並擁有無數 Mod 戰役的核心秘密。
