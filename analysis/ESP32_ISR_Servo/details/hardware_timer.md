# ESP32 硬體定時器中斷機制深度剖析 (Level 3)

## 1. 跨晶片變體支援
`ESP32FastTimerInterrupt.hpp` 透過預編譯指令針對不同 ESP32 晶片架構進行適配：

- **標準 ESP32 / S2 / S3**: 
    - 擁有 2 個定時器群組 (Timer Group 0/1)，每組 2 個定時器 (Timer 0/1)，共 4 個。
    - 定義 `MAX_ESP32_NUM_TIMERS` 為 4。
- **ESP32-C3**:
    - 結構不同，擁有 2 個定時器群組，但每組僅 1 個定時器。
    - 定義 `MAX_ESP32_NUM_TIMERS` 為 2。
    - 強制映射 `_timerIndex` 為 `TIMER_0`，並將 `timerNo` 直接映射至 `_timerGroup`。

## 2. 定時器配置細節
函式庫使用 ESP-IDF 的底層驅動 API 進行配置：

- **預分頻器 (Prescaler)**: 設定 `TIMER_DIVIDER` 為 80。
    - 由於 ESP32 的基頻 (APB_CLK) 通常為 80MHz，分頻後得到 1MHz 的計數頻率。
    - 這意味著定時器每 1 微秒 (1μs) 計數一次。
- **報警模式 (Alarm Mode)**: 啟用自動重載 (`TIMER_AUTORELOAD_EN`)，確保中斷週期性觸發而不需手動重置。
- **計數方向**: 向上計數 (`TIMER_COUNT_UP`)。

## 3. 中斷註冊機制
本函式庫採用了較新版本的 ESP-IDF 建議方式：
- 使用 `timer_isr_callback_add()` 取代舊有的 `timer_isr_register()`。
- 優點是能更好地與系統內部的定時器管理共存，且支援更現代的驅動模型。
- 中斷函數被要求使用 `IRAM_ATTR` 屬性，確保代碼常駐於內部 RAM，避免因快取失效（Flash Cache Miss）導致的中斷延遲。

## 4. 精度與解析度
- **系統解析度**: 1μs。
- **伺服控制解析度**: 12μs (由 `TIMER_INTERVAL_MICRO` 定義)。
    - 選擇 12μs 而非 10μs 是為了相容 ESP32 core v2.0.1+ 的系統開銷需求。
    - 對於標準伺服馬達（500us - 2500us 脈衝），12μs 的解析度提供了約 160 階的細分，足以應付大多數非工業級應用。

---
*註：內容同步紀錄於 `analysis/ESP32_ISR_Servo/details/hardware_timer.md`*
