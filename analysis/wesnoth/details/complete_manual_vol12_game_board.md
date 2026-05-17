# Wesnoth 技術全典：世界容器與狀態管理 (第十二卷)

本卷解構 `src/game_board.cpp` 與 `src/game_state.cpp`。這是 The Battle for Wesnoth 遊戲引擎的「世界觀容器」，所有的地圖、單位、AI 與玩家皆被封裝於此。

---

## 1. 遊戲棋盤核心 (`game_board.cpp`)

`game_board` 是遊戲中最重要的狀態機 (State Machine) 容器，負責回合的推進與空間實體的擁有權。

### 1.1 回合生命週期控制 (Turn Lifecycle)
- **`game_board::new_turn(player_num)`**: 
  - **狀態重置**：當輪到某個陣營時，此函數會遍歷該陣營的所有單位，恢復其移動力 (Movement Points)、攻擊次數，並重置「已招募」狀態。
  - **環境事件**：觸發由於時間推移產生的變化（如：晝夜交替導致的地形光影更新）。
- **`game_board::end_turn(player_num)`**: 
  - **結算觸發**：在回合結束時進行狀態檢查。
- **`game_board::heal_all_survivors()`**: 
  - **全域恢復**：處理回合間的靜態治療（如村莊恢復、友軍薩滿治療、或是重生 (Regeneration) 特性），並嚴格按照治療規則（如中毒狀態下優先解毒而不補血）進行狀態寫入。

### 1.2 實體與空間交互 (Entity-Spatial Interaction)
- **`game_board::find_visible_unit(loc, current_team, see_all)`**: 
  - **視野權限系統**：回傳特定坐標上的單位，但**嚴格遵循戰爭迷霧與隱形規則**。如果單位處於森林中且具備「伏擊 (Ambush)」特性，對於非盟友的 `current_team`，此函數將回傳空迭代器。這是 AI 無法作弊透視隱形單位的核心原因。
- **`game_board::try_add_unit_to_recall_list(...)`**: 
  - **跨場景狀態持久化**：戰役模式中，將生還的單位移出當前物理地圖，封裝並寫入「召回清單 (Recall List)」中，保留其經驗值與特質供下一關使用。

### 1.3 暫時性實體管理器 (RAII 模式)
在戰鬥預演或 AI 模擬中，系統需要頻繁地在棋盤上「試擺」單位。
- **`temporary_unit_placer` / `temporary_unit_remover` / `temporary_unit_mover`**: 
  - **工程解析**：這些類別利用 C++ 的 RAII (Resource Acquisition Is Initialization) 機制。在建構子 (Constructor) 中改變地圖上的單位位置，並在解構子 (Destructor) 中自動將狀態完美復原。這保證了 AI 在執行數萬次 `analyze_attack` 模擬時，遊戲棋盤的狀態絕對不會被污染。

---

## 2. 遊戲狀態封裝 (`game_state.cpp`)

`game_state` 是 `game_board` 的上層包裝，包含了棋盤與時間 (Time of Day)。

- **`game_state::write_config(cfg)`**: 
  - **全域序列化 (Serialization)**：將整個世界的快照（包含地圖字串、所有單位的狀態、所有玩家的金幣、當前時間與回合數）寫入 WML `[snapshot]` 節點。這就是存檔 (Savegame) 機制的底層實作。

---
*第十二卷解析完畢。遊戲棋盤提供了 AI 與地圖交互的物理空間，而下一卷我們將深入探討這個空間中活躍的實體——單位 (Units) 與其複雜的技能系統。*
*最後更新: 2026-05-17*
