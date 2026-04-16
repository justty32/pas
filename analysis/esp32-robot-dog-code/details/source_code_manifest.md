# 原始碼檔案職責詳解 (Source Code Details)

以下是 `software/robot_dog_esp32/` 目錄下各檔案的具體功能說明：

## 1. 入口與核心調度 (Root Files)

*   **`robot_dog_esp32.ino`**: 系統總入口。定義了雙核心任務 (`loop` 與 `servicesLoop`)，初始化所有模組，並控制 250Hz 的主運動循環。
*   **`config.h` / `config_small.h`**: 全域配置。包含腳位定義、PID 參數、步態週期、WiFi SSID 以及舵機頻率設定。
*   **`def.h`**: 定義核心數據結構，如 `point` (x,y,z), `leg` (腿部狀態), `figure` (身體位姿) 與 `moveVector`。
*   **`settings.ino`**: 負責與 EEPROM 交互，讀取與儲存舵機校準參數。

## 2. 演算法庫 (`libs/`)

*   **`libs/IK/IK.cpp`**: 核心逆向運動學。實作了幾何法解算，包含對身體 `Yaw` 軸的旋轉補償。
*   **`libs/gait/gait.cpp`**: 步態狀態機。管理擺動進度，並調度 `transition` 來生成抬腿軌跡。
*   **`libs/planner/planner.cpp`**: 預測下一步的「著地點」。根據當前移動速度，計算出為了維持平衡，腿應該落在什麼坐標。
*   **`libs/balance/balance.cpp`**: 靜態平衡器。計算支撐多邊形的中心，並試圖將身體投影點移向中心。
*   **`libs/transition/transition.cpp`**: 軌跡插值器。提供線性 (`linear`) 與三段式抬腿 (`swing`) 兩種路徑生成算法。

## 3. 硬體抽象與通訊 (Hardware & Communication)

*   **`HAL.ino`**: 通用的硬體接口定義，調用具體的 PWM 實作。
*   **`HAL_ESP32PWM.ino`**: ESP32 原生 PWM 驅動。包含極具價值的 **`angleToPulse` 分段線性映射算法**。
*   **`HAL_PCA9685.ino`**: I2C PWM 擴展板驅動（可選）。
*   **`imu.ino`**: 封裝了 MPU9250 的讀取邏輯，並將數據轉換為 Roll/Pitch/Yaw 弧度。
*   **`webServer.ino`**: 建立非同步 Web 伺服器，託管 Web UI 並處理 WebSocket 連線。
*   **`packagesProcess.ino`**: 定義二進位通訊協定，將 `moveVector` 解包並將 `telemetryPackage` 封包發送至網頁。
*   **`cli.ino`**: 實作了串口指令系統，支援如 `set LF_HAL_trim_alpha 5` 等即時調校指令。

## 4. 安全與輔助 (Helpers)

*   **`failsafe.ino`**: 安全監視器。若 WebSocket 斷連超過 1 秒，會立即切換 `FS_FAIL` 狀態並停止所有舵機。
*   **`i2cscan.ino`**: 調試工具。啟動時掃描 I2C 總線，確認 PCA9685 或 MPU9250 是否在線。
*   **`subscription.ino`**: 遙測訂閱系統。控制哪些數據需要以什麼頻率發送給客戶端。
