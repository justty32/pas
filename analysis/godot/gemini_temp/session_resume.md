# Session Resume - Godot Engine 分析進度彙整

## 1. 當前專案理解 (Project Context)
- **專案名稱**：Godot Engine 4.7.dev
- **核心技術**：C++ (C++17), SCons (Python), GLSL
- **架構特點**：基於「伺服器-場景-資源」模型，透過 `RID` 實現邏輯與渲染/物理後端的解耦。GDExtension 作為主要的外部擴展手段。

## 2. 已完成的分析路徑 (Completed Architecture Paths)
- **Level 1 & 2 (基礎與核心)**：
    - `core/`: 基礎類型、物件模型 (`Object`, `RefCounted`)、`Variant` 系統、自定義容器 (`CowData`, `Vector`)。
    - `modules/gdscript`: 編譯管線 (Parser, Analyzer) 與 VM 執行機制。
    - `core/extension`: GDExtension 載入與初始化流程。
    - `editor`: 編輯器核心架構、插件系統與 `EditorInterface`。
- **Level 3 & 4 (子系統與資源深度)**：
    - `scene/gui`: `Control` 事件流、`Container` 自動佈局。
    - `scene/animation`: `AnimationMixer` 混音架構、`Animation` 資源軌道資料模型。
    - `scene/2d & 3d`: 空間變換更新、渲染指令提交、`CanvasItem` 與 `VisualInstance`。
    - `scene/physics & navigation`: 碰撞形狀管理、導航網格烘焙與路徑開銷。
    - `core/io`: 資源序列化、`.tscn` 與 `.tres` 檔案結構。
- **Level 5 (低階運行機制)**：
    - `main/main.cpp`: 物理 Tick (Fixed Timestep) 與累積器邏輯。
    - `servers/rendering`: 著色器 Uniform 同步與伺服器通訊。

## 3. 已建立的教學文件 (Tutorials)
1. `gdextension_custom_node.md`: 基礎 Node 建立與 ClassDB 註冊。
2. `gdextension_advanced_resources_signals.md`: 自定義資源與 C++/腳本信號通訊。
3. `gdextension_threading_memory.md`: 執行緒池與 memnew/memdelete 規範。
4. `gdextension_node_lifecycle.md`: 動態增刪節點與 queue_free。
5. `gdextension_procedural_mesh.md`: SurfaceTool 程序化幾何生成。
6. `gdextension_procedural_material.md`: 動態材質與 Shader 參數設定。
7. `gdextension_procedural_animation.md`: 程序化 Animation 資源與軌道操作。
8. `gdextension_serialization.md`: 資源自動與手動序列化。
9. `gdextension_local_slow_motion.md`: 特定節點的時間縮放實作。
10. `gdextension_3d_dyeing_system.md`: 3D Shader 遮罩染色。
11. `gdextension_2d_dyeing_system.md`: 2D 精靈區域染色。
12. `gdextension_procedural_particles.md`: 程序化粒子發射器配置。
13. `gdextension_custom_astar.md`: 高效能 A* 算法擴充。
14. `gdextension_procedural_tilemap.md`: TileMapLayer 程序化填充與地形。
15. `gdextension_image_to_sprite.md`: 外部圖片載入與 Texture 轉換。
16. `gdextension_bouncing_ball_physics.md`: 物理場景、材質與衝量操作。
17. `gdextension_mouse_hover_glow.md`: 滑鼠互動描邊與發光 Shader 特效。

## 4. 剩餘待辦事項 (TODOs / Next Steps)
- [ ] **Servers 深度剖析**：分析 `servers/rendering/renderer_rd` (RenderingDevice 後端) 的具體實作。
- [ ] **網路系統**：分析 `core/io/multiplayer_api.h` 實作網路同步。
- [ ] **平台適配**：分析 `platform/windows` 或 `platform/android` 的入口點。
- [ ] **插件實戰**：撰寫如何開發一個包含自定義面板的 `EditorPlugin` 教學。

## 5. 上下文摘要
目前的分析已覆蓋 Godot 絕大部分常用的開發接口。下一次可以從 `servers` 的底層渲染邏輯或 `platform` 的系統整合開始。
