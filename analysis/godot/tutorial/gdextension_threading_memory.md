# GDExtension 進階教學：多執行緒處理與記憶體管理

本教學將探討如何在 GDExtension 中安全地進行多執行緒開發，以及如何遵循 Godot 的記憶體管理規範。

## 1. 目標導向
本教學旨在解決以下問題：
- 如何在 C++ 中正確分配與釋放記憶體，避免與引擎產生衝突。
- 如何利用 `WorkerThreadPool` 執行耗時的背景任務。
- 如何在多執行緒環境下安全地存取共享數據。
- 如何避免常見的記憶體洩漏與執行緒競態 (Race Conditions)。

## 2. 前置知識
- 已完成基礎與資源相關教學。
- **`core/os`**: 了解 `Memory`, `Thread`, `Mutex` 等抽象層。
- **`core/templates`**: 了解 `SafeNumeric` 等原子操作類。

## 3. 原始碼導航 (核心參考)
- **記憶體分配**: `core/os/memory.h` (L100: `alloc_static` 等基礎分配函數)
- **執行緒池**: `core/object/worker_thread_pool.h` (L45: `add_task` 與 `add_group_task`)
- **執行緒同步**: `core/os/mutex.h` (標準互斥鎖封裝)

## 4. 記憶體管理規範

在 Godot 引擎開發中，應避免直接使用標準庫的 `new` / `delete` 或 `malloc` / `free`，而應使用引擎提供的巨集：

### 4.1 靜態物件分配
使用 `memnew` 與 `memdelete`，這能讓引擎追蹤記憶體使用狀況並確保建構/解構子被正確呼叫。

```cpp
// 推薦做法
MyObject *obj = memnew(MyObject);
// ... 使用物件 ...
memdelete(obj);
```

### 4.2 引用計數物件 (RefCounted/Resource)
對於繼承自 `RefCounted` 的物件，務必使用 `Ref<T>` 智慧指標。

```cpp
{
    Ref<MyDataResource> data = memnew(MyDataResource);
    // 離開作用域後，引用計數歸零，自動 memdelete
}
```

### 4.3 陣列與緩衝區
優先使用 `PackedArray` 或 `Vector<T>`，它們內建了寫入時複製 (CoW) 與記憶體安全檢查。

## 5. 多執行緒處理機制

Godot 4 引入了 `WorkerThreadPool` 來處理非同步工作。

### 5.1 執行簡單任務 (Task)
適合處理一次性的背景計算。

```cpp
void MyNode3D::start_background_task() {
    WorkerThreadPool::TaskID task_id = WorkerThreadPool::get_singleton()->add_task(
        callable_mp(this, &MyNode3D::_expensive_calculation)
    );
    // 稍後可以透過 task_id 檢查進度或等待完成
}

void MyNode3D::_expensive_calculation() {
    // 執行重度運算
    // 注意：禁止在此處修改場景樹 (Node tree)！
}
```

### 5.2 執行群組任務 (Group Task)
適合將一個大任務拆分成多個小塊並行處理（例如：處理大量頂點數據）。

```cpp
void process_data_chunk(void *userdata, uint32_t index) {
    // 根據 index 處理對應的資料塊
}

void MyNode3D::run_parallel_process(int count) {
    WorkerThreadPool::GroupID group_id = WorkerThreadPool::get_singleton()->add_group_task(
        process_data_chunk, nullptr, count
    );
    WorkerThreadPool::get_singleton()->wait_for_group_task_completion(group_id);
}
```

## 6. 執行緒安全性與同步

### 6.1 使用 Mutex 保護資料
當多個執行緒同時存取同一個變數時，必須加鎖。

```cpp
Mutex data_mutex;
int shared_value;

void MyNode3D::safe_increment() {
    MutexLock lock(data_mutex);
    shared_value++;
}
```

### 6.2 使用 SafeNumeric
對於簡單的數值計數，使用原子操作類更具效能。

```cpp
SafeNumeric<uint32_t> counter;

void thread_func() {
    counter.increment(); // 原子性增加
}
```

## 7. 重要禁令與最佳實務
1. **禁止在子執行緒修改場景樹**：絕對不要在主執行緒以外的地方呼叫 `add_child()`, `remove_child()` 或修改 Node 的變換。應計算完結果後回到主執行緒 (透過 `call_deferred`) 進行更新。
2. **避免長時持有 Mutex**：縮短加鎖區間，避免造成主執行緒卡頓。
3. **檢查記憶體洩漏**：在偵錯模式下執行 Godot，關閉時引擎會報告是否有未釋放的物件。
