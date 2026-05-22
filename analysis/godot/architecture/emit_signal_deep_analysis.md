# emit_signal 底層完整呼叫鏈分析

> 對應原始碼：`core/variant/callable.h/cpp`, `core/object/object.h/cpp`, `core/object/class_db.h`, `core/object/message_queue.h`

---

## 1. Callable 的內部結構

`core/variant/callable.h:48-53`

```cpp
class Callable {
    alignas(8) StringName method;   // 標準 Callable：方法名（非空時）
    union {
        uint64_t object = 0;        // 標準 Callable：ObjectID（存 uint64_t）
        CallableCustom *custom;     // 自訂 Callable（Lambda、bind/unbind 包裝）
    };
};
```

`Callable` 只有 16 bytes（`alignas(8)` 強制對齊），三種狀態：

| 狀態 | `method` | `object/custom` | 對應情境 |
|------|---------|-----------------|---------|
| null | `StringName()` | 0 | 未初始化 |
| 標準 | 非空 | ObjectID (uint64) | `callable_mp(obj, &Cls::method)` |
| 自訂 | `StringName()` | `CallableCustom*` | Lambda、bind()、unbind() |

`is_standard()`、`is_custom()`、`is_null()` 就是靠這兩個欄位的狀態判斷。

---

## 2. Callable::callp() —— 三路分派

`core/variant/callable.cpp:43-71`

```cpp
void Callable::callp(const Variant **p_arguments, int p_argcount,
                     Variant &r_return_value, CallError &r_call_error) const {
    if (is_null()) {
        r_call_error.error = CallError::CALL_ERROR_INSTANCE_IS_NULL;
    } else if (is_custom()) {
        // 自訂路徑：Lambda、bind/unbind 包裝
        if (!is_valid()) { /* 錯誤 */ return; }
        custom->call(p_arguments, p_argcount, r_return_value, r_call_error);
    } else {
        // 標準路徑：Object + method name
        Object *obj = ObjectDB::get_instance(ObjectID(object)); // 安全查詢！
        r_return_value = obj->callp(method, p_arguments, p_argcount, r_call_error);
    }
}
```

關鍵：標準路徑先通過 `ObjectDB::get_instance()` 做 validator 檢查，確認物件還活著，才進入 `obj->callp()`。

---

## 3. Object::callp() —— 腳本優先，C++ 備援

`core/object/object.cpp:893-952`

```cpp
Variant Object::callp(const StringName &p_method, const Variant **p_args,
                      int p_argcount, Callable::CallError &r_error) {
    // 特殊處理：free()
    if (p_method == CoreStringName(free_)) { memdelete(this); return Variant(); }

    Variant ret;

    // === 第一優先：腳本層（GDScript / C# / 其他腳本語言）===
    if (script_instance) {
        ret = script_instance->callp(p_method, p_args, p_argcount, r_error);
        switch (r_error.error) {
            case CALL_OK: return ret;                  // GDScript 處理成功，直接返回
            case CALL_ERROR_INVALID_METHOD: break;     // 方法不在腳本中，繼續往下
            default: return ret;                       // 其他錯誤，直接返回
        }
    }

    // === 第二優先：C++ 原生方法（ClassDB）===
    MethodBind *method = ClassDB::get_method(get_class_name(), p_method);
    if (method) {
        ret = method->call(this, p_args, p_argcount, r_error);
    } else {
        r_error.error = CALL_ERROR_INVALID_METHOD;
    }
    return ret;
}
```

**查找順序**：腳本（GDScript 的 method table）→ 原生 C++ MethodBind（ClassDB 繼承鏈）。

這正是為什麼 GDScript 可以「覆寫」（override）C++ 的虛擬方法：因為腳本層永遠先被查詢。

---

## 4. MethodBind::call() —— C++ 方法的最終調用

`core/object/method_bind.h`（`MethodBind` 為抽象基底，各個 bind 模板特化）

每個 `ClassDB::bind_method()` 都會建立一個模板化的 `MethodBind` 子類實例。其核心是：

```cpp
// 簡化示意（實際由宏生成）
virtual Variant call(Object *p_object, const Variant **p_args, int p_arg_count,
                     Callable::CallError &r_error) override {
    // 1. 做參數型別與數量驗證
    // 2. 將 Variant** 參數轉換為 C++ 具體型別（PtrToArg<T>::convert）
    // 3. 調用實際的成員函數指標
    return (static_cast<MyClass*>(p_object)->*method_ptr)(typed_arg1, typed_arg2, ...);
}
```

