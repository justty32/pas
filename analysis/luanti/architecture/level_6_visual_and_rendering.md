# Level 6: 視覺、動畫與渲染技術分析

## 1. 渲染架構 (Rendering Engine)
Luanti 的渲染核心建立在 Irrlicht MT 之上：
- **核心類別**：`RenderingEngine` (`src/client/renderingengine.h`)
- **主要組件**：
    - **動態陰影 (Dynamic Shadows)**：由 `DynamicShadowsRender` 處理，支援即時陰影投射。
    - **FpsControl**：精確控制渲染循環的睡眠時間與繁忙時間。
    - **霧效處理**：透過 `FOG_RANGE_ALL` 模擬遠景剪裁。

## 2. Shader 系統
- **機制**：Luanti 不僅僅是加載靜態 Shader 檔案，而是動態建構 Shader 原始碼。
- **常量注入**：`ShaderConstants` 允許將 C++ 的變數（如 `int` 或 `float`）以 `#define` 的形式注入 GLSL 程式碼。
- **快取系統**：`getShaderPath` 結合線程安全快取，優化 Shader 載入速度。

## 3. 地圖網格化 (Mesh Generation)
這是體素遊戲效能的關鍵：
- **MeshMakeData**：收集 16x16x16 區域內的節點資訊。
- **平滑光照 (Smooth Lighting)**：在頂點層級進行顏色插值，使方塊邊緣的光影過渡更自然。
- **節點網格化過程**：
    1. 從 `VoxelManipulator` 獲取原始數據。
    2. 根據節點類型（Cube, Liquid, Plant, Mesh 等）生成對應的幾何體。
    3. 合併頂點並應用貼圖 (Texture Atlas)。

## 4. UI 與視覺回饋
- **HUD (Head-Up Display)**：處理準星、血條、氧氣條與自定義 Lua HUD 元素。
- **粒子系統 (Particles)**：高效的 CPU 驅動粒子系統，用於爆炸、挖掘碎屑與天氣效果。
