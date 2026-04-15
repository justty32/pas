# 渲染架構

Taisei Project 具有自定義的渲染系統，設計上與底層圖形 API 無關。

## 渲染器 API (`src/renderer/api.h`)

渲染系統的核心是一個抽象層，定義了高級圖形操作和類型：
-   **紋理 (`Texture`)**：2D 圖像和立方體貼圖的抽象。
-   **幀緩衝 (`Framebuffer`)**：渲染到紋理的目標。
-   **緩衝區 (`VertexBuffer`, `IndexBuffer`)**：用於幾何數據的 GPU 端存儲。
-   **著色器 (`ShaderObject`, `ShaderProgram`)**：用於頂點和片元階段的自定義 GLSL（或兼容）程序。
-   **模型和精靈 (Models and Sprites)**：3D 網格和基於 2D 四邊形視覺效果的高級抽象。

API 提供了一組功能和能力（例如：`RFEAT_DRAW_INSTANCED`, `RCAP_DEPTH_TEST`），後端可以報告是否支持。

## 渲染器後端 (`src/renderer/`)

Taisei 目前支持多個渲染後端：
1.  **OpenGL 3.3 (`src/renderer/gl33/`)**：主要的桌面端後端。
2.  **OpenGL ES 3.0 (`src/renderer/gles30/`)**：用於移動端和基於 Web 的平台（通過 Emscripten）。
3.  **SDL_gpu (`src/renderer/sdlgpu/`)**：利用 SDL3 高級 GPU API 的後端（如果可用）。
4.  **空渲染器 (`src/renderer/null/`)**：不執行實際渲染的虛擬後端，用於無頭回放驗證或性能測試。

## 渲染流水線

渲染過程通常分為幾個階段：
1.  **加載屏幕**：資源初始化期間的早期渲染。
2.  **背景渲染**：特定關卡的背景元素（3D 背景、滾動圖像）。
3.  **遊戲內容渲染**：彈幕、敵人、玩家和粒子。
4.  **UI 和 HUD**：界面元素和分數疊加。
5.  **後處理 (`src/resource/postprocess.c`)**：應用於最終幀的模糊、模糊或顏色調整等效果。

## 精靈批處理 (`src/renderer/common/sprite_batch.h`)

鑑於彈幕遊戲中大量的彈幕，Taisei 使用了高效的精靈批處理系統。該系統通過在發送到 GPU 之前將共享材質和紋理的精靈分組為更大的批次，從而最大限度地減少狀態切換和繪製調用。
