# GDExtension 進階教學：自定義資源 (Resources) 與信號 (Signals)

本教學將深入探討如何利用 GDExtension 建立自定義資源類別，以及如何在 C++ 中定義與觸發信號。

## 1. 目標導向
本教學旨在解決以下進階開發問題：
- 如何建立可重複使用的數據容器 (`Resource`)。
- 如何在 C++ 中定義信號並傳遞參數。
- 如何在 GDScript 中監聽來自 C++ 的信號。
- 如何處理方法的預設參數。

## 2. 前置知識
- 已完成「建立自定義 Node 與 Scene」基礎教學。
- **`core/object`**: 了解 `RefCounted` 與 `Resource` 的關係。
- **`core/variant`**: 了解 `Variant` 如何封裝不同類型的參數。

## 3. 原始碼導航 (核心參考)
- **資源基底**: `core/object/ref_counted.h` (約 L45: `RefCounted` 類別)
- **信號註冊**: `core/object/class_db.h` (約 L150: `ClassDB::add_signal`)
- **參數封裝**: `core/variant/variant.h` (了解如何傳遞複雜資料)

## 4. 實作步驟

### 步驟 A：建立自定義資源 (`my_resource.h`)
資源是 Godot 中用於儲存資料的基礎物件，繼承自 `Resource` (進而繼承自 `RefCounted`)。

```cpp
#ifndef MY_RESOURCE_H
#define MY_RESOURCE_H

#include <godot_cpp/classes/resource.hpp>

namespace godot {

class MyDataResource : public Resource {
    GDCLASS(MyDataResource, Resource);

private:
    String player_name;
    int level;

protected:
    static void _bind_methods();

public:
    void set_player_name(const String &p_name);
    String get_player_name() const;
    
    void set_level(int p_level);
    int get_level() const;

    MyDataResource();
};

}

#endif
```

### 步驟 A-2：實作 `MyDataResource::_bind_methods()` (`my_resource.cpp`)
這一步至關重要，缺少它資源的屬性將無法在編輯器中顯示，也無法序列化。

```cpp
#include "my_resource.h"
#include <godot_cpp/core/class_db.hpp>

using namespace godot;

MyDataResource::MyDataResource() {
    level = 1;
}

void MyDataResource::_bind_methods() {
    // 綁定 getter/setter
    ClassDB::bind_method(D_METHOD("get_player_name"), &MyDataResource::get_player_name);
    ClassDB::bind_method(D_METHOD("set_player_name", "p_name"), &MyDataResource::set_player_name);
    ClassDB::bind_method(D_METHOD("get_level"), &MyDataResource::get_level);
    ClassDB::bind_method(D_METHOD("set_level", "p_level"), &MyDataResource::set_level);

    // 暴露給 Inspector 與序列化系統
    ADD_PROPERTY(PropertyInfo(Variant::STRING, "player_name"), "set_player_name", "get_player_name");
    ADD_PROPERTY(PropertyInfo(Variant::INT, "level", PROPERTY_HINT_RANGE, "1,100,1"), "set_level", "get_level");
}

void MyDataResource::set_player_name(const String &p_name) { player_name = p_name; }
String MyDataResource::get_player_name() const { return player_name; }
void MyDataResource::set_level(int p_level) { level = p_level; }
int MyDataResource::get_level() const { return level; }
```

並在 `register_types.cpp` 的 `initialize` 函數中一併註冊：
```cpp
void initialize_my_extension_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) { return; }
    ClassDB::register_class<MyDataResource>(); // 必須先於使用它的節點
    ClassDB::register_class<MyNode3D>();
}
```

### 步驟 B：定義並觸發信號 (`my_node_advanced.h`)
我們將擴展先前的 `MyNode3D`，加入信號支援。

```cpp
class MyNode3D : public Node3D {
    GDCLASS(MyNode3D, Node3D);

protected:
    static void _bind_methods() {
        // ... 原有的方法綁定 ...

        // 核心：定義信號 "threshold_reached"，帶有一個名為 "value" 的參數
        ADD_SIGNAL(MethodInfo("threshold_reached", PropertyInfo(Variant::INT, "value"), PropertyInfo(Variant::OBJECT, "data", PROPERTY_HINT_RESOURCE_TYPE, "MyDataResource")));

        ClassDB::bind_method(D_METHOD("trigger_event"), &MyNode3D::trigger_event);
    }

public:
    void trigger_event(int p_val, const Ref<MyDataResource> &p_data) {
        // 核心：觸發信號
        emit_signal("threshold_reached", p_val, p_data);
    }
};
```

### 步驟 C：方法預設參數與進體綁定
有時您希望 C++ 方法在 Godot 中有預設參數。

```cpp
void MyNode3D::_bind_methods() {
    // 綁定帶有預設參數的方法
    ClassDB::bind_method(D_METHOD("test_defaults", "p_val"), &MyNode3D::test_defaults, DEFVAL(100));
}

void MyNode3D::test_defaults(int p_val) {
    // 若 GDScript 呼叫 test_defaults()，p_val 將為 100
}
```

## 5. 實務應用範例 (GDScript 端)

當您編譯並註冊後，在 GDScript 中可以這樣使用：

```gdscript
extends Node3D

func _ready():
    var my_node = $MyNode3D
    # 監聽 C++ 信號
    my_node.threshold_reached.connect(_on_threshold_reached)
    
    # 建立自定義資源並傳遞
    var res = MyDataResource.new()
    res.player_name = "Gemini"
    res.level = 99
    
    my_node.trigger_event(500, res)

func _on_threshold_reached(value, data):
    print("收到 C++ 信號！數值：", value, " 玩家：", data.player_name)
```

## 6. 驗證與偵錯方式
1. **資源序列化**：嘗試在編輯器中建立 `MyDataResource` 實例，並存為 `.tres` 檔案。檢查文字編輯器中屬性是否正確儲存。
2. **信號追蹤**：在編輯器的「節點 (Node)」面板中，檢查 `MyNode3D` 是否列出了 `threshold_reached` 信號。
3. **類型檢查**：確保在 `ADD_SIGNAL` 中指定的 `PROPERTY_HINT_RESOURCE_TYPE` 與您的資源類別名稱一致，否則 Inspector 將無法正確辨識。
