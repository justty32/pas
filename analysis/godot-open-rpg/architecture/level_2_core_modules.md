# Level 2 — 核心模組職責（Core Modules & Responsibilities）

> 目標：逐一展開三大支柱（`field`, `combat`, `common`）的入口檔案、類別責任與彼此關係；並追蹤一條完整的「觸發戰鬥」事件流。
> 分析日期：2026-04-18

---

## 1. 全域事件匯流排 (Signal Buses)

整個專案的「控制反轉」核心是兩個 autoload 事件匯流排。任何子系統都只 emit/connect 這些 signal，彼此不互相持有引用。

### 1.1 `FieldEvents` — `src/field/field_events.gd`

| Signal | 用途 |
| :--- | :--- |
| `cell_highlighted(cell)` | 游標移動到某格 |
| `cell_selected(cell)` | 玩家點擊某格 |
| `interaction_selected(interaction)` | 玩家選中一個 Interaction（如 NPC）|
| `combat_triggered(arena)` | 【關鍵】場景態 → 戰鬥態的唯一管道 |
| `cutscene_began` / `cutscene_ended` | 過場動畫開始 / 結束 |
| `input_paused(is_paused)` | 暫停/恢復整個 field 狀態的輸入（由戰鬥、對話、過場觸發） |

> `field_events.gd:6` 設 `PROCESS_PRIORITY = 99999999`，確保此 manager 的 `_process` 在所有 Gamepieces/Controllers 之後執行，避免一幀內狀態錯亂。

### 1.2 `CombatEvents` — `src/combat/combat_events.gd`

| Signal | 用途 |
| :--- | :--- |
| `combat_initiated(arena)` | 戰鬥視覺就緒（螢幕已全黑） |
| `combat_finished(is_player_victory)` | 戰鬥結束（螢幕已黑，結果已知） |
| `player_battler_selected(battler)` | 輪到某位玩家 Battler 選擇行動 |

---

## 2. `src/field/` — 場景 / 探索狀態

### 2.1 入口：`field.gd`

見 `src/field/field.gd`。`Field` 是 **Node2D**，不是 autoload。它是主場景的根節點，負責：

1. 動態掛載 `PlayerController` 到當前玩家 Gamepiece（`field.gd:19-35`）。
2. 監聽 `Player.gamepiece_changed`，切換相機與控制器（`field.gd:19-21`）。
3. 監聽 `CombatEvents.combat_initiated/finished` 來 `hide()` / `show()` 自身，實現場景切換（`field.gd:42-43`）。
4. 啟動 `opening_cutscene`（若有指派，`field.gd:49-50`）。

### 2.2 Gameboard 子系統 — `src/field/gameboard/`

| 檔案 | 職責 |
| :--- | :--- |
| `gameboard.gd`（Autoload） | 格子座標 ↔ 像素座標互轉、鄰格查詢、向 `Pathfinder` 註冊/移除格子（`gameboard.gd:39-99`） |
| `gameboard_properties.gd` | 格子尺寸、地圖邊界（`Rect2i`） |
| `gameboard_layer.gd` | 擴充 `TileMapLayer`；透過 `BLOCKED_CELL_DATA_LAYER` 自訂資料標記阻擋格；加入 `GameboardLayer.GROUP` 後會被 `Gameboard._is_cell_clear()` 掃描 |
| `pathfinder.gd` | 包裝 `AStar2D`，供 AI / 玩家移動查路 |
| `debug/*.gd` | 可視化 debug 工具（邊界、pathfinder 節點） |

**運作流程**：地圖的 `TileMapLayer`（繼承為 `GameboardLayer`）於 `_ready` 自動註冊到 `Gameboard`（見 `gameboard.gd:105-121`），並在格子變化時自動更新 `Pathfinder`，無需手動呼叫。

### 2.3 Gamepiece 子系統 — `src/field/gamepieces/`

核心三件套：

