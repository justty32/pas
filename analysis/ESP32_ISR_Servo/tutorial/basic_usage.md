# ESP32_ISR_Servo 基礎使用教學

本教學將引導您如何使用 `ESP32_ISR_Servo` 函式庫，透過硬體定時器中斷精確控制多個伺服馬達。

## 1. 快速開始步驟

### 第一步：包含標頭檔
在您的 `.ino` 或主程式檔中包含函式庫：
```cpp
#define TIMER_INTERRUPT_DEBUG       1
#define ISR_SERVO_DEBUG             1

// 選擇 ESP32 硬體定時器編號 (0-3)
#define USE_ESP32_TIMER_NO          3

#include "ESP32_ISR_Servo.h"
```

### 第二步：初始化定時器與伺服馬達
在 `setup()` 函數中，設定定時器並綁定伺服馬達腳位：
```cpp
int servoIndex1 = -1;

void setup() {
    Serial.begin(115200);
    
    // 選擇要使用的硬體定時器
    ESP32_ISR_Servos.useTimer(USE_ESP32_TIMER_NO);

    // 設置伺服馬達 (腳位, 最小脈衝寬度, 最大脈衝寬度)
    // SG90 常用範圍約 500-2450us
    servoIndex1 = ESP32_ISR_Servos.setupServo(GPIO_NUM_18, 544, 2400);

    if (servoIndex1 != -1) {
        Serial.println("伺服馬達 1 初始化成功");
    }
}
```

### 第三步：控制轉動角度
在 `loop()` 或任何地方使用 `setPosition()`：
```cpp
void loop() {
    // 將伺服馬達轉動到 90 度
    ESP32_ISR_Servos.setPosition(servoIndex1, 90);
    delay(1000);

    // 轉動到 180 度
    ESP32_ISR_Servos.setPosition(servoIndex1, 180);
    delay(1000);
}
```

## 2. 核心 API 說明

- `useTimer(timerNo)`: 指定使用 ESP32 四個硬體定時器中的哪一個（建議避開系統預留或 WiFi 使用的定時器）。
- `setupServo(pin, min, max)`: 註冊一個伺服馬達，返回一個 `servoIndex`。若返回 `-1` 表示失敗（可能超過 16 個或腳位錯誤）。
- `setPosition(index, position)`: 設定角度 (0-180 度)。
- `setPulseWidth(index, width)`: 直接設定脈衝寬度 (微秒)，提供更底層的控制。

## 3. 重要注意事項
1. **中斷安全**: 由於此函式庫運作於 ISR 中，避免在 `setPosition` 頻繁調用的變數上使用非原子操作。
2. **非阻塞特性**: 即使您的 `loop()` 中有長達 5 秒的 `delay()`，伺服馬達的 PWM 信號仍會持續輸出，不會抖動或停止。
3. **電源供應**: ESP32 的 3.3V 腳位電流有限，若連接多個伺服馬達，請務必使用外部 5V 電源並與 ESP32 共地。

---
*註：內容同步紀錄於 `analysis/ESP32_ISR_Servo/tutorial/basic_usage.md`*
