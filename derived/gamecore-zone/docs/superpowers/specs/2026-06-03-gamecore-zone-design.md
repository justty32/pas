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

## 7. 時間驅動 Actor Poll 構想（2026-06-03）

> 以下為使用者提出的設計方向，尚未實作。

> **⚠ 更新（2026-06-07）：單 hero 假設作廢，改走「出手順序表（order 表）」。**
> 起因：**玩家會同時操控多個角色**，世界裡沒有單一 hero。因此本節中所有「以 `hero_` 單一實體」為前提的細節已被取代：
> - ❌ **作廢**：`tick_actor(hero_, dt)` 先手 + `view<ActorComponent>(exclude<HeroComponent>)`、單一 `snapshot.hero.idle` 阻塞訊號、`step(cmd)` 立即套用到 hero。
> - ✅ **取代為**：`orders`（actor index 排列）+ 跨呼叫保存的續推游標；阻塞 = **任一玩家角色 idle 且無新指令**，迴圈停在該角色（`waiting_actor`）等指令；下令順序可選 **Initiative / PlayerFirst**（`stable_partition` 我方排前段）；打斷**非即時**（指令於迴圈掃到該角色的出手格才讀，故不需 `step(cmd)` 立即路徑）。
> - ✅ **仍然成立（本節的不變核心）**：玩家=「指令來源不同的 actor」、action 有 duration 且可被覆寫打斷、阻塞=idle 的自然狀態（C++ 不 spin）、`dt = min(剩餘, display_chunk)` 的步調節流規則（display_chunk 在 order 表下退化為「固定 1 回合」或「自動結算速度的計時器」）。
> - 真相層：對的版本見同目錄 **`turn-loop-example.cpp`**（多角色 order 表 + 可選排序 + 消費指令 + `waiting_actor` 聚焦訊號）。下方 7.x 單 hero 內文保留作設計脈絡，閱讀時以本 callout 與 example 為準。

### 核心概念：時間差驅動回合演繹

每次訪問 actor 時，不是以「整回合 / 半回合」的離散方式切換，而是丟入一個**經過時間（pass_time）**，讓 actor 自己依時間差決定能演繹多少狀態。

```
actor.tick(pass_time)
```

- 若相鄰兩次觀測的時間差 = 6 秒（一個基本單位），actor 可完整演繹一回合
- 若時間差 = 3 秒，actor 演繹半回合
- polling 間隔不必鎖死，彈性由 actor 自行消化

### 各層時間基本單位

| 層級 | ZoneType | 時間單位 | 對應節奏 |
|---|---|---|---|
| Area (z=3) | 區域層 | 1 秒 | 格子戰術（近距離動作） |
| Region (z=2) | 戰略層 | 1 分鐘 | 區域移動、事件 |
| World (z=1) | 世界層 | 1 小時 | 全局時局推進 |

### 核心抽象：玩家不是特例，只是「指令來源不同的 actor」

**所有 actor（玩家、NPC）共用同一套狀態與 tick 邏輯**，差別只有一處：行動結算後，下一個行動從哪來。

| | 進行中行動 | tick(dt) 消耗時間 | 行動結算後 |
|---|---|---|---|
| NPC | `OngoingAction` | 共用 | AI 自己挑下一個（自走） |
| 玩家 | `OngoingAction`（同上） | 共用（同上） | **不自挑，進入 idle，等外部指令** |

`HeroComponent` / `ActorComponent` 標籤的真正意義就在這裡：**標記「此 actor 的下一個行動由外部（Godot 輸入）供給，而非 AI」**。其餘 tick、時間消耗、效果結算全部共用同一份程式碼，沒有任何「玩家特判」。

進行中行動的狀態存在每個 actor 的 ECS component：

```cpp
struct OngoingActionComponent {
    Action   action;       // Attack / Cast(fireball) / Defend / Continue ...
    PassTime remaining;    // 剩餘時間，tick 時遞減；歸零＝結算
};
```

### 「阻塞」不是機制，是 snapshot 的自然狀態

世界推進只發生在 Godot 呼叫 `step()` 時。當玩家的進行中行動結算完、且無新指令，hero 進入 idle —— 這個 idle 狀態本身就是「世界阻塞、等玩家」的訊號，**不需要額外設計阻塞，C++ 也永遠不 spin 等待**。

```
snapshot = step(cmd?)        # cmd 有值＝換新行動（含打斷）；無值＝繼續進行中行動
if snapshot.hero.idle:       # 玩家行動剛結算完
    停止呼叫 step，等玩家輸入    # ← 這就是「世界阻塞」
else:                        # 玩家還在多回合行動中（remaining > 0）
    可自動續推，或接受打斷
```