`PtrToArg<T>` 是一組特化模板，負責 `Variant ↔ C++ 型別` 的零拷貝轉換。

---

## 5. 自訂 Callable 路徑：bind() / unbind() / Lambda

`core/variant/callable_bind.h`（`CallableCustom` 子類）

`callable.bind(extra_arg)` 回傳一個新的 `Callable`，其 `custom` 指向 `CallableBind` 實例：

```
原始 Callable: { object=A, method="on_hp_changed" }
            ↓ .bind(player_name)
CallableBind: { inner_callable=原始, bound_args=[player_name] }
```

呼叫時 `CallableBind::call()` 會把 bound_args 附加到 p_args 陣列末尾再轉發。

`unbind(n)` 類似，建立 `CallableUnbind`，呼叫時忽略最後 n 個參數。

Lambda (`callable_mp`) 生成 `CallableMethodPointer`，其 `call()` 直接呼叫 C++ 成員函數指標，不經過 ClassDB 查詢。

---

## 6. CONNECT_DEFERRED 路徑：MessageQueue

`core/object/message_queue.h`

當連接帶有 `CONNECT_DEFERRED` 旗標時，`emit_signalp()` 改為：

```cpp
MessageQueue::get_singleton()->push_callablep(callable, args, argc, true);
```

`MessageQueue` 是一個環形緩衝區（`CommandBuffer`），存放「待執行的 Callable + 參數」。在每個主迴圈的特定階段（SceneTree 的 `_notification(NOTIFICATION_PROCESS)` 之後）調用 `flush()`，此時所有 deferred callable 才真正執行。

```
幀開始
  ↓
物理更新 (_physics_process)
  ↓
幀更新 (_process)
  ↓
MessageQueue::flush()   ← CONNECT_DEFERRED 的 signal 在此執行
  ↓
渲染
  ↓
幀結束
```

這確保 deferred signal 的 callback 不會在物理或動畫更新到一半時觸發，造成物件狀態不一致。

---

## 7. 完整呼叫鏈（含所有路徑）

```
emit_signal("signal_name", arg1, arg2)
  │
  └─ Object::emit_signalp("signal_name", &args, 2)
       │
       ├─ [鎖定 signal_mutex]
       ├─ 從 signal_map 取出 SignalData
       ├─ 快照 slot_callables[]（≤5 個用 stack，>5 個用 heap）
       ├─ [解鎖]
       │
       ├─ ONE_SHOT 的 Callable → _disconnect() 預先斷開
       │
       ├─ RefCounted 物件 → reference() 防止 emit 期間銷毀
       │
       └─ for each callable:
            │
            ├─ [CONNECT_DEFERRED]
            │     MessageQueue::push_callablep()
            │       → 推入環形緩衝區，等 flush() 時再執行
            │
            └─ [立即執行]
                  Callable::callp(args, argc, ret, ce)
                    │
                    ├─ [is_standard] ObjectDB::get_instance(object_id)
                    │                  → validator 通過 → Object*
                    │               obj->callp(method, args, argc, error)
                    │                  │
                    │                  ├─ script_instance->callp()  ← GDScript 優先
                    │                  │    → GDScriptFunction::call()
                    │                  │        → GDScript VM 位元組碼執行
                    │                  │
                    │                  └─ ClassDB::get_method() → MethodBind
                    │                       → PtrToArg 轉型
                    │                       → C++ 成員函數指標直接呼叫
                    │
                    └─ [is_custom]  custom->call()
                         ├─ CallableMethodPointer → C++ 函數指標直接呼叫
                         ├─ CallableBind → 附加參數後遞迴呼叫 inner
                         └─ CallableUnbind → 裁切參數後遞迴呼叫 inner
```

---

## 8. 效能關鍵點

| 階段 | 開銷來源 | 緩解方式 |
|------|---------|---------|
| slot 快照 | `Callable` 複製 | ≤5 個時完全在 stack 上，無 heap 分配 |
| ObjectDB 查詢 | SpinLock + 陣列存取 | `_ALWAYS_INLINE_`，實際就是兩次記憶體讀取 |
| GDScript 方法查詢 | HashMap 查詢 + VM 進入 | 無法避免；這是 GDScript 比 C++ 慢的根本原因 |
| C++ MethodBind | PtrToArg 轉型 | 通常為零拷貝（直接讀 Variant 內部 union） |
| DEFERRED push | 環形緩衝區寫入 | 幾乎是一次 memcpy |

---

*原始碼版本：Godot Engine 4.7.dev*
*分析日期：2026-05-22*
