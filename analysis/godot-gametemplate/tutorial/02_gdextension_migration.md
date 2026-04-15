# 教學 02: 將 MoverTopDown2D 遷移至 GDExtension (C++)

本教學將引導您如何利用 GDExtension 將 `Godot-GameTemplate` 中效能最密集的移動模組 (`MoverTopDown2D`) 重寫為 C++。這對於處理大量敵人（超過 100 個）時的效能優化至關重要。

## 1. 環境準備
1. **克隆 godot-cpp**: 確保 `projects/godot-cpp` 已存在且初始化。
2. **安裝編譯工具**: 確保您的系統已安裝 `SCons` 與 `C++` 編譯器 (MSVC/GCC/Clang)。

## 2. 建立 C++ 類別 (宣告)
在您的 C++ 專案 `src/` 下建立 `mover_top_down_2d.h`：

```cpp
#ifndef MOVER_TOP_DOWN_2D_H
#define MOVER_TOP_DOWN_2D_H

#include <godot_cpp/classes/shape_cast2d.hpp>
#include <godot_cpp/classes/character_body2d.hpp>
#include <godot_cpp/variant/vector2.hpp>

namespace godot {

class MoverTopDown2D : public ShapeCast2D {
    GDCLASS(MoverTopDown2D, ShapeCast2D)

private:
    Vector2 velocity;
    float acceleration = 1000.0f;
    float max_speed = 300.0f;
    CharacterBody2D *character = nullptr;

protected:
    static void _bind_methods();

public:
    MoverTopDown2D();
    ~MoverTopDown2D();

    void _physics_process(double delta) override;
    void add_impulse(const Vector2 &impulse);
    // ... 其他方法
};

}

#endif
```

## 3. 實作核心邏輯 (C++ 轉譯)
在 `src/mover_top_down_2d.cpp` 中實作 `get_impulse` 的 C++ 版本：

```cpp
Vector2 MoverTopDown2D::get_impulse(Vector2 current_velocity, Vector2 target_velocity, float acc, float delta) {
    Vector2 direction = target_velocity - current_velocity;
    float distance = direction.length();
    float step_acc = (float)delta * acc;
    float ratio = 0.0f;
    if (distance > 0.0f) {
        ratio = (step_acc / distance < 1.0f) ? (step_acc / distance) : 1.0f;
    }
    return direction * ratio;
}
```

## 4. 註冊與編譯
1. 在 `register_types.cpp` 中註冊類別：
   `GDREGISTER_CLASS(MoverTopDown2D);`
2. 執行 `scons platform=linux` (或 windows) 編譯擴展庫。
3. 將產出的 `.gdextension` 檔案放入 `addons/top_down/bin/`。

## 5. 在編輯器中整合
1. 打開 `addons/top_down/scenes/actors/actor.tscn`。
2. 找到 `MoverTopDown2D` 節點。
3. **重要步驟**:
    - 在 Inspector 中右鍵點擊 Script -> **Clear**。
    - 在「新增節點」選單中，您會發現一個新的 `MoverTopDown2D` (帶有 C++ 圖標)。
    - 或者，如果類別名稱衝突，將 C++ 類別重新命名為 `MoverTopDownNative`。
4. 重新連接 `ResourceNode` 的引用的數據。

## 6. 效能對比驗證
1. **情境**: 在畫面上生成 200 個分裂中的 Slime 敵人。
2. **觀察**: 
    - [ ] 使用 `F6` 啟動遊戲並開啟 `Monitor` 視窗。
    - [ ] 比較 `Physics Frame Time`。GDScript 通常在 12ms 以上，C++ 應能降至 1ms - 2ms。
    - [ ] 觀察 CPU 負載與卡頓（Shader 預載後）。
