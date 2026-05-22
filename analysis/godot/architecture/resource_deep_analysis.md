# Resource 系統深度分析

> 對應原始碼：`core/io/resource.h/cpp`, `core/io/resource_loader.h/cpp`, `core/io/resource_saver.h/cpp`, `core/io/resource_uid.h`

---

## 1. Resource 的類別階層

`core/io/resource.h:53`

```cpp
class Resource : public RefCounted {
    GDCLASS(Resource, RefCounted);
public:
    static constexpr AncestralClass static_ancestral_class = AncestralClass::RESOURCE;
```

`Resource` 繼承自 `RefCounted`，這是整個系統的核心設計決策：

- **生命週期由引用計數管理**：`Ref<T>` 自動 reference/unreference，歸零時自動銷毀。
- **不是 Node**：Resource 不屬於場景樹，不受 `add_child()`/`remove_child()` 管理。
- **可序列化**：配合 `GDCLASS` 宏，所有 `PROPERTY_USAGE_STORAGE` 的屬性可以自動序列化/反序列化。

### Resource 的核心私有成員

`core/io/resource.h:73-93`

```cpp
class Resource : public RefCounted {
private:
    String name;            // 編輯器顯示名稱（不影響載入）
    String path_cache;      // 資源路徑（如 "res://sprites/player.png"）
    String scene_unique_id; // 場景內部唯一 ID（用於 local_to_scene）

    EmitChangedState emit_changed_state;  // 封鎖 emit_changed() 的狀態機
    bool local_to_scene = false;          // 是否為場景局部資源
    Node *local_scene = nullptr;          // local_to_scene 時，所屬的場景根節點

    SelfList<Resource> remapped_list;     // 翻譯重映射用串列節點
};
```

`path_cache` 同時是 `ResourceCache` 的 key。空字串 = 內建資源（built-in，未存檔）。

---

## 2. ResourceCache —— 全域路徑快取

`core/io/resource.h:198-216`

```cpp
class ResourceCache {
    static Mutex lock;
    static HashMap<String, Resource *> resources;  // path → Resource* (raw pointer)
    // ...
public:
    static bool has(const String &p_path);
    static Ref<Resource> get_ref(const String &p_path);
};
```

**關鍵設計**：快取存的是 `Resource *`（裸指標），不是 `Ref<Resource>`。

這意味著快取**不持有引用計數**。當 Resource 的 `Ref<T>` 引用歸零時，Resource 析構函數會自動從 `ResourceCache::resources` 移除自己——這是一個 `weak` 語意的快取。

`get_ref()` 回傳 `Ref<Resource>`：先透過 `ObjectDB` 驗證指標有效性，再包裝成 `Ref`。

### set_path() —— 路徑與快取的原子更新

`core/io/resource.cpp:70-107`

```cpp
void Resource::set_path(const String &p_path, bool p_take_over) {
    // 上鎖：整個操作必須原子
    MutexLock lock(ResourceCache::lock);

    // 1. 從快取移除舊路徑
    if (!path_cache.is_empty()) {
        ResourceCache::resources.erase(path_cache);
    }
    path_cache = "";

    // 2. 檢查新路徑是否已被占用
    Ref<Resource> existing = ResourceCache::get_ref(p_path);
    if (existing.is_valid()) {
        if (p_take_over) {
            // 強制取代：移除舊的快取條目
            existing->path_cache = String();
            ResourceCache::resources.erase(p_path);
        } else {
            ERR_FAIL_MSG("Another resource is loaded from path...");
        }
    }

    // 3. 新路徑寫入快取
    path_cache = p_path;
    if (!path_cache.is_empty()) {
        ResourceCache::resources[path_cache] = this;
    }
}
```

`p_take_over = true` 用於「重新載入」場景：新資源強制占用路徑，舊資源的引用仍有效但從快取中消失。

---

## 3. emit_changed() 的執行緒安全設計

`core/io/resource.cpp:40-51`

```cpp
void Resource::emit_changed() {
    // 如果被封鎖（例如 copy_from() 期間），記錄 pending
    if (emit_changed_state != EMIT_CHANGED_UNBLOCKED) {
        emit_changed_state = EMIT_CHANGED_BLOCKED_PENDING_EMIT;
        return;
    }

    // 如果在非主執行緒的載入過程中，透過 ResourceLoader 代理發送
    if (ResourceLoader::is_within_load() && !Thread::is_main_thread()) {
        ResourceLoader::resource_changed_emit(this);
        return;
    }

    emit_signal(CoreStringName(changed));
}
```

