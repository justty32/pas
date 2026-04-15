# GEMINI.md 生成分析紀錄

## 步驟 1：初始探索
根據目錄結構，這是一個名為 Veloren 的開源像素風格 RPG 專案（Rust 編寫）。

### 預計讀取的檔案：
1. `README.md` - 專案概覽。
2. `Cargo.toml` (根目錄) - 專案依賴與工作區配置。
3. `CONTRIBUTING.md` - 開發規範與貢獻指南。
4. `.gitlab-ci.yml` - 構建、測試與 CI 流程。
5. `CHANGELOG.md` - 專案演進。
6. `common/Cargo.toml` - 核心邏輯依賴。
7. `voxygen/Cargo.toml` - 用戶端 (Voxygen) 依賴。
8. `server/Cargo.toml` - 伺服器端依賴。
9. `assets/credits.ron` - 專案貢獻資訊。
10. `nix/default.nix` - 構建環境資訊。