| 類別 | 檔案 | 職責 |
| :--- | :--- | :--- |
| `Gamepiece` | `gamepiece.gd` | **場景中可被格子吸附、可沿路徑平滑移動的物件**。繼承 `Path2D`，透過 `PathFollow2D` 讓動畫與實際位置解耦（`gamepiece.gd:103-151`）。 |
| `GamepieceController` | `controllers/gamepiece_controller.gd` | **控制器基底**：走 `move_path` 路徑。玩家與 AI 皆繼承此類。 |
| `GamepieceAnimation` | `animation/gamepiece_animation.gd` | Sprite 動畫播放（方向 / idle / run）。 |

派生控制器：

- `player_controller.gd` — 玩家輸入（鍵盤 + 滑鼠點擊目標格）。
- `path_loop_ai_controller.gd` — 沿預設巡邏路徑走動（NPC）。
- `cursor/field_cursor.gd` — 玩家滑鼠游標的格子吸附。

**關鍵解耦**：`Gamepiece` 本身是「笨物件」（`gamepiece.gd:7-11` 的註解寫明 *"dumb objects that do nothing but occupy and move"*），所有「主動行為」都由其子節點（controller）提供，實踐**組合優於繼承**。

#### 位置註冊

`GamepieceRegistry`（autoload）維護 `Dictionary[Vector2i, Gamepiece]` 的全域位置表，見 `gamepiece_registry.gd`。
`Gamepiece._ready()` 中呼叫 `GamepieceRegistry.register(self, cell)` 完成註冊（`gamepiece.gd:121-122`）。

### 2.4 Cutscene 系統 — `src/field/cutscenes/`

| 類別 | 用途 |
| :--- | :--- |
| `Cutscene` (`cutscene.gd`) | 基底類別。`run()` 時切到 `_is_cutscene_in_progress = true`，自動 emit `FieldEvents.input_paused(true)`；`_execute()` 供子類覆寫 |
| `Interaction` (`interaction.gd`) | 玩家主動互動觸發（按鍵） |
| `Trigger` (`trigger.gd`) | 玩家走上某格自動觸發 |
| `templates/` 子目錄 | 內建範本：寶箱 / 門 / 區域切換 / 戰鬥觸發 / 對話 / 拾取物 |

> **戰鬥的觸發源頭**：`templates/combat/combat_trigger.gd` 與 `roaming_combat_trigger.gd` 覆寫 `_execute()`，呼叫 `FieldEvents.combat_triggered.emit(arena_scene)`。

### 2.5 UI — `src/field/ui/`

- `dialogue_window.gd` — 包裝 Dialogic 的對話視窗。
- `inventory/ui_inventory.gd` + `ui_inventory_item.gd` — 物品欄 UI。
- `popups/ui_popup.gd` — 通用彈窗。

---

## 3. `src/combat/` — 戰鬥狀態

### 3.1 入口：`combat.gd`

`Combat extends CanvasLayer`（見 `src/combat/combat.gd:26`）。頂層容器，負責整輪戰鬥流程。

**完整戰鬥回合邏輯**（`combat.gd:42-188`）：

```
setup(arena) ←─ 監聽 FieldEvents.combat_triggered（combat.gd:43-44）
  ├─ Transition.cover(0.2) // 遮黑畫面
  ├─ 實例化 CombatArena → 取得 BattlerRoster
  ├─ 播放競技場配樂
  ├─ emit CombatEvents.combat_initiated
  ├─ Transition.clear(0.2) // 淡入
  ├─ UI fade_in
  └─ next_round()

next_round()  // combat.gd:90-101
  ├─ round_count += 1
  ├─ 所有 AI 敵方 Battler 選擇 action  (battler.ai.select_action)
  └─ _select_next_player_action() // 玩家逐一選擇，可前後切換

_select_next_player_action()  // combat.gd:111-150
  ├─ 找「尚未 cached_action」的玩家 Battler
  │    空 → _play_next_action()
  │    非空 → 前推該 Battler，等待 action_cached signal
  └─ 玩家按「back」時清除 cached_action 回到上一位

_play_next_action()  // combat.gd:155-186
  ├─ 檢查敗北條件（雙方倖存）
  ├─ 找最快且仍擁有 cached_action 的 Battler
  │    空 → next_round()
  └─ 呼叫 battler.act() → turn_finished → 遞迴呼叫 _play_next_action

_on_combat_finished(is_player_victory)  // combat.gd:189-213
  ├─ UI fade_out
  ├─ 顯示 Dialogic 對話框（_display_combat_results_dialog）
  ├─ Transition.cover(0.2) → hide()
  ├─ 清空 _combat_container
  ├─ 還原先前音樂
  └─ emit CombatEvents.combat_finished(is_player_victory)
```

