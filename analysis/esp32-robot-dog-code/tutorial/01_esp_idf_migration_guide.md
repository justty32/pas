# 教學：如何將 ESP32 機器狗專案移植到 ESP-IDF

這份教學將引導你如何將 `esp32-robot-dog-code` 的核心演算法與控制邏輯從老舊的 Arduino 環境遷移到專業的 ESP-IDF 框架。我們將重點放在目錄結構規劃、C++ 演算法的移植，以及使用 ESP-IDF 原生 API 重寫舵機驅動。

## 步驟 1：建立 ESP-IDF 專案與結構規劃

首先，使用 ESP-IDF 工具鏈建立一個空白專案：

```bash
idf.py create-project robot_dog_idf
cd robot_dog_idf
```

為了保持架構清晰，我們將原專案的 `libs/` 內容提取為獨立的 Component。建立如下的目錄結構：

```text
robot_dog_idf/
├── CMakeLists.txt
├── main/
│   ├── CMakeLists.txt
│   └── main.cpp            # 主程式與 FreeRTOS 任務調度
└── components/
    ├── robot_algo/         # 存放 IK, Planner, Gait, Transition
    │   ├── CMakeLists.txt
    │   ├── include/        # 所有的 .h 檔
    │   └── src/            # 所有的 .cpp 檔
    └── servo_hal/          # 存放新的 LEDC 舵機驅動
        ├── CMakeLists.txt
        ├── include/
        └── src/
```

## 步驟 2：移植核心演算法 (`robot_algo` 組件)

將原專案 `software/robot_dog_esp32/libs/` 下的所有代碼（除了硬體相依的 `HAL_body`）複製到 `components/robot_algo/` 中。

### 關鍵修改 1：修正數學依賴與 `NaN` 保護
在 `IK.cpp` 中，原作者直接使用了 `<math.h>`。在 ESP-IDF 中這可以直接使用，但**必須**加入邊界保護。修改 `ikAcos` 和 `ikAsin`：

```cpp
#include <math.h>
#include <algorithm> // 為了使用 std::clamp (C++17) 或自己寫巨集

// 假設在 IK.cpp 內部
double clamp(double d, double min, double max) {
  const double t = d < min ? min : d;
  return t > max ? max : t;
}

double IK::ikAcos(double value) {
    // 防止超出 [-1, 1] 導致 NaN
    return normalizeAngleRad(acos(clamp(value, -1.0, 1.0)));
}

double IK::ikAsin(double value) {
    return normalizeAngleRad(asin(clamp(value, -1.0, 1.0)));
}
```

### 關鍵修改 2：Component 的 CMakeLists
在 `components/robot_algo/CMakeLists.txt` 寫入：

```cmake
idf_component_register(SRCS "src/IK.cpp" "src/planner.cpp" "src/gait.cpp" "src/transition.cpp"
                    INCLUDE_DIRS "include")
```

## 步驟 3：重寫舵機驅動 (`servo_hal` 組件)

原專案依賴 `ESP32_ISR_Servo`。在 ESP-IDF 中，控制 12 顆舵機最穩定的方式是使用 **LEDC (LED Control)** 模組，它支援高達 16 個硬體 PWM 通道。

### 實作 LEDC 初始化與脈衝輸出
在 `components/servo_hal/src/servo_hal.cpp` 中實作：

