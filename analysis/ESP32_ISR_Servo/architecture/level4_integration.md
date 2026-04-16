# ESP32_ISR_Servo 整合模式分析 (Level 4)

## 1. Header-Only 模式與衝突解決
本函式庫採用了變形的 Header-only 模式，將宣告與實作分離至 `.hpp` 與 `_Impl.h`：

- **ESP32_ISR_Servo.hpp**: 包含類別宣告。適用於多檔案專案中的標頭包含。
- **ESP32_ISR_Servo.h**: 包含實作。**只能被包含一次**。

這種設計允許開發者在多個模組中引用伺服馬達物件，同時避免了在 Arduino 環境下常見的 `multiple definition` 錯誤。

## 2. 物件實體化 (Singleton Pattern)
函式庫在 `_Impl.h` 中通常會定義一個全域單例物件 `ESP32_ISR_Servos`。

## 3. 程式碼位置
- 類別宣告：`src/ESP32_ISR_Servo.hpp`
- 實作引導：`src/ESP32_ISR_Servo.h`
- 具體實作：`src/ESP32_ISR_Servo_Impl.h`
