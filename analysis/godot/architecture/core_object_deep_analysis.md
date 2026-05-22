# Godot Object 系統深度分析

> 對應原始碼：`core/object/object.h`, `core/object/object.cpp`, `core/object/class_db.h`, `core/object/class_db.cpp`, `core/object/ref_counted.h`, `core/object/object_id.h`

---

## 1. ObjectID 的 64 位元布局

`ObjectID` 是一個 64 位元整數，並非單純的指標或遞增序號，而是具有精確的位元分層：

```
 bit 63       bit 62 ～ bit 24       bit 23 ～ bit 0
┌──────┬───────────────────────────┬─────────────────────┐
│isRef │   validator (39 bits)     │  slot index (24 bits)│
└──────┴───────────────────────────┴─────────────────────┘
```

- **bit 63** (`OBJECTDB_REFERENCE_BIT`)：為 1 表示物件是 `RefCounted` 子類別。
- **bits 24-62** (`OBJECTDB_VALIDATOR_BITS = 39`)：驗證碼，每次物件被分配到 slot 時遞增。讓 ObjectDB 能偵測「懸空 ID」——即 slot 被回收再利用後，舊 ID 的 validator 不再匹配。
- **bits 0-23** (`OBJECTDB_SLOT_MAX_COUNT_BITS = 24`)：slot 索引，最多支援 $2^{24} = 16,777,216$ 個同時存在的物件。

原始碼位置：`core/object/object.h:1072-1091`

```cpp
struct ObjectSlot { // 128 bits per slot
    uint64_t validator : 39;
    uint64_t next_free : 24;
    uint64_t is_ref_counted : 1;
    Object *object = nullptr;
};
```

### ObjectDB::get_instance() 的查詢路徑

`core/object/object.h:1106-1126`

```cpp
_ALWAYS_INLINE_ static Object *get_instance(ObjectID p_instance_id) {
    uint64_t id = p_instance_id;
    uint32_t slot = id & OBJECTDB_SLOT_MAX_COUNT_MASK;     // 取 slot 索引
    spin_lock.lock();
    uint64_t validator = (id >> 24) & OBJECTDB_VALIDATOR_MASK; // 取 validator
    if (unlikely(object_slots[slot].validator != validator)) {  // validator 不符？
        spin_lock.unlock();
        return nullptr;  // 物件已被刪除，ID 已失效
    }
    Object *object = object_slots[slot].object;
    spin_lock.unlock();
    return object;
}
```

重點：這是整個引擎中「安全取用物件指標」的標準路徑，比直接存指標安全，因為它能偵測已刪除的物件。

---

## 2. AncestralClass 快速型別位元欄位

`core/object/object.h:585-603`

```cpp
enum class AncestralClass : unsigned int {
    REF_COUNTED             = 1 << 0,
    NODE                    = 1 << 1,
    RESOURCE                = 1 << 2,
    SCRIPT                  = 1 << 3,
    CANVAS_ITEM             = 1 << 4,
    CONTROL                 = 1 << 5,
    NODE_2D                 = 1 << 6,
    COLLISION_OBJECT_2D     = 1 << 7,
    AREA_2D                 = 1 << 8,
    NODE_3D                 = 1 << 9,
    VISUAL_INSTANCE_3D      = 1 << 10,
    GEOMETRY_INSTANCE_3D    = 1 << 11,
    COLLISION_OBJECT_3D     = 1 << 12,
    PHYSICS_BODY_3D         = 1 << 13,
    MESH_INSTANCE_3D        = 1 << 14,
};
```

每個 `Object` 實例在 `_ancestry` 欄位（15 bits）中存放這個 bitfield。這讓引擎可以用一次位元運算（`_ancestry & (uint32_t)AncestralClass::NODE`）做型別檢查，而不需要 vtable 查詢或動態型別轉換。

物件在建立時，各子類別負責在建構子中設定自己的 bit。例如 `RefCounted` 的建構子會設 `REF_COUNTED` bit，`Node` 的建構子會設 `NODE` bit。

---

## 3. GDCLASS 宏的完整展開

`core/object/object.h:489-556`

`GDCLASS(MyClass, ParentClass)` 是整個物件模型的核心。它展開成以下功能：

### 3.1 型別靜態標識