此流程正是 **「兩階段回合制」** 的教科書寫法：階段一選擇所有 action，階段二依 speed 排序執行。

### 3.2 `CombatArena` — 戰鬥場地容器

見 `src/combat/combat_arena.gd`。極簡：一個 `Control`，帶 `music`（AudioStream）export，並提供 `get_battler_roster()` 取得 `$Battlers` 子節點。

> 設計師只需在編輯器拖拉 Battler 節點到 `$Battlers` 下、拖個 AudioStream 進 `music`，即可定義一個新戰鬥。**無需寫任何程式**。

### 3.3 `Battler` — 戰鬥參與者 ★ 核心類別

見 `src/combat/battlers/battler.gd:9`，`Battler extends Node2D`。

**職責**：統整一個戰鬥參與者的**狀態**（stats）、**行動清單**（actions）、**動畫**（anim）與**AI**（ai）。

**關鍵設計**：

1. **Resource 原型 + 執行期複製**（`battler.gd:155-174`）
   `stats` 與 `actions` 是 `@export` 的 Resource。由於 Godot 的 Resource 實例是共享的，`_ready()` 會 `duplicate()` 它們，避免多個 Battler 共用同一份 BattlerStats。
2. **Packed Scene 驅動子節點**（`battler.gd:40-92`）
   `battler_anim_scene` 與 `ai_scene` 都是 `@export var PackedScene`。Setter 會在執行期（以及編輯器 `@tool` 階段）實例化並加到 children。**型別錯誤（不是 BattlerAnim / CombatAI）會印 warning 並自動清除**，提供強烈的設計時保護。
3. **signal 驅動的回合控制**
   `action_cached`（選好 action）、`turn_finished`（action 執行完）、`health_depleted`（死亡）、`hit_received` / `hit_missed`（受擊回饋）。
4. **靜態排序函式**（`battler.gd:143-144`）
   `Battler.sort` 依 `stats.speed` 降序排序，供 `Combat._get_next_actor()` 使用。

### 3.4 `BattlerStats` — Resource 形式的屬性 + 修飾器系統

見 `src/combat/battlers/battler_stats.gd`。`BattlerStats extends Resource`。

- **基礎屬性**：`max_health`, `max_energy`, `attack`, `defense`, `speed`, `hit_chance`, `evasion`（`battler_stats.gd:22-51`）。
- **Modifiers / Multipliers 系統**（`battler_stats.gd:68-162`）
  - 每個屬性都有兩個 dict：加算的 `_modifiers` 與乘算的 `_multipliers`。
  - 新增 `add_modifier()` / `add_multiplier()` 回傳唯一 id，可用於之後 `remove_*`（例如裝備移除）。
  - 重新計算公式：`value = max(0, round(base_value * (1 + ΣΣ multipliers) + Σ modifiers))`。
- **元素親和性**：`affinity: Elements.Types`（見 `src/combat/elements.gd`），供 `BattlerHit` 計算傷害加成。

### 3.5 `BattlerAction` — Resource 形式的戰技

目錄 `src/combat/actions/`：

| 類別 | 用途 |
| :--- | :--- |
| `battler_action.gd` | 基底 Resource，定義 `source`, `battler_roster`, `cached_targets`, `energy_cost`, `get_possible_targets()`, `execute()` |
| `battler_action_attack.gd` | 一般攻擊 |
| `battler_action_heal.gd` | 治療 |
| `battler_action_projectile.gd` | 發射物（有動畫） |
| `battler_action_modify_stats.gd` | 增益/減益 |
| `battler_hit.gd` | 單次攻擊的「打擊封包」（傷害、命中） |

