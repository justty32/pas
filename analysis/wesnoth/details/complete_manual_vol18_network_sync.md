# Wesnoth 技術全典：AI 網路同步與確定性機制 (第十八卷)

Wesnoth 支援多人連線中的 AI 玩家。要讓分處世界各地、不同硬體架構的電腦算出完全相同的 AI 決策，必須依賴極端嚴苛的「確定性 (Determinism)」與同步機制。本卷解構 `src/synced_checkup.cpp` 與 `src/network.cpp`。

---

## 1. 確定性亂數生成器 (Deterministic RNG)

在 AI 戰鬥與地圖生成中，所有的「隨機」都必須是偽隨機 (Pseudo-Random)。
- **種子同步 (Seed Synchronization)**：
  每一局遊戲開始時，伺服器會派發一個全域亂數種子。AI 的 `attack_analysis` 在模擬機率或 `default_map_generator` 在生成地形時，嚴格呼叫這個全域 RNG。
- **禁止本地亂數**：
  任何 `std::rand()` 或依賴系統時間的亂數呼叫在 AI 邏輯中是被嚴格禁止的。這保證了：只要初始種子相同，AI 決定攻擊誰、移動到哪裡，在所有客戶端上都會得出 $100\%$ 一致的評分。

## 2. OOS (Out of Sync) 防範與追蹤

當某個客戶端的 AI 決策與伺服器或其他玩家不同步時，稱為 OOS。這通常是因為浮點數精度差異或未初始化的記憶體造成。

### 2.1 `synced_context` (同步上下文)
- **工程解析**：
  AI 在執行 `execute()` 之前，會進入 `synced_context`。這是一個 RAII 鎖。
- **行為審查**：
  在這個上下文內，AI 所有的物理改變（如移動、扣血）都會被記錄為 `[command]` WML 節點，並打包成二進位流發送給伺服器。伺服器再將這些指令廣播給其他玩家。其他玩家的電腦「不負責思考 AI 要做什麼」，而是直接「執行伺服器傳來的 AI 動作」。

### 2.2 `synced_checkup` (同步檢查點)
- 每當 AI 完成一個 RCA 階段，系統會呼叫 `synced_checkup::check()`。
- **雜湊校驗 (Hash Verification)**：
  系統會對當前 `gamemap` 的地形與 `unit_map` 中所有單位的血量、位置進行 SHA-1 雜湊運算。將這串雜湊值發送給伺服器比對。一旦發現雜湊值不符，遊戲會立即彈出 "Out of Sync" 錯誤，防止錯亂的遊戲狀態繼續延續。
