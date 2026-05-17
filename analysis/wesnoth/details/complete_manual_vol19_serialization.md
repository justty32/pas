# Wesnoth 技術全典：WML 記憶體解析與序列化核心 (第十九卷)

AI 的決策參數與地圖的座標資料，最初都是硬碟上的純文字。本卷解構 `src/serialization/`，這是將字串轉化為 C++ 高效記憶體結構的引擎心臟。

---

## 1. 詞法與語法分析管線 (Tokenizer & Parser)

Wesnoth 沒有使用現成的 JSON 或 XML，而是自研了 WML (Wesnoth Markup Language)。

### 1.1 `preprocessor.cpp` (巨集展開引擎)
- **工程語義**：處理 `#define` 與 `{MACRO}`。
- **演算法**：使用遞歸下降 (Recursive Descent) 掃描文字流。當遇到巨集呼叫時，會將其替換為緩存中的字串，並處理參數替換（如 `{ATTACK_DAMAGE 10}`）。這讓 AI 的配置檔案可以模組化。

### 1.2 `tokenizer.cpp` (詞法掃描器)
- **工程語義**：將字串流切分為 Token（如 `TAG_START`, `STRING`, `EQUALS`）。
- **效能優化**：它直接操作指標 `const char*` 而非頻繁複製 `std::string`，大幅降低了讀取龐大地圖檔案時的記憶體分配 (Allocation) 開銷。

### 1.3 `parser.cpp` (語法樹建構)
- **工程語義**：將 Token 流轉化為 `config` 樹狀結構。
- **資料結構**：`config` 類別內部結合了 `std::vector` (用於保持子節點的順序，這對 AI 階段執行順序至關重要) 與 `std::map` (用於 $O(\log N)$ 的快速屬性查找)。

## 2. 二進位快取 (Binary Cache)

純文字解析依然太慢，特別是當地圖與 AI 配置高達數十 MB 時。
- **`binary_wml.cpp`**：
  第一次解析完純文字後，引擎會將 `config` 樹序列化為二進位格式（Cache）。下次啟動時，直接將二進位資料映射 (Memory Mapping) 到 C++ 物件，這將地圖加載與 AI 初始化的速度提升了數十倍。
