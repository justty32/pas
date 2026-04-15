# 實踐：創建你的第一個敵人與彈幕

在這一章，我們將學習如何編寫一個簡單的敵人和彈幕邏輯。假設您正在為一個新的關卡編寫腳本。

## 1. 定義敵人邏輯

在您的 `timeline.c` 中，使用 `TASK` 宏定義一個簡單的敵對行為。

```c
#include "stages/common_imports.h"

// 隨機發射圓形彈幕的任務
TASK(circle_shot, { BoxedEnemy e; int shots; }) {
    Enemy *e = TASK_BIND(ARGS.e);
    
    // 獲取一個隨機起始角度
    double start_angle = rng_angle();
    
    for(int i = 0; i < ARGS.shots; ++i) {
        double angle = start_angle + (M_TAU / ARGS.shots) * i;
        
        PROJECTILE(
            .proto = pp_rice,      // 彈幕形狀：米粒
            .pos = e->pos,         // 從敵人位置發射
            .color = RGB(0.2, 0.6, 1.0), // 藍色
            .move = move_linear(2 * cdir(angle)) // 線性移動
        );
    }
    
    // 播放音效
    play_sfx("shot1");
}

// 敵人的主邏輯
TASK(my_first_enemy, { cmplx start_pos; }) {
    // 生成一個紅色的小妖精 (espawn_fairy_red)
    // 並掉落能量道具 (ITEMS(.power = 1))
    Enemy *e = TASK_BIND(espawn_fairy_red(ARGS.start_pos, ITEMS(.power = 1)));
    
    // 設置敵人的移動路徑
    // 從 start_pos 移動到屏幕中心 (VIEWPORT_W/2, 100)
    e->move = move_from_towards(e->pos, VIEWPORT_W/2 + 100*I, 0.02);
    
    // 等待 60 幀到達位置
    WAIT(60);
    
    // 停止移動 (加速度設為 0)
    e->move.attraction = 0;
    e->move.velocity = 0;
    
    // 進行三次圓形射擊
    for(int r = 0; r < 3; ++r) {
        INVOKE_SUBTASK(circle_shot, ENT_BOX(e), .shots = 12 + r * 4);
        WAIT(45); // 每次間隔 45 幀
    }
    
    // 向屏幕上方逃離
    e->move.acceleration = -0.05 * I;
    
    // 保持任務運行，直到實體超出邊界或被銷毀
    STALL;
}
```

## 2. 在關卡時間軸中觸發任務

您的關卡時間軸（Timeline）通常會有一個循環或一系列的 `WAIT` 指令。

```c
TASK(stage_timeline, { ... }) {
    // 等待關卡開始 120 幀
    WAIT(120);
    
    // 在屏幕左側生成敵人
    INVOKE_TASK(my_first_enemy, .start_pos = -50 + 100*I);
    
    WAIT(180);
    
    // 在屏幕右側生成敵人
    INVOKE_TASK(my_first_enemy, .start_pos = VIEWPORT_W + 50 + 100*I);
    
    // 繼續關卡流程...
}
```

## 3. 重要宏解讀：`PROJECTILE`

作為 C++ 開發者，您可能會預期這是一個對象構造函數。實際上，`PROJECTILE` 是一個非常巧妙的包裝宏：

```c
PROJECTILE(
    .proto = pp_ball,   // 彈幕原型
    .pos = e->pos,      // 初始位置
    .color = RGB(1,0,0),// 顏色
    .move = ...         // 移動屬性 (重要!)
);
```

### 移動模式 (`move` 屬性)

Taisei 提供了一系列工廠函數來創建移動邏輯：
-   `move_linear(velocity)`: 恆定速度。
-   `move_asymptotic_simple(dest_velocity, speed_factor)`: 速度漸進到目標。
-   `move_sine(amplitude, frequency)`: 正弦路徑。
-   `move_accelerated(velocity, acceleration)`: 加速度運動。

## 4. 如何編譯與測試

1.  將您的代碼放入 `src/stages/` 下的對應關卡目錄。
2.  確保 `meson.build` 包含了您的源文件。
3.  運行 `meson compile -C build` (如果您已配置環境)。
4.  啟動遊戲並選擇對應關卡。

---

## 總結

-   **實體生命週期**：通過 `TASK_BIND` 確保實體存在。
-   **異步編程**：利用 `WAIT` 和 `INVOKE_TASK` 輕鬆實現並發行為。
-   **聲明式數據**：`PROJECTILE` 和 `ITEMS` 宏讓繁瑣的參數設置變得直觀。