```cpp
static const GDType &get_gdtype_static() {
    static GDType *_class_static;
    if (unlikely(!_class_static)) {
        assign_type_static(&_class_static, "MyClass", &ParentClass::get_gdtype_static());
    }
    return *_class_static;
}
static const StringName &get_class_static() {
    return get_gdtype_static().get_name();
}
```

第一次呼叫時才建立（lazy init），之後快取在靜態指標中。`get_class_static()` 回傳的 `StringName` 就是 ClassDB 中的 key。

### 3.2 initialize_class() — 唯一執行一次的 Registration 入口

```cpp
static void initialize_class() {
    static bool initialized = false;
    if (initialized) return;
    ParentClass::initialize_class();            // 1. 先確保父類已初始化
    _add_class_to_classdb(get_gdtype_static(), &super_type::get_gdtype_static()); // 2. 在 ClassDB 建立 ClassInfo
    if (MyClass::_get_bind_methods() != ParentClass::_get_bind_methods()) {
        _bind_methods();                        // 3. 只在子類有覆寫時才呼叫
    }
    initialized = true;
}
```

**呼叫時機**：`ClassDB::register_class<T>()` 會呼叫 `T::initialize_class()`。

### 3.3 _setv / _getv 虛擬鏈

GDSOFTCLASS（被 GDCLASS 包含）也展開了 `_setv`/`_getv`/`_notification_forwardv` 等虛擬方法，讓 `_set`/`_get`/`_notification` 能透過函數指標比對的方式做 Override 偵測，不需要每個類別都顯式呼叫 `super::_set()`。

---

## 4. ClassDB 的資料結構

`core/object/class_db.h:122-168`

### ClassInfo —— 每個類別在 ClassDB 中的記錄

```cpp
struct ClassInfo {
    ClassInfo *inherits_ptr = nullptr;         // 指向父類 ClassInfo 的直接指標
    const GDType *gdtype = nullptr;

    HashMap<StringName, MethodBind *> method_map;             // 方法名 → MethodBind
    HashMap<StringName, LocalVector<MethodBind *>> method_map_compatibility; // 相容性方法
    AHashMap<StringName, int64_t> constant_map;               // 常數
    AHashMap<StringName, MethodInfo> signal_map;              // 信號定義（注意：只存 MethodInfo，不存連接）
    List<PropertyInfo> property_list;                         // 屬性的有序清單（Inspector 順序）
    HashMap<StringName, PropertyInfo> property_map;           // 屬性名 → PropertyInfo
    AHashMap<StringName, PropertySetGet> property_setget;     // setter/getter 快取

    StringName inherits;
    StringName name;
    bool exposed = false;           // 是否可以在 GDScript 中使用
    bool is_virtual = false;        // 是否為抽象類別
    Object *(*creation_func)(bool); // 工廠函數指標
};
```

`signal_map` 只存信號的**定義**（參數型別、名稱）；實際的**連接**（哪個 Callable 訂閱了哪個物件的哪個信號）存在每個 `Object` 實例的 `signal_map` 中，不在 ClassDB。

### ClassDB::register_class<T>() 的流程

`core/object/class_db.h:254-267`

```cpp
template <typename T>
static void register_class(bool p_virtual = false) {
    Locker::Lock lock(Locker::STATE_WRITE);
    static_assert(std::is_same_v<typename T::self_type, T>, "Class not declared properly");
    T::initialize_class();                       // ← 呼叫 GDCLASS 展開的 initialize_class
    ClassInfo *t = classes.getptr(T::get_class_static());
    t->creation_func = &creator<T>;              // 設定工廠函數
    t->exposed = true;                           // 標記為可在 GDScript 使用
    t->is_virtual = p_virtual;
    t->class_ptr = T::get_class_ptr_static();
    T::register_custom_data_to_otdb();           // 可選的額外 OTDB 資料
}
```

`register_abstract_class()` 不設定 `creation_func`，所以無法被 `ClassDB::instantiate()` 直接創建。

---

## 5. Object 實例的信號資料結構

`core/object/object.h:631-644`

```cpp
// 每個 Object 實例擁有：
HashMap<StringName, SignalData> signal_map;   // key = 信號名
List<Connection> connections;                 // 此物件作為「訂閱者」的所有連接清單

struct SignalData {
    MethodInfo user;                          // 若為 add_user_signal() 加入，存信號資訊
    HashMap<Callable, Slot> slot_map;         // key = 訂閱者 Callable（含 target object）
    bool removable = false;                   // 只有 add_user_signal 加入的才可移除

    struct Slot {
        int reference_count = 0;             // 用於 CONNECT_REFERENCE_COUNTED 模式
        Connection conn;                     // 完整連接資訊
        List<Connection>::Element *cE;       // 反向指向訂閱者 connections list 的節點
    };
};
```

