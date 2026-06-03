# gamecore-zone 設計文件

> 狀態：初稿（待補充）  
> 日期：2026-06-03  
> 作者：brainstorming session

---

## 1. 目標定位

`derived/gamecore-zone/` 是 gamecore 三層架構中的**區域層（Zone Layer）**實作——玩家從世界層（mapcore_godot）進入某個地點時，切換到的 roguelike 格子戰術場景。

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

- [ ] 區域層與世界層的資料介面（ZoneWorld 如何接收 mapcore 傳入的地點資訊）
- [ ] 是否需要新的 Component 對應 gamecore 語意（如勢力、區域 ID）
- [ ] 長期：NPC 生成資料來源（取代原型系統的方案）
- [ ] 測試策略調整

---

## 8. 實作起點

1. 複製 `derived/opennefia-cpp/` → `derived/gamecore-zone/`
2. 依刪除清單移除對應子目錄與檔案
3. 全域搜尋替換命名（`opennefia` → `zone`、`OpenNefia` → `Zone`）
4. 簡化 `CombatStatsComponent`
5. 刪除 `ServiceContext`，替換為 `ZoneContext`
6. 更新 CMakeLists.txt（移除 yaml-cpp、改目標名）
7. 跑 ctest 確認剩餘測試全綠
8. 建 GDExtension + headless verify
