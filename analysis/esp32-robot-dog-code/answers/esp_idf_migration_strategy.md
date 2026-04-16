# ESP-IDF 遷移策略與架構設計

針對 `esp32-robot-dog-code` 專案老舊且在 Arduino 框架下遇到瓶頸（定時器衝突、I2C 阻塞、Task Watchdog 觸發）的問題，將其核心演算法遷移至 ESP-IDF 是最佳的解決方案。

## 1. 核心架構映射 (Architecture Mapping)

在遷移過程中，我們需要將 Arduino 的抽象層對應到 ESP-IDF 的底層 API：

| 功能模組 | 原 Arduino 實現 | ESP-IDF 建議實現 |
| :--- | :--- | :--- |
| **多核心調度** | `xTaskCreatePinnedToCore` (Arduino 包裝) | 原生 FreeRTOS `xTaskCreatePinnedToCore` |
| **伺服控制 (PWM)** | `ESP32_ISR_Servo` (軟體/硬體混合計時器) | **LEDC** (硬體 PWM，支援高達 16 通道，完美適配 12 顆舵機) |
| **通訊 (WebServer)** | `ESPAsyncWebServer` | `esp_http_server` (內建 HTTP/WebSocket 伺服器) |
| **數據存儲 (參數校準)**| `EEPROM.h` | **NVS** (Non-Volatile Storage) |
| **感測器 (IMU)** | `MPU9250_WE` (I2C) | `driver/i2c` 配合開源的 C 語言 MPU9250 驅動 |
| **數學與演算法** | C++ Classes (`libs/` 目錄) | **直接移植** (保持 C++ 類別，修正數學依賴與邊界檢查) |

## 2. 演算法精髓的保留與優化

本專案最有價值的兩大核心必須完整保留並在 ESP-IDF 中優化：

### A. 分段線性舵機校準 (Segmented Linear Mapping)
原專案的 `angleToPulse` 函數透過 7 個手動校準點來抵消廉價 MG90D 舵機的非線性誤差。
*   **遷移策略**：將 `servoProfile` 結構體存儲於 NVS 中。使用 ESP-IDF 的 `LEDC` 模組，其硬體計時器可以提供極高解析度的佔空比（Duty Cycle）控制，讓插值計算出來的脈衝寬度（如 1532us）能被精確輸出，徹底消除 Arduino `analogWrite` 的誤差。

### B. 逆向運動學 (IK) 與步態生成 (Gait)
`IK.cpp`、`planner.cpp` 和 `transition.cpp` 中的純數學計算是機器狗運動的核心。
*   **遷移策略**：將這些檔案封裝成 ESP-IDF 的獨立 Component（例如命名為 `robot_algo`）。
*   **關鍵修正**：原 IK 計算中直接使用 `asin` 與 `acos`，缺乏邊界檢查。在移植時，必須在傳入這些數學函數前加入 `clamp` 處理（即限制輸入值在 `[-1.0, 1.0]` 之間），以防止因目標坐標超出物理極限而產生 `NaN`（Not a Number），進而導致控制迴圈崩潰。

## 3. 解決硬體資源瓶頸

遷移至 ESP-IDF 後，可徹底解決原有的 I2C 競爭與抖動問題：
*   **獨立 PWM**：完全拋棄 PCA9685，利用 ESP32 本身的 12 個 GPIO 配合 LEDC 直接驅動 12 顆舵機。
*   **中斷優先級**：在 ESP-IDF 中，可以將運動控制 Task (Core 1) 設置為最高優先級，並將 I2C 讀取 (IMU) 設置為異步或較低優先級的 Task，確保 250Hz 的運動控制迴圈絕不被阻塞。
