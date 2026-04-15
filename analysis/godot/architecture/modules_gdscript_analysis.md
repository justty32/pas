# GDScript 模組架構分析 - Level 1 & 2

## 1. 核心職責與概覽
`modules/gdscript` 實作了 Godot 的原生腳本語言 GDScript。它包含了一個完整的編譯管線與一個高效的虛擬機器 (VM)。

### 關鍵組件分析：
- **前端 (Frontend)**：
    - `GDScriptTokenizer`：將原始碼轉換為 Token 流。
    - `GDScriptParser`：構建抽象語法樹 (AST)，定義了各種節點類型 (如 `IfNode`, `FunctionNode`)。
    - `GDScriptAnalyzer`：進行靜態分析、類型推斷與語法檢查。
- **後端 (Backend)**：
    - `GDScriptCompiler`：將 AST 編譯為虛擬機器可執行的位元組碼 (Bytecode)。
    - `GDScriptByteCodeGenerator`：負責位元組碼的具體生成邏輯。
- **執行環境 (Runtime)**：
    - `GDScriptFunction`：封裝了一個可執行的函數，包含其位元組碼、堆疊大小與參數資訊。
    - `GDScriptVirtualMachine` (`gdscript_vm.cpp`)：位元組碼解釋器，執行具體的指令集。
    - `GDScriptInstance`：代表一個已實例化的腳本物件，管理其成員變數與生命週期。

## 2. 語言整合機制
- **`GDScriptLanguage`**：單例類別，作為引擎與 GDScript 模組之間的通訊介面，負責資源載入、調試支援與腳本管理。
- **`GDScriptNativeClass`**：包裝 C++ 類別，使其能在 GDScript 中像原生類別一樣被調用。
- **快取機制 (`GDScriptCache`)**：優化腳本編譯與載入速度，處理腳本間的依賴關係。

## 3. 重要發現
- **強類型支援**：Godot 4 的 GDScript 強化了靜態類型系統 (`DataType`)，在 `GDScriptAnalyzer` 階段進行嚴格檢查。
- **Lambda 與 Callable**：支援匿名函數 (`LambdaNode`) 與一等公民函數 (`Callable`)。
- **熱重載 (Hot-Reloading)**：`GDScript` 類別內建了 `old_static_variables` 等機制來支援在工具模式下的代碼更新。

---
*檔案位置：`modules/gdscript/gdscript.h`, `modules/gdscript/gdscript_parser.h`, `modules/gdscript/gdscript_vm.cpp`*
