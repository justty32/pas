# ESP32_ISR_Servo 專案架構概覽 (Level 1)

## 1. 專案目的 (Project Purpose)
`ESP32_ISR_Servo` 是一個為 ESP32 系列微控制器設計的 Arduino 函式庫。其核心目標是利用 **硬體定時器中斷 (Hardware Timer Interrupt)** 來驅動多個伺服馬達（Servo Motors）。透過 ISR（中斷服務常式）機制，可以確保伺服馬達的控制信號精確度，且不會受到 `loop()` 中其他耗時任務（如 WiFi 連線、阻塞式延遲）的干擾。

## 2. 核心技術棧 (Core Technology Stack)
- **硬體平台**: ESP32, ESP32-S2, ESP32-S3, ESP32-C3。
- **開發框架**: Arduino 框架, PlatformIO。
- **程式語言**: C++。
- **關鍵技術**: 
    - **硬體定時器 (Hardware Timer)**: 使用 ESP32 的 64 位元計數器硬體定時器。
    - **中斷服務常式 (ISR)**: 透過中斷觸發伺服脈衝控制，達到非阻塞與高精度特性。

## 3. 主要功能 (Key Features)
- **高效能定時器利用**: 僅需使用 1 個硬體定時器即可控制多達 16 個（甚至更多）獨立的伺服馬達。
- **高精確度**: 相較於基於 `millis()` 或 `micros()` 的軟體定時器，ISR 驅動的信號幾乎完美對齊。
- **非阻塞控制**: 控制邏輯運行於中斷層級，即使 `setup()` 或 `loop()` 被阻塞（例如進行 WiFi/Blynk 連線），伺服馬達仍能正常運作。
- **多型號支援**: 廣泛支援最新的 ESP32 核心（v2.0.1+）及其各種衍生晶片。

## 4. 目錄結構分析 (Source Tree)
- `src/`: 核心邏輯實現。
    - `ESP32_ISR_Servo.h`: 主要標頭檔。
    - `ESP32_ISR_Servo.hpp`: 可多次包含的標頭檔，用於解決重複定義問題。
    - `ESP32_ISR_Servo_Impl.h`: 具體的模板或函數實現（Impl 模式）。
    - `ESP32FastTimerInterrupt.hpp`: 底層定時器中斷封裝。
- `examples/`: 示範程式碼，包含多檔案專案範例、多伺服馬達隨機轉動等。
- `library.properties`: Arduino 函式庫描述文件。

## 5. 初始分析結論 (Initial Findings)
該專案是典型的嵌入式底層驅動封裝，重點在於對 ESP32 定時器中斷的高效封裝。對於需要精確控制伺服馬達且同時執行複雜任務（如網路通訊）的專案非常有價值。

---
*註：內容同步紀錄於 `analysis/ESP32_ISR_Servo/architecture/overview.md`*
