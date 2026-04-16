# ESP32_ISR_Servo 子系統與權責分析 (Level 2)

## 1. 核心元件與職責
本專案採 Header-only 實作模式，核心邏輯拆分為類別定義與實作兩部分。

### A. `ESP32_ISR_Servo` 類別 (控制中心)
- **職責**: 管理多達 16 個伺服馬達的生命週期、狀態與脈衝生成。
- **關鍵成員變數**:
    - `servo_t servo[MAX_SERVOS]`: 儲存每個伺服馬達的腳位、目標計數、角度位置及啟用狀態。
    - `timerCount`: 全域計數器，用於追蹤當前週期內的微秒進度（以 12μs 為單位）。
    - `timerMux`: ESP32 專用的臨界區鎖（Spinlock），確保多核心環境下 ISR 與主迴圈存取共享資料的安全性。
- **關鍵方法**:
    - `run()`: **核心 ISR 邏輯**。每 12μs 觸發一次。
        - 當 `timerCount == 1` 時，將所有啟用的伺服腳位設為 `HIGH`。
        - 當 `timerCount` 達到該馬達預設的 `count` 時，將腳位設為 `LOW`。
        - 當計數達到 20ms (REFRESH_INTERVAL) 時，歸零重啟。
    - `setupServo()`: 初始化腳位並分配槽位。
    - `setPosition()`: 將角度（0-180）映射為對應的脈衝計數值。

### B. `ESP32FastTimer` (硬體抽象層)
- **職責**: 封裝 ESP32 的硬體定時器驅動（Timer Group 0/1）。
- **職能**: 提供 `attachInterruptInterval()` 介面，讓上層能以微秒為單位設定定時中斷。

## 2. 脈衝生成機制 (PWM Logic)
不同於傳統的硬體 PWM，本函式庫採用 **軟體模擬的 ISR PWM**:
1. **頻率**: 固定為 50Hz (20ms 週期)。
2. **解析度**: 由 `TIMER_INTERVAL_MICRO` (12μs) 決定。
3. **運作流程**:
   - `[0us]` (timerCount=1): 輸出高電位。
   - `[544us - 2400us]` (timerCount=45~200): 根據角度計算出的計數值關閉輸出。
   - `[20000us]`: 週期結束，重置計數。

## 3. 並行與安全機制 (Thread Safety)
由於 ESP32 是雙核心架構，且中斷可能在任何核心觸發：
- 使用 `portENTER_CRITICAL(&timerMux)` 保護 `setPosition` 等寫入操作。
- 使用 `portENTER_CRITICAL_ISR(&timerMux)` 在 `run()` 中斷處理程序中保護讀取與腳位操作。
- 變數多標註為 `volatile` 以防止編譯器優化導致的資料不同步。

---
*註：內容同步紀錄於 `analysis/ESP32_ISR_Servo/architecture/subsystems.md`*
