# GDExtension 教學：建立自定義 Node 與 Scene

本教學將引導您如何使用 C++ 透過 GDExtension 機制在 Godot 4 中建立自定義的 Node 類型。

## 1. 目標導向
本教學旨在解決以下問題：
- 如何定義一個繼承自 Godot 原生類別（如 `Node3D`）的 C++ 類別。
- 如何將該類別註冊到 Godot 的 `ClassDB` 中，使其能在編輯器與腳本中使用。
- 如何在 GDExtension 中定義屬性與方法並暴露給引擎。

## 2. 前置知識
在開始之前，您需要了解以下 Godot 核心模組：
- **`core/object`**: 了解 `GDCLASS` 宏與 `ClassDB` 註冊機制。
- **`core/extension`**: 了解 GDExtension 的初始化層級 (`InitializationLevel`)。
- **`godot-cpp`**: 這是官方提供的 C++ 綁定庫（雖然本教學專注於原理，但實務開發通常使用此庫）。

## 3. 原始碼導航 (核心參考)
開發自定義節點時，應參考以下引擎原始碼以了解介面規範：
- **類別定義規範**: `core/object/object.h` (約 L100: `GDCLASS` 宏定義)
- **類別註冊介面**: `core/object/class_db.h` (約 L70: `ClassDB::register_class<T>()`)
- **GDExtension 介面**: `core/extension/gdextension_interface.cpp` (定義了外部庫如何與引擎通訊)

## 4. 實作步驟

### 步驟 A：定義 C++ 類別 (`my_node.h`)
首先，建立您的自定義類別。

```cpp
#ifndef MY_NODE_H
#define MY_NODE_H

#include <godot_cpp/classes/node3d.hpp>

namespace godot {

class MyNode3D : public Node3D {
    GDCLASS(MyNode3D, Node3D); // 核心：註冊類別與父類資訊

private:
    double time_passed;
    double amplitude;

protected:
    static void _bind_methods(); // 用於暴露方法與屬性

public:
    void set_amplitude(const double p_amplitude);
    double get_amplitude() const;

    void _process(double delta) override; // 重載生命週期函數

    MyNode3D();
    ~MyNode3D();
};

}

#endif
```

### 步驟 B：實作類別邏輯 (`my_node.cpp`)

```cpp
#include "my_node.h"
#include <godot_cpp/core/class_db.hpp>

using namespace godot;

MyNode3D::MyNode3D() {
    time_passed = 0.0;
    amplitude = 10.0;
}

MyNode3D::~MyNode3D() {}

// 核心：將方法與屬性綁定到 ClassDB
void MyNode3D::_bind_methods() {
    ClassDB::bind_method(D_METHOD("get_amplitude"), &MyNode3D::get_amplitude);
    ClassDB::bind_method(D_METHOD("set_amplitude", "p_amplitude"), &MyNode3D::set_amplitude);

    // 暴露屬性給編輯器 Inspector
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "amplitude"), "set_amplitude", "get_amplitude");
}

void MyNode3D::set_amplitude(const double p_amplitude) {
    amplitude = p_amplitude;
}

double MyNode3D::get_amplitude() const {
    return amplitude;
}

void MyNode3D::_process(double delta) {
    time_passed += delta;
    Vector3 new_pos = Vector3(
        Math::sin(time_passed) * amplitude,
        0,
        0
    );
    set_position(new_pos);
}
```

### 步驟 C：註冊擴展入口 (`register_types.cpp`)
您需要定義初始化函數，告訴 Godot 您的擴展包含哪些類別。