三個狀態：
| 狀態 | 說明 |
|------|------|
| `EMIT_CHANGED_UNBLOCKED` | 正常，直接 emit |
| `EMIT_CHANGED_BLOCKED` | 被 `_block_emit_changed()` 封鎖（例如 `copy_from()`） |
| `EMIT_CHANGED_BLOCKED_PENDING_EMIT` | 封鎖期間有人呼叫了 `emit_changed()`，解鎖後補發 |

`_block_emit_changed()` + `_unblock_emit_changed()` 配對使用，確保批次屬性設定只觸發一次 `changed` 信號。

---

## 4. duplicate() —— 淺複製與深複製

`core/io/resource.cpp:367-420`

Godot 4.x 的 `duplicate()` 有兩個主要入口：

```cpp
// 淺複製：子 Resource 不複製（共享引用）
Ref<Resource> Resource::duplicate(bool p_deep = false) const;

// 深複製：可控制子 Resource 是否一起複製
Ref<Resource> Resource::duplicate_deep(ResourceDeepDuplicateMode p_mode) const;
```

`_duplicate()` 的核心邏輯（`core/io/resource.cpp:367`）：

```cpp
Ref<Resource> Resource::_duplicate(const DuplicateParams &p_params) const {
    // 1. 建立同型別的空白實例
    Ref<Resource> r = Object::cast_to<Resource>(ClassDB::instantiate(get_class()));

    // 2. 把自己加入 remap cache（避免循環引用無限遞迴）
    thread_duplicate_remap_cache->insert(Ref<Resource>(this), r);

    // 3. 遍歷所有 PROPERTY_USAGE_STORAGE 屬性
    List<PropertyInfo> plist;
    get_property_list(&plist);
    for (const PropertyInfo &E : plist) {
        if (!(E.usage & PROPERTY_USAGE_STORAGE)) continue;
        Variant p = get(E.name);
        // _duplicate_recursive 遞迴決定子 Resource 是否複製
        r->set(E.name, _duplicate_recursive(p, p_params, E.usage));
    }
    return r;
}
```

### _duplicate_recursive() 的決策邏輯

`core/io/resource.cpp:269-320`

```cpp
// 對於 Variant::OBJECT（即 Ref<Resource>）：
bool should_duplicate = false;
if (p_usage & PROPERTY_USAGE_ALWAYS_DUPLICATE) {
    should_duplicate = true;               // 屬性標記強制複製
} else if (p_usage & PROPERTY_USAGE_NEVER_DUPLICATE) {
    should_duplicate = false;              // 屬性標記強制不複製
} else {
    switch (p_params.subres_mode) {
        case RESOURCE_DEEP_DUPLICATE_NONE:     should_duplicate = false; break;
        case RESOURCE_DEEP_DUPLICATE_INTERNAL: should_duplicate = sr->is_built_in(); break; // 只複製內建資源
        case RESOURCE_DEEP_DUPLICATE_ALL:      should_duplicate = true; break;    // 複製所有子資源
    }
}
```

**is_built_in()** 的定義（`core/io/resource.h:148`）：

```cpp
_FORCE_INLINE_ bool is_built_in() const {
    return path_cache.is_empty()       // 無路徑 = 內建
        || path_cache.contains("::")   // 含 "::" = 嵌入場景（如 "res://scene.tscn::Resource_abc12"）
        || path_cache.begins_with("local://");
}
```

`duplicate_deep(RESOURCE_DEEP_DUPLICATE_INTERNAL)` 是預設行為：複製嵌入在場景/資源檔案中的子資源，但不複製有獨立路徑的資源（例如不會複製 Texture2D，因為它有 `res://` 路徑）。

---

## 5. ResourceUID —— 穩定路徑標識符

`core/io/resource_uid.h:41-80`

```cpp
class ResourceUID : public Object {
    typedef int64_t ID;
    constexpr const static ID INVALID_ID = -1;

    HashMap<ID, Cache> unique_ids;     // ID → utf8 路徑
    HashMap<CharString, ID> reverse_cache;  // 路徑 → ID（執行期使用）
};
```

UID 格式：`uid://abc12` 這樣的字串，對應一個 `int64_t` 數字。

