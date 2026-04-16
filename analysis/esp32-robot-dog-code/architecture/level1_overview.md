# Level 1 分析：esp32-robot-dog-code 初始探索

## 1. 專案背景與目標
此專案旨在利用 ESP32 控制一個小型四足機器狗。它實現了從底層 PWM 舵機控制到高層步態規劃與逆向運動學（IK）的完整流程。

## 2. 硬體架構
- **控制器**：ESP32 (Dual-core, 240MHz)
- **執行器**：12x MG90D 舵機 (3 DOF per leg)
- **感測器**：
  - **IMU**: MPU9250 (I2C) - 用於姿態檢測與平衡補償。
  - **Power**: INA219 (I2C) - 監測電池電壓與功耗。
- **電源**：2x 18650 鋰電池。

## 3. 軟體技術棧
- **框架**：Arduino-ESP32
- **核心庫**：
  - `IK` (Inverse Kinematics): 將機器狗足端座標轉換為 3 個舵機的角度。
  - `Gait`: 步態生成器（如 Trot, Walk）。
  - `Balance`: PID 平衡補償算法。
  - `HAL` (Hardware Abstraction Layer): 抽象舵機輸出控制（PCA9685 或 ESP32 PWM）。
- **通訊**：
  - **Serial CLI**: 提供即時參數調整與調試指令。
  - **WebSockets**: 與控制網頁進行低延遲數據交換。

## 4. 目錄結構分析
- `/software/robot_dog_esp32/`: 核心固件目錄。
  - `libs/`: 演算法實作。
  - `config.h`: 靜態配置項目（腳位、通訊、初始角度）。
  - `*.ino`: 依功能劃分的 Arduino 源碼片段。
- `/software/web/`: 控制端 Web UI 原始碼。
- `/tools/`: 校準與測試工具。

## 5. 待深入研究點
- **IK 實作細節**：觀察其幾何解法或數值解法。
- **步態規劃**：如何實現平滑的步態切換。
- **平衡演算法**：IMU 數據如何反饋至 IK 鏈。
