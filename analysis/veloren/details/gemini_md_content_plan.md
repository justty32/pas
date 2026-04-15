# Veloren 專案分析 (為 GEMINI.md 準備)

## 專案概述
Veloren 是一款開源的多玩家像素風格 RPG。專案採用 Rust 編寫，並使用 Workspace 結構管理。

## 關鍵模組
- `voxygen`: 用戶端 (Client)。
- `server`: 伺服器端 (Server)。
- `common`: 用戶端與伺服器端共享的核心邏輯。
- `world`: 世界生成與經濟系統。
- `assets`: 遊戲資源檔案 (位於 `assets/` 和 `common/assets/`)。

## 常用命令 (推導)
- `cargo run --bin veloren-voxygen`: 啟動遊戲用戶端。
- `cargo run --bin veloren-server`: 啟動遊戲伺服器。
- `cargo test --workspace`: 執行全域測試。
- `cargo build --release`: 編譯正式版本。
- `cargo run --bin chat_cli`: 位於 `client/examples/`，推測為測試用的聊天命令列工具。

## 開發規範
- 嚴禁 AI 生成代碼與資產。
- 使用 `specs` ECS 框架。
- 偏好 `ron` 格式進行配置與資產定義。
