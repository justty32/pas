# gamecore-zone 設計文件

> 狀態：初稿 v2  
> 日期：2026-06-03  
> 作者：brainstorming session

---

## 1. 目標定位

`derived/gamecore-zone/` 是 gamecore / medps **三層世界架構**中的**第三層——區域層（Area Layer，ZoneType::Area, z=3）**的實作。

三層對應關係（參照 `medps/work/design/zone_layers.md` + `gamecore/plans/002-world-structure.md`）：

| 層級 | medps ZoneType | gamecore 名稱 | 現有實作 |
|---|---|---|---|
| 1 | World (z=1) | 世界層 | mapcore_godot |
| 2 | Region (z=2) | 戰略層 | 尚未實作 |
| 3 | Area (z=3) | 區域層 | **本專案** |

區域層是玩家「進入某個地點」後切換到的 roguelike 格子戰術場景（一格 ≈ 數公尺）。

來源：從 `derived/opennefia-cpp/` Hard Fork，保留 ECS 核心、FOV、戰鬥邏輯，刪除 OpenNefia 特有機制。

---

## 2. 保留 / 刪除清單

### 保留
- ECS 核心（EnTT registry、EntityManager、SystemCtx）
- FOV 系統（Bresenham LOS）
- 戰鬥邏輯（HealthComponent、CombatStatsComponent 簡化版）
- 地圖網格（MapData、Tile）
- BSP 地城生成（MapGen）
- 多樓層機制
- NPC AI（wander + chase）
- Save/Load（cereal snapshot）
- GDExtension 綁定層（`gbind/`）
- HeroComponent 正向 tag 識別

### 刪除
- OpenNefia 原型系統（`core/prototypes/`、PrototypeManager、PrototypeId）
- Elona 屬性（CombatStatsComponent 中的 Elona 特有欄位）
- EventBus（`core/ecs/event_bus.*`）
- Locale 系統（`core/locale/`）
- CVar 系統（`core/cvar/`）
- AllComponents type_list（原型序列化不再需要）
- MetaDataComponent（原型系統殘留）
- yaml-cpp 依賴（無原型載入）
- ServiceContext（改由 ZoneContext 取代）

---

## 3. 目錄結構

```
derived/gamecore-zone/
├── PROJECT.md
├── CMakeLists.txt
├── src/
│   ├── core/
│   │   ├── ecs/          # EntityManager, SystemCtx
│   │   ├── components/   # Spatial, Health, NpcAi, Item, Hero, CombatStats
│   │   ├── systems/      # npc_ai, fov, combat, movement
│   │   ├── maps/         # MapData, Tile, MapGen（BSP）
│   │   └── serialize/    # save/load（cereal snapshot）
│   └── gbind/            # GDExtension 綁定層（ZoneWorld）
├── godot_zone/           # 獨立 Godot 專案（自己的 project.godot）
├── tests/
└── docs/
```

---

## 4. 核心架構

### ECS 層
- `EntityManager`：EnTT registry 薄殼，保留不動
- `SystemCtx`：系統執行上下文，保留不動
- **EventBus 刪除**：系統間溝通改直接函式呼叫；GDExtension 層直接 emit Godot signal

### 回合制：Actor Poll 模式

遊戲是**回合制**，採 poll 輪詢執行：每次 `advance_turn()` 時，從 registry 取出所有帶有 `ActorComponent` 的實體，依序對每個 actor 執行對應的系統邏輯。

```cpp
// 概念示意（非最終 API）
void advance_turn(ZoneContext& ctx) {
    auto view = ctx.registry.view<ActorComponent, SpatialComponent>();
    for (auto entity : view) {
        if (ctx.registry.all_of<HeroComponent>(entity)) {
            // 英雄行動由前端驅動（等待玩家輸入後才呼叫）
        } else if (ctx.registry.all_of<NpcAiComponent>(entity)) {
            npc_ai_system::tick(ctx, entity);
        }
    }
    fov_system::update(ctx);
}
```

