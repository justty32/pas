# 教學導引：如何用 godot-demo-projects 學習特定主題

本 repo 是「按主題拆好的範例庫」，學習方式不是逐一讀，而是**鎖定一個主題 → 找對應 demo → 由淺入深排序**。本文提供幾條常見學習路徑與閱讀順序。

## 前置知識
- 先讀 `architecture/level1_overview.md`：理解「每個資料夾＝獨立專案」、Godot 版本（4.6）、如何用 Project Manager 的 Scan 一次匯入全部 demo。
- 全 132 個 demo 的索引：`architecture/level2_catalog.md`。

## 通用使用步驟
1. 開 Godot 4.6（C# demo 需 .NET 版），用 **Scan** 匯入 repo 根目錄，把全部 demo 載入 Project Manager。
2. 從清單雙擊你要學的 demo（例 `2D Platformer`）開啟。
3. 先讀該 demo 內的 `README.md` 了解操作方式，按 F5 試玩。
4. 從主場景（`project.godot` 的 `run/main_scene`）往下看掛載的腳本。

---

## 路徑 A：做一個 2D 平台遊戲

| 步驟 | Demo | 學到什麼 |
|---|---|---|
| 1 | `2d/dodge_the_creeps` | 最小完整遊戲：節點、輸入、計分、重來 |
| 2 | `2d/platformer` | 角色控制、跳躍手感、射擊、敵人、暫停、分割畫面（深入見 `details/demo_2d_platformer.md`） |
| 3 | `2d/finite_state_machine` | 當行為變複雜，用狀態機重構（深入見 `details/demo_2d_finite_state_machine.md`） |
| 4 | `2d/physics_platformer` | 改用 RigidBody2D 的物理驅動變體，比較兩種角色實作 |

重點對照：`2d/platformer` 用 `get_new_animation()` 的輕量 if/else（`player.gd:62-76`）；`2d/finite_state_machine` 升級成訊號驅動、可堆疊的正式 FSM。先理解前者再看後者，最能體會「何時該引入 FSM」。

## 路徑 B：3D 渲染與畫面品質

| 主題 | Demo |
|---|---|
| 抗鋸齒 | `3d/antialiasing` |
| 全域光照 | `3d/global_illumination` |
| 光與陰影 | `3d/lights_and_shadows`、`3d/decals` |
| 體積效果 | `3d/volumetric_fog`、`3d/sky_shaders` |
| 色調 / HDR | `3d/tonemap_color_correction`、`misc/hdr_output` |
| 效能（剔除 / LOD） | `3d/occlusion_culling_mesh_lod`、`3d/visibility_ranges` |
| 完整設定選單 | `3d/graphics_settings`（把上述開關做成 UI） |

建議：先 `3d/material_testers` 熟悉材質，再依需求挑光影/效能 demo；`3d/graphics_settings` 適合最後看，了解如何把這些選項暴露給玩家。

## 路徑 C：Compute Shader / GPU 計算

| 步驟 | Demo | 難度 |
|---|---|---|
| 1 | `compute/heightmap` | 入門：純算資料，不接渲染 |
| 2 | `compute/texture` | 進階：結果回灌材質、render thread、ping-pong（深入見 `details/demo_compute_texture.md`） |
| 3 | `compute/post_shader` | Compositor Effect 做後處理 |

核心觀念（來自 `compute/texture`）：所有 `RenderingDevice` 操作要鎖在 render thread，用 `RenderingServer.call_on_render_thread`（`water_plane.gd:39,55,129`）；compute 輸出靠 `Texture2DRD` 回灌一般材質。

## 路徑 D：多人連線 / 網路

| 步驟 | Demo | 學到什麼 |
|---|---|---|
| 1 | `networking/websocket_minimal` | 兩 peer 最小連線 |
| 2 | `networking/websocket_chat` | 自架 server、手動 poll、廣播（深入見 `details/demo_networking_websocket_chat.md`） |
| 3 | `networking/websocket_multiplayer` | WebSocket 接 Godot 高階 Multiplayer API |
| 4 | `networking/multiplayer_bomber` | RPC + MultiplayerSpawner 的完整對戰遊戲 |
| 替代 | `networking/webrtc_minimal` → `webrtc_signaling` | 改用 WebRTC（P2P）的路徑 |

關鍵心智模型（來自 `websocket_chat`）：**WebSocketPeer 是 poll 驅動**，每幀必須 `poll()` 才收得到訊息與斷線事件（`WebSocketServer.gd:91-130`）。

## 路徑 E：GUI / UI 系統

| 主題 | Demo |
|---|---|
| 認識所有 Control | `gui/control_gallery` |
| 執行時換膚 | `gui/theming_override` |
| 按鍵重綁 | `gui/input_mapping` |
| 富文字 | `gui/rich_text_bbcode` |
| 多語言 / 字體 | `gui/translation`、`gui/bidi_and_font_features`、`gui/msdf_font` |
| 多解析度自適應 | `gui/multiple_resolutions` |
| 在 3D 中放 GUI | `viewport/gui_in_3d` |

## 路徑 F：載入、存檔、場景管理

| 主題 | Demo |
|---|---|
| 切場景（最簡） | `loading/scene_changer`、`loading/autoload` |
| 背景非阻塞載入 | `loading/load_threaded`、`loading/threads` |
| 存讀檔 | `loading/serialization`、`loading/runtime_save_load` |
| 暫停遊戲 | `misc/pause`（`2d/platformer` 的 `game.gd:18-25` 即套用此機制） |

## 路徑 G：GDScript ↔ C# 對照
想學 C# 寫 Godot，直接把 `mono/` 的 demo 與其 GDScript 同名版並排閱讀：

| GDScript 版 | C# 版 |
|---|---|
| `2d/dodge_the_creeps` | `mono/dodge_the_creeps` |
| `2d/pong` | `mono/pong` |
| `3d/squash_the_creeps` | `mono/squash_the_creeps` |
| `misc/2.5d` | `mono/2.5d` |
| `networking/multiplayer_pong` | `mono/multiplayer_pong` |

---

## 驗證方式
- 每條路徑的每個 demo 都可直接 F5 執行驗證行為。
- 想改著色器 / 參數，多數渲染類 demo 有即時 UI 滑桿（如 `compute/texture` 的 `main.gd:21-26`、`misc/noise_viewer`）。
- 網路類用 `combo.tscn`（`websocket_chat`）可在單一畫面同時跑 server 與 client 自測。
