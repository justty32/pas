# Scene 模組架構分析 - Level 1 & 2

## 1. 核心職責與概覽
`scene/` 目錄實作了 Godot 的高階場景樹系統。它將 `core/` 提供的基礎物件模型轉化為可視化、可操作的層級結構。

### 關鍵子目錄分析：
- **`main/`**: 核心場景系統，包含 `Node`, `SceneTree`, `Viewport`, `Window`。
- **`2d/`**: 所有 2D 相關節點（基於 `CanvasItem`）。
- **`3d/`**: 所有 3D 相關節點（基於 `Node3D`）。
- **`gui/`**: 使用者介面組件（基於 `Control`）。
- **`resources/`**: 場景專用的資源類型（如 `Mesh`, `Texture`, `Shape`, `PackedScene`）。
- **`animation/`**: 動態與過渡系統（`AnimationPlayer`, `AnimationTree`, `Tween`）。

## 2. 核心入口與基礎類別
- **`Node` (`scene/main/node.h`)**:
    - 所有場景物件的基底類別。
    - **層級管理**：處理父子關係、節點路徑 (`NodePath`)。
    - **生命週期**：`_enter_tree`, `_ready`, `_exit_tree`, `_process`, `_physics_process`。
    - **處理模式 (`ProcessMode`)**：控制節點在暫停時的行為。
    - **執行緒安全**：引入了 `MTFlag` 與 `MTNumeric` 來支援多執行緒處理。
- **`SceneTree` (`scene/main/scene_tree.h`)**:
    - 管理節點樹的主循環。
    - 處理暫停、分組 (Groups) 與計時器。
- **`Viewport` (`scene/main/viewport.h`)**:
    - 定義了一個渲染區域，是 2D/3D 渲染的入口。

## 3. 重要發現
- **Node 是 Object 的擴展**：它增加了空間/邏輯層級的概念。
- **資料分譯**：`Node` 內部的 `Data` 結構體用於減少衍生類別的命名空間污染。
- **多執行緒處理**：Godot 4 強化了 `Node` 的多執行緒處理能力 (`ProcessThreadGroup`)，允許將特定節點的分支放到子執行緒執行。
- **資源與節點的分離**：節點處理邏輯，資源 (`Resource`) 儲存資料（如材質、模型）。

---
*檔案位置：`scene/main/node.h`, `scene/register_scene_types.cpp`*
