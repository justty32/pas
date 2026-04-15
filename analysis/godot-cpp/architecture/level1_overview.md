# godot-cpp Level 1: Initial Exploration

## 專案基本資訊 (Project Overview)
- **GitHub 專案名稱**：godot-cpp
- **專案目標**：提供 Godot 引擎 GDExtension 的 C++ 語言綁定。它是原有的 GDNative 的現代化後繼者，允許開發者使用 C++ 編寫高性能的遊戲邏輯、自定義節點或整合外部庫，而無需重新編譯整個 Godot 引擎。
- **核心技術棧**：C++, Python (用於生成綁定代碼), SCons/CMake (構建系統)。

## 目錄結構初探 (Directory Structure)
| 路徑 | 職責 |
| :--- | :--- |
| `include/` | 綁定庫的頭文件，包含 `godot_cpp/core/`, `godot_cpp/classes/` 等。 |
| `src/` | 綁定庫的 C++ 實現。 |
| `gdextension/` | 包含核心的 GDExtension 介面標頭 (GDExtension Interface)，由 Godot 引擎主倉庫提供或更新。 |
| `binding_generator.py` | 核心自動化工具，解析 Godot 導出的 `extension_api.json` 並生成 C++ 類別。 |
| `SConstruct` | SCons 構建指令碼，是 Godot 官方推薦的編譯方式。 |
| `test/` | 單元測試與範例代碼。 |

## 核心工作流程 (Core Workflow)
1. **API 導出**：從 Godot 引擎執行檔中導出 `extension_api.json`。
2. **綁定生成**：運行 `binding_generator.py` 根據 JSON 生成對應的 C++ 類別與方法包裝器 (Wrapper)。
3. **靜態庫編譯**：使用 SCons 將生成的代碼與靜態部分（`core/`）編譯為 `libgodot-cpp.a` (或 `.lib`)。
4. **開發 Extension**：開發者將此庫鏈接到自己的 GDExtension 專案。

## 下一步分析建議 (Next Steps)
- **Level 2**：深入 `binding_generator.py` 的代碼生成邏輯。
- **Level 3**：探究 `ClassDB` 在 C++ 端如何映射 Godot 的反射系統。
- **Level 4**：分析 C++ 虛擬函數 (Virtual Functions) 的註冊與回調機制。

---
*由 Gemini CLI 分析於 2026-04-15。*