```cpp
#include "register_types.h"
#include "my_node.h"
#include <gdextension_interface.h>
#include <godot_cpp/core/defs.hpp>
#include <godot_cpp/godot.hpp>

using namespace godot;

void initialize_my_extension_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }
    // 核心：將您的類別註冊到場景層級
    ClassDB::register_class<MyNode3D>();
}

void uninitialize_my_extension_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }
}

extern "C" {
GDExtensionBool GDE_EXPORT my_extension_library_init(GDExtensionInterfaceGetProcAddress p_get_proc_address, const GDExtensionClassLibraryPtr p_library, GDExtensionInitialization *r_initialization) {
    godot::GDExtensionBinding::InitObject init_obj(p_get_proc_address, p_library, r_initialization);

    init_obj.register_initializer(initialize_my_extension_module);
    init_obj.register_terminator(uninitialize_my_extension_module);
    init_obj.set_minimum_library_initialization_level(MODULE_INITIALIZATION_LEVEL_SCENE);

    return init_obj.init();
}
}
```

## 5. 建置與配置

### 步驟 D：專案目錄結構
建議的工作目錄佈局（Extension 獨立於 Godot 專案外）：
```
my_extension/
├── godot-cpp/          # git submodule：官方 C++ 綁定
├── src/
│   ├── my_node.h
│   ├── my_node.cpp
│   └── register_types.cpp
├── SConstruct          # 建置腳本
└── demo/               # Godot 專案
    ├── project.godot
    └── bin/
        └── my_extension.gdextension
```

### 步驟 E：建置腳本 (`SConstruct`)
最簡化的 SCons 腳本（詳細版本參考 godot-cpp 官方範本）：

```python
#!/usr/bin/env python
import os

# godot-cpp 提供的建置環境設定
env = SConscript("godot-cpp/SConstruct")

# 加入您的原始碼
env.Append(CPPPATH=["src/"])
sources = Glob("src/*.cpp")

# 建置共享函式庫
library = env.SharedLibrary(
    "demo/bin/libmy_extension{}{}".format(env["suffix"], env["SHLIBSUFFIX"]),
    source=sources,
)
Default(library)
```

執行建置：
```bash
# Debug 版本
scons

# Release 版本
scons target=template_release
```

### 步驟 F：`.gdextension` 設定檔
在 Godot 專案的 `res://bin/` 下建立 `my_extension.gdextension`：

```ini
[configuration]
entry_symbol = "my_extension_library_init"
compatibility_minimum = "4.1"

[libraries]
# Windows
windows.debug.x86_64   = "res://bin/libmy_extension.windows.template_debug.x86_64.dll"
windows.release.x86_64 = "res://bin/libmy_extension.windows.template_release.x86_64.dll"

# Linux
linux.debug.x86_64     = "res://bin/libmy_extension.linux.template_debug.x86_64.so"
linux.release.x86_64   = "res://bin/libmy_extension.linux.template_release.x86_64.so"

# macOS (使用 framework bundle)
macos.debug             = "res://bin/libmy_extension.macos.template_debug.framework"
macos.release           = "res://bin/libmy_extension.macos.template_release.framework"
```

## 6. 驗證方式
1. **編譯**：執行 `scons` 產出動態連結庫，確認 `demo/bin/` 下出現對應的 `.dll` / `.so` 檔案。
2. **配置確認**：`.gdextension` 的 `entry_symbol` 必須與 `register_types.cpp` 中 `GDE_EXPORT` 函數名稱完全一致。
3. **檢查編輯器**：
    - 開啟 Godot 編輯器（`demo/` 目錄）。
    - 在「建立新節點」對話框中搜尋 `MyNode3D`。
    - 若出現則表示 Extension 載入成功。
    - 檢查右側 Inspector 面板是否出現 `Amplitude` 屬性。
4. **執行場景**：將 `MyNode3D` 加入場景並執行，觀察其是否根據 `_process` 邏輯進行左右擺動。
5. **常見問題**：
    - 若節點不出現：確認 `.gdextension` 路徑正確，且 `entry_symbol` 名稱無誤。
    - 若引擎崩潰：通常是因為 `_bind_methods()` 中使用了不存在的方法指標，或 `ClassDB::register_class` 呼叫在錯誤的 `InitializationLevel`。
