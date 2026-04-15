# Editor 模組架構分析 - Level 1 & 2

## 1. 核心職責與概覽
`editor/` 目錄包含了 Godot 編輯器的完整實作。編輯器本身就是一個複雜的 Godot 場景，利用引擎自身的 GUI 與場景系統構建而成。

### 關鍵組件分析：
- **`EditorNode` (`editor/editor_node.h`)**：
    - 編輯器的主入口與核心控制器。
    - 管理主選單、場景切換、儲存/載入邏輯。
    - 協調各個子系統（如 `FileSystemDock`, `Inspector`, `EditorLog`）。
- **`EditorInterface` (`editor/editor_interface.h`)**：
    - 提供給腳本與 GDExtension 的單例介面，用於與編輯器核心互動。
    - 允許存取選取項 (`EditorSelection`)、資源系統 (`EditorFileSystem`) 與主螢幕控制。
- **插件系統 (`plugins/`)**：
    - 允許透過 `EditorPlugin` 擴展編輯器功能。
    - 支援自定義主螢幕、底部面板、上下文選單以及屬性編輯器。
- **資源與匯入 (`import/`, `export/`)**：
    - 處理資源的自動匯入 (Asset Import) 與跨平台匯出 (Export) 流程。
- **偵錯工具 (`debugger/`)**：
    - 實作了遠端偵錯、效能剖析與錯誤日誌顯示。

## 2. 編輯器 UI 佈局架構
- **`EditorMainScreen`**：管理 2D, 3D, Script, AssetLib 四個主要工作視窗。
- **`Docks` (`docks/`)**：
    - `FileSystemDock`：檔案瀏覽器。
    - `SceneTreeDock`：場景樹視圖。
    - `InspectorDock`：屬性編輯器。
    - `HistoryDock`：復原/重做歷史。
- **`Inspector` (`inspector/`)**：
    - `EditorInspector`：根據物件屬性自動生成的編輯介面。
    - 支援 `EditorProperty` 插件化，可為特定類型自定義編輯組件。

## 3. 重要發現
- **編輯器是 Godot 應用程式**：它完全建立在 `scene/gui` 基礎之上，這意味著學習 Godot UI 開發與理解編輯器原始碼有高度相關性。
- **復原/重做機制**：`EditorUndoRedoManager` 負責管理整個編輯器的操作歷史，並整合了場景與資源的變更追蹤。
- **高度模組化**：幾乎每個主要功能（如 Shader 編輯、動畫編輯）都被封裝為 `EditorPlugin`。

---
*檔案位置：`editor/editor_node.h`, `editor/editor_interface.h`, `editor/register_editor_types.cpp`*