**目的**：即使資源檔案移動或重新命名，只要 UID 不變，其他引用它的資源仍可正確解析路徑。資源載入時 `_validate_local_path()` 先嘗試解析 UID：

```cpp
// core/io/resource_loader.cpp:505-513
String ResourceLoader::_validate_local_path(const String &p_path) {
    ResourceUID::ID uid = ResourceUID::get_singleton()->text_to_id(p_path);
    if (uid != ResourceUID::INVALID_ID) {
        return ResourceUID::get_singleton()->get_id_path(uid); // UID → 實際路徑
    } else if (p_path.is_relative_path()) {
        return ("res://" + p_path).simplify_path();
    } else {
        return ProjectSettings::get_singleton()->localize_path(p_path);
    }
}
```

UID 存儲在同名 `.uid` 檔案中（如 `player.png.uid`），格式是一行 `uid://xxxxx`。

---

## 6. ResourceFormatLoader —— 格式載入器模式

`core/io/resource_loader.h:47-95`

```cpp
class ResourceFormatLoader : public RefCounted {
    // 子類必須實作（GDVIRTUAL4RC_REQUIRED）：
    GDVIRTUAL4RC_REQUIRED(Variant, _load, String, String, bool, int)

    // 子類可選實作：
    GDVIRTUAL0RC(Vector<String>, _get_recognized_extensions)
    GDVIRTUAL1RC(bool, _handles_type, StringName)
    GDVIRTUAL1RC(String, _get_resource_type, String)
    GDVIRTUAL1RC(ResourceUID::ID, _get_resource_uid, String)
    GDVIRTUAL2RC(Vector<String>, _get_dependencies, String, bool)
    // ...
};
```

### 全域 loader 陣列

```cpp
static Ref<ResourceFormatLoader> loader[MAX_LOADERS];  // MAX_LOADERS = 64
static int loader_count;
```

`add_resource_format_loader()` 按優先級插入，`_find_custom_resource_format_loader()` 先嘗試自訂 loader。

### _load() 的 loader 選擇邏輯

`core/io/resource_loader.cpp:289-318`

```cpp
Ref<Resource> ResourceLoader::_load(const String &p_path, ...) {
    load_nesting++;
    load_paths_stack.push_back(original_path);  // 用於進度計算與循環偵測

    bool found = false;
    Ref<Resource> res;

    // 依序嘗試所有 loader，選第一個 recognize_path() 返回 true 的
    for (int i = 0; i < loader_count; i++) {
        if (!loader[i]->recognize_path(p_path, p_type_hint)) continue;
        found = true;
        res = loader[i]->load(p_path, original_path, r_error, ...);
        if (res.is_valid()) break;  // 找到即停止
    }

    load_paths_stack.resize(load_paths_stack.size() - 1);
    load_nesting--;
    return res;
}
```

`recognize_path()` 預設比對副檔名（如 `.png`, `.tres`），子類可覆寫 `_recognize_path` 做更精確的判斷。

---

## 7. ResourceLoader::load() —— 同步載入的完整路徑

`core/io/resource_loader.cpp:541-564`

```cpp
Ref<Resource> ResourceLoader::load(const String &p_path, ...) {
    // 決定執行緒模式
    LoadThreadMode thread_mode = LOAD_THREAD_FROM_CURRENT;
    if (WorkerThreadPool::get_singleton()->get_caller_task_id() != INVALID_TASK_ID) {
        thread_mode = LOAD_THREAD_SPAWN_SINGLE; // 在 pool 任務中 → 生成新任務
    }

    // 建立 LoadToken（包含任務元資料）
    Ref<LoadToken> load_token = _load_start(p_path, p_type_hint, thread_mode, p_cache_mode);

    // 等待完成並取得結果
    Ref<Resource> res = _load_complete(*load_token.ptr(), r_error);
    return res;
}
```

### _load_start() —— 快取命中的早期返回

`core/io/resource_loader.cpp:616-627`

```cpp
if (p_cache_mode == ResourceFormatLoader::CACHE_MODE_REUSE) {
    Ref<Resource> existing = ResourceCache::get_ref(local_path);
    if (existing.is_valid()) {
        // 快取命中：不啟動任何載入任務，直接包裝 LoadToken 回傳
        load_task.resource = existing;
        load_task.status = THREAD_LOAD_LOADED;
        load_task.progress = 1.0;
        thread_load_tasks[local_path] = load_task;
        return load_token;
    }
}
```

