# VCMI GUI 與開發工具分析 (`launcher/`, `mapeditor/`, `vcmiqt/`)

除了遊戲核心引擎外，VCMI 還提供了一套基於 **Qt** 框架的圖形化管理與編輯工具。

## 1. VCMI 啟動器 (`launcher/`)
- **角色**: 用於管理遊戲設定、下載/更新 Mod 以及啟動客戶端/伺服器。
- **Mod 管理 (`modManager/`)**: VCMI 的 Mod 系統與啟動器深度整合，支援從官方 Mod 目錄下載。
- **跨平台預算 (`prepare_android.cpp`, `prepare_ios.mm`)**: 啟動器針對不同平台（Android, iOS, Windows, Linux）進行環境初始化。
- **InnoExtract (`innoextract.cpp`)**: 用於從 Heroes III 原始安裝程序中提取資產（特別是針對 Windows 安裝包）。

## 2. 地圖編輯器 (`mapeditor/`)
- **角色**: 提供一個強大的可視化編輯器，支援 VCMI 擴展的地圖特性（如：更多地圖層、更大的地圖尺寸）。
- **物件放置**: 允許玩家放置、配置複雜的地圖物件，並即時預覽。
- **整合 VCMI 規則**: 編輯器直接引用 `VCMI_lib`，確保地圖數據與引擎規則完全一致。

## 3. 共享 Qt 組件 (`vcmiqt/`)
- **角色**: 作為啟動器與編輯器共享的工具庫。
- **JSON 工具 (`jsonutils.cpp`)**: 封裝了 Qt 與 VCMI 內部 JSON 格式之間的轉換。
- **UI 共用組件 (`MessageBox.h`)**: 標準化的彈窗、路徑轉換工具。

## 關鍵流程 (啟動過程)
1. 使用者在 `launcher` 中選擇 Mod。
2. `launcher` 寫入設定檔，並調用 `vcmiclient`。
3. `vcmiclient` 加載設定，根據需要啟動本地或連接遠程 `vcmiserver`。
