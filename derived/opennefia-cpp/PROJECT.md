# PROJECT — opennefia-cpp

> 衍生小專案：用 **C++20** 重寫 OpenNefia 的**引擎核心**，架構藍本取自使用者自有的 `medps`。
> 建立於 2026-06-01（Create 模式，依 `create_workflow.md`）。

---

## 1. 源專案

- **重寫對象**：OpenNefia（C# / .NET 8.0 的 Elona 開源重製引擎）。分析產物：`analysis/OpenNefia/`（architecture 14 篇 + C++ 重寫初探 `details/plan_cpp/`）。
- **架構藍本**：medps（使用者自有 C++20 4X 模擬核心，EnTT + cereal）。分析產物：`analysis/medps/`。

## 2. 衍生目標

把 OpenNefia 的 **C# 引擎核心**（ECS、原型、序列化、系統、地圖邏輯、設定 / 日誌 / 在地化）以 **godot-free 的純 C++20 函式庫**重新實作，**完全基於 medps 已驗證的做法**：

- 用 **EnTT** 取代自製 EntityManager。
- 用 **`entt::type_list` + fold expression + cereal** 取代 C# `[DataField]` 反射序列化。
- 用 **自由函式系統 + 明確註冊** 取代 C# Assembly 掃描自動發現。
- 用 **編譯目標邊界**（核心目標不連任何前端庫）取代 IoC 注入式解耦。

> 核心命題：OpenNefia 的 C# 架構大量依賴**反射**（DI 注入、系統自動發現、欄位序列化）。C++ 沒有反射。medps 證明——順著 C++ 的紋理（type_list、自由函式、編譯期展開）能用**更少抽象**表達同樣意圖。本專案就是把這個證明套用到 OpenNefia 的內容規模上。

## 3. 範圍（重要：目前只做核心）

**本階段聚焦純 C++ 核心，不碰 Godot 整合與前端。**

### ✅ 範圍內（godot-free 核心）
- ECS（EnTT registry / component / 自由函式系統 / 事件）
- 原型系統（YAML 載入、`PrototypeId<T>`、繼承合併）
- 序列化 / 存讀檔（EnTT snapshot + cereal）
- 地圖**邏輯**（tile 稠密網格 component、實體佈局；不含渲染）
- 設定（CVar）、日誌、在地化資料、亂數、計時、虛擬檔案系統（讀 YAML / data）

### ⏸ 暫緩（前端，之後另開階段）
- 圖形 / 渲染、UI（Wisp / Control）、輸入裝置、音效、視窗 / OS
- Godot GDExtension 綁定層（`gbind/` 對應物）

> 暫緩不代表忽略：核心的所有對外介面都會設計成「前端可掛接」——例如系統產出的事件 / 狀態以 POD 形式暴露，未來薄殼 facade（仿 medps `gbind/`）即可橋接 Godot。但本階段不寫任何前端碼。

## 4. 技術棧

| 功能 | 函式庫 | 對應 medps |
|---|---|---|
| 語言 | C++20 | 同 |
| ECS | EnTT | `gcore/` 全面採用 |
| 序列化 | cereal（PortableBinary） | `serialize/` |
| YAML | yaml-cpp | （medps 用 cereal binary；本專案另需 YAML 讀原型） |
| 日誌 | spdlog | （medps 尚未引入） |
| 設定 | tomlplusplus 或自製 CVar | 對應 OpenNefia Configuration |
| 構建 | CMake ≥3.14 | 同 medps 雙目標式 |
| 測試 | doctest v2.4.11 | medp_test |

> 與 OpenNefia 不同：本專案**不採 raylib**（已棄）。前端方向（未來）為 Godot 4 GDExtension，與 medps 一致——但本階段不實作。

## 5. 完成定義（本階段＝核心）

核心階段「做完了」的判準：

1. `opennefia_core` 靜態庫可獨立編譯，**不連任何前端庫**（編譯邊界可驗證）。
2. 能從 YAML 載入一批原型（如角色 / 物品定義），`SpawnEntity(protoId)` 組出帶 component 的實體。
3. ECS 事件匯流排可跑：系統訂閱 / 發送定向與廣播事件。
4. 一張地圖（tile 網格 component + 若干實體）能 **snapshot 存檔 → 還原**，round-trip 正確。
5. 有最小測試套件涵蓋上述（仿 `medp_test` 的綠燈保證）。

