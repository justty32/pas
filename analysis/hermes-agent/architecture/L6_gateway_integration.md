# hermes-agent 架構分析 - Level 6: 閘道與多平台整合

## 1. 閘道系統架構 (Gateway Architecture)
`hermes-agent` 的閘道系統將 Agent 從單機 CLI 擴展為一個可多端存取的個人助理服務。

### 核心元件：
- **GatewayRunner**: 位於 `gateway/run.py`，是整個閘道系統的控制器，負責啟動、監控各平台適配器，並管理 Agent 實例的生命週期。
- **適配器 (Platform Adapters)**: 位於 `gateway/platforms/`，為 Telegram, Discord, Slack, Matrix 等平台提供專屬實現。
- **Agent 快取機制**: 閘道為每個使用者（或頻道）維護一個 `AIAgent` 實例。為了防止資源耗盡，採用了 LRU 快取（預設 128 個實例）與閒置逾時移除（預設 1 小時）機制。

## 2. 訊息處理與標準化
為了在不同平台間保持一致的體驗，閘道執行了以下轉換：

- **格式轉換**: 將各平台的訊息事件（MessageEvent）轉換為 Agent 通用的內部格式。
- **Slash 指令系統**: `gateway/slash_commands.py` 實作了豐富的指令（如 `/model`, `/tools`, `/usage`, `/reset`），讓使用者能像在 CLI 一樣控制 Agent。
- **輸出過濾**: `_TELEGRAM_NOISY_STATUS_RE` 等正則表達式會過濾掉系統內部的雜訊訊息（如「正在壓縮會話...」），只將對使用者有意義的狀態（如「正在使用 Google 搜尋...」）傳送至前端。

## 3. 多模態支援 (Multimodal Support)
閘道不僅處理文字，還支援更豐富的互動方式：
- **語音處理**: 支援語音訊息的接收與轉錄（Transcribe），並能透過 TTS 回應。
- **圖片與檔案**: 支援圖片的上傳與視覺模型（Vision）分析。
- **表情符號與進度條**: 透過 `agent/display.py` 提供的 Emoji 與狀態更新，在 Telegram 等平台呈現生動的進度提示（Kawaii Spinners）。

## 4. 配對與認證 (Pairing & Auth)
- **Session Pairing**: `gateway/pairing.py` 允許使用者將其各平台帳號與特定的 Agent 設定檔連結。
- **存取控制**: 支援多租戶隔離，確保不同使用者的會話、記憶與憑證互不干擾。
- **安全性**: 透過 `authz_mixin.py` 提供基於權限的指令執行保護。

## 5. 穩定性與診斷
- **Shutdown Forensics**: 閘道關閉時會記錄詳細的取證資訊，以便診斷崩潰原因。
- **自動重啟**: 支援在特定錯誤下自動重啟適配器。
- **診斷指令**: 提供 `hermes doctor` 等工具，協助使用者排除連線或憑證問題。
