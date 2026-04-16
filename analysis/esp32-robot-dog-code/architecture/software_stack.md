# 軟體堆疊與數據流架構 (Software Stack & Data Flow)

理解本專案的關鍵在於其「分層控制」邏輯。數據從高層的抽象指令（速度向量）一路轉換到底層的物理訊號（PWM 脈衝）。

## 1. 軟體堆疊 (Software Stack)

*   **應用層 (Application Layer)**:
    *   `webServer.ino`, `cli.ino`: 負責接收來自 Web 介面或串口的控制指令。
*   **規劃層 (Planning Layer)**:
    *   `planner.cpp`: 根據速度向量預測機器狗下一時刻的位姿。
    *   `gait.cpp`: 決定當前哪些腿應該處於擺動相 (Swing)，哪些處於支撐相 (Stance)。
*   **演算法層 (Algorithm Layer)**:
    *   `IK.cpp`: 逆向運動學，將足端坐標轉換為關節角度 ($\alpha, \beta, \gamma$)。
    *   `balance.cpp`: 根據重心 (CoM) 修正身體位姿。
*   **硬體抽象層 (HAL Layer)**:
    *   `HAL_body.cpp`: 協調 12 個舵機的角度分配。
    *   `HAL_ESP32PWM.ino`: 將角度映射為精確的微秒級脈衝。

## 2. 數據流向 (Data Flow)

1.  **指令輸入**：`moveVector` (x, y, yaw 速度) 被寫入。
2.  **步態時鐘**：`updateGait()` 根據時鐘進度決定每條腿的目標坐標。
3.  **預測與修正**：`planner` 預測足端位置，`balance` 根據 IMU 數據疊加補償量。
4.  **座標轉換**：`IK::solve()` 將足端 3D 坐標轉換為三個關節弧度。
5.  **脈衝轉換**：`angleToPulse()` 透過分段線性映射將弧度轉為 PWM 微秒值。
6.  **物理執行**：`ESP32_ISR_Servos` 將訊號輸出至 GPIO。
