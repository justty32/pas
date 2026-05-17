# Wesnoth 技術全典：行動結算與 Undo 歷史紀錄引擎 (第十卷)

本卷窮舉並解構 `src/actions/` 目錄下的**所有**檔案及函數。這是遊戲引擎從 AI 或玩家接收指令後，進行「合法性驗證、物理結算、狀態快照與撤銷」的核心層。

---

## 1. 戰鬥結算與機率引擎 (`attack.cpp`)

這是遊戲中負責處理傷害、命中與戰鬥狀態推進的核心。

- **`battle_context::simulate(prev_def)`**：
  - **工程解析**：給定攻擊方與防禦方的 `battle_context_unit_stats`，根據雙方武器的基礎傷害、命中率與特技（如：吸血、減速），使用動態規劃 (Dynamic Programming) 建立雙方的戰後血量分佈矩陣 (HP Distribution Matrix)。
- **`battle_context::better_attack(...)` / `better_defense(...)`**：
  - **武器選擇邏輯**：在擁有多把武器時，尋找使自身存活率最高或對手死亡率最高的武器組合。
- **`attack::unit_info::get_unit()` / `valid()`**：
  - **實體追蹤**：封裝單位的指標，避免在長時間的戰鬥動畫中，單位被其他事件（如 WML 腳本）殺死而造成懸空指標 (Dangling Pointer)。
- **`attack::perform_hit(attacker_turn, stats)`**：
  - **原子操作**：執行單次打擊。呼叫 RNG 決定是否命中，扣除血量，並處理「中毒 (Poison)」、「石化 (Petrifies)」等狀態機切換。
- **`attack::perform()`**：
  - **主迴圈**：控制整個交戰回合 (Combat Session)。包含動畫觸發、事件分發 (Fire Events) 以及單位經驗值 (XP) 的結算與升級觸發。

---

## 2. 空間移動與視野結算 (`move.cpp`, `vision.cpp`)

- **`move_unit_spectator::move_unit_spectator(units)`**：
  - **觀察者模式**：單位移動時並非瞬間瞬移，而是「逐格結算」。此類別監控單位在每一格的狀態。
- **`move_unit_spectator::add_seen_enemy(u)` / `get_ambusher()`**：
  - **伏擊中斷 (Ambush Interrupt)**：在移動途中，若發現原本隱形的敵軍，或踏入敵方 ZOC，觸發強制中斷邏輯，並更新可撤銷狀態。
- **`get_village(...)`**：
  - **資源結算**：檢查座標是否為村莊，並處理佔領權轉移與陣營經濟更新。
- **`shroud_clearer::calculate_jamming(new_team)`**：
  - **反向視野**：計算具備「干擾 (Jamming)」特性的單位如何重新覆蓋戰爭迷霧 (Fog of War)。
- **`shroud_clearer::clear_dest(dest, viewer)`**：
  - **光線投射 (Raycasting) 結算**：根據單位的視野半徑，清除目標座標周圍的迷霧與黑幕 (Shroud)，並處理 `[event] name=sighted`（看見敵軍事件）。

---

## 3. Undo 撤銷機制與歷史狀態機 (`undo.cpp`, `undo_action.cpp` 系列)

Wesnoth 提供強大的撤銷功能，這依賴於一個嚴密的命令模式 (Command Pattern) 歷史紀錄器。

- **`undo_list::add_dismissal(u)` / `add_auto_shroud(...)`**：
  - **動作壓棧**：將玩家或 AI 的任何微小動作壓入堆疊 (Stack)。
- **`undo_list::commit_vision()`**：
  - **不可逆檢查**：若某次移動「開啟了新視野」並看見了新敵軍，或發現了隱藏單位，則該次移動及其之前的動作會被**標記為不可撤銷**，以防止玩家作弊（走過去看一眼再 Undo）。
- **`undo_action_container::undo(side)`**：
  - **主撤銷迴圈**：從堆疊頂端彈出動作，呼叫多型介面執行逆操作。
- **`move_action::undo(side)`**：
  - **逆向結算**：將單位瞬間拉回原座標，並恢復原本佔領的村莊與移動力 (MP)。
- **`recruit_action::undo(side)` / `recall_action::undo(side)`**：
  - **資源回滾**：銷毀新生成的單位，並將花費的黃金 (Gold) 加回該陣營的國庫中。

---

## 4. 單位實體化 (`create.cpp`, `unit_creator.cpp`)

- **`find_recruit_location(...)` / `find_recall_location(...)`**：
  - **空間分配**：從領袖所在的城堡出發，使用 BFS 尋找最近且合法的招募空位 (Keep & Castle)。
- **`unit_creator::post_create(...)`**：
  - **生命週期掛載**：單位創建後，觸發進場動畫、套用初始特質 (Traits)，並將其正式註冊至 `game_board` 與 AI 視圖中。
- **`get_advanced_unit(u, advance_to)`** (`advancement.cpp`)：
  - **狀態變異**：處理經驗值滿後的晉升。繼承舊單位的 HP 比例與裝備，載入新兵種的素質，並處理分歧升級 (Branching Advancement)。

---
*第十卷解析完畢。本卷詳細拆解了所有改變遊戲世界物理狀態的原子操作。*
*最後更新: 2026-05-17*