`slot_map` 以 `Callable` 為 key。`Callable` 的比對邏輯使用 `get_base_comparator()`，因此帶 `bind()`/`unbind()` 的 Callable 在重複連接判斷時，會先退掉這些包裝層再比較。

---

## 6. emit_signalp() 完整呼叫鏈

`core/object/object.cpp:1303-1440`

### 步驟一：鎖定並複製 slot 清單

```cpp
constexpr int MAX_SLOTS_ON_STACK = 5;
alignas(Callable) uint8_t slot_callable_stack[sizeof(Callable) * 5]; // stack 優化
// ...
{
    ObjectSignalLock signal_lock(this);    // 加 Mutex
    SignalData *s = signal_map.getptr(p_name);
    if (!s) return ERR_UNAVAILABLE;       // 信號未被任何人連接，直接返回

    if (s->slot_map.size() > 5) {
        slot_callables = (Callable *)memalloc(...); // 超過 5 個才 heap 分配
    }
    for (auto &slot_kv : s->slot_map) {
        memnew_placement(&slot_callables[i], Callable(slot_kv.value.conn.callable)); // 深拷貝
        slot_flags[i] = slot_kv.value.conn.flags;
    }
} // 解鎖
```

關鍵設計：**拷貝完 slot 清單後立即解鎖**，讓後續的 callback 執行時不持有鎖。這允許 callback 內部再次 emit_signal 或 connect/disconnect，而不會死鎖。

### 步驟二：預先斷開 ONE_SHOT 連接

```cpp
for (uint32_t i = 0; i < slot_count; ++i) {
    if (slot_flags[i] & CONNECT_ONE_SHOT) {
        _disconnect(p_name, slot_callables[i]); // 在呼叫前就斷開，防止遞迴再次觸發
    }
}
```

### 步驟三：防止 RefCounted 物件在 emit 期間被銷毀

```cpp
bool pending_unref = Object::cast_to<RefCounted>(this)
    ? ((RefCounted *)this)->reference()   // 暫時增加引用計數
    : false;
```

信號 callback 可能是最後一個持有此物件的引用，為防止物件在 emit 過程中被刪除，先人工增加一次引用。

### 步驟四：分派給每個 Callable

```cpp
for (uint32_t i = 0; i < slot_count; ++i) {
    if (!callable.is_valid()) continue; // 目標已被刪除

    if (flags & CONNECT_DEFERRED) {
        // 延遲：推入 MessageQueue，下一幀主迴圈末尾執行
        MessageQueue::get_singleton()->push_callablep(callable, args, argc, true);
    } else {
        // 立即：直接呼叫
        _emitting = true;
        Variant ret;
        callable.callp(args, argc, ret, ce);
        _emitting = false;
    }
}
```

`CONNECT_DEFERRED` 的本質是將 Callable 推入 `MessageQueue`，而不是在當前影格呼叫。MessageQueue 在每個主迴圈結束時被清空。

---

## 7. Ref<T> 智慧指標的兩種「引用」路徑

`core/object/ref_counted.h:57-225`

```cpp
template <bool Init>
_FORCE_INLINE_ void ref_pointer(T *p_refcounted) {
    Ref cleanup_ref;
    cleanup_ref.reference = reference; // 舊指標交給 cleanup_ref 管理，離開 scope 自動 unref
    reference = p_refcounted;
    if (reference) {
        if constexpr (Init) {
            if (!reference->init_ref()) { reference = nullptr; } // 第一次賦值（從裸指標）
        } else {
            if (!reference->reference()) { reference = nullptr; } // 複製（從 Ref<T>）
        }
    }
}
```

- `Init = true`（`operator=(T*)` 呼叫）：使用 `init_ref()`，處理物件剛 `new` 出來、引用計數從 0 → 1 的特殊初始狀態。
- `Init = false`（`operator=(const Ref&)` 呼叫）：使用 `reference()`，普通的引用計數遞增。

`unref()` 時：
```cpp
void unref() {
    if (reference) {
        if (reinterpret_cast<RefCounted *>(reference)->unreference()) {
            memdelete(reinterpret_cast<RefCounted *>(reference)); // 引用歸零才刪除
        }
        reference = nullptr;
    }
}
```

