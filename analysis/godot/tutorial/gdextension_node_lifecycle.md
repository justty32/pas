# GDExtension 教學：新增與釋放子節點

本教學將介紹如何在 C++ 中動態管理 Godot 場景樹中的節點生命週期。

## 1. 目標導向
- 如何在執行時動態建立一個節點實例。
- 如何將節點加入場景樹以及從中移除。
- 如何正確釋放記憶體以避免洩漏。

## 2. 前置知識
- 已了解 `memnew` 與 `memdelete` 規範。
- 已了解 `Node` 的基本層級概念。

## 3. 原始碼導航
- **節點操作**: `scene/main/node.h` (L200+: `add_child`, `remove_child`)
- **安全刪除**: `scene/main/node.h` (L400+: `queue_free`)

## 4. 實作步驟

### 步驟 A：建立與加入子節點
在 Godot 中，建立節點必須使用 `memnew`。

```cpp
void MyNode3D::spawn_child() {
    // 1. 建立實例
    MeshInstance3D *new_mesh = memnew(MeshInstance3D);
    new_mesh->set_name("MyDynamicMesh");

    // 2. 加入子節點
    // p_legible_unique_name 為 true 時，若名稱重複會自動加數字
    add_child(new_mesh, true); 
}
```

### 步驟 B：移除與釋放節點
移除節點 (`remove_child`) 只是將其從場景樹斷開，**不會**從記憶體刪除。

```cpp
void MyNode3D::remove_and_delete_child(Node *p_child) {
    if (p_child && p_child->get_parent() == this) {
        // 1. 從場景樹移除
        remove_child(p_child);
        
        // 2. 立即刪除 (慎用，若該節點正在處理邏輯可能導致崩潰)
        memdelete(p_child);
    }
}

void MyNode3D::safe_delete_child(Node *p_child) {
    if (p_child) {
        // 推薦做法：排隊等待在本幀結束時刪除
        p_child->queue_free();
    }
}
```

## 5. 重要注意事項
1. **執行緒安全**：`add_child` 與 `remove_child` **不是執行緒安全的**。如果您在子執行緒中執行，必須使用 `call_deferred`：
   ```cpp
   call_deferred("add_child", new_node);
   ```
2. **所有權**：一旦 `add_child` 被呼叫，場景樹將接管該節點。當父節點被刪除時，子節點也會被自動刪除。
3. **重複加入**：一個節點實例同時只能有一個父節點。

---

## 6. 完整生命週期通知順序

以下是一個節點從建立到銷毀所會經歷的通知（NOTIFICATION）順序，以及對應的虛擬函數：

| 順序 | NOTIFICATION 常數 | 對應虛擬函數 | 觸發時機 |
|------|-------------------|-------------|----------|
| 1 | `NOTIFICATION_POSTINITIALIZE` | `_init()` (內部) | 物件建立後立即觸發 |
| 2 | `NOTIFICATION_ENTER_TREE` | `_enter_tree()` | 節點被加入場景樹 |
| 3 | `NOTIFICATION_READY` | `_ready()` | 節點與所有子節點都已完成 `_enter_tree` |
| 4 | `NOTIFICATION_PROCESS` | `_process(delta)` | 每幀更新（需 `set_process(true)`） |
| 5 | `NOTIFICATION_PHYSICS_PROCESS` | `_physics_process(delta)` | 每個物理幀（需 `set_physics_process(true)`） |
| 6 | `NOTIFICATION_EXIT_TREE` | `_exit_tree()` | 節點從場景樹移除 |
| 7 | `NOTIFICATION_PREDELETE` | `~Destructor` | 即將被 `memdelete` 前 |

### `_enter_tree()` vs `_ready()` 的核心差異

```
父節點 _enter_tree()
  └── 子節點 _enter_tree()   ← 所有節點依序進入場景樹
        └── 孫節點 _enter_tree()

孫節點 _ready()              ← 由深至淺（葉節點先）
  └── 子節點 _ready()
        └── 父節點 _ready()  ← 最後執行，此時子樹已完全就緒
```

**關鍵原則**：
- `_enter_tree()` 適合「自身初始化」，此時子節點**可能尚未就緒**。
- `_ready()` 適合「依賴子節點」的初始化，子樹已完全建立。

### C++ 實作示範

```cpp
void MyNode3D::_enter_tree() {
    // 適合：訂閱訊號、設定自身屬性
    // 不適合：存取子節點（可能尚未就緒）
    set_process(true);
    set_physics_process(true);
}

void MyNode3D::_ready() {
    // 安全：此時可以存取子節點
    MeshInstance3D *mesh = get_node<MeshInstance3D>("Mesh");
    if (mesh) {
        // 安全地操作子節點
    }
}

void MyNode3D::_exit_tree() {
    // 適合：取消訂閱訊號、清理跨節點引用
    // 此函數在 ~Destructor 之前執行，此時場景樹仍可存取
}
```

### 自訂通知處理

```cpp
void MyNode3D::_notification(int p_what) {
    switch (p_what) {
        case NOTIFICATION_ENTER_TREE:
            _enter_tree();
            break;
        case NOTIFICATION_READY:
            _ready();
            break;
        case NOTIFICATION_EXIT_TREE:
            _exit_tree();
            break;
        case NOTIFICATION_PREDELETE:
            // 緊急清理（避免在此存取其他節點，場景樹狀態不確定）
            break;
    }
}
```