Action 是 Resource 代表可當 `.tres` 檔儲存並在編輯器掛到 Battler 的 `actions` array，完全**資料驅動**。

### 3.6 `CombatAI` — 策略物件

見 `src/combat/combat_ai_random.gd`。`CombatAI extends Node` 作為基底類別，`select_action(source)` 是覆寫點。內建實作隨機選 action + 隨機挑目標（最多嘗試 `ITERATION_MAX = 60` 次）。

> Battler 透過 `ai_scene: PackedScene` 指派 AI 節點（見 `battler.gd:74-92`），**要替換 AI 策略只需製作新場景並拖拉**，不需修改 Battler。

### 3.7 `BattlerRoster` — 戰鬥名冊

見 `src/combat/battlers/battler_roster.gd`。為 `Node`，是 `CombatArena` 下的 `$Battlers` 子節點。
提供篩選 API：`get_player_battlers()`、`get_enemy_battlers()`、`find_live_battlers()`、`find_battlers_needing_actions()`、`find_ready_to_act_battlers()`、`are_battlers_defeated()`。

此設計讓 `Combat` 腳本以**宣告式**方式查詢狀態，避免散落各處的 `for battler in ...` 判斷。

### 3.8 戰鬥 UI — `src/combat/ui/`

- `ui_combat.gd` — 戰鬥主介面（綁定 roster、管理 action menu、轉場動畫）。
- `action_menu/` — 動作選擇選單。
- `battler_entry/` — 每位 Battler 的血條/能量條顯示。
- `cursors/` — 目標選擇游標。
- `effect_labels/` — 傷害數字飄字。

---

## 4. `src/common/` — 跨狀態共用服務

| 檔案 | 職責 |
| :--- | :--- |
| `player.gd`（Autoload） | 玩家全域狀態；只持有一個屬性 `gamepiece`，setter emit `gamepiece_changed` |
| `inventory.gd` | 物品欄邏輯（供 field UI 使用） |
| `directions.gd` | 四向枚舉 `Points.NORTH/EAST/SOUTH/WEST` + `MAPPINGS: Dictionary[int, Vector2i]` + `angle_to_direction()` |
| `collision_finder.gd` | 包裝 `PhysicsPointQueryParameters2D`，查詢某點的 collider（供 Trigger / Interaction 判斷） |
| `screen_transitions/screen_transition.gd`（Autoload） | 畫面遮黑 / 淡入；`cover()`, `clear()`, `finished` signal |
| `music/music_player.gd`（Autoload） | 背景音樂播放、淡入淡出、保存/恢復上一曲 |

`common` 下的東西都是**引擎層級的工具**，不耦合 field / combat。

---

## 5. 案例：從「踩到觸發器」到「戰鬥結束」的完整事件流

以下用行號追蹤一次完整的狀態切換，展示整個架構如何協作：