這就是為什麼同一路徑的資源只會被實際解析一次：第二次呼叫 `ResourceLoader::load()` 時，`_load_start()` 在加鎖的情況下從 `ResourceCache` 取出已存在的 `Ref<Resource>` 直接返回。

### CacheMode 的五種模式

| 模式 | 行為 |
|------|------|
| `CACHE_MODE_REUSE` | 有快取就返回快取（預設） |
| `CACHE_MODE_IGNORE` | 忽略快取，強制重新載入（子資源也忽略） |
| `CACHE_MODE_REPLACE` | 重新載入，並用新資料覆蓋舊 Resource（`copy_from()`） |
| `CACHE_MODE_IGNORE_DEEP` | 同 IGNORE，但傳遞給所有依賴資源 |
| `CACHE_MODE_REPLACE_DEEP` | 同 REPLACE，深度傳遞 |

`REPLACE` 模式的關鍵用途：編輯器「重新載入資源」時，已持有 `Ref<T>` 的使用者程式碼不需要更新任何引用，舊物件的資料被就地覆蓋。

---

## 8. 非同步載入（load_threaded_request）

`core/io/resource_loader.h:176-209`

```cpp
struct ThreadLoadTask {
    WorkerThreadPool::TaskID task_id = 0; // 在 worker pool 中的任務 ID
    Thread::ID thread_id = 0;             // 若在使用者執行緒，記錄其 ID
    ConditionVariable *cond_var = nullptr;// 等待機制
    float progress = 0.0f;               // 載入進度（0.0 ~ 1.0）
    ThreadLoadStatus status;             // IN_PROGRESS / LOADED / FAILED
    Ref<Resource> resource;              // 載入完成後的結果
    HashSet<String> sub_tasks;           // 子依賴的路徑（進度計算用）
};
```

非同步 API 呼叫流程：

```
load_threaded_request(path)          → 建立 LoadToken + ThreadLoadTask，提交到 WorkerThreadPool
  ↓（其他幀繼續執行）
load_threaded_get_status(path)       → 查詢 task.status，計算進度（含子任務加權平均）
  ↓（status == THREAD_LOAD_LOADED）
load_threaded_get(path)              → 取出 Ref<Resource>，清理 LoadToken
```

**進度計算**（`_dependency_get_progress()`）：
- 若有子任務：`progress = (子任務平均進度 × 0.5) + (自身 progress × 0.5)`
- 這是遞迴計算，考慮到大型資源（如 `.tscn`）會依賴多個子 Resource 的載入進度。

---

## 9. ResourceFormatSaver —— 格式儲存器模式

`core/io/resource_saver.h:36-56`

```cpp
class ResourceFormatSaver : public RefCounted {
    GDVIRTUAL3R(Error, _save, Ref<Resource>, String, uint32_t)  // 必須實作
    GDVIRTUAL1RC(bool, _recognize, Ref<Resource>)               // 識別資源型別
    GDVIRTUAL1RC(Vector<String>, _get_recognized_extensions, Ref<Resource>) // 副檔名
    GDVIRTUAL2RC(bool, _recognize_path, Ref<Resource>, String)  // 識別路徑
};
```

`ResourceSaver::save()` 的選擇邏輯（`core/io/resource_saver.cpp:110-153`）：

```cpp
Error ResourceSaver::save(RequiredParam<Resource> rp_resource, const String &p_path, uint32_t p_flags) {
    for (int i = 0; i < saver_count; i++) {
        if (!saver[i]->recognize(p_resource)) continue;      // 認識這個資源型別嗎？
        if (!saver[i]->recognize_path(p_resource, path)) continue; // 認識這個副檔名嗎？

        err = saver[i]->save(p_resource, path, p_flags);
        if (err == OK) return OK;  // 儲存成功即停止
    }
}
```

### SaverFlags

| 旗標 | 值 | 效果 |
|------|-----|------|
| `FLAG_RELATIVE_PATHS` | 1 | 使用相對路徑 |
| `FLAG_BUNDLE_RESOURCES` | 2 | 將引用的外部資源打包進檔案 |
| `FLAG_CHANGE_PATH` | 4 | 儲存後更新 resource 的 path_cache |
| `FLAG_OMIT_EDITOR_PROPERTIES` | 8 | 不儲存編輯器專用屬性 |
| `FLAG_COMPRESS` | 32 | 壓縮輸出 |
| `FLAG_REPLACE_SUBRESOURCE_PATHS` | 64 | 子資源路徑替換 |

