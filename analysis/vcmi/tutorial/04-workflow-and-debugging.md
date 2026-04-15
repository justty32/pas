# 04 - 工作流與偵錯：高效開發實踐

作為資深工程師，掌握 VCMI 的構建系統與偵錯工具，能大幅提升你的開發效率。

## 1. 構建系統：CMake 與 Conan

VCMI 使用 **CMake** 管理構建，並利用 **Conan** 處理依賴項（如 Boost, SDL2, Qt, TBB 等）。

### 常用構建參數
- `ENABLE_LUA=ON`: 啟用 Lua 腳本支持。
- `ENABLE_PCH=ON`: 使用預編譯頭文件，顯著提升 C++ 編譯速度。
- `ENABLE_TBB=ON`: 啟用 Intel TBB 併發支持。

## 2. 獨立進程與單一進程模型

- **預設 (Standalone)**: 客戶端 (`vcmiclient`) 與伺服器 (`vcmiserver`) 為獨立進程。偵錯時，你可能需要分別 Attach。
- **iOS/Android**: 伺服器作為靜態庫與客戶端編譯在一起。這依賴於 `Global.h` 中定義的命名空間宏，以防止符號衝突。

## 3. 偵錯策略 (Debugging)

### 多線程偵錯
- VCMI 在日誌中標記了執行緒名稱（例如 `MainGUI`, `runServer`, `runNetwork`）。
- 使用 `CThreadHelper.cpp` 提供的工具來跟蹤跨執行緒的死結。

### 網路偵錯
- **`NetPack` 序列化檢查**: 在 `lib/serializer/` 中增加追蹤點，確認封包在網路傳輸中未損壞。
- **狀態不同步 (Desync)**: 這是多人遊戲的噩夢。VCMI 提供了狀態對比工具，可以 dump 客戶端與伺服器的 `CGameState` 並進行比較。

## 4. 效能優化 (Profiling)

- **TBB Parallelism**: 檢查 `Nullkiller` AI 的回合計算時間。如果 CPU 佔用低且計算慢，可能是過度序列化或不必要的 Mutex 競爭。
- **SDL 渲染**: 如果 FPS 低，檢查 `client/renderSDL/`。VCMI 雖然是 2D 引擎，但精靈層級過多（數千個地圖物件）仍會造成瓶頸。

## 5. 日誌系統 (`logging/`)

VCMI 使用分層日誌。你可以在 `gameConfig.json` 或 `settings.json` 中動態調整每個子模組的日誌級別：
- `trace`: 最詳細，適合追蹤封包流。
- `debug`: 適合追蹤逻辑變遷。
- `warn`/`error`: 預設設置。

---
恭喜，你已完成 VCMI 引擎開發的快速入門。如果你有具體的擴展目標，可以隨時向我提問！
