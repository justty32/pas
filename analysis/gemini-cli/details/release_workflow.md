# Gemini CLI 發行與發布機制 (Level 6 分析)

## 1. 單一執行檔 (SEA)
Gemini CLI 支援編譯成單一可執行檔案，無需安裝 Node.js 即可執行。
- **`sea/sea-launch.cjs`**: SEA 的啟動腳本。
- **`scripts/build_binary.js`**: 核心打包流程：
  1. 使用 `esbuild` 打包程式碼。
  2. 使用 Node.js 內建的 `postject` 工具將打包後的 JS 注入 Node.js 二進制檔。
  3. 處理不同平台（macOS, Windows, Linux）的數位簽章。

## 2. 嚴格的開發驗證 (`preflight`)
專案實作了 `npm run preflight` 指令，作為 PR 合併前的最終門檻：
- `clean` & `npm ci`: 確保乾淨的安裝環境。
- `format` & `lint`: 程式碼風格檢查。
- `build`: 驗證全模組編譯。
- `typecheck`: 靜態型別檢查。
- `test:ci`: 執行全量單元測試、整合測試與 SEA 啟動測試。

## 3. 測試體系
- **Vitest**: 單元測試。
- **Integration Tests**: 驗證工具在真實檔案系統中的行為。
- **E2E Tests**: 模擬使用者在終端機中的完整對話流程。
- **Performance/Memory Tests**:  nightly 執行的效能與記憶體迴歸測試。

## 4. UI 互動設計
- **鍵盤綁定 (`keyBindings.ts`)**: 統一管理所有快捷鍵（如 `QUIT`, `SCROLL`, `HISTORY`）。
- **Ink 特性利用**: 
  - `AppContainer.tsx` 管理全域狀態。
  - 使用 `ResizeObserver` 實現終端機視窗的響應式佈局。
  - 專門處理了 ANSI 逸出字串的解析與渲染。