---

## 10. local_to_scene —— 場景局部資源

`core/io/resource.h:89-91`

```cpp
bool local_to_scene = false;
Node *local_scene = nullptr;
```

啟用 `local_to_scene = true` 後，同一個場景中的每個節點實例（當場景被 instantiate 多次時）會各自持有該資源的**獨立複製**。

`duplicate_for_local_scene()` 在場景實例化時被呼叫，使用一個 `HashMap<Ref<Resource>, Ref<Resource>>` 的 remap cache 確保同一個場景實例內多次引用同一資源時，共享同一個複製（而不是每次都複製）。

典型使用情境：`AnimationPlayer` 播放的 `AnimationLibrary`，希望每個場景實例有獨立的播放狀態。

---

## 11. reload_from_file() —— 就地重新載入

`core/io/resource.cpp:254-267`

```cpp
void Resource::reload_from_file() {
    String path = get_path();
    if (!path.is_resource_file()) return;

    // 用 CACHE_MODE_IGNORE 強制重新解析（不走快取）
    Ref<Resource> s = ResourceLoader::load(
        ResourceLoader::path_remap(path),
        get_class(),
        ResourceFormatLoader::CACHE_MODE_IGNORE
    );

    if (s.is_null()) return;

    // copy_from() 把新資料複製到 this，原有的 Ref<T> 持有者感知不到替換
    copy_from(s);
}
```

`copy_from()` 的實作：遍歷所有 `PROPERTY_USAGE_STORAGE` 屬性，逐一 `set()`，並在整個過程中封鎖 `emit_changed()`，最後統一發射一次。

---

## 12. 完整載入呼叫鏈

```
GDScript: load("res://player.png")
  └─ ResourceLoader::load("res://player.png", "", CACHE_MODE_REUSE)
       │
       ├─ _validate_local_path()        → UID 解析 or 路徑正規化
       ├─ _load_start()
       │    ├─ [快取命中] ResourceCache::get_ref() → 直接返回 LoadToken（含 existing resource）
       │    └─ [快取未命中] 建立 ThreadLoadTask
       │         ├─ LOAD_THREAD_FROM_CURRENT → _run_load_task() 直接在當前執行緒執行
       │         └─ LOAD_THREAD_SPAWN_SINGLE → WorkerThreadPool::add_native_task()
       │
       └─ _load_complete() → 等待任務完成，取出 task.resource
            │
            └─ [任務執行中] _run_load_task()
                 ├─ _path_remap()        → 翻譯重映射（i18n）
                 ├─ _load()              → 遍歷 loader[]，找到 recognize_path() 的 loader
                 │    └─ loader[i]->load() → ResourceFormatLoader 子類實作
                 │         └─ [.tres/.res] ResourceFormatText::load() / ResourceFormatBinary::load()
                 │         └─ [.png]      ResourceFormatLoaderImage::load()
                 │         └─ [.glb/.gltf] GLTFDocument::append_from_file()
                 │         └─ [.tscn]     ResourceFormatLoaderBinaryCompat::load()
                 │
                 └─ resource->set_path() → 加入 ResourceCache
```

---

## 13. 設計重點總結

| 設計 | 效果 |
|------|------|
| Resource 繼承 RefCounted | 自動生命週期管理，`Ref<T>` 超出作用域自動釋放 |
| ResourceCache 用裸指標（weak） | 快取不延長生命週期，引用歸零資源自動清除快取 |
| `emit_changed_state` 三態封鎖 | 批次屬性設定只觸發一次 changed 信號 |
| ResourceFormatLoader/Saver 分離 | 新格式只需新增 loader/saver，不修改核心邏輯（開放/封閉原則） |
| LoadToken + ThreadLoadTask | 同路徑的並發載入請求自動合併（token 共享同一 task） |
| CACHE_MODE_REPLACE + copy_from() | 就地更新資源，所有現有 Ref<T> 持有者自動感知新資料 |
| UID 系統（.uid 旁置檔案） | 資源重命名/移動後，引用不斷裂 |
| duplicate() + remap cache | 深複製時循環引用的子資源不會被無限複製 |
| local_to_scene + scene instance remap | 同一資源在不同場景實例中可以有獨立狀態 |

---

*原始碼版本：Godot Engine 4.7.dev*
*分析日期：2026-05-22*