---

#### C++ 端：純計算引擎（不傳 dt，C++ 自己算）

行動時長（攻擊 0.5t、詠唱 3t）是**遊戲邏輯**，由 C++ 擁有，Godot 不傳 `dt`。介面收斂成兩個：

```cpp
Snapshot ZoneWorld::step();               // 繼續（玩家無新輸入）
Snapshot ZoneWorld::step(PlayerCommand);  // 換新行動（含打斷進行中行動）
```

內部流程（**玩家恆先手**：先處理 hero，再迭代排除 hero 的 view）：

```cpp
Snapshot ZoneWorld::step(/* optional */ PlayerCommand cmd) {
    auto& reg = em_.registry();
    if (cmd) hero_set_action(cmd);       // 換行動／打斷（覆寫 OngoingActionComponent）
    PassTime dt = compute_dt();           // = min(hero 行動剩餘, display_chunk_)

    tick_actor(hero_entity_, dt);         // ← 玩家恆先手，先結算
    for (auto e : reg.view<ActorComponent>(entt::exclude<HeroComponent>))
        tick_actor(e, dt);               // 其餘 actor 隨後，同步消化相同 dt

    advance_clock(dt);
    return snapshot();
}
```

- **玩家恆先手**：`entt::exclude<HeroComponent>` 把 hero 從 view 排掉，hero 只在迴圈前被處理一次。先手是強制的，不靠 pool 迭代順序碰運氣。
- **新指令 = 打斷**：`hero_set_action()` 直接覆寫 `OngoingActionComponent`，舊行動（詠唱剩餘）自然取消。
- **同步時間**：所有 actor 在同一次 `step()` 消化相同的 `dt`。

#### 顯示分塊（`display_chunk_`）：動態可調的反應粒度

`dt = min(hero 行動剩餘, display_chunk_)`。其中 `display_chunk_` 是**步調 / UI 訴求**，由 Godot 隨時調整：

```cpp
void ZoneWorld::set_display_chunk(PassTime dt);   // Godot 轉的旋鈕
```

- 戰鬥緊張 → 調小（如 0.5t），反應窗口密
- 趕路 / 無威脅 → 調大（甚至 ∞），長行動一口氣跑完
- **關鍵鐵律**：分塊再大，玩家也不會被跳過 —— 迴圈只要 hero 一 idle 就回傳。`display_chunk_` 只控制「行動進行中」時的中途反應點密度，不影響「行動結束就停下問玩家」。

> **自然延伸（先記著，現在不做）**：大分塊可配「中斷條件」—— 平時大步快轉，敵人進視野 / HP 破門檻就自動把這步切短停下。即 roguelike 的「自動探索/休息，遇敵自動停」。趕路體驗時再長出來。

職責分界一句話：**行動時長 = C++ 擁有；顯示分塊 = Godot 可調；C++ 擁有的是 `min()` 這條規則本身。**

---

#### Godot 端：顯示 + 輸入收集

Godot 職責極簡：顯示最新快照、收集輸入、在適當時機呼叫 `step()`。

```
# Godot 側流程（概念）
var last_snapshot: Snapshot

func _process(_delta):
    render(last_snapshot)                  # 純顯示，不碰 C++

func _input(event):
    var cmd = build_cmd(event)             # 玩家任意時刻輸入
    if cmd:
        last_snapshot = zone_world.step(cmd)   # 換行動／打斷，立即觸發
        render(last_snapshot)

func _on_advance_timer():                  # ★ 獨立計時器（如每 1 秒），不綁渲染幀
    last_snapshot = zone_world.core_loop() # 推進世界；卡在某玩家角色時 C++ 內部即刻 return
    render(last_snapshot)
```

**推進與渲染解耦（2026-06-07）**：驅動 `core_loop` 的節拍由**獨立計時器**（例如每 1 秒一次）觸發，而非 `_process` 的每渲染幀。理由：世界推進的步調是玩法節奏（可慢可快、可暫停），不該被 FPS 綁定；渲染只負責把最新 snapshot 畫出來，兩者各走各的時鐘。
- 阻塞不靠前端判斷：`core_loop` 卡在某玩家角色（`waiting_actor`）時會即刻 return，故計時器每次無腦呼叫都安全。
- 計時器間隔 = 「多回合行動自動結算速度」的旋鈕（對應原 `display_chunk_` 的步調角色）：戰鬥放慢、趕路加快、玩家思考時可暫停計時器。
- 玩家輸入仍走 `_input` 即時收集，寫入 `player_instructions[waiting_actor]`；下次計時器觸發時被讀取。

