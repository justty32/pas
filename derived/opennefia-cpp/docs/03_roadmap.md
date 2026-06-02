# 03 — 核心階段路線圖

> 只規劃 **godot-free 核心**。前端（Godot 綁定 / 渲染 / UI / 輸入 / 音效）是核心穩定後的另一條路線，本文末尾僅列為「未來」。
> 每個 Phase 的「完成判準」對應 `PROJECT.md` §5 的整體完成定義。

---

## Phase 0 — 構建骨架（編譯邊界先立起來）✅ 完成 2026-06-01

**目標**：一個能編譯、能跑空測試的雙目標 CMake 專案，核心目標**不連任何前端庫**。

- [x] `CMakeLists.txt`：仿 `medps/CMakeLists.txt`——`opennefia_core`（STATIC）；`GLOB_RECURSE src/` 並排除 `/gbind/`；C++20；選用旗標 `OPENNEFIA_BUILD_GDEXTENSION`（預設 OFF）。
- [x] vendoring（FetchContent）：EnTT v3.16.0、cereal v1.3.2、spdlog v1.14.1、doctest v2.4.11。yaml-cpp 延至 Phase 2（0.8.0 與 CMake 4.0+ 不相容，待升版）。
- [x] 測試框架接上（doctest），`version()` smoke test 綠燈（1/1 PASS，0.08s）。

**判準**：✅ `cmake --build` 產出 `opennefia_core.lib`，編譯單元無任何前端 / godot include。

> **注意**：yaml-cpp 0.8.0 在 CMake 4.0+ 下以 `cmake_minimum_required(VERSION 2.8.12)` 報錯。CMakeLists.txt 已用 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 相容 doctest 舊宣告；yaml-cpp 本身延後至 Phase 2 再換版本引入。

---

## Phase 1 — ECS 地基 ✅ 完成 2026-06-01

**目標**：registry + 基礎 component + 自由函式系統 + 事件匯流排能跑。

- [x] `core/util/`：`Vector2i`、`ResourcePath`。
- [x] `core/ecs/`：薄 `EntityManager`（`entt::registry` + 系統 vector + `tick()`）；`SystemCtx`（Phase 1：只有 `EventBus&`）；`EventBus`（定向 void* 抹除 + `entt::dispatcher` 廣播）。
- [x] `core/services/`：`ServiceContext`（Phase 1：spdlog logger；預設 null logger）。
- [x] `core/components/`：`MetaDataComponent`（proto_id + is_alive）、`SpatialComponent`（x/y + parent entity；serialize 預留 Phase 3）。
- [x] 系統註冊：明確 vector + 順序執行的 `tick()`（仿 `medps/global_manager.cpp:130`）。
- [x] **事件匯流排**：void* 類型抹除的定向 `raise_local` + `entt::dispatcher` 廣播。

**判準**：✅ 8 test cases，20 assertions 全綠（system 訂閱 + 發送定向事件 + handler 修改 component）。

> **注意**：doctest v2.4.11 在 MSVC 2022 中需要 `DOCTEST_CONFIG_USE_STD_HEADERS`（讓 doctest 用完整 `<sstream>` 取代前向宣告，避免 `string_view` 的 `operator<<` 因 ostream 不完整而報錯）。已寫入 `tests/CMakeLists.txt`。

---

## Phase 2 — 原型系統（資料驅動）✅ 完成 2026-06-01

**目標**：YAML → 記憶體原型 → `SpawnEntity`。

- [x] `PrototypeId<T>` 強型別 id（`EntityProtoId = PrototypeId<EntityPrototypeTag>`）。
- [x] `PrototypeManager`：`load_file` → `resolve_inheritance`（拓撲排序 + component flat merge）→ `spawn / apply_to`。
- [x] yaml-cpp 載入器：`ComponentLoader = std::function<void(registry&, entity, Node&)>` 顯式登錄（零反射）。
- [x] `EntityManager::spawn(proto_id, pm)` 便利包裝（forward decl 避免循環依賴）。
- [x] `data/test_prototypes.yaml`：3 層繼承（BaseEntity → BaseChara → Putit/EliteWarrior）+ 獨立 SimpleItem。

**判準**：✅ 20 test cases / 70 assertions 全綠（繼承解析、值覆蓋、spawn component 正確性）。

> **關鍵坑**：
> 1. yaml-cpp `for (const auto& x : node)` 回傳 `YAML::detail::iterator_value`，MSVC 多載解析偏向 `template operator=<T>` 而不是 copy assignment，改用 `root[i]` index 存取。
> 2. `YAML::Node` map copy 只 copy handle（共享底層 `detail::node`），子原型的 `operator=` 會呼叫 `set_ref` 污染所有共享 handle。修正：繼承 merge 時用 `YAML::Clone` 確保節點獨立。

---

## Phase 3 — 序列化 / 存讀檔（移植 medps 三件套）✅ 完成 2026-06-01

**目標**：整張地圖 snapshot 存檔 → 還原，round-trip 正確。

- [x] `serialize/all_components.h`：`AllComponents = entt::type_list<MetaDataComponent, SpatialComponent>` 單一來源。
- [x] `serialize/entt_cereal_archive.h`：entt↔cereal adapter（直接移植 medps）。
- [x] `serialize/save_load.h`：fold expression snapshot / loader（移植 medps zone_io.h）；三層 API（stream / path / SaveStore）。
- [x] `SpatialComponent` 換成 `save()/load()` split（parent entt::entity → raw int round-trip）。
- [x] 存檔後端：`save_store.h` `SaveStore` 抽象 + `FolderSaveStore` 實作（string slot name 取代 ZoneKey，仿 medps zone_store.h）。

