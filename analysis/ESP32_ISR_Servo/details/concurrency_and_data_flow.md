# ESP32_ISR_Servo 並發安全性與數據流剖析 (Level 5)

## 1. 雙核心安全機制 (SMP Safety)
由於 ESP32 的雙核心特性，函式庫必須處理競爭條件 (Race Conditions)：
- **同步原語**: 使用 `portMUX_TYPE timerMux` 作為 Spinlock。
- **讀寫保護**: 在 `setPosition` 等 API 中，使用 `portENTER_CRITICAL` 保護對 `servo[servoIndex]` 結構體的寫入。
- **ISR 保護**: 在 `run()` 中使用 `portENTER_CRITICAL_ISR` 確保在讀取狀態進行 GPIO 翻轉時，數據不會被主迴圈修改。

## 2. 脈衝生成時序圖
- **T = 0**: 所有馬達腳位 -> HIGH。
- **T = Target_Count**: 個別馬達腳位 -> LOW。
- **T = 20ms**: 週期重置。

## 3. 實作細節：`digitalWrite` 性能
在 ISR 內部頻繁調用 `digitalWrite` 會有一定的系統開銷。雖然本庫支援 16 個馬達，但若中斷頻率過高（如縮短 `TIMER_INTERVAL_MICRO`），可能會佔用過多 CPU 時間。

## 4. 關鍵位置
- 臨界區鎖定：`src/ESP32_ISR_Servo_Impl.h` 行 55, 115。
- 中斷邏輯：`src/ESP32_ISR_Servo_Impl.h` 行 50-84 (`run()` 函數)。
