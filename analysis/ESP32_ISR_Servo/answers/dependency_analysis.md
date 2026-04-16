# ESP32_ISR_Servo 依賴性分析

## 1. 是否依賴 Arduino 框架？
**是。** 該函式庫主要作為一個 Arduino Library 開發。

## 2. 具體依賴點
- **標頭檔**: 包含 `<Arduino.h>`。
- **GPIO 控制**: 使用 `pinMode()` 與 `digitalWrite()` 進行腳位初始化與 PWM 脈衝輸出。
- **型別定義**: 使用 Arduino 定義的 `boolean`, `uint8_t` 等型別（雖然部分與標準 C++ 重疊）。
- **除錯輸出**: 依賴 `Serial.print` 進行訊息顯示。

## 3. 與 ESP-IDF 的關係
該函式庫採用了「Arduino 外殼 + ESP-IDF 核心」的模式：
- **外殼 (API)**: 提供給使用者的是 Arduino 風格的類別與方法。
- **核心 (Hardware Timer)**: 透過調用 ESP-IDF 的 `driver/timer.h` 來操作硬體暫存器，以達到微秒級的中斷精確度。

## 4. 移植建議
若要在純 ESP-IDF 環境中使用：
1. 需移除所有 `Arduino.h` 依賴。
2. 將 `digitalWrite` 替換為 `gpio_set_level`。
3. 將 `pinMode` 替換為 `gpio_config`。
4. 重寫硬體定時器的初始化流程，以符合純 ESP-IDF 的專案結構。
