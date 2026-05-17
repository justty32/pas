# Wesnoth 技術全典：大一統引擎架構與生命週期 (第二十一卷：總綱)

本卷為《Wesnoth 技術全典》的最高層級總結（Capstone）。我們將前二十卷的碎片化知識，整合為一個由上而下、從啟動到渲染的「大一統 (Grand Unified)」生命週期模型。

---

## 1. 引擎啟動與資料掛載 (Bootstrapping & Data Binding)

當玩家執行 `wesnoth` 執行檔時，系統進入啟動管線：
1. **全域初始化**：`wesnoth_main` 啟動 SDL2 視訊/音訊子系統，並初始化 Boost.Asio 網路執行緒。
2. **WML 編譯期 (VFS 虛擬檔案系統)**：
   - 系統透過 `preprocessor` 將所有的 `.cfg` 檔案展開巨集。
   - `parser` 將龐大的純文字字串流轉化為 `config` 記憶體樹狀圖。
   - 若為二次啟動，則直接從 `binary_wml` 的二進位快取中透過 Memory Mapping 高速載入。
3. **元數據緩存 (Metadata Caching)**：
   - 地形代碼 (`terrain_code`) 被編譯並寫入 `terrain_type_data`。
   - 單位素質 (`unit_type`) 被實體化為唯讀的原型庫。

## 2. 遊戲主迴圈 (The Main Game Loop)

進入戰役或對戰後，控制權交由 `play_controller` 管理。這是一個巨大的狀態機。

### 2.1 階段一：回合交替與狀態結算 (Turn Transition)
- `game_board::new_turn()` 觸發。
- 系統掃描全圖 `gamemap`：
  - 結算村莊收益 (`get_village`)、扣除單位維持費。
  - 執行全域治療 (`heal_all_survivors`) 並重置單位移動力 (MP)。
  - 若偵測到晝夜交替，觸發 `terrain_builder::rebuild_cache_all` 更新光影。

### 2.2 階段二：事件泵浦 (Event Pumping)
- `game_events::manager::pump()` 接管。
- 處理 `turn refresh`, `side turn` 等 WML 事件。
- Lua 腳本的 `intf_fire_event` 可能在此時被觸發，透過 `application_lua_kernel` 修改地形或生成劇情對話。

### 2.3 階段三：玩家/AI 決策輸入 (Input Gathering)
根據當前陣營，控制權分發給 UI 或 AI。
- **若是 AI 陣營**：
  - `ai_composite::play_turn()` 被呼叫。
  - **RCA 競爭模型**啟動：
    1.  `attack_analysis` 在背後執行數萬次的馬可夫鏈戰鬥模擬。
    2.  `recruitment` 執行未來 5 回合的財政預測與兵種相剋計算。
    3.  `ca_move_to_targets` 呼叫 A* 搜尋並計算 ZOC 阻斷。
  - 最高分的 `candidate_action` 執行其原子動作（如 `move_unit`），並將動作記錄至 `synced_context`，廣播給網路上的其他玩家。

### 2.4 階段四：物理結算與歷史壓棧 (Physics & History)
- 當動作被提出後，進入 `src/actions/` 結算。
- 若發生戰鬥，`attack::perform()` 執行亂數擲骰，更新血量分佈。
- 若單位移動，`move_unit_spectator` 即時結算伏擊 (Ambush) 與戰爭迷霧 (Fog) 的清除。
- 所有的改變被封裝為 `undo_action`，壓入歷史紀錄堆疊，支援玩家隨時撤銷。

### 2.5 階段五：視覺渲染管線 (Rendering Pipeline)
- 在每幀的結尾，`display::draw()` 根據「髒矩形 (Dirty Rectangles)」執行局部重繪。
- 系統呼叫 `terrain_builder` 將地圖單元轉化為具有旋轉適配與多層次覆蓋 (Overlay) 的 SDL 紋理。
- 最後，透過 Z-Index 畫家演算法，將地形、網格、光環、單位與 UI 介面依序繪製到螢幕緩衝區，並透過 `SDL_RenderPresent` 送至顯示卡。

---

## 總結
The Battle for Wesnoth 是一座完美的工程金字塔。底層由嚴密的 C++ 幾何與記憶體管理構成，中層透過事件佇列與 RCA 模型處理狀態轉移，最上層則透過 WML 與 Lua 開放了無限的模組化可能。這 21 卷技術全典，正是這座金字塔的完整設計藍圖。