**判準**：✅ 29 test cases / 95 assertions 全綠（stream round-trip、parent entity 引用、is_alive、空 registry、無 Spatial entity、檔案 API、FolderSaveStore 存取）。

> **坑記錄**：
> 1. `entt::entity == entt::null_t` 在 doctest `CHECK()` 中與 EnTT template operator== 歧義 → 先求值成 `bool` 再 `CHECK`。
> 2. cereal 序列化 `std::string` 需 `<cereal/types/string.hpp>`（沒有 include 時 cereal static_assert 報「找不到序列化函式」）→ 加入 `save_load.h`。

---

## Phase 4 — 地圖邏輯 + 最小遊戲循環骨幹 ✅ 完成 2026-06-01

**目標**：把前三者串成「可推進的世界」（仍無圖形）。

- [x] `core/maps/tile.h`：`Tile { terrain, flags }`；`TILE_WALKABLE / TILE_BLOCKS_SIGHT` 旗標（仿 medps area_terrain.h）。
- [x] `core/maps/map_data.h`：`MapData { width, height, vector<Tile> }`；`at(x,y) / get(x,y) / in_bounds`；稠密網格在單一「地圖實體」上，可移動演員是獨立 entity（仿 medps Rimworld-style 設計）。
- [x] `AllComponents` 加入 `MapData`；`save_load.h` 加入 `<cereal/types/vector.hpp>`。
- [x] 實體佈局：`SpatialComponent` + 可走性判斷系統（tick 時向右移動，碰牆停下）。
- [x] 回合 / tick 骨幹：`EntityManager::add_system + tick()`（Phase 1 已在，本階段串接地圖邏輯）。
- [x] 多 registry 評估：Elona 地圖規模無需 zone streaming，維持單 registry；序列化路徑已仿 medps，未來可平滑擴張。

**判準**：✅ 36 test cases / 139 assertions 全綠。
整合測試覆蓋：原型生成 → 地圖可走性設定 → tick 3 回合（牆阻擋正確）→ save → 清空 → restore → 驗證 hero 座標 + 地圖 tile 旗標 ≡ PROJECT.md §5 完成定義。

---

## F1 — GDExtension 工具鏈 + Smoke Test ✅ 完成 2026-06-02

**目標**：建 `gbind/`（仿 medps），`opennefia_gd` GDExtension 目標，工具鏈端到端打通。

- [x] `src/gbind/opennefia_core_gd.h/.cpp`：`OpenNefiaCore : RefCounted`，暴露 `version()` → 呼叫核心 `opennefia::version()`。
- [x] `src/gbind/register_types.h/.cpp`：GDExtension 進入點 `opennefia_library_init`，`MODULE_INITIALIZATION_LEVEL_SCENE` 層級註冊。
- [x] `CMakeLists.txt` 已有 `OPENNEFIA_BUILD_GDEXTENSION=ON` 開關，`add_subdirectory(godot-cpp)` + `target_link_libraries(opennefia_gd PRIVATE opennefia_core godot-cpp)`。
- [x] `godot_test/opennefia.gdextension`：entry_symbol + compatibility_minimum 4.4。
- [x] `godot_test/bin/opennefia_gd.dll`（1.4 MB）已產出。
- [x] `godot_test/smoke_test.gd`：`OpenNefiaCore.new().version()` 呼叫腳本。

**判準**：✅ `cmake --build --target opennefia_gd` 通過，`opennefia_gd.dll` 產出。Godot 端載入驗證待手動開啟 godot_test/ 確認（見下方說明）。

> **godot-cpp 版本**：4.4（`projects/godot-cpp`），`gdextension/extension_api.json` 預設 4.5 API。CMakeLists.txt 已以 `GODOT_CPP_DIR` 指向本地 checkout，不走 FetchContent。

> **驗證步驟**：用 Godot 4.4+ 開啟 `godot_test/`，將 `smoke_test.gd` 掛在場景根節點執行，確認主控台印出 `opennefia core version: 0.0.1-alpha` 及 `smoke test PASSED`。

---

## 未來

- **F2 渲染**：Godot TileMapLayer 畫 tile 層；Sprite2D / MultiMesh 畫實體；FOV overlay。
- **F3 UI**：Godot Control / .tscn 取代 Wisp（**不移植 XAML**）；UI 邏輯（顯示什麼 / 觸發什麼）仍在核心。
- **F4 輸入 / 音效**：Godot InputMap action ↔ 核心指令；AudioStreamPlayer 接核心音效事件。

---

## 風險與待決

- **事件匯流排定向派發的效能 / 設計**：OpenNefia 比 medps 多這塊，需自行設計並驗證——本路線最大的「新東西」。
- **原型繼承合併的複雜度**：OpenNefia 的原型繼承 + YAML 巢狀需仔細處理依賴排序。
- **多 registry 與否**：Elona 規模未必需要 medps 的 zone streaming；決策延到 Phase 4，但介面預留。
- **vendoring 策略**：extern/ 直接 clone vs FetchContent——Phase 0 決定（參 medps 把 godot-cpp 放 `projects/`、entt 放 extern/ 的做法）。
</content>
