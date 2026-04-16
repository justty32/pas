# 教學 05：資深工程師的 ESP-IDF 遷移架構指南

既然你 C++ 很強，遷移過程對你來說本質上是**「重新封裝」**。

## 1. 從 .ino 到 .cpp
Arduino 的 `.ino` 檔案本質上是把所有的函數揉在一起。遷移的第一步是**模組化**：
*   把 `imu.ino` 封裝成一個 `IMU` 類別。
*   把 `webServer.ino` 封裝成一個 `NetworkManager` 類別。

## 2. 使用 ESP-IDF 的組件化 (Components)
ESP-IDF 鼓勵將功能拆分為獨立的組件。這對你來說就是建立獨立的 Libs：
*   `components/robot_algo`：直接把原來的 `libs/IK`, `libs/gait` 放進去。它們是純數學，幾乎不用改動。
*   `components/servo_driver`：這是你要重寫的部分。利用 ESP-IDF 的 `ledc` 驅動來實現原有的 `angleToPulse` 邏輯。

## 3. 異常安全與數值穩定性
作為資深開發者，你在移植 IK 演算法時，最重要的一件事是增加**防禦性編程**：
*   **數學保護**：原代碼直接使用 `acos(val)`。如果 `val` 因為浮點誤差變成 `1.000001`，`acos` 會崩潰。
*   **移植實踐**：建立一個 `safe_acos` 函數，內部使用 `std::clamp(val, -1.0, 1.0)`。這能保證即便運動超出物理極限，系統也不會拋出 `NaN`。

## 4. 日誌系統 (Logging)
拋棄 `Serial.print`，改用 ESP-IDF 的 `ESP_LOGI`, `ESP_LOGE`。
*   這能讓你根據標籤（Tag）與層級（Info, Error）過濾資訊，這在調試複雜的多核心競爭問題時非常有幫助。

## 5. 遷移清單 (Checklist)
1.  **建立 CMake 專案**。
2.  **配置 NVS (Non-volatile Storage)**：取代 EEPROM 來儲存舵機校準值。
3.  **配置 MCPWM/LEDC**：實現底層驅動。
4.  **搬運 C++ 算法**：封裝進 Components。
5.  **建立 FreeRTOS Task**：設定優先級並綁定核心。
