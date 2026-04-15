# GDExtension 擴展機制分析 - Level 1 & 2

## 1. 核心職責與概覽
GDExtension 是 Godot 4 的核心功能之一，旨在取代舊有的 GDNative。它允許開發者使用 C/C++ (或其他語言) 編寫高效能擴展，且無需重新編譯引擎。

### 關鍵組件分析：
- **`GDExtension` 資源 (`core/extension/gdextension.h`)**：
    - 代表一個 GDExtension 擴展庫。
    - 管理 `GDExtensionLoader`，負責動態連結庫 (.dll, .so, .dylib) 的載入與卸載。
    - 追蹤擴展中定義的類別 (`extension_classes`) 與實例。
- **`GDExtensionManager` (`core/extension/gdextension_manager.h`)**：
    - 全域單例，負責管理所有已載入的擴展。
    - **分層初始化**：嚴格遵循 `CORE` -> `SERVERS` -> `SCENE` -> `EDITOR` 的初始化順序 (`InitializationLevel`)。
    - 處理擴展的依賴關係與熱重載 (Hot-Reloading)。
- **`GDExtensionInterface` (`core/extension/gdextension_interface.cpp`)**：
    - 提供一組穩定的 C API 函數指標，作為引擎與外部庫之間的通訊橋樑。
    - 包含類別註冊、方法註冊、Variant 操作、伺服器存取等核心介面。

## 2. 擴展工作流程
1. **載入**：`GDExtensionManager` 讀取配置並載入動態連結庫。
2. **初始化**：呼叫擴展的進入點函數，並傳遞 `GDExtensionInterface` 指標。
3. **類別註冊**：擴展透過介面將自定義類別註冊到 Godot 的 `ClassDB`。
4. **互動**：一旦註冊完成，這些類別就能像原生引擎類別一樣，在 GDScript 或編輯器中使用。

## 3. 重要發現
- **ABI 穩定性**：GDExtension 採用版本化的初始化資訊 (`GDExtensionClassCreationInfo5`)，確保引擎更新時的相容性。
- **熱重載支援**：在 `TOOLS_ENABLED` 模式下，`GDExtension` 支援 `prepare_reload()` 與 `finish_reload()`，這對於插件開發者極其重要。
- **透明性**：對於終端使用者而言，GDExtension 類別與內建類別幾乎沒有區別。

---
*檔案位置：`core/extension/gdextension.h`, `core/extension/gdextension_manager.cpp`, `core/extension/gdextension_interface.cpp`*
