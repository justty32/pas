# Level 3: 進階機制 - Unique 系統 (DSL 架構)

Unciv 的核心競爭力在於其極強的模組化能力，這主要歸功於其「Unique」系統。這是一個實作在 Kotlin 中的領域特定語言 (DSL)，用於定義遊戲規則。

## Unique 系統的三大支柱

### 1. 定義層：`UniqueType.kt`
- **語法定義**：使用 `UniqueType` 列舉定義了數百種模式 (Patterns)。
- **範例**：`Stats("[stats] [cityFilter]")`。
- **目標限制**：每個 Unique 會標註其適用的目標（如 `Global`, `City`, `Unit`）。
- **可擴展性**：雖然目前是編譯時定義的，但它涵蓋了文明帝國系列的大部分機制。

### 2. 解析層：`Unique.kt`
- **正則解析**：將 JSON 中的字串（如 `"Gain a free [Library] [in all cities]"`）解析為 `Unique` 物件。
- **參數提取**：自動識別括號 `[]` 內的內容為參數。
- **條件系統 (Conditionals)**：支援透過角括號 `<>` 附加條件（如 `<during a Golden Age>`）。這些條件在 `Unique.kt` 中被遞迴解析。
- **乘數邏輯**：處理 `For every ...` 類型的邏輯，使效果可以疊加。

### 3. 執行層：`UniqueTriggerActivation.kt`
- **觸發機制**：區分「被動效果」與「主動觸發」。
  - **被動效果**：在計算各類數值（如城市產出、單位戰鬥力）時，實時檢查 `unique.stats` 並過濾 `conditionalsApply`。
  - **主動觸發**：如「贈送單位」、「移除建築」等效果，由 `UniqueTriggerActivation.getTriggerFunction` 映射到具體的 Kotlin 程式碼執行。

## Unique 的語法結構範例
一個典型的複雜 Unique 字串：
`[+2 Culture] [in all cities] <after adopting [Tradition]>`
1.  **核心模式**: `[stats] [cityFilter]`
2.  **參數 1**: `+2 Culture`
3.  **參數 2**: `in all cities`
4.  **修飾符 (Modifier)**: `<after adopting [Tradition]>` (這本身是一個 `Conditional` 類型的 Unique)

## 這種設計的優點
- **數據與邏輯分離**：遊戲的大部分邏輯都存在於 JSON 檔案中，開發者或模組製作者不需要修改程式碼即可改變遊戲規則。
- **易於調試**：規則是人類可讀的字串。
- **動態性**：條件系統允許規則根據遊戲狀態（回合數、資源、科技）動態生效。

## 接下來的分析方向 (Level 4)
- 分析 `WorldScreen` 與 LibGDX Scene2D 的整合（渲染與 UI 佈局）。
- 探索 AI 決策邏輯（如何評估這些 Unique 帶來的價值）。
