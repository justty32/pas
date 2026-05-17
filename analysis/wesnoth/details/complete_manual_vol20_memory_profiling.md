# Wesnoth 技術全典：CPU 效能與記憶體生命週期剖析 (第二十卷)

作為一款回合制遊戲，Wesnoth 的 AI 思考時間是玩家體驗的關鍵。本卷探討地圖與 AI 系統在 `src/` 底層是如何壓榨 CPU 效能與管理記憶體的。

---

## 1. 記憶體池與快取命中 (Cache Locality)

### 1.1 地圖的連續記憶體 (`ter_map`)
在 `src/map/map.hpp` 中，地圖地形並不是使用 `std::vector<std::vector<terrain_code>>`（這會導致記憶體碎片化與 Cache Miss）。
- **一維陣列降維**：
  地形被存儲在一個單一的、連續的 `std::vector<terrain_code>` 中。透過公式 `index = y * width + x` 來存取。
- **物理意義**：
  當 AI 的 A* 尋路演算法在掃描相鄰六角格時，連續記憶體保證了 CPU 的 L1/L2 Cache Line 能夠一次預載相鄰的地形數據，使得尋路速度達到極致。

### 1.2 AI 模擬的快取優化 (`unit_stats_cache`)
在 `attack.cpp` 中，AI 每一回合可能需要評估數千次「單位 A 攻擊 單位 B」的結果。
- **雜湊快取 (Memoization)**：
  每次呼叫 `battle_context` 前，會將攻擊方、防禦方、地形、時間計算出一個 Hash Key。若快取中存在，則以 $O(1)$ 複雜度直接拿取機率矩陣，省去成千上萬次的動態規劃運算。

## 2. 智慧指標與生命週期 (Smart Pointers)

### 2.1 懸空指標防護
AI 在思考時（可能長達數秒），若某個 WML 事件突然被觸發並刪除了一個單位，C++ 的原始指標將指向被釋放的記憶體 (Use-After-Free)，導致崩潰。
- **`unit_ptr` 與 `unit_const_ptr`**：
  在 AI 與 Actions 系統中，Wesnoth 大量使用了 `std::shared_ptr` 與 `std::weak_ptr` 來管理單位實體。
- **`unit_info::valid()`**：
  在戰鬥模擬的每一幀，系統會檢查 `weak_ptr::lock()` 是否成功。若單位意外死亡（指標失效），戰鬥迴圈會安全地中斷，保證遊戲引擎的絕對穩固。

---
*全套二十卷史詩級解剖落幕。從最上層的 Lua 腳本行為，到核心的地圖生成幾何演算法，再到最底層的 CPU 快取優化與多人連線同步，Wesnoth 的技術堆疊已被毫無死角地全景展現。*
*最後更新: 2026-05-17*
