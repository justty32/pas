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

## Phase 1 — ECS 地基

**目標**：registry + 基礎 component + 自由函式系統 + 事件匯流排能跑。

- [ ] `core/util/`：Vector2i、ResourcePath 等（翻新自既有骨架）。
- [ ] `core/ecs/`：薄 `EntityManager`（封裝 `entt::registry`，提供 `SpawnEntity` 佔位）、`ServiceContext`、`SystemCtx`。
- [ ] `core/components/`：`MetaDataComponent`、`SpatialComponent`（座標 + 父子）。
- [ ] **事件匯流排**（本專案重點，medps 沒有）：`entt::dispatcher` 包廣播；自製定向 `EventBus`（`RaiseLocalEvent(entity, ev)` + 明確 `Subscribe`）。
- [ ] 系統註冊：明確 vector + 順序執行的 `tick()`（仿 `global_manager.cpp:130`）。

**判準**：一個示範系統訂閱事件、發送定向事件、修改 component，測試驗證。

---

## Phase 2 — 原型系統（資料驅動）

**目標**：YAML → 記憶體原型 → `SpawnEntity`。

- [ ] `PrototypeId<T>` 強型別 id。
- [ ] `PrototypeManager`：多型別存放 + `parent` 繼承合併（依賴圖排序）。
- [ ] yaml-cpp 載入器：把 YAML 節點映射成原型的 component 清單。
- [ ] `EntityManager::SpawnEntity(protoId)`：依原型 emplace component。

**判準**：從 `data/` 的範例 YAML（如一個角色 + 一個物品原型，含繼承）spawn 出帶正確 component 的實體。

---

## Phase 3 — 序列化 / 存讀檔（移植 medps 三件套）

**目標**：整張地圖 snapshot 存檔 → 還原，round-trip 正確。

- [ ] `serialize/all_components.h`：`AllComponents` type_list 單一來源。
- [ ] `serialize/entt_cereal_archive.h`：entt↔cereal adapter（仿 `medps/.../entt_cereal_archive.h`）。
- [ ] `serialize/save_load.h`：fold expression snapshot / loader（仿 `medps/.../zone_io.h`）。
- [ ] 每個 component 的 cereal `serialize()`（POD 慣例）。
- [ ] 存檔後端：先 `FolderZoneStore` 式單檔；介面留可換（medps `zone_store.h`）。

**判準**：建一張地圖（tile 網格 component + 數個實體）→ 存 → 清空 → 載 → 狀態一致。

---

## Phase 4 — 地圖邏輯 + 最小遊戲循環骨幹

**目標**：把前三者串成「可推進的世界」（仍無圖形）。

- [ ] `core/maps/`：`MapData` 帶 `tdarray<Tile>` 稠密網格 component（仿 `area_terrain.h`）；`Tile` 含可走 / 擋視線 flags。
- [ ] 實體佈局：在地圖上 spawn / 移動實體（`SpatialComponent`）。
- [ ] 回合 / tick 骨幹：`update()` 跑註冊系統一輪（驅動者是測試）。
- [ ] 是否需要多 registry / streaming：依 Elona 地圖規模評估——初版單 / 少數 registry 即可，但序列化路徑已照 medps，可平滑擴張。

**判準**：跑一段「載入原型 → 生成地圖與角色 → tick N 回合 → 存檔 → 還原」的整合測試，綠燈。達成即等同 `PROJECT.md` §5 完成定義。

---

## 未來（核心穩定後，另開路線，本階段不做）

- **F1 前端綁定**：建 `gbind/`（仿 medps），`opennefia_gd` GDExtension 目標，把核心狀態 / 事件以 POD 橋接給 Godot。
- **F2 渲染**：Godot TileMapLayer 畫 tile 層；Sprite2D / MultiMesh 畫實體；FOV overlay。
- **F3 UI**：Godot Control / .tscn 取代 Wisp（**不移植 XAML**）；UI 邏輯（顯示什麼 / 觸發什麼）仍在核心。
- **F4 輸入 / 音效**：Godot InputMap action ↔ 核心指令；AudioStreamPlayer 接核心音效事件。

> 前端方向確定為 Godot 4 GDExtension（與 medps 一致，raylib 已棄），但細節待核心完成後再規劃。

---

## 風險與待決

- **事件匯流排定向派發的效能 / 設計**：OpenNefia 比 medps 多這塊，需自行設計並驗證——本路線最大的「新東西」。
- **原型繼承合併的複雜度**：OpenNefia 的原型繼承 + YAML 巢狀需仔細處理依賴排序。
- **多 registry 與否**：Elona 規模未必需要 medps 的 zone streaming；決策延到 Phase 4，但介面預留。
- **vendoring 策略**：extern/ 直接 clone vs FetchContent——Phase 0 決定（參 medps 把 godot-cpp 放 `projects/`、entt 放 extern/ 的做法）。
</content>
