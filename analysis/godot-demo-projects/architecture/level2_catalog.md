# godot-demo-projects — Level 2 分類目錄（核心交付物）

本文件逐一列出 13 個分類下的全部 demo（共 137 個 `project.godot`），附「一句話用途」，供快速查表「想學 X 該看哪個 demo」。
路徑均相對於 `projects/godot-demo-projects/`；每個列出的目錄都是一個獨立可執行專案（含自己的 `project.godot`）。

摘要統計：2d(26)、3d(32)、audio(9)、compute(3)、gui(14)、loading(6)、misc(12)、mobile(4)、mono(6)、networking(7)、plugins(1 專案/4 addon)、viewport(7)、xr(10)。

---

## 2d/ — 2D 玩法、渲染、導航（26）

| Demo | 一句話用途 |
|---|---|
| `2d/bullet_shower` | 高效管理大量物件（彈幕）：用伺服器 API 取代節點以承載成千上萬子彈 |
| `2d/custom_drawing` | 不使用節點、直接以 `_draw()` 繪製 2D 圖元 |
| `2d/dodge_the_creeps` | 官方新手教學的成品：閃避敵人的簡單小遊戲 |
| `2d/dynamic_tilemap_layers` | 用 TileMap 圖層做出可穿越的「假牆」效果 |
| `2d/finite_state_machine` | 有限狀態機（FSM）設計模式套用於玩家控制 |
| `2d/glow` | 透過 WorldEnvironment 在 2D 遊戲中使用輝光（glow） |
| `2d/hexagonal_map` | 六角形 TileMap 與 TileSet 的最小範例 |
| `2d/instancing` | 場景實例化（scene instancing）的用法示範 |
| `2d/isometric` | 傳統等距視角（isometric）含深度排序 |
| `2d/kinematic_character` | 用 CharacterBody2D 做運動學角色控制器 |
| `2d/light2d_as_mask` | 用 2D 光源當作遮罩遮蔽螢幕上的物件 |
| `2d/lights_and_shadows` | 2D 光源與陰影的簡單示範 |
| `2d/navigation` | 2D 導航（NavigationRegion + Agent）路徑尋找 |
| `2d/navigation_astar` | 用 AStarGrid2D 做格子型 2D 導航 |
| `2d/navigation_mesh_chunks` | 為大型世界分塊烘焙導航網格 |
| `2d/particles` | 2D 粒子系統運作方式展示 |
| `2d/physics_platformer` | 用 RigidBody2D 製作物理驅動的平台跳台 |
| `2d/physics_tests` | 一系列 2D 物理行為測試 |
| `2d/platformer` | 完整像素風 2D 平台遊戲（含音效、敵人、分割畫面） |
| `2d/polygons_lines` | 實心 / 帶貼圖的 2D 多邊形與線段繪製 |
| `2d/pong` | 簡易 Pong，示範 2D 遊戲最佳實務 |
| `2d/role_playing_game` | 格子型移動（grid-based movement）的 RPG 範例 |
| `2d/screen_space_shaders` | 多個全螢幕 2D 著色器後處理範例 |
| `2d/skeleton` | 用骨架（Skeleton2D）做綁定與動畫角色 |
| `2d/sprite_shaders` | 套用於 Sprite 的各式著色器範例集 |
| `2d/tween` | 進階 Tween（補間動畫）用法 |

## 3d/ — 3D 渲染、物理、光影（32）

