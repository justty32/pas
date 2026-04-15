# Core Templates 分析 - Level 2

## 1. 寫入時複製 (Copy-on-Write, CoW) 機制
Godot 的許多基礎容器（如 `Vector`, `String`, `Array`）都使用了 CoW 技術，以減少不必要的資料複製並簡化記憶體管理。

### `CowData<T>` (`core/templates/cowdata.h`)：
- **核心實作**：這是 CoW 容器的底層支柱。它不直接儲存陣列，而是管理一個指向包含引用計數、容量、大小與實際資料的記憶體塊的指標。
- **記憶體佈局**：
    - `REF_COUNT_OFFSET`: 儲存 `SafeNumeric<USize>` 引用計數。
    - `CAPACITY_OFFSET`: 儲存目前分配的容量。
    - `SIZE_OFFSET`: 儲存目前的元素數量。
    - `DATA_OFFSET`: 實際元素陣列的起始位置。
- **行為**：
    - 當容器被複製時，僅增加引用計數。
    - 當呼叫 `ptrw()` (取得可寫入指標) 或進行修改操作時，若引用計數大於 1，則會執行深層複製（Deep Copy）。

## 2. 常用容器類別
- **`Vector<T>` (`core/templates/vector.h`)**：
    - 基於 `CowData` 的動態陣列。
    - 提供 `write` 代理 (Proxy) 來確保 CoW 行為的正確觸發。
- **`LocalVector<T>` (`core/templates/local_vector.h`)**：
    - **非 CoW** 的動態陣列，行為類似於 `std::vector`。
    - 用於效能敏感且不需要共享資料的內部邏輯，避免了 CoW 的檢查開銷。
- **`HashMap<K, V>` & `HashSet<T>`**：
    - 使用開放定址法 (Open Addressing) 實作的高效雜湊容器。
    - 整合了引擎的 `hashfuncs.h`。
- **`List<T>`**：雙向連結串列。
- **`RID` (Resource ID)**：輕量級的資源標記，用於在伺服器層（如 `RenderingServer`）高效引用資源。

## 3. 為什麼不使用 STL？
1. **二進制大小控制**：STL 在不同平台與編譯器下的實作差異較大，自定義容器有助於減少模板展開產生的二進制體積。
2. **記憶體分配控制**：Godot 使用自定義的分配器（如 `memnew`），可以更好地追蹤記憶體使用與碎片。
3. **CoW 整合**：引擎深度依賴 CoW 來優化資源傳遞，這是 STL 容器不具備的特性。

---
*檔案位置：`core/templates/cowdata.h`, `core/templates/vector.h`*
