# Wesnoth 技術專題 - WML 引擎與 Config 系統深度剖析

## 1. 核心數據結構: `config` 類別
`config` 類別是 Wesnoth 中最基礎且最重要的數據結構，幾乎所有的遊戲配置、存檔、網路數據包都以這種格式存在。

### 內部結構
- **Attributes (屬性)**: `std::map<std::string, attribute_value, std::less<>> values_`
  - 儲存鍵值對（例如 `name=Hero`）。
  - 使用 `std::less<>` 實現異構查找 (Heterogeneous Lookup)，優化字符串查找性能。
- **Children (子標籤)**: `std::map<std::string, std::vector<config*>, std::less<>> children_`
  - 按標籤名稱分類儲存子配置。
- **Ordered Children (順序子標籤)**: `std::vector<any_child> ordered_children_`
  - 記錄子標籤出現的原始順序。這對 WML 至關重要，因為有些邏輯（如 [event] 或 [unit]）依賴於順序。

### 優化策略
- **內存管理**: 採用指標與智慧型容器管理子對象。
- **異構查找**: 避免在查找時產生臨時的 `std::string` 對象，直接使用 `std::string_view` 或 `const char*`。

## 2. WML 解析流程 (Parsing Workflow)
WML 的加載是一個多階段過程：

### 階段 A: 預處理 (Preprocessing)
- **組件**: `src/serialization/preprocessor.cpp`
- **職責**: 
  - 處理宏定義 (`#define`, `#macro`)。
  - 處理條件編譯 (`#ifdef`, `#ifndef`)。
  - 處理文件包含 (`{~path/to/file}`)。
- **結果**: 產生一個純粹的 WML 文本流。

### 階段 B: 詞法分析 (Tokenizing)
- **組件**: `src/serialization/tokenizer.cpp`
- **職責**: 將文本流切分為標籤 (`[` `]`)、賦值符 (`=`)、字符串、底線 (i18n 標記) 等 Token。

### 階段 C: 語法解析 (Parsing)
- **組件**: `src/serialization/parser.cpp`
- **職責**: 
  - 遞歸構建 `config` 樹。
  - 處理標籤的開閉對稱性。
  - 驗證標籤名稱與屬性鍵名的合法性（僅允許英數字與底線）。

## 3. Config 系統的應用
- **遊戲定義**: 單位、種族、武器、戰役場景皆由 WML 定義。
- **遊戲狀態**: 存檔文件本質上就是一個巨大的 WML `config` 對象。
- **網路協議**: 客戶端與伺服器之間傳遞的是 WML 片段。

## 4. 程式碼參考
- `src/config.hpp` / `src/config.cpp`: 核心結構實作。
- `src/serialization/parser.cpp`: 解析邏輯。
- `src/serialization/tokenizer.cpp`: 詞法掃描。

---
*最後更新: 2026-05-17*