| Demo | 一句話用途 |
|---|---|
| `3d/antialiasing` | 展示 Godot 各種 3D 抗鋸齒（MSAA/TAA/FXAA…） |
| `3d/csg` | 建構式實體幾何（CSG）布林造型功能 |
| `3d/decals` | Decal 貼花節點的多種使用範例 |
| `3d/global_illumination` | 全域光照系統（VoxelGI / SDFGI / LightmapGI） |
| `3d/graphics_settings` | 圖形設定選單的實作範例 |
| `3d/ik` | 不同反向運動學（IK）演算法示範 |
| `3d/kinematic_character` | 用方塊角色示範 3D 運動學角色控制 |
| `3d/labels_and_texts` | 兩種 3D 文字技巧：Label3D 與 TextMesh |
| `3d/lights_and_shadows` | 3D 各式光源與陰影功能展示 |
| `3d/material_testers` | 多顆複雜材質球，當作材質測試場 |
| `3d/navigation` | 3D 場景導航，角色沿路徑移動 |
| `3d/navigation_mesh_chunks` | 為大型世界分塊烘焙 3D 導航網格 |
| `3d/occlusion_culling_mesh_lod` | 遮擋剔除（occlusion culling）+ Mesh LOD |
| `3d/particles` | 3D 粒子（GPU 與 CPU 版）功能展示 |
| `3d/physical_light_camera_units` | 物理光照與相機單位（流明 / 光圈快門 ISO） |
| `3d/physics_interpolation` | 物理插值（physics interpolation）平滑畫面 |
| `3d/physics_tests` | 一系列 3D 物理行為測試 |
| `3d/platformer` | 3D 平台遊戲範例 |
| `3d/procedural_materials` | 3 種程序化生成材質的技巧 |
| `3d/ragdoll_physics` | 角色布娃娃（ragdoll）模擬範例 |
| `3d/rigidbody_character` | 用膠囊 RigidBody 做 3D 角色 |
| `3d/sky_shaders` | 天空著色器，含即時體積雲 |
| `3d/soft_body_physics` | 軟體物理（SoftBody）範例 |
| `3d/sprites` | 3D 中使用 Sprite3D 與 AnimatedSprite3D |
| `3d/squash_the_creeps` | 官方 3D 新手教學成品：踩扁敵人的小遊戲 |
| `3d/tonemap_color_correction` | 各色調映射運算子與調色互動 |
| `3d/truck_town` | 不同類型卡車的駕駛物理示範 |
| `3d/variable_rate_shading` | 可變速率著色（VRS）使用方式 |
| `3d/visibility_ranges` | 用可見距離（visibility ranges）建階層式 LOD |
| `3d/volumetric_fog` | Vulkan 渲染器下的體積霧範例 |
| `3d/voxel` | 最小第一人稱體素（voxel）遊戲 |
| `3d/waypoints` | 在 3D 世界顯示 Label 等 GUI（導航點） |

## audio/ — 音效系統（9）

| Demo | 一句話用途 |
|---|---|
| `audio/audio_effects` | 各式 Audio Effect（總線效果）示範 |
| `audio/bpm_sync` | 將音訊播放與時間同步以維持一致 BPM |
| `audio/device_changer` | 從 Godot 切換音訊輸出裝置 |
| `audio/generator` | 用 AudioStreamGenerator 程序化生成音訊 |
| `audio/mic_record` | 從麥克風錄音 |
| `audio/midi_piano` | 使用 MIDI 輸入做鋼琴 |
| `audio/rhythm_game` | 簡易節奏遊戲（處理音訊延遲對齊） |
| `audio/spectrum` | 用頻譜分析器（SpectrumAnalyzer）做視覺化 |
| `audio/text_to_speech` | 文字轉語音（TTS）支援示範 |

## compute/ — Compute Shader / Compositor（3）

| Demo | 一句話用途 |
|---|---|
| `compute/heightmap` | 用 compute shader 生成高度圖（入門級 RenderingDevice 用法） |
| `compute/post_shader` | 用 Compositor Effect 做後處理 |
| `compute/texture` | 用 compute shader 即時填充材質（水波漣漪，整合進渲染管線） |

## gui/ — Control 介面、主題、國際化（14）

| Demo | 一句話用途 |
|---|---|
| `gui/accessibility` | UI 無障礙（accessibility）功能示範 |
| `gui/bidi_and_font_features` | 雙向文字（BiDi）、斷行對齊、OpenType 字體特性 |
| `gui/control_gallery` | 各種 Control 節點集中陳列，附名稱便於辨識 |
| `gui/drag_and_drop` | 拖放（drag and drop）功能示範 |
| `gui/gd_paint` | 用 GDScript 做的簡易繪圖編輯器 |
| `gui/input_mapping` | 按鍵重新綁定（remap）設定畫面 |
| `gui/msdf_font` | 多通道有號距離場（MSDF）字體 |
| `gui/multiple_resolutions` | 多解析度自適應（content scaling）示範 |
| `gui/pseudolocalization` | 偽本地化（pseudolocalization）測試功能 |
| `gui/regex` | RegEx（正規表達式）功能與用法 |
| `gui/rich_text_bbcode` | RichTextLabel 的 BBCode 富文字支援 |
| `gui/theming_override` | 執行時覆寫 GUI 顏色與 StyleBox |
| `gui/translation` | 專案國際化（i18n）翻譯流程 |
| `gui/ui_mirroring` | UI 鏡像（RTL 版面）示範 |