**ActorComponent** 是新增的空 tag（仿 HeroComponent 模式），凡是「有行動資格」的實體（英雄、NPC）都掛此 tag；物品、地形等不掛。這讓系統不需排除法即可精確選取行動者。

> 與 medps 的對應：medps 的 `GlobalManager::tick()` 也是對特定 registry view 的 poll 迭代（`zone_layers.md:139`——「不需要 lister，view 本身就是 lister」）。

### ZoneContext（取代 ServiceContext）
只持有兩樣東西：
```cpp
struct ZoneContext {
    entt::registry registry;
    MapData map;
};
```
夠用即止，不再塞 locale / cvars / prototypes。

### Component 集合

| Component | 狀態 | 備註 |
|---|---|---|
| `SpatialComponent` | 保留 | 不動 |
| `HealthComponent` | 保留 | 不動 |
| `NpcAiComponent` | 保留 | 不動 |
| `ItemComponent` | 保留 | 不動 |
| `HeroComponent` | 保留 | 正向 tag，不用排除法 |
| `ActorComponent` | **新增** | 空 tag，標記「有行動資格」的實體（英雄/NPC）；poll 輪詢依此選取 |
| `CombatStatsComponent` | 重構 | 只留 `attack`、`base_hp`，拿掉 Elona 欄位 |
| `MetaDataComponent` | **刪除** | 原型系統殘留 |

### 依賴（CMake FetchContent）

| 函式庫 | 狀態 |
|---|---|
| EnTT | 保留 |
| cereal | 保留 |
| spdlog | 保留 |
| doctest | 保留 |
| godot-cpp | 保留 |
| yaml-cpp | **刪除** |

### CMake 建置目標
- `zone_core`：STATIC 靜態庫，godot-free 純 C++
- `zone_gd`：GDExtension `.so`（`-DZONE_BUILD_GDEXTENSION=ON`）

### GDExtension 主類別
`OpenNefiaWorld` → `ZoneWorld`（`Node` 子類別，持有 ZoneContext）

---

## 5. 命名規則

所有 `opennefia_*` 前綴改為 `zone_*`：

| 舊名 | 新名 |
|---|---|
| `opennefia_core` | `zone_core` |
| `opennefia_gd` | `zone_gd` |
| `OpenNefiaWorld` | `ZoneWorld` |
| `opennefia_world_gd.*` | `zone_world_gd.*` |
| `libopennefia_gd.so` | `libzone_gd.so` |

---

## 6. Godot 前端

獨立 Godot 專案（`godot_zone/`，自己的 `project.godot`），不整進 mapcore_godot。
暫時保留與 opennefia-cpp 類似的 `map_view.tscn` 結構，之後再依 gamecore 需求調整。

---

## 7. 待補充（使用者後續提出）

- [ ] 玩家控制介面設計（英雄行動如何由 Godot 前端驅動）
- [ ] Godot 前端取得資料的方式（poll snapshot vs. signal-driven）
- [ ] 是否需要新的 Component 對應 gamecore 語意（如勢力、區域 ID）
- [ ] 長期：NPC 生成資料來源（取代原型系統的方案）
- [ ] 跨層資料介面（暫緩，之後再議）

---

## 8. 實作起點

1. 複製 `derived/opennefia-cpp/` → `derived/gamecore-zone/`
2. 依刪除清單移除對應子目錄與檔案
3. 全域搜尋替換命名（`opennefia` → `zone`、`OpenNefia` → `Zone`）
4. 新增 `ActorComponent` 空 tag，英雄與 NPC 建立時掛上
5. 簡化 `CombatStatsComponent`
6. 刪除 `ServiceContext`，替換為 `ZoneContext`
7. 更新 CMakeLists.txt（移除 yaml-cpp、改目標名）
8. 跑 ctest 確認剩餘測試全綠
9. 建 GDExtension + headless verify
