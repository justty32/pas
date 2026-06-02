# 教學：新增 GDExtension Signal 並串接 GDScript

> 核對於 2026-06-02（Claude Sonnet 4.6）。源碼位置：`derived/opennefia-cpp/src/gbind/`。

本教學說明如何在 `OpenNefiaWorld`（或任何 GDExtension 類別）裡新增一個 Signal，並在 GDScript 端 connect 與實作 handler。以「英雄升級」signal（`hero_level_up(new_level: int)`）為例。

---

## 修改點一覽

| 步驟 | 檔案 | 改動 |
|---|---|---|
| ① 宣告 Signal | `src/gbind/opennefia_world_gd.cpp` → `_bind_methods()` | `ADD_SIGNAL(...)` |
| ② 觸發 Signal | 同檔案的相關邏輯 | `emit_signal("hero_level_up", level)` |
| ③ GDScript 訂閱 | `godot_test/map_view.gd` | `connect()` + handler 函式 |

---

## 1. 宣告 Signal（`_bind_methods()`）

**`src/gbind/opennefia_world_gd.cpp`**，`_bind_methods()` 函式（約 `cpp:47`）：

### 無參數 Signal
```cpp
// 例：game_over（已有）
ADD_SIGNAL(MethodInfo("game_over"));
```

### 帶一個 int 參數
```cpp
// 例：floor_changed（已有）
ADD_SIGNAL(MethodInfo("floor_changed",
    PropertyInfo(Variant::INT, "floor_num")));

// 新增：hero_level_up
ADD_SIGNAL(MethodInfo("hero_level_up",
    PropertyInfo(Variant::INT, "new_level")));
```

### 帶多個不同型別參數
```cpp
// 例：item_picked_up（已有）——String + int
ADD_SIGNAL(MethodInfo("item_picked_up",
    PropertyInfo(Variant::STRING, "item_name"),
    PropertyInfo(Variant::INT,    "heal_amount")));
```

### 常用 Variant 型別對照

| C++ 型別 | `PropertyInfo` 第一參數 | GDScript 型別 |
|---|---|---|
| `int` / `int64_t` | `Variant::INT` | `int` |
| `float` / `double` | `Variant::FLOAT` | `float` |
| `godot::String` | `Variant::STRING` | `String` |
| `bool` | `Variant::BOOL` | `bool` |
| `godot::Vector2` | `Variant::VECTOR2` | `Vector2` |
| `godot::Array` | `Variant::ARRAY` | `Array` |

---

## 2. 在邏輯中觸發 Signal

**`src/gbind/opennefia_world_gd.cpp`**，在升級判斷的地方呼叫 `emit_signal()`：

```cpp
// 假設英雄每擊殺 5 隻 NPC 升一級（例子，非實際源碼）
void opennefia_gd::OpenNefiaWorld::check_level_up() {
    int kills = get_kill_count();
    int new_level = kills / 5 + 1;
    if (new_level > hero_level_) {
        hero_level_ = new_level;
        // 傳 int 參數：直接傳值
        emit_signal("hero_level_up", new_level);
    }
}
```

### 各型別的傳遞方式

```cpp
// int
emit_signal("floor_changed", current_floor_);          // floor_changed(int)

// String（C++ std::string → godot::String）
String npc_id_gd(meta.proto_id.c_str());
emit_signal("npc_died", npc_id_gd);                    // npc_died(String)

// 多參數
emit_signal("item_picked_up", iname, heal_done);        // item_picked_up(String, int)

// 無參數
emit_signal("game_over");                               // game_over()
```

---

## 3. GDScript 端訂閱與 handler

**`godot_test/map_view.gd`**：

### 訂閱（`_ready()` 或場景初始化時）

```gdscript
func _ready() -> void:
    # 已有的訂閱範例
    world.world_changed.connect(_on_world_changed)
    world.game_over.connect(_on_game_over)
    world.item_picked_up.connect(_on_item_picked_up)

    # 新增：訂閱 hero_level_up
    world.hero_level_up.connect(_on_hero_level_up)
```

### Handler 函式（參數型別需對應 Signal 宣告）

```gdscript
# 無參數 Signal
func _on_game_over() -> void:
    _dead = true
    info_label.text = "GAME OVER — 按 R 重試"

# 帶 int
func _on_hero_level_up(new_level: int) -> void:
    info_label.text = "升級！目前等級：%d" % new_level

# 帶 String + int
func _on_item_picked_up(item_name: String, heal: int) -> void:
    info_label.text = "拾取 %s（+%d）" % [item_name, heal]
```

---

## 4. 重建流程

新增 Signal 只改 `_bind_methods()` 與 emit 邏輯，**不需要新增 .cpp 檔**，只需重建：

```powershell
cmake --build build --target opennefia_gd
# 複製 .dll 到 godot_test/bin/
```

若 Signal 宣告與 handler 參數不吻合（如宣告 int 但 handler 收 String），Godot 執行時會在 Output 面板印出警告，連線仍成功但參數值未定義。

---

## 常見陷阱

| 問題 | 原因 | 修正 |
|---|---|---|
| Godot 找不到 Signal 名稱 | 忘記重建 DLL 或 DLL 版本舊 | 重建並確認複製到 `godot_test/bin/` |
| handler 收到型別錯誤 | C++ 的 `emit_signal` 傳 `std::string`（非 `godot::String`） | 先轉：`String gd_str(cpp_str.c_str())` 再 emit |
| Signal 沒被觸發 | `emit_signal` 在 C++ 端呼叫時 Node 未進場景樹 | 確認 `_ready()` 後才觸發，或用 `call_deferred` |