## loading/ — 載入、場景切換、執行緒、序列化（6）

| Demo | 一句話用途 |
|---|---|
| `loading/autoload` | 用 Autoload 單例切換場景 |
| `loading/load_threaded` | 用 ResourceLoader 做背景（多執行緒）載入 |
| `loading/runtime_save_load` | 執行時載入 / 存檔各種檔案格式（不經 import） |
| `loading/scene_changer` | 用 SceneTree 兩個函式在兩場景間切換 |
| `loading/serialization` | 各種序列化方式存檔的比較 |
| `loading/threads` | 用 Thread 載入圖片的範例 |

## misc/ — 視窗、輸入、座標、雜項（12）

| Demo | 一句話用途 |
|---|---|
| `misc/2.5d` | 2.5D 遊戲（3D 場景 2D 視覺）做法 |
| `misc/custom_logging` | 自訂 Logger，與引擎並行運作 |
| `misc/graphics_tablet_input` | 繪圖板（壓感）輸入支援 |
| `misc/hdr_output` | HDR 輸出與最佳實務 |
| `misc/joypads` | 手把（joypad）測試工具 |
| `misc/large_world_coordinates` | 雙精度（double）渲染支援，超大世界座標 |
| `misc/matrix_transform` | 互動視覺化 Transform（矩陣變換）原理 |
| `misc/multiple_windows` | 在主視窗內使用各種 Window 類別 |
| `misc/noise_viewer` | 即時調整各種雜訊（noise）參數的檢視器 |
| `misc/os_test` | 各種 OS 相關功能（OS 類別）測試 |
| `misc/pause` | 遊戲暫停（SceneTree.paused）機制 |
| `misc/window_management` | 視窗管理（DisplayServer）各功能展示 |

## mobile/ — 行動裝置（4）

| Demo | 一句話用途 |
|---|---|
| `mobile/android_iap` | Android 應用內購買（IAP） |
| `mobile/multitouch_cubes` | 多點觸控與手勢操作（需觸控裝置） |
| `mobile/multitouch_view` | 多點觸控除錯器（顯示按壓點彩色圓點） |
| `mobile/sensors` | 加速度計、陀螺儀、磁力計等感測器 |

## mono/ — C#（.NET）版範例（6）

| Demo | 一句話用途 |
|---|---|
| `mono/2.5d` | 2.5D 遊戲的 C# 版本 |
| `mono/android_iap` | Android IAP 的 C# 版本 |
| `mono/dodge_the_creeps` | dodge_the_creeps 的 C# 版本 |
| `mono/multiplayer_pong` | 多人 Pong 的 C# 版本 |
| `mono/pong` | Pong 的 C# 版本 |
| `mono/squash_the_creeps` | squash_the_creeps 的 C# 版本 |

> mono/ 的多數 demo 是其他分類同名 demo 的 C# 對照，便於學習 GDScript ↔ C# 的等價寫法；需 .NET 版 Godot。

## networking/ — 網路與多人連線（7）

| Demo | 一句話用途 |
|---|---|
| `networking/multiplayer_bomber` | 用高階 Multiplayer API（RPC + MultiplayerSpawner）做炸彈超人 |
| `networking/multiplayer_pong` | 多人 Pong 實作 |
| `networking/webrtc_minimal` | 用 WebRTC 連接兩個 peer 的最小範例 |
| `networking/webrtc_signaling` | WebRTC 完整信令（signaling）流程（含 server） |
| `networking/websocket_chat` | WebSocket 聊天室：自架 WS server + client（手動 poll） |
| `networking/websocket_minimal` | 用 WebSocket 連兩 peer 的最小範例 |
| `networking/websocket_multiplayer` | WebSocket 搭配 Multiplayer API |

