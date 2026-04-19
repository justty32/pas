# 主教學：打造 GDExtension 後端的回合制 RPG 前端

> 本文是給實作者的完整施工指南。
> 架構決策已定案，按照本文的順序與規格實作即可。
> 詳細規格見同目錄的 `01_extraction_and_modification_guide.md` 與 `02_frontend_design.md`。

---

## 專案定位

仿照 **Tales of Maj'Eyal (ToME)** 的設計哲學：

- **後端（GDExtension / C++）**：擁有所有遊戲狀態，自行跑邏輯迴圈，把結果以事件形式推給前端。
- **前端（GDScript / Godot 4）**：純粹的顯示層與輸入層，等後端說「你可以動了」再接受玩家輸入。
- 兩端唯一的契約：三個方法 + 一份事件定義 + 一份 `visual_key` 命名清單。

參考素材：`projects/godot-open-rpg`（GDQuest 的 Godot 4.5 回合制 RPG 示範）。

---

## 一、從 godot-open-rpg 提取的素材

### 直接複製，幾乎不改

| 來源檔案 | 用途 |
| :--- | :--- |
| `src/field/gameboard/gameboard.gd` | 格子座標系統（Autoload） |
| `src/field/gameboard/gameboard_properties.gd` | 格子尺寸/邊界 |
| `src/field/gameboard/gameboard_layer.gd` | TileMapLayer 擴充（阻擋格判斷） |
| `src/field/gameboard/pathfinder.gd` | AStar2D 包裝（初期前端用，之後可移入後端） |
| `src/field/gamepieces/gamepiece_registry.gd` | 格子 ↔ Gamepiece 映射（Autoload） |
| `src/field/gamepieces/animation/gamepiece_animation.gd` | 動畫播放 |
| `src/common/directions.gd` | 四向枚舉與向量映射 |
| `src/common/screen_transitions/` | 畫面轉場（Autoload） |
| `src/common/music/` | 音樂播放（Autoload） |
| `src/field/gameboard/debug/` | 除錯工具 |

### 改造後使用

| 原始檔案 | 改造方向 |
| :--- | :--- |
| `src/field/gamepieces/gamepiece.gd` | 移除 `Path2D` 連續移動；改為 Tween 跳格 + `await` |
| `src/field/field_events.gd` | 整合為新的 `DisplayAPI`（signal bus 模式保留） |

### 完全丟棄（邏輯移入後端）

`combat.gd`、`combat_arena.gd`、`battler*.gd`、`combat_ai_random.gd`、Dialogic、`cutscene*.gd`、`trigger*.gd`、`inventory.gd`、`path_loop_ai_controller.gd`

---

## 二、前端元件清單與職責

### Autoloads（全域服務，開機即存在）

| 名稱 | 職責 | 來源 |
| :--- | :--- | :--- |
| `GameEngine` | GDExtension 後端單例，前端的唯一通信對象 | GDExtension 提供 |
| `DisplayAPI` | 每幀呼叫 `GameEngine.tick()`，把事件派發給各元件 | 新建 |
| `InputHandler` | 捕捉輸入，在輪到玩家時組裝 `PlayerAction` 送後端 | 新建 |
| `VisualRegistry` | `visual_key → 場景/圖磚` 查找表，純前端資料 | 新建 |
| `Gameboard` | 格子座標系統（從 godot-open-rpg 複製） | 複製改造 |
| `GamepieceRegistry` | entity_id / 格子 ↔ Gamepiece 節點映射 | 複製改造 |
| `Transition` | 畫面轉場 | 複製 |
| `Music` | 背景音樂 | 複製 |

### 場景節點