`reinterpret_cast` 的安全性由 C++ 的線性繼承保證：`T*` 等於 `RefCounted*` 在記憶體布局上是相同的。

---

## 8. GDExtension 的 ObjectGDExtension 橋接結構

`core/object/object.h:316-380`

```cpp
struct ObjectGDExtension {
    GDExtension *library;            // 指回 .gdextension 的 GDExtension 資源
    ObjectGDExtension *parent;       // 繼承鏈（GDExtension 類可繼承另一個 GDExtension 類）

    // C 函數指標 —— 這是跨 ABI 的橋接介面
    GDExtensionClassSet set;         // 對應 _set()
    GDExtensionClassGet get;         // 對應 _get()
    GDExtensionClassGetPropertyList get_property_list;
    GDExtensionClassNotification2 notification2;
    GDExtensionClassCreateInstance2 create_instance2;  // 工廠函數
    GDExtensionClassFreeInstance free_instance;
    GDExtensionClassGetVirtual2 get_virtual2;          // 取得虛擬方法實作的函數
    GDExtensionClassCallVirtualWithData call_virtual_with_data;

    const GDType *gdtype;            // 此擴展的類型物件
};
```

當一個 GDExtension 類別被呼叫虛擬方法時，引擎呼叫 `get_virtual2` 取得該虛擬方法在 C++ 側的函數指標，再透過 `call_virtual_with_data` 執行。這一層間接讓引擎可以在不知道外部 C++ 實作的情況下，透過穩定的 C ABI 呼叫它。

`ClassDB::register_extension_class()` 的流程（`core/object/class_db.cpp:2324`）：
1. 確認父類 `parent_class_name` 已存在於 ClassDB。
2. 在 `classes` HashMap 中建立新的 `ClassInfo`。
3. 將 `ClassInfo.gdextension` 指向傳入的 `ObjectGDExtension` 結構。
4. 設定 `creation_func` 為包裝 `create_instance2` 的 lambda。

---

## 9. 呼叫鏈總覽圖

### 類別註冊（引擎啟動時）
```
ClassDB::register_class<MyClass>()
  └─ MyClass::initialize_class()
       ├─ ParentClass::initialize_class()   （遞迴確保父類先完成）
       ├─ _add_class_to_classdb()           → 在 ClassDB.classes 建立 ClassInfo
       └─ MyClass::_bind_methods()          → ADD_SIGNAL, ADD_PROPERTY, bind_method
            ├─ ClassDB::add_signal()        → 寫入 ClassInfo.signal_map (只存 MethodInfo)
            └─ ClassDB::bind_method()       → 建立 MethodBind，寫入 ClassInfo.method_map
```

### 信號發射（執行時）
```
my_obj->emit_signal("hp_changed", new_hp)
  └─ Object::emit_signalp("hp_changed", &args, 1)
       ├─ [加鎖] signal_map.getptr("hp_changed") → 取得 SignalData
       ├─ [複製 slot 清單到 stack 或 heap]
       ├─ [解鎖]
       ├─ [ONE_SHOT 的 Callable 預先 disconnect]
       ├─ [若是 RefCounted，暫時 reference() 防止銷毀]
       └─ for each slot:
            ├─ CONNECT_DEFERRED → MessageQueue::push_callablep()  （下一幀執行）
            └─ 否則 → callable.callp(args, argc, ret, ce)          （立即執行）
```

---

## 10. 關鍵設計原則小結

| 設計 | 實現方式 | 目的 |
|------|---------|------|
| 安全物件查詢 | ObjectID = slot index + validator bits | 偵測懸空 ID，不儲存裸指標 |
| 快速型別測試 | `_ancestry` 15-bit bitfield | 避免 vtable 查詢，O(1) 型別檢查 |
| 信號執行緒安全 | emit 時複製 slot 清單後解鎖 | 允許 callback 中 connect/disconnect |
| 跨語言虛擬方法 | `ObjectGDExtension` C 函數指標 | ABI 穩定，不依賴 C++ vtable |
| 智慧指標正確性 | `init_ref` vs `reference` 兩路徑 | 正確處理從裸指標首次賦值的邊界情況 |

---

*原始碼版本：Godot Engine 4.7.dev*
*分析日期：2026-05-22*
