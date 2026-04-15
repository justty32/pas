# Core 物件模型分析 (Object & RefCounted) - Level 2

## 1. Object 類別 (`core/object/object.h`)
`Object` 是 Godot 引擎中幾乎所有類別的基石。它提供了強大的動態特性：

### 核心功能：
- **中介資料 (Metadata)**：允許在執行時為物件附加額外的資料。
- **腳本支援 (Scripting)**：透過 `ScriptInstance` 連結到腳本語言（如 GDScript）。
- **信號與屬性 (Signals & Properties)**：與 `ClassDB` 整合，支援動態調用與編輯器檢查。
- **GDExtension 整合**：`ObjectGDExtension` 結構體定義了 C/C++ 擴展如何與引擎核心物件模型對接。
- **虛擬函數 (Virtual Functions)**：使用 `GDVIRTUAL_*` 巨集族群來處理跨語言的虛擬函數重載。

### 關鍵宏與機制：
- `GDCLASS(m_class, m_inherits)`：用於註冊類別繼承關係與元資訊。
- `ADD_PROPERTY`, `ADD_SIGNAL`：用於在 `_bind_methods` 中暴露接口給引擎。

## 2. 引用計數機制 (`core/object/ref_counted.h`)
`RefCounted` 繼承自 `Object`，為需要自動記憶體管理的類別提供基礎。

### 實作細節：
- **`SafeRefCount`**：使用原子操作確保在多線程環境下的引用計數安全。
- **`Ref<T>` 模板類**：這是 Godot 版的智慧指標，透過建構、解構、賦值運算子自動調用 `reference()` 與 `unreference()`。
- **`init_ref()`**：處理物件剛建立時的特殊狀態，確保第一次賦值給 `Ref<T>` 時能正確管理。

### 記憶體管理策略：
- **非 RefCounted 物件**：通常由父物件管理（如 `Node` 的場景樹）或手動 `memdelete()`。
- **RefCounted 物件**：當引用計數歸零時自動銷毀。`Resource` 類別即繼承自 `RefCounted`。

---
*檔案位置：`core/object/object.h`, `core/object/ref_counted.h`*
