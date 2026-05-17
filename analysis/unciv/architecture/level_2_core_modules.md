# Level 2: 核心模組職責與入口點 - Unciv

## 入口點 (Entry Point)
Unciv 是一個跨平台的 LibGDX 專案，其啟動流程如下：

1.  **桌面端入口**: `desktop/src/com/unciv/app/desktop/DesktopLauncher.kt`
    - 負責平台相關的初始化（日誌、顯示、字體、存檔路徑）。
    - 建立並啟動 `DesktopGame`（繼承自 `UncivGame`）。
    - 透過 `Lwjgl3Application` 啟動遊戲循環。

2.  **核心遊戲邏輯入口**: `core/src/com/unciv/UncivGame.kt`
    - 這是遊戲的核心類別，繼承自 LibGDX 的 `Game`。
    - **單例存取**: 透過 `UncivGame.Current` 提供全域存取。
    - **生命週期管理**: `create()`, `render()`, `pause()`, `resume()`, `dispose()`。
    - **畫面管理 (Screen Management)**: 維護一個 `screenStack` (`ArrayDeque<BaseScreen>`)，支援畫面的推入 (push) 與彈出 (pop)。

## 核心模組與權責劃分

| 模組路徑 | 主要職責 |
| :--- | :--- |
| `com.unciv.UncivGame` | 中央協調者，處理畫面切換、全域資源加載與生命週期。 |
| `com.unciv.logic.GameInfo` | **數據模型 (Model)**：存儲當前遊戲的所有狀態，包括地圖、文明、單位、回合數等。 |
| `com.unciv.models.ruleset` | **規則集 (Ruleset)**：定義遊戲的靜態數據（如單位屬性、建築效果、科技樹）。這是 Unciv 高度可模組化的核心。 |
| `com.unciv.ui.screens` | **視圖層 (View)**：不同的遊戲介面。`WorldScreen` 是主要的遊戲進行畫面。 |
| `com.unciv.logic.files` | **持久化層**：負責遊戲存檔 (`UncivFiles`)、設置與自動存檔。 |
| `com.unciv.ui.images` | **資源管理**：透過 `ImageGetter` 管理貼圖集 (Atlas) 與規則集圖片的映射。 |

## 遊戲循環與畫面流程
- `UncivGame` 使用自定義的 `BaseScreen`。
- 啟動後通常路徑為：`GameStartScreen` -> `MainMenuScreen` -> (`NewGameScreen` 或 `LoadGameScreen`) -> `WorldScreen`。
- `WorldScreen` 負責渲染 4X 遊戲的地圖、單位並處理使用者輸入。

## 關鍵技術點
- **Kotlin 協程**: 在 `loadGame` 等耗時操作中使用了 `suspend` 函數與協程，確保 UI 不會卡死。
- **自定義 UI 框架**: 基於 LibGDX 的 Scene2D，但有大量的自定義封裝（如 `Popup`, `BaseScreen`）。
- **規則集驅動**: 遊戲邏輯高度依賴 JSON 定義的規則集，而非硬編碼。