```
GameWorld (主場景)
  MapDisplay
    TerrainLayer      ← TileMapLayer：地板/牆/門
    EntityLayer       ← Node2D：所有 Gamepiece 節點
    EffectLayer       ← Node2D：粒子/Shader 特效
    FogLayer          ← TileMapLayer：FOV 視野霧
  Camera2D

HUD (CanvasLayer，永遠在最上層)
  MessageLog          ← 訊息日誌（MUD 風格文字）
  StatusPanel         ← HP/MP/狀態效果列
  HotkeyBar           ← 技能快捷鍵
  MiniMap             ← 小地圖（可選）

UIManager (CanvasLayer，Modal 層)
  InventoryDialog     ← 物品欄（純前端，需資料時呼叫 query）
  CharacterDialog     ← 角色面板
  SpellbookDialog     ← 法術書
```

---

## 三、後端接口（GDExtension 必須實作）

GDExtension 暴露一個名為 `GameEngine` 的 Autoload Node，**只需實作三個方法**：

```
GameEngine.tick(delta: float) -> Array[GameEvent]
  每幀由前端呼叫。後端推進邏輯，回傳本幀積累的所有事件。
  無事發生時回傳空陣列。

GameEngine.submit_action(action: PlayerAction) -> void
  玩家做了動作時呼叫。後端非同步處理，結果以後續的 tick() 事件回傳。

GameEngine.query(request: QueryRequest) -> QueryResult
  純資料查詢，不影響遊戲邏輯，不消耗時間。
  用於前端需要顯示後端計算結果的場合（物品描述、法術傷害預覽等）。
```

---

## 四、事件定義（`GameEvent`）

後端透過 `tick()` 回傳的事件清單。每種事件只帶「前端顯示所需的視覺提示」，不含完整遊戲狀態。

| 事件類型 | 觸發時機 | 關鍵欄位 |
| :--- | :--- | :--- |
| `TERRAIN_CHANGED` | 地形改變（門開關、牆被炸） | `cell`, `tile_id` |
| `FOV_UPDATE` | 視野更新 | `visible[]`, `remembered[]` |
| `ENTITY_SPAWN` | 實體出現 | `entity_id`, `cell`, `visual_key`, `direction`, `layer` |
| `ENTITY_REMOVE` | 實體消失 | `entity_id` |
| `ENTITY_MOVE` | 實體移動 | `entity_id`, `from_cell`, `to_cell` |
| `ENTITY_FACE` | 實體轉向 | `entity_id`, `direction` |
| `ENTITY_ANIMATE` | 播放動畫 | `entity_id`, `animation`, `wait` |
| `EFFECT_AT` | 播放位置特效 | `cell`, `effect_key`, `duration` |
| `PROJECTILE_LAUNCH` | 發射投射物視覺 | `from_cell`, `to_cell`, `visual_key`, `speed` |
| `LOG_MESSAGE` | 文字訊息 | `text`（支援 BBCode）, `category` |
| `STATS_UPDATE` | 玩家數值更新 | `data: Dictionary`（只送有變化的欄位） |
| `PLAYER_TURN` | 現在輪到玩家 | `force: bool`（true = 立即解鎖；false = 等當前動畫完成再解鎖） |
| `MAP_ENTER` | 進入新地圖 | `map_id`, `player_cell`, `map_width`, `map_height` |

### visual_key / tile_id / effect_key 命名約定

後端送出的識別名必須在前端的 `VisualRegistry` 中有對應項目。
命名用蛇形：`&"goblin_warrior"`、`&"wall_stone"`、`&"explosion_fire"`。
前後端各自維護，雙方共同遵守同一份命名清單（放在專案根目錄的 `visual_keys.md`）。

---

## 五、玩家動作定義（`PlayerAction`）

```
PlayerAction.type 的枚舉值：
  MOVE          direction: Vector2i（鄰格方向）
  WAIT          （無參數，跳過回合）
  ATTACK        direction: Vector2i
  USE_SKILL     skill_id: int, target_cell: Vector2i
  INTERACT      direction: Vector2i（與鄰格物件互動）
  USE_ITEM      item_index: int
  PICKUP        （撿起腳下物品）
  DROP          item_index: int
  DESCEND       （下樓）
  ASCEND        （上樓）
  REQUEST_TURN  （玩家請求插隊行動，後端決定是否允許）
```