```
┌─ [場景態] 玩家 Gamepiece 走到某格
│
│   player_controller.gd：接收 cell_selected、塞入 move_path
│   gamepiece_controller.gd:57-87：呼叫 Gamepiece.move_to()
│   gamepiece.gd:125-151：_process 每幀沿 Curve2D 前進
│
├─ [觸發] 該格放了一個 RoamingCombatTrigger（Cutscene 子類）
│
│   trigger.gd：玩家停在該格時呼叫 Cutscene.run()
│   cutscene.gd:45-52：
│     _is_cutscene_in_progress = true
│       → FieldEvents.input_paused.emit(true)     // 場景輸入鎖定
│       → all GamepieceController is_active = false
│     await _execute()                             // 覆寫的 RoamingCombatTrigger 邏輯
│
├─ [戰鬥觸發] _execute() 內部：
│
│   FieldEvents.combat_triggered.emit(arena_packed_scene)
│
├─ [切換] Combat 捕獲該 signal
│
│   combat.gd:43-44：FieldEvents.combat_triggered.connect(setup)
│   combat.gd:50-86：setup(arena)
│     → Transition.cover → show Combat CanvasLayer
│     → 實例化 CombatArena，取得 BattlerRoster
│     → Music.play(arena.music)
│     → CombatEvents.combat_initiated.emit()
│         ├─ field.gd:42 hide()                    // 場景隱藏
│         └─ combat UI fade_in
│     → next_round()
│
├─ [戰鬥中] 階段一：所有 AI 選 action
│
│   for battler in enemy_battlers: battler.ai.select_action(battler)
│   combat_ai_random.gd:14-47：隨機挑 action + 目標
│     → source.cached_action = action              // action_cached signal 觸發
│
├─ [戰鬥中] 階段一：玩家逐一選 action
│
│   combat.gd:111-150：_select_next_player_action
│   CombatEvents.player_battler_selected.emit(battler)
│   ui_combat.gd 捕獲 → 顯示 action menu
│   玩家選完 → battler.cached_action = action
│   battler.gd:139-140：set cached_action 會 emit action_cached
│
├─ [戰鬥中] 階段二：依速度執行
│
│   combat.gd:155-186：_play_next_action
│   ready_to_act_battlers.sort_custom(Battler.sort)  // 依 speed
│   battler.act() → action.execute()                 // 傷害 / 動畫
│     → battler.turn_finished → 遞迴 _play_next_action
│
│   死亡：stats.health_depleted → battler.is_active = false
│     → are_battlers_defeated 檢測 → _on_combat_finished
│
└─ [戰鬥結束]
    combat.gd:189-213：
      → UI fade_out
      → Dialogic 顯示勝負對話
      → Transition.cover
      → 清空 _combat_container
      → Music.play(_previous_music_track)
      → CombatEvents.combat_finished.emit(is_player_victory)
          └─ field.gd:43 show()                   // 場景重新出現
    cutscene.gd 回到 run() 第 51 行：
      _is_cutscene_in_progress = false
        → FieldEvents.input_paused.emit(false)    // 輸入解鎖
```

這條完整流程中，**沒有任何一個類別 hold 另一個類別的引用**（除了 Combat 對 arena 實例化後的短暫 hold）。所有跨模組通訊都走兩條 signal bus：`FieldEvents` 與 `CombatEvents`。

---

## 6. Level 2 小結與觀察

### 設計哲學三柱

1. **Signal Bus**：跨模組只透過 autoload 事件匯流排，禁止互相 `get_node()`。
2. **Composition over Inheritance**：`Battler` 的動畫與 AI 透過 `PackedScene export` 動態掛接；`Gamepiece` 的行為由多種 Controller 子節點提供。
3. **Resource-as-Template**：`BattlerStats` / `BattlerAction` 是 `.tres` 檔，設計階段可編輯、執行期 `duplicate()` 成實例，**邏輯與數據完全分離**。

### 擴展性評估

| 需求 | 擴充方式 | 需改動程式嗎？ |
| :--- | :--- | :--- |
| 新戰鬥場地 | 新 `CombatArena` 場景 + `$Battlers` 下擺 Battler | ❌ |
| 新戰技 | 繼承 `BattlerAction` 或新 `.tres` 檔 | 多半 ❌ |
| 新 AI 策略 | 繼承 `CombatAI` 做新 scene | ✔ 但隔離 |
| 新地圖 | 新 `Map` 場景，TileMapLayer 使用 `GameboardLayer` | ❌ |
| 新 Cutscene 類型 | 繼承 `Cutscene` 覆寫 `_execute()` | ✔ 局部 |

### 下一步（Level 3 建議）

- **Level 3**：Battler 生命週期與 BattlerAction execute 細節（含 BattlerHit 命中/傷害計算公式）。
- **Level 4**：Gameboard + Pathfinder 的實作細節（格子圖層、Dijkstra、阻擋計算）。
- **Level 5**：Dialogic 整合方式、Inventory 的 Resource 結構、UI 訂閱事件匯流排的模式。
- **Level 6**：實戰教學（如何新增一個新職業 / 新元素類型 / 新地圖 / 新過場動畫）。
