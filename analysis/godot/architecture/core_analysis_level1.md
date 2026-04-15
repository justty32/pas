# Core 模組架構分析 - Level 1 & 2

## 1. 核心職責與概覽
`core/` 目錄是 Godot 引擎的基石，提供了所有高階系統（如 `scene`, `servers`, `editor`）所依賴的基礎工具、類型與基礎設施。

### 關鍵子目錄分析：
- **`object/`**: 引擎的物件模型核心，包含 `Object`, `RefCounted`, `ClassDB` (反射與類別註冊)。
- **`variant/`**: 萬用容器類型 `Variant` 的實作，支援多種數據類型及其轉換與運算。
- **`math/`**: 2D/3D 數學基礎（向量、矩陣、變換等）。
- **`io/`**: 檔案訪問、網路、資源載入/儲存架構。
- **`os/`**: 平台抽象層，處理時間、線程、輸入、環境資訊。
- **`string/`**: 字串處理、國際化 (Translation) 與最佳化。
- **`templates/`**: 自定義的容器類 (Vector, List, Map, Hash).
- **`extension/`**: GDExtension 的核心基礎設施。

## 2. 核心入口與初始化
- **`core/typedefs.h`**:
    - 定義了引擎全域使用的基礎類型、巨集與編譯旗標。
    - 強制執行 **C++17** 標準。
    - 定義了關鍵的內聯巨集 (`_FORCE_INLINE_`) 與錯誤處理相關基礎。
- **`core/register_core_types.cpp`**:
    - 負責核心系統的啟動與關閉順序。
    - 註冊基礎物件類別到 `ClassDB`。
    - 初始化單例物件 (如 `OS`, `Engine`, `ResourceLoader`)。

## 3. 重要發現
- Godot 引擎不依賴 STL 容器，而是使用自定義的 `core/templates` 類別，這有助於嚴格控制記憶體與二進制大小。
- `Variant` 是與腳本語言（GDScript, C#）互動的核心，其定義位於 `core/variant/`。
- `Object` 模型支援訊號 (Signals) 與屬性 (Properties)，這是 Godot 動態特性的源頭。

---
*檔案位置：`core/typedefs.h` (基礎定義), `core/register_core_types.cpp` (核心初始化)*