### `REQUEST_TURN` 說明

玩家角色速度可能很慢，輪到玩家前可能先看多輪 NPC 行動。
此時玩家若按下任意遊戲鍵，前端送出 `REQUEST_TURN`，後端決定是否在此時機讓玩家插隊。
若後端同意，回傳 `PLAYER_TURN`（可帶 `force=true` 立即打斷動畫）；若不同意則忽略。

---

## 六、前端元件的接線規則

所有前端元件**只 connect `DisplayAPI` 的 signal，不互相 reference**。

```
DisplayAPI 的 signal 清單：
  terrain_changed(event)      → MapDisplay 監聽
  fov_updated(event)          → MapDisplay 監聽
  entity_spawned(event)       → MapDisplay 監聽
  entity_removed(event)       → MapDisplay 監聽
  entity_moved(event)         → MapDisplay 監聽
  entity_faced(event)         → MapDisplay 監聽
  entity_animated(event)      → MapDisplay 監聽
  effect_requested(event)     → MapDisplay 監聽
  projectile_requested(event) → MapDisplay 監聽
  message_logged(event)       → MessageLog 監聽
  stats_updated(event)        → StatusPanel 監聽
  player_turn_started()       → InputHandler 監聽（解鎖輸入）
  map_entered(event)          → MapDisplay + MapManager 監聽
```

---

## 七、`Gamepiece` 節點規格

前端地圖上每個實體（NPC、玩家、物品）都是一個 `Gamepiece` 節點。

**繼承**：`Node2D`（不是 `Path2D`）

**必要屬性**：
- `entity_id: int`：對應後端的實體 ID
- `animation: GamepieceAnimation`：動畫子節點（從 godot-open-rpg 複製）
- `direction: Directions.Points`：面向（setter 會更新動畫）

**必要方法**：
- `move_to_cell(cell: Vector2i) -> void`：Tween 動畫移動到目標格，用 `await` 等完成
- `play_animation(name: StringName) -> void`：播放動畫，`wait` 為 true 時可 `await`

**生命週期**：
- 由 `MapDisplay._on_entity_spawned()` 建立
- 由 `MapDisplay._on_entity_removed()` 播死亡動畫後移除
- 建立時自動向 `GamepieceRegistry` 登記

---

## 八、雙層地圖系統

遊戲有兩種地圖模式：

**世界地圖（WorldMap）**：大地圖，每格代表一個地區。  
**局部地圖（LocalMap）**：進入地區後的詳細地圖（城鎮、地牢樓層）。

切換觸發：後端送出 `MAP_ENTER` 事件 → 前端 `MapManager` 負責切換場景。

```
MapManager（Autoload）
  switch_to(map_id, player_cell)
    → 播轉場效果
    → 若 map_id == "world"：顯示 WorldMap，隱藏 LocalMap
    → 否則：載入 res://maps/local/<map_id>.tscn 到 LocalMap
    → 更新 Gameboard.properties（格子尺寸可能不同）
    → 清空所有 Gamepiece，等後端送 ENTITY_SPAWN 重建
```

---

## 九、輸入鎖設計

前端在任何時候都不應假設「現在輪到玩家」，完全由後端的 `PLAYER_TURN` 事件決定。

```
初始狀態：InputHandler._can_act = false（鎖定）

玩家按下任意遊戲鍵：
  ├─ _can_act = true  → 正常送行動 → _can_act = false → 等待下一個 PLAYER_TURN
  └─ _can_act = false → 送 REQUEST_TURN → 後端決定是否理會
                          ├─ 後端同意 → 回傳 PLAYER_TURN（見下方解鎖流程）
                          └─ 後端不同意 → 忽略，繼續等

收到 PLAYER_TURN（force=false）→ 等當前動畫序列播完 → _can_act = true
收到 PLAYER_TURN（force=true） → 立即清空動畫佇列  → _can_act = true
```

純 UI 操作（開物品欄、翻頁）：不需要 `_can_act == true`，隨時可用。
純資料查詢（開啟角色面板）：呼叫 `GameEngine.query()`，不影響 `_can_act`。

