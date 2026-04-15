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
