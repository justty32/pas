# Level 4 分析：控制與遙測系統 (Control & Telemetry)

## 1. 使用者介面架構
專案提供了一個基於 Web 的操作面板，整體流程如下：
- **資源託管**：前端 HTML/JS 資源被壓縮為 Gzip 格式並以 C 語言數組的形式（`index_html_gz.h`）存儲在 Flash 中。
- **動態引導**：ESP32 提供 `/c.js` 端點，動態生成 WebSocket 連線路徑，解決了靜態 IP 或 DHCP 環境下的連線匹配問題。

## 2. WebSockets 通訊機制
系統採用二進位封裝協定以提高傳輸效率：
- **上行指令 (Frontend -> ESP32)**：
  - `P_MOVE`: 傳輸 8-bit 或 16-bit 的方向與旋轉指令。
  - `P_SET`: 調整內部參數（如步態頻率、抬腳高度）。
- **下行數據 (ESP32 -> Frontend)**：
  - `P_TELEMETRY`: 回傳 `telemetryPackage`。這是一個結構化的二進位數據包，包含 12 個舵機的當前角度、身體位姿與電池健康度。

## 3. CLI 指令系統
為了方便調試，專案實作了一套靈活的 CLI 框架：
- **核心結構**：使用 `cliCommand` 結構體定義指令名稱與回調函數 (`cliFunction`)。
- **功能類別**：
  - `CLI_GET`: 獲取當前配置或感測器數值。
  - `CLI_SET`: 寫入參數並同步至 EEPROM。
  - `CLI_RUN`: 執行特定序列（如舵機校準模式、歸位序列）。

## 4. 安全保護 (Failsafe)
- **連線監控**：主循環 (`loop`) 會持續檢查 `FS_WS_count`。
- **自動觸發**：若超過 1 秒未收到有效的 WebSocket 數據，計數器將觸發安全鎖，立即停止所有運動並鎖定舵機。