## plugins/ — 編輯器插件（1 專案，內含多個 addon）

| Addon（位於 `plugins/addons/`） | 一句話用途 |
|---|---|
| `plugins/addons/custom_node` | 用插件註冊自訂節點型別 |
| `plugins/addons/main_screen` | 在編輯器主畫面新增自訂分頁 |
| `plugins/addons/material_creator` | 提供材質建立工具的插件 |
| `plugins/addons/simple_import_plugin` | 自訂資源匯入（import plugin）流程 |

> `plugins/` 本身是單一專案（`plugins/project.godot`），把多個 EditorPlugin demo 集中於 `addons/`，並用 `plugins/test_scene.tscn` 展示。

## viewport/ — SubViewport 與分割畫面（7）

| Demo | 一句話用途 |
|---|---|
| `viewport/2d_in_3d` | 用 viewport 把 2D 場景顯示在 3D 場景中 |
| `viewport/3d_in_2d` | 用 viewport 把 3D 場景顯示在 2D 場景中 |
| `viewport/3d_scaling` | 縮放 3D 解析度而不影響 2D（render scale） |
| `viewport/dynamic_split_screen` | 動態分割畫面（兩玩家靠近時合併） |
| `viewport/gui_in_3d` | 在 3D 場景中放置可互動的 GUI |
| `viewport/screen_capture` | 擷取畫面截圖 |
| `viewport/split_screen_input` | 本地多人分割畫面與輸入處理 |

## xr/ — VR / AR（OpenXR / WebXR）（10）

| Demo | 一句話用途 |
|---|---|
| `xr/mobile_vr_interface_demo` | 啟用 Mobile VR 介面的最簡範例 |
| `xr/openxr_binding_modifier_demo` | OpenXR action map 的 binding modifier 功能 |
| `xr/openxr_character_centric_movement` | 以 CharacterBody3D 為基底的 VR 移動 |
| `xr/openxr_composition_layers` | OpenXR compositor layer（合成層）功能 |
| `xr/openxr_hand_tracking_demo` | OpenXR 手部追蹤與控制器追蹤 |
| `xr/openxr_origin_centric_movement` | 以 XROrigin3D 為基底的 VR 移動 |
| `xr/openxr_passthrough` | OpenXR 透視（passthrough，AR）功能 |
| `xr/openxr_render_models` | OpenXR 渲染模型（render models）實作 |
| `xr/openxr_spectator_view` | 頭盔內外不同視角（旁觀者視角） |
| `xr/webxr` | WebXR 渲染與控制器支援的最小範例 |

---

## 速查：常見學習主題 → 推薦 demo

| 想學… | 看這個 demo |
|---|---|
| 2D 平台跳台完整做法 | `2d/platformer`、`2d/physics_platformer` |
| 狀態機設計模式 | `2d/finite_state_machine` |
| 角色控制器 | `2d/kinematic_character`、`3d/kinematic_character`、`3d/rigidbody_character` |
| 第一個完整小遊戲 | `2d/dodge_the_creeps`、`3d/squash_the_creeps` |
| 導航 / 尋路 | `2d/navigation_astar`、`2d/navigation`、`3d/navigation` |
| Compute Shader | `compute/heightmap`（入門）→ `compute/texture`（整合渲染） |
| 多人連線（高階 API） | `networking/multiplayer_bomber` |
| WebSocket 通訊 | `networking/websocket_minimal` → `websocket_chat` → `websocket_multiplayer` |
| UI / 控制項 | `gui/control_gallery`、`gui/theming_override` |
| 國際化與字體 | `gui/translation`、`gui/bidi_and_font_features`、`gui/msdf_font` |
| 場景切換與背景載入 | `loading/scene_changer`、`loading/load_threaded` |
| 暫停遊戲 | `misc/pause` |
| 分割畫面 | `viewport/dynamic_split_screen`、`viewport/split_screen_input` |
| VR 開發起步 | `xr/openxr_character_centric_movement`、`xr/openxr_hand_tracking_demo` |
| C# 寫 Godot | `mono/` 任一（與 GDScript 版對照） |
| 編輯器插件 | `plugins/`（內含 4 種 addon） |