---

## 十、實作 Milestone

### M1：靜態地圖，玩家可移動

- [ ] 複製 `gameboard/`、`gamepiece_registry.gd`、`directions.gd` 到新專案
- [ ] 建立改造版 `Gamepiece`（Tween 移動）
- [ ] 建立 `DisplayAPI` autoload（signal bus）
- [ ] 建立 `InputHandler` autoload
- [ ] 建立 `VisualRegistry` autoload（先寫幾個 key）
- [ ] 建立 `MapDisplay` 場景，監聽 `DisplayAPI` signals
- [ ] 用 **GDScript mock** 版 `GameEngine` 測試流程：
  - `tick()` 回傳 `ENTITY_SPAWN`（玩家）＋ `PLAYER_TURN`
  - 玩家按 WASD → `submit_action(MOVE)` → `tick()` 回傳 `ENTITY_MOVE`
- [ ] **驗收**：玩家可在地圖上一格一格移動，每次移動後等 `PLAYER_TURN`

### M2：訊息日誌 + 狀態列

- [ ] 建立 `MessageLog` 節點，監聽 `message_logged`
- [ ] 建立 `StatusPanel` 節點，監聽 `stats_updated`
- [ ] mock `GameEngine` 在玩家移動後送 `LOG_MESSAGE`（"你往北走了一步"）
- [ ] **驗收**：移動後訊息出現在日誌，HP 條顯示正確

### M3：視野霧（FOV）

- [ ] 建立 `FogLayer`（TileMapLayer），全圖初始為黑
- [ ] `DisplayAPI.fov_updated` → 更新可見格（透明）/ 已探索格（半透明）/ 未知格（黑）
- [ ] mock `GameEngine` 回傳玩家周圍 5 格為 `visible`
- [ ] **驗收**：玩家只看得到周圍範圍，走過的地方變暗

### M4：NPC 與多實體

- [ ] 接 GDExtension：`tick()` 回傳 NPC 的 `ENTITY_SPAWN` + `ENTITY_MOVE`
- [ ] `MapDisplay` 正確建立 NPC Gamepiece 並移動
- [ ] **驗收**：玩家移動後，NPC 也跟著移動（全部動畫同步播放）

### M5：特效與投射物

- [ ] 建立 `EffectLayer`
- [ ] 實作 `EFFECT_AT` 播放粒子特效
- [ ] 實作 `PROJECTILE_LAUNCH` 播放飛行動畫
- [ ] 攻擊動作：`ENTITY_ANIMATE(attack, wait=true)` → 等動畫 → `ENTITY_ANIMATE(hurt, wait=false)` 對敵人
- [ ] **驗收**：玩家攻擊，看到攻擊動畫與受擊動畫，死亡後 Gamepiece 消失

### M6：物品欄 UI + 查詢接口

- [ ] 建立 `InventoryDialog`（純前端，不消耗時間）
- [ ] 開啟時呼叫 `GameEngine.query(INVENTORY)` 取得物品清單顯示
- [ ] `USE_ITEM` 送出 `PlayerAction` → 接收 `LOG_MESSAGE` + `STATS_UPDATE`
- [ ] **驗收**：開物品欄不暫停時間，使用物品後 HP 條更新

### M7：雙層地圖切換

- [ ] 建立 `MapManager` autoload
- [ ] 接 `MAP_ENTER` 事件 → 切換 WorldMap / LocalMap
- [ ] **驗收**：在世界地圖走到城鎮格，畫面切換到城鎮內部

---

## 十一、給後端開發者的最小接口清單

如果你是後端（GDExtension）開發者，你只需要：

1. 暴露 `GameEngine` Node（Autoload）實作上述三個方法
2. 使用前端定義的 `GameEvent` 類別格式
3. 使用前端定義的 `PlayerAction` 類別格式
4. 遵守 `visual_keys.md` 中的命名清單

前端不需要你暴露任何其他東西。
