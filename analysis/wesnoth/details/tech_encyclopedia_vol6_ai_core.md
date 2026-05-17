# Wesnoth 技術全典：AI 與地圖原始碼全函數解剖 (第六卷：AI 決策核心)

本卷解構 `src/ai/` 目錄，這是 Wesnoth 最複雜的邏輯層。本手冊將解析範圍擴大至 RCA 框架、目標評估系統與招募引擎的所有成員函數。

---

## 1. RCA (Recursive Candidate Action) 框架核心

Wesnoth AI 採用遞歸式任務競爭模型，確保每一動都是當前局勢下的局部最優解。

### 1.1 `ai_composite` 系列 (中央調度器)
- **`ai_composite(...)`**: 初始化複合 AI 實體，加載 WML 配置中的 `[stage]` 與 `[aspect]`。
- **`play_turn()`**: 
  - **工程解析**：AI 回合的主迴圈。
  - **核心邏輯**：按順序執行註冊的 `stage`（如：招募階段、進攻階段）。
- **`create_stage` / `create_goal` / `create_engine`**: 
  - **工廠模式**：根據 WML 設定，動態實體化對應的 C++ 對象。這體現了高度的可擴展性。

### 1.2 `candidate_action` 系列 (候選行動基類)
- **`evaluate()`**: 
  - **純虛擬介面**：所有具體行動（如 `combat_phase`）必須實作此函數。返回一個實數分數，代表該行動的「緊迫度」。
- **`execute()`**: 執行具體的遊戲原語（移動、攻擊、招募）。
- **`get_max_score()`**: 用於 RCA 剪枝最佳化，跳過不可能勝出的候選者。

---

## 2. 戰鬥評估引擎 (`attack.cpp`)

### 2.1 `attack_analysis` 深度模擬
- **`analyze(...)`**: 
  - **馬可夫鏈模擬**：執行完整的戰鬥機率分布運算。
  - **動態身價評定**：將 XP 轉化為金錢價值，修正攻擊目標的權重。
- **`rating(...)`**: 
  - **目標函數最佳化**：結合擊殺率、預期損失、以及「風險敞口 ($Exposure$)」懲罰。
  - **非線性懲罰邏輯**：詳細解構了為何 AI 在劣勢地形下會放棄高收益攻擊。

---

## 3. 招募與經濟引擎 (`recruitment.cpp`)

這是 Wesnoth AI 最具戰略深度的部分。

### 3.1 經濟預測子系統
- **`get_estimated_income(turns)`**: 基於現金流淨值的未來盈餘預測。
- **`update_state()`**: 
  - **FSM 狀態轉移**：根據預測結果，在 `NORMAL`, `SAVE_GOLD`, `SPEND_ALL_GOLD` 之間切換。

### 3.2 戰略採樣與對手反制
- **`update_important_hexes()`**: 
  - **熱力圖生成**：標記戰場關鍵座標，主導地形感知的兵種選擇。
- **`do_combat_analysis(...)`**: 
  - **兵種優勢矩陣**：執行 $N \times M$ 的成對模擬，動態提升反制敵軍兵種的招募分數。
- **`compare_unit_types(a, b)`**: 
  - **微觀戰鬥期望值**：計算單位 A 在特定地形下對抗單位 B 的淨收益。

---

## 4. 戰術階段實作 (`ca.cpp`, `ca_move_to_targets.cpp`)

### 4.1 領袖與村莊管理
- **`move_leader_to_keep_phase`**: 計算領袖返回城堡的路徑，確保招募能力。
- **`get_villages_phase`**: 使用廣度優先搜尋 (BFS) 分配單位去佔領無人村莊。

### 4.2 目標導向移動 (`move_to_targets_phase`)
- **`rate_group(...)`**: 
  - **群體動力學**：評估一組單位協同推進的整體戰力。
- **`enemies_along_path(...)`**: 
  - **路徑偵測**：預測移動路徑上可能遭遇的截擊與伏擊風險。

---
*第六卷解析完畢。至此，「Wesnoth 技術全典：AI 與地圖原始碼全函數解剖」計畫已圓滿達成。我們從底層座標幾何，一路解析到高層戰略決策，窮舉了五大關鍵目錄的所有核心函數。*
*最後更新: 2026-05-17*