## 6. 參照素材

- `analysis/medps/architecture/02_core_patterns.md` —— 六條核心藍本（多 registry / type_list 序列化 / 自由函式系統 / ...）。
- `analysis/OpenNefia/architecture/03_ecs_system.md`、`06_prototype_serialization.md`、`11_save_load_system.md` —— 要重現的目標語意。
- `analysis/OpenNefia/details/plan_cpp/05_lessons_from_medps.md` —— 三大反射難題的 medps 對照。
- medps 源碼：`C:/code/mine/medps/src/gcore/`（直接當實作參考）。

## 7. 設計文件索引

- `docs/01_core_architecture.md` —— 核心分層與目標結構（godot-free）。
- `docs/02_subsystem_mapping.md` —— OpenNefia 子系統 → C++ 核心對照（範圍內 / 暫緩）。
- `docs/03_roadmap.md` —— 核心階段路線圖（Phase 0–4）。
- `docs/decisions/` —— 重要設計決策的追溯連結（借鑒自哪份分析）。

## 8. 外部連結

GitHub Repo：（尚無；如日後推送由使用者手動建立並於此記錄）

## 9. 進度

- 2026-06-01：專案初始化，完成 PROJECT.md 與設計文件 01–03。尚未開始實作（src/ 空）。
- 2026-06-01：**Phase 0 完成**。CMakeLists.txt（FetchContent：EnTT v3.16.0 / cereal v1.3.2 / spdlog v1.14.1 / doctest v2.4.11），`opennefia_core` STATIC 靜態庫編譯通過，`version()` smoke test 綠燈（1/1）。
- 2026-06-01：**Phase 1 完成**。`core/ecs/`（EntityManager + EventBus + SystemCtx）、`core/services/`（ServiceContext）、`core/components/`（MetaDataComponent + SpatialComponent）、`core/util/`（Vector2i + ResourcePath）。8 test cases / 20 assertions 全綠。
- 2026-06-01：**Phase 2 完成**。`core/prototypes/`（PrototypeId + Prototype + PrototypeManager：yaml-cpp 載入、拓撲繼承解析、ComponentLoader 顯式登錄、spawn）；`data/test_prototypes.yaml`（3 層繼承 + 獨立原型）。20 test cases / 70 assertions 全綠。
- 2026-06-01：**Phase 3 完成**。`core/serialize/`（AllComponents type_list + entt_cereal_archive + save_load 三層 API + SaveStore/FolderSaveStore）；`SpatialComponent` save/load split（parent entity round-trip）。29 test cases / 95 assertions 全綠。
- 2026-06-01：**Phase 4 完成（核心完成定義達成）**。`core/maps/`（Tile + MapData 稠密網格）；AllComponents 更新；整合測試：原型生成 → 地圖可走性 → 移動系統 tick 3 輪 + 牆阻擋 → FolderSaveStore 存讀 → 驗證座標與地圖旗標。36 test cases / 139 assertions 全綠。**核心階段 Phase 0–4 全部完成。**
- 2026-06-02：**F1 完成（GDExtension 工具鏈）**。`src/gbind/`（`OpenNefiaCore : RefCounted` + `register_types`）；`godot_test/`（`.gdextension` + `project.godot` + `smoke_test.gd` + `bin/opennefia_gd.dll`）。`-DOPENNEFIA_BUILD_GDEXTENSION=ON` 建置通過，1.4 MB DLL 產出。
- 2026-06-02：**F2 完成（地圖橋接 + Image 渲染）**。`gbind/opennefia_world_gd`（`OpenNefiaWorld : Node` 持有 EM + ServiceContext、`setup_test_world` 20×15、`generate_map_image` 三色）；`map_view.gd`（Image→ImageTexture→Sprite2D + Camera2D）。4.9 MB DLL。
- 2026-06-02：**F3 完成（輸入→核心→Signal）**。`OpenNefiaWorld` `move/wait_turn/get_hero_x/y/turn_count` + `world_changed` signal；`map_view.gd` 8 向輸入 + InfoLabel。閉環跑通（5.1 MB DLL）。
- 2026-06-02：**遊戲性擴充（在前端上長出可玩 roguelike）**。依序完成：NPC AI（wander，`npc_ai_component` + `npc_ai_system`，`advance_turn`/EventBus）→ FOV（`fov_system` Bresenham LOS radius=8 + `map_data` visible/explored）+ 8 格追蹤 + 碰撞信號 + F4 音效框架 → 戰鬥（`health_component`，hero 20 / NPC 10，撞擊扣血 + `npc_died`/`game_over`）→ BSP 地城（`map_gen`，60×40，房間連走廊）→ 多樓層（`TILE_STAIR_DOWN` + `next_floor`/`restart` + `floor_changed`，NPC 隨層強化）→ 物品拾取（`item_component` 回血藥 + `item_picked_up`）→ NPC 多類型（`combat_stats_component` putit/warrior/bat）→ 存讀檔（`world_state_component` + `save_game/load_game`，cereal PortableBinary，GDScript F5/F9）。詳見 `docs/03_roadmap.md`「遊戲性擴充」段；事後分析同步至 `../../analysis/opennefia-cpp/`。
- 2026-06-02：**Linux/GCC 16 移植修復**（先前皆 Windows/MSVC）。yaml-cpp 0.8.0 `-include cstdint`、`fov_system.cpp` 去 `opennefia::` 限定名、`GODOT_CPP_DIR` 改相對 repo 預設。`opennefia_core` + 測試在 GCC 16 重建，ctest **36/36 cases、139 assertions 全綠**。
- 2026-06-02：**F5 — Linux 前端 .so 實機驗證**。godot-cpp 4.6 本機編譯出 `libopennefia_gd.so`；修 `opennefia_core_gd.cpp` 缺 `#include <string>`（GCC 16）。新寫 `godot_test/verify.gd`（headless SceneTree），godot-mono 4.6.3 `--headless` 跑出 **VERIFY PASSED**（版本/地圖/HP/NPC/map image/wait/move/save-load 全綠）。
- 2026-06-02：**GUI 實機觀察 + 戰鬥 bug 修復**。建 `map_view.tscn` + 設 main_scene，godot-mono 開圖形視窗實玩（移動/等待/重開/存讀檔/攻擊皆正常）。修「撞 NPC 能傷敵但英雄不掉血」，實機診斷確認**雙重缺陷**：(1) **主因——hero 辨識選錯實體**：`npc_ai_system.cpp` 舊用 `view<Spatial>(exclude<NpcAi>)` 取首個非 NPC 有座標實體，但物品也符合（有 Spatial 無 NpcAi）；EnTT view 由 storage 尾端往前掃、真機物品建於英雄之後 → hero_ent 誤指向物品（無 HealthComponent）→ 攻擊打空、英雄永不掉血。改 `view<Spatial, Health>(exclude<NpcAi, Item>)` 以「有血量」唯一鎖定英雄。(2) **次因——行動機率閘門**擺在最前，連視野更新＋鄰接攻擊一併擋掉，使低 `move_chance` 弱怪短兵相接時常還不了手；重構為**視野每回合必更新、警覺且鄰接必定攻擊**，閘門下移只管移動。新增 `tests/src/test_npc_combat.cpp` 三案例（含「物品建於英雄之後」真機順序回歸）。ctest **39 cases、142 assertions 全綠**。
- 2026-06-02：**英雄辨識正規化（F6 補強，消除根因）**。新增 `HeroComponent` 空 tag（列入 `all_components.h`），`npc_ai_system` 改 `view<HeroComponent, SpatialComponent>` 正向辨識；gbind 建英雄時掛 tag、load 路徑改用它找回 `hero_entity_`。確立設計準則「辨識實體用正向 tag，不用排除法」於 `docs/decisions/01_entity_identification.md`。回歸測試補掛 tag + 新增空 tag 序列化 round-trip 案例。ctest **40 cases、146 assertions 全綠**，headless `verify.gd` 仍 `VERIFY PASSED`。
</content>
