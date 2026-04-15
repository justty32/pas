# Level 1 Analysis: godot-cpp 初始探索

## 1. 專案概述
`godot-cpp` 是 Godot 4 官方提供的 C++ 綁定庫。它允許開發者以接近引擎內核的效能撰寫遊戲邏輯，同時保持與 GDScript 相似的開發體驗。

## 2. 核心架構組件
### 2.1 綁定生成器 (Binding Generator)
- **核心腳本**: `binding_generator.py`
- **輸入**: `gdextension/extension_api.json` (由 Godot 引擎 `dump` 產出)。
- **輸出**: 自動生成的 C++ 類別標頭檔與源碼，封裝了所有引擎 API 調用。

### 2.2 變量與類型系統 (Variant System)
- 位於 `include/godot_cpp/variant/`。
- 完美映射了 Godot 的 `Variant` 類型，提供 C++ 風格的操作符重載與類型轉換。

### 2.3 註冊與綁定 (ClassDB)
- 位於 `include/godot_cpp/core/class_db.hpp`。
- 提供靜態介面，用於在 GDExtension 初始化時向引擎註冊自定義類別、方法、屬性與信號。

## 3. 開發模式摘要 (Boilerplate)
一個典型的 GDExtension 類別包含：
1. **GDCLASS 宏**: 定義類型元數據。
2. **_bind_methods**: 註冊對外介面。
3. **initialize_module / uninitialize_module**: 定義插件的啟動與關閉邏輯。

## 4. 初始探索結論
`godot-cpp` 是一個**高度自動化且結構嚴謹**的框架。它的核心挑戰在於理解 C++ 與 Godot 虛擬機器之間的數據傳遞（Marshal）與引用計數（RefCounting）機制。對於效能敏感型模組（如 AI 計算、物理模擬），它是 Godot 生態中的首選方案。