---

#### 完整流程範例

```
[玩家看到地圖，敵人接近]

1. 玩家按攻擊（0.5t 基本動作）
   Godot → step(Attack)
   C++: hero_set_action(Attack); dt=min(0.5, chunk)=0.5
        tick(hero,0.5) 先結算攻擊 → tick(其餘,0.5) → 回傳
   snapshot.hero.idle == true → Godot 停手等輸入
   顯示：攻擊命中，敵人損血並移近 0.5t

2. 玩家按詠唱火球（3t）
   Godot → step(Cast(fireball))
   C++: OngoingAction=Cast(remaining=3); dt=min(3, chunk=1)=1
        tick 全體 1t → remaining=2 → 回傳
   snapshot.hero.idle == false → Godot 自動續推
   顯示：詠唱中（剩2），敵人又移近

3. 玩家無輸入（「繼續」）
   Godot → step()
   C++: dt=min(2,1)=1 → tick 全體 → remaining=1 → 回傳
   顯示：詠唱中（剩1），敵人即將攻擊！

4. 玩家按防禦（緊急打斷）
   Godot → step(Defend)
   C++: hero_set_action(Defend) 覆寫掉 Cast → dt=min(0.5,1)=0.5
        tick(hero,0.5) 先擋 → tick(其餘,0.5) → 回傳
   snapshot.hero.idle == true → 停手等輸入
   顯示：防禦成功，敵人攻擊被擋
```

### 決策定案（2026-06-03，部分於 2026-06-07 修訂為 order 表）
- ~~**玩家恆先手**：先處理 hero，再迭代 `view<ActorComponent>(exclude<HeroComponent>)`~~ → **改**：多角色無單一 hero；先手由 `orders` 排序決定（PlayerFirst 模式把我方排前段）。見 §7 開頭 callout 與 `turn-loop-example.cpp`。
- ✅ **狀態全在 C++**：進行中行動存 `OngoingActionComponent`，Godot 僅顯示 + 輸入
- ~~**阻塞 = snapshot.hero.idle**~~ → **改**：阻塞 = 任一玩家角色 idle 且無指令，迴圈停在 `waiting_actor`；C++ 仍不 spin。
- ✅ **打斷非即時**：指令於迴圈掃到該角色出手格才讀取生效（最多延遲一輪），不需 `step(cmd)` 立即路徑。
- ✅ **下令順序可選**：`OrderMode::Initiative`（依先攻穿插）/ `PlayerFirst`（我方排前段），由 `rebuild_orders()` 切換、`core_loop` 不變。
- ✅ **推進與渲染解耦**：驅動 `core_loop` 的節拍**不綁渲染幀**——獨立計時器（如每 1 秒）觸發推進，渲染走自己的 `_process`。詳見下方「Godot 端」。

### 待確認
- [ ] `PassTime` 型別：浮點秒 vs. 整數毫秒 vs. 固定分數回合（如 `Ratio<1,2>`）
- [ ] `Snapshot` 內容：精簡 view struct（推薦）vs. 整份 ECS dump
- [ ] `Action` 的列舉/多型設計：enum + 參數？還是 variant？多回合行動的「結算」與「逐 tick 效果」如何分離
- [ ] NPC 行動結算後的「自挑下一個」：在 `tick_actor` 內部完成（單次 step 可能跑多個 NPC 子行動）
- [ ] 跨層時間轉換：從 World 進入 Area 時如何同步時間基準
- [ ] NPC 累積未演繹時間的上限（防止長時間離線後 NPC 爆炸行動）

---

## 8. 其他待補充

- [ ] Godot 前端取得資料的方式（poll snapshot vs. signal-driven）
- [ ] 是否需要新的 Component 對應 gamecore 語意（如勢力、區域 ID）
- [ ] 長期：NPC 生成資料來源（取代原型系統的方案）
- [ ] 跨層資料介面（暫緩，之後再議）

---

## 9. 實作起點

1. 複製 `derived/opennefia-cpp/` → `derived/gamecore-zone/`
2. 依刪除清單移除對應子目錄與檔案
3. 全域搜尋替換命名（`opennefia` → `zone`、`OpenNefia` → `Zone`）
4. 新增 `ActorComponent` 空 tag，英雄與 NPC 建立時掛上
5. 簡化 `CombatStatsComponent`
6. 刪除 `ServiceContext`，替換為 `ZoneContext`
7. 更新 CMakeLists.txt（移除 yaml-cpp、改目標名）
8. 跑 ctest 確認剩餘測試全綠
9. 建 GDExtension + headless verify
