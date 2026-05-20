# Gemini CLI 沙盒安全機制 (Level 5 分析)

## 1. 多層次安全防禦
Gemini CLI 採用「深度防禦」策略來執行不可信的 AI 生成程式碼或工具調用。

## 2. macOS Seatbelt 沙盒
在 macOS 上，專案利用系統內建的 Seatbelt (sandbox-exec) 技術：
- **`seatbeltArgsBuilder.ts`**: 動態建構 Scheme 格式的沙盒配置。
- **嚴格白名單**: 預設禁止所有檔案寫入，除非是專案的工作目錄或 OS 暫存區。
- **治理檔案保護**: 強制禁止修改 `.git`、`.gitignore` 等關鍵配置，防止 RCE 或惡意鉤子植入。
- **路徑解析**: 自動解析符號連結 (Symlinks)，確保沙盒規則涵蓋真實路徑。

## 3. 跨平台支援
- **Linux**: 支援使用 Docker 或 Podman 容器進行隔離。
- **Windows**: 主要依賴權限控制與未來的容器化支援（目前相對較弱，建議在 WSL 或 Docker 中執行）。

## 4. 權限提升機制
- **Proactive Permissions**: 在執行涉及網路或系統關鍵路徑的操作前，代理會主動請求提權。
- **Policy Engine**: 根據使用者的設定（如 `GEMINI.md` 中的策略）決定是否自動核准某些安全操作。

## 5. 網路隔離
- 除非顯式授予 `networkAccess` 權限，否則沙盒會封鎖所有出站連線，防止資料外洩。