```cpp
#include "driver/ledc.h"
#include "esp_err.h"

// 定義 50Hz (20ms 週期) 的 PWM
#define SERVO_FREQ_HZ 50 
#define LEDC_TIMER    LEDC_TIMER_0
#define LEDC_MODE     LEDC_LOW_SPEED_MODE
#define LEDC_DUTY_RES LEDC_TIMER_14_BIT // 14-bit 解析度，0-16383

void init_servo_channel(int gpio_num, ledc_channel_t channel) {
    // 1. 初始化 Timer
    ledc_timer_config_t ledc_timer = {
        .speed_mode       = LEDC_MODE,
        .duty_resolution  = LEDC_DUTY_RES,
        .timer_num        = LEDC_TIMER,
        .freq_hz          = SERVO_FREQ_HZ,
        .clk_cfg          = LEDC_AUTO_CLK
    };
    ledc_timer_config(&ledc_timer);

    // 2. 初始化通道
    ledc_channel_config_t ledc_channel = {
        .gpio_num       = gpio_num,
        .speed_mode     = LEDC_MODE,
        .channel        = channel,
        .intr_type      = LEDC_INTR_DISABLE,
        .timer_sel      = LEDC_TIMER,
        .duty           = 0, // 初始佔空比
        .hpoint         = 0
    };
    ledc_channel_config(&ledc_channel);
}

// 將微秒 (us) 轉換為 14-bit Duty Cycle
uint32_t us_to_duty(uint32_t pulse_us) {
    // 20ms (20000us) 對應 2^14 (16384)
    return (pulse_us * 16384) / 20000;
}

void set_servo_pulse(ledc_channel_t channel, uint32_t pulse_us) {
    uint32_t duty = us_to_duty(pulse_us);
    ledc_set_duty(LEDC_MODE, channel, duty);
    ledc_update_duty(LEDC_MODE, channel);
}
```

### 移植「分段線性映射」演算法
將原專案中極具價值的 `angleToPulse` 函數移植過來：

```cpp
// 在 servo_hal.cpp 中
uint32_t angleToPulse(double angleRad, const servoProfile_t& profile) {
    double angleDeg = angleRad * (180.0 / M_PI);
    
    // 邊界保護
    if (angleDeg < profile.minAngle) angleDeg = profile.minAngle;
    if (angleDeg > profile.maxAngle) angleDeg = profile.maxAngle;

    // 分段線性插值 (與原專案邏輯一致)
    if (angleDeg < 30) return mapf(angleDeg, profile.minAngle, 30, profile.degMin, profile.deg30);
    if (angleDeg < 50) return mapf(angleDeg, 30, 50, profile.deg30, profile.deg50);
    // ... 依此類推 ...
    
    return 1500; // Default
}
```

## 步驟 4：多核心任務調度 (`main.cpp`)

ESP-IDF 建立在 FreeRTOS 之上。原專案的 `loop()` 和 `servicesLoop()` 需要被封裝為明確的 Task。

```cpp
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

static const char *TAG = "ROBOT_DOG";

// 宣告原有的全域物件 (IK, Planner 等)
// ...

// Core 1：運動控制迴圈 (250Hz -> 4ms)
void motion_control_task(void *pvParameters) {
    TickType_t xLastWakeTime;
    const TickType_t xFrequency = pdMS_TO_TICKS(4); // 4ms
    xLastWakeTime = xTaskGetTickCount();

    while (1) {
        // 1. 執行 updateGait()
        // 2. 執行 IK 運算
        // 3. 透過 servo_hal 更新 LEDC 佔空比
        
        // 絕對精確的延遲，保證 250Hz
        vTaskDelayUntil(&xLastWakeTime, xFrequency); 
    }
}

// Core 0：服務迴圈 (Web, WiFi, IMU)
void service_task(void *pvParameters) {
    while (1) {
        // 處理 WebSocket 封包
        // 讀取 IMU 數據
        vTaskDelay(pdMS_TO_TICKS(10)); // 10ms 釋放 CPU
    }
}

extern "C" void app_main(void) {
    ESP_LOGI(TAG, "Starting Robot Dog ESP-IDF Port");

    // 1. 初始化 NVS、WiFi、硬體
    // 2. 初始化 LEDC 舵機通道
    
    // 啟動運動控制任務綁定到 Core 1
    xTaskCreatePinnedToCore(
        motion_control_task, 
        "MotionTask", 
        8192, 
        NULL, 
        configMAX_PRIORITIES - 1, // 高優先級
        NULL, 
        1                         // Core 1
    );

    // 啟動服務任務綁定到 Core 0
    xTaskCreatePinnedToCore(
        service_task, 
        "ServiceTask", 
        8192, 
        NULL, 
        5, 
        NULL, 
        0                         // Core 0
    );
}
```

## 總結
透過上述步驟，你將成功剝離 Arduino 的臃腫依賴。使用 `LEDC` 取代原有的混合計時器能提供極度穩定的 PWM 輸出，而原生的 FreeRTOS `vTaskDelayUntil` 能保證你的 250Hz IK 運算迴圈精確無誤，從根本上解決原專案因計時器衝突和阻塞導致的失效問題。
