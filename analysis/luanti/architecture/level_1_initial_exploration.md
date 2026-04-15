# Level 1: 初始探索與基礎架構分析

## 專案概述
Luanti (前身為 Minetest) 是一個以 C++17 編寫的體素遊戲引擎。它使用 CMake 作為建置系統，並透過 vcpkg 管理依賴。

## 技術棧與依賴 (vcpkg.json)
根據 `vcpkg.json` (1-40行)，核心依賴包括：
- **圖形與輸入**：`sdl2`, `freetype`, `libjpeg-turbo`
- **腳本引擎**：`luajit` (高效能 Lua 執行環境)
- **資料儲存**：`sqlite3`
- **網路與通訊**：`curl` (支援 SSL), `openssl`
- **音訊**：`openal-soft`, `libvorbis`, `libogg`
- **公用程式**：`zlib`, `zstd` (壓縮), `gmp` (大數運算), `jsoncpp`, `gettext` (多語言)

## 核心進入點分析 (src/main.cpp)
`src/main.cpp` 負責整個引擎的生命週期啟動：
- **初始化階段 (110-160行)**：
    - `debug_set_exception_handler()`: 設定異常處理。
    - `porting::osSpecificInit()`: 執行作業系統相關的初始設定。
    - `get_cmdline_opts()`: 解析命令行參數。
    - `porting::initializePaths()`: 初始化資料、快取、使用者路徑。
- **功能分流**：
    - 透過命令行參數判斷執行模式：`--version` (顯示版本), `--worldlist` (列出世界), `--server` (啟動伺服器)。
- **核心組件啟動**：
    - `setup_log_params()`: 設定日誌系統。
    - `create_userdata_path()`: 確保使用者資料目錄存在。

## 工作空間結構
- `src/`: C++ 核心代碼。
- `builtin/`: 內建 Lua 邏輯，為 Mod 提供基礎 API。
- `games/`: 遊戲定義，包含一組 Mods。
- `lib/`: 內嵌的第三方庫。
- `doc/`: 開發與使用文件。
