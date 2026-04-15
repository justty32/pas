# 深度解析：Taisei 的 Task DSL

在 Taisei 中，大多數遊戲邏輯不是在 `update()` 循環中完成的，而是在**任務（Tasks）**中定義。對於 C++ 開發者來說，這是一種類似於非搶佔式、協程化的行為樹。

## 核心宏定義

### 1. `TASK(name, args)`

定義一個新的協程任務。

```c
// 定義一個名為 my_enemy_logic 的任務，它接受一個敵人 Boxed 指針和一個初始位置
TASK(my_enemy_logic, { BoxedEnemy e; cmplx start_pos; }) {
    // 通過 TASK_BIND 獲取實體。如果該實體已銷毀，任務將在此處掛起。
    Enemy *e = TASK_BIND(ARGS.e);
    
    // 初始化位置
    e->pos = ARGS.start_pos;
    
    // 進入行為循環
    for (int i = 0; i < 5; ++i) {
        // 發射彈幕
        play_sfx("shot1");
        PROJECTILE(
            .proto = pp_ball,
            .pos = e->pos,
            .color = RGB(1.0, 0.5, 0.0),
            .move = move_linear(2 * cdir(rng_angle()))
        );
        
        // 等待 30 幀 (0.5 秒)
        WAIT(30);
    }
    
    // 逃離屏幕並銷毀 (STALL 防止任務結束後立即釋放實體，直到實體自行銷毀)
    e->move = move_linear(-2 * I);
    STALL;
}
```

### 2. `WAIT(n)` 與 `YIELD`

-   `WAIT(n)`：任務在當前點掛起，並在 `n` 幀後恢復。
-   `YIELD`：在當前幀出讓控制權，下一幀立即恢復。這對於在每一幀都需要運算的邏輯（如追蹤玩家）很有用。

### 3. `INVOKE_TASK(name, ...)`

異步啟動一個子任務。子任務會獨立於父任務運行。

### 4. `INVOKE_SUBTASK(name, ...)`

啟動一個子任務並掛起當前任務，直到子任務完成。這與函數調用類似，但發生在協程上下文中。

## 內存安全與實體綁定

在 C++ 中，您可能會擔心指針懸空（Dangling Pointers）。在 Taisei 的 Task DSL 中：

-   實體通過「裝箱（Boxing）」進行傳遞，例如 `BoxedEnemy`。
-   `TASK_BIND` 內部會檢查實體是否仍然有效。如果實體已被銷毀，`TASK_BIND` 會直接將當前任務設為 `DEAD` 狀態並終止。
-   這在很大程度上解決了異步行為中常見的引用失效問題。

## 向量運算技巧 (C++ vs. C99 Complex)

| 操作 | C++ (Eigen/GLM) | Taisei (C99 Complex) |
| :--- | :--- | :--- |
| 定義向量 | `Vector2 pos(x, y)` | `cmplx pos = x + y*I;` |
| 單位向量 | `vec.normalized()` | `cnormalize(vec)` |
| 獲取角度 | `atan2(y, x)` | `carg(vec)` |
| 旋轉 90 度 | `Rotation(pi/2) * vec` | `vec * I` |
| 按角度旋轉 | `Rotation(a) * vec` | `vec * cdir(a)` |

---

## 練習建議

觀察 `src/stages/stage1/timeline.c` 中的任務定義。試著理解他們如何通過嵌套任務來構建敵人的複雜行為序列。
