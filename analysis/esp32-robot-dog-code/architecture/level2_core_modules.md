# Level 2 深度分析：多核心調度與資源競爭

## 1. 任務模型 (Concurrency Model) 詳解

專案嚴格利用 ESP32 的雙核特性（Core 0 與 Core 1），其分工逻辑如下：

### Core 1 (Pro-CPU): 運動控制專核
*   **頻率**：250Hz (`LOOP_TIME = 4000us`)。
*   **行為**：同步執行。每一週期必須完成 `Gait -> Planner -> IK -> HAL` 的完整計算。
*   **關鍵限制**：若計算耗時超過 4ms，會直接在 Serial 拋出 `WARNING! Increase LOOP_TIME`。

### Core 0 (App-CPU): 通訊與感測專核
*   **任務 1 (Fast Service)**：500Hz (`SERVICE_FAST_LOOP_TIME = 2000us`，實際代碼中為 5000us/200Hz)。
    *   負責 IMU 讀取 (`updateIMU`) 與高頻指令處理。
*   **任務 2 (Slow Service)**：10Hz (`SERVICE_LOOP_TIME = 100000us`)。
    *   負責 WiFi 維護、WebServer、電源監測與 CLI 更新。

## 2. 隱藏的資源瓶頸：I2C 競爭

雖然任務在不同核心，但硬體資源是共享的：
*   **競爭點**：若 `PWM_CONTROLLER_TYPE` 設為 `PCA9685`，則 Core 1 的舵機輸出與 Core 0 的 IMU 讀取（MPU9250）都會競爭唯一的 I2C 匯流排。
*   **後果**：I2C 操作是阻塞式的，這會導致 Core 1 的 4ms 運動週期不穩定，產生「微抖動 (Jitter)」。
*   **優化建議**：原始碼中出現了切換至 `ESP32PWM` (直接硬體 PWM) 的配置，這正是為了避開 I2C 瓶頸的改良方案。

## 3. 失敗的關鍵點：Task Watchdog

在 `servicesLoop` (Core 0) 中，代碼明確使用了 `vTaskDelay(1)`。這是為了防止 FreeRTOS 的 IDLE 任務被飢餓導致 Watchdog 重啟。然而，在新版 Arduino-ESP32 核心中，頻繁的 WebSocket 通訊與 WiFi 中斷可能會在 Core 0 產生競爭，導致服務執行緒延遲，進而觸發 `failsafe.ino` 中的安全鎖定，使機器狗停止運作。
