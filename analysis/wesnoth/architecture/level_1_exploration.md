# Wesnoth 專案分析 - Level 1: 初始探索

## 專案基本資訊
- **專案名稱**: The Battle for Wesnoth (韋諾之戰)
- **GitHub 倉庫**: [wesnoth/wesnoth](https://github.com/wesnoth/wesnoth)
- **專案類型**: 開源、回合制戰術策略遊戲 (Open Source, turn-based tactical strategy game)。
- **核心特色**:
  - 多樣化的戰役與故事。
  - 高度可模組化 (Moddable)，使用自定義的 WML (Wesnoth Markup Language)。
  - 支援單人、多人連線與 AI 對戰。

## 技術棧 (Tech Stack)
- **程式語言**: C++ (大量使用 Boost 函式庫)。
- **圖形與輸入**: SDL2 (核心渲染與事件處理)。
- **文字與 UI**: Pango, Cairo (用於文字渲染與佈局)。
- **音訊**: SDL2_mixer。
- **網路與工具**: 
  - **Boost**: 使用了 Asio, Filesystem, Locale, Regex, Spirit, Coroutine 等多個模組。
  - **Curl**: 用於網路傳輸。
  - **OpenSSL**: 加密支援。
- **編譯系統**: CMake, SCons。
- **套件管理**: vcpkg。

## 目錄結構分析
- `src/`: 核心 C++ 源碼目錄。
- `data/`: 包含遊戲數據、場景、單位設定 (WML) 以及影音素材。
- `doc/`: 專案文檔與說明。
- `utils/`: 各種輔助腳本與開發工具。
- `po/`: 國際化與在地化 (i18n) 翻譯文件。
- `projectfiles/`: 針對特定 IDE 或系統的專案配置。
- `cmake/`: CMake 編譯配置腳本。

## 初始觀察
- **程式碼規模**: 專案歷史悠久，代碼量龐大且高度模組化。
- **依賴關係**: 強烈依賴 Boost 函式庫來處理系統底層、邏輯解析 (Spirit) 與非同步操作 (Asio/Coroutine)。
- **擴展性**: 遊戲邏輯與內容很大程度依賴於 `data/` 中的 WML 配置，而非硬編碼在 C++ 中。

---
*最後更新: 2026-05-17*
