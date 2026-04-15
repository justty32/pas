# Core Variant 分析 - Level 2

## 1. Variant 類別 (`core/variant/variant.h`)
`Variant` 是 Godot 引擎中最核心的資料結構，它是一個多型容器，可以儲存幾乎任何引擎支援的資料類型。

### 核心設計：
- **類型枚舉 (`Type`)**：涵蓋了從基礎類型 (INT, BOOL, FLOAT) 到複雜的數學類型 (VECTOR3, TRANSFORM3D) 以及引擎特有類型 (RID, OBJECT, DICTIONARY, ARRAY)。
- **內部儲存**：
    - 針對小資料（如數值、小型向量）直接儲存在 `Variant` 實例中。
    - 針對大資料（如 `AABB`, `Transform3D`, `Projection`）或引用類型（如 `Object`, `Array`, `Dictionary`）則使用指標或引用管理。
- **Object 整合**：`ObjData` 結構體負責管理對 `Object` 的引用，包括透過 `ObjectID` 追蹤與處理 `RefCounted` 物件的引用計數。

### 關鍵特性：
- **動態類型**：支援在執行時檢查類型 (`get_type()`) 並進行安全轉換。
- **運算子重載**：`variant_op.h/cpp` 定義了 `Variant` 之間各種算術與邏輯運算，這是 GDScript 等腳本語言運算基礎。
- **高效能**：避免了不必要的堆積 (Heap) 分配，對於常用的小型數學類型（如 `Vector3`）有極佳的傳遞效能。

## 2. 容器類型
- **`Array` & `Dictionary`**：這兩者在 `Variant` 中是以引用方式儲存的，支援共享與自動垃圾回收（透過引用計數）。
- **`PackedArray` 系列**：如 `PackedByteArray`, `PackedInt32Array`，這是為了高效儲存大量同類型資料而設計的，對應底層的 `Vector<T>`。

---
*檔案位置：`core/variant/variant.h`, `core/variant/variant.cpp`*
