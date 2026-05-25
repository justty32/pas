# Level 4 — Resource 驅動資料 與 場景／場域系統

> 模板 A／L5：資源定義；L3：地圖與場域。
> 目標：（A）剖析角色/技能/物品以 `.tres` 定義並於執行期 `duplicate()` 的「原型模式」與載入流程；（B）剖析 field（探索）↔ combat（戰鬥）的場域切換、Gameboard 格子系統與存檔現況。
> 分析對象：`projects/godot-open-rpg/combat/`（資料）、`src/field/`（場域）、`src/common/inventory.gd`
> 分析日期：2026-05-25
> 核對於 2026-05-25（已對照源碼與 `bear_stats.tres` 等 `.tres`，檔名/行號/載入流程確認正確，無需修正）

---

## A. Resource 驅動資料系統

### A.1 為什麼用 Resource

Godot 的 `Resource` 可序列化成 `.tres` 檔，於編輯器以 inspector 視覺化編輯。godot-open-rpg 把**所有戰鬥數值與戰技都做成 Resource**，達成「資料與程式碼分離」：設計師編 `.tres`，程式設計師寫 `.gd`。

| Resource 類別 | 腳本 | `.tres` 範例 |
| :--- | :--- | :--- |
| `BattlerStats` | `src/combat/battlers/battler_stats.gd:2` | `combat/battlers/bear/bear_stats.tres` |
| `BattlerAction`（及子類） | `src/combat/actions/battler_action.gd:7` | `combat/battlers/bear/focus_attack.tres`、`player_melee_action.tres` |
| `Inventory` | `src/common/inventory.gd:3` | `user://inventory.tres`（執行期存檔） |

### A.2 `.tres` 的實際結構

以 `combat/battlers/bear/bear_stats.tres` 為例：

```ini
[gd_resource type="Resource" script_class="BattlerStats" load_steps=2 format=3 uid="uid://bn4nqbuhq4ih8"]
[ext_resource type="Script" path="res://src/combat/battlers/battler_stats.gd" id="1_o2q0b"]
[resource]
script = ExtResource("1_o2q0b")
base_max_health = 100
base_speed = 40
...
```

關鍵點：
- `script_class="BattlerStats"` 綁定腳本，inspector 才能顯示 `@export` 欄位。
- **只存 `base_*` 值**——modifier/multiplier 字典是執行期狀態，不序列化。
- action 的 `.tres`（`focus_attack.tres`）會 `ext_resource` 引用圖示與腳本，並設 `target_scope` / `targets_friendlies` / `readiness_saved` 等。

### A.3 ★ 原型模式：執行期 `duplicate()`

**核心陷阱**：Godot 的 Resource 實例預設**跨節點共享**。若多個 Battler 直接用同一份 `.tres`，會共用血量與 cooldown，互相污染。godot-open-rpg 的解法是把 `.tres` 當「**原型 (prototype)**」，執行期複製出獨立實例：

- `Battler._ready()`：`stats = stats.duplicate()` + `stats.initialize()`（`battler.gd:155-156`）。
- `Battler._ready()`：對 `actions` 陣列逐一 `duplicate()`，並補上 `source` / `battler_roster`（`battler.gd:168-174`）。
- `CombatAI.select_action()`：選定 action 後也 `duplicate()`（`combat_ai_random.gd:27-29`），讓同一回合多個敵人能用同名 action 而 cached_targets 不互撞。

### A.4 載入流程

```mermaid
flowchart LR
    A[".tres 原型<br/>編輯器編輯"] -->|"@export 掛到 Battler"| B[Battler 節點]
    B -->|"_ready() duplicate()"| C[獨立執行期實例]
    C -->|"修改 health / modifier"| D[互不污染]
```

- **戰鬥數值**：設計師在 `Battler.stats` / `Battler.actions`（`battler.gd:32-36`）的 inspector 拖入 `.tres`，引擎載入場景時自動 `preload` 資源，`_ready()` 複製。
- **物品欄**：`Inventory.restore()`（`inventory.gd:37-50`）以 `ResourceLoader.load("user://inventory.tres")` 載入存檔，若不存在則 `Inventory.new()`。

### A.5 Inventory — 唯一的持久化 Resource

`inventory.gd:3`，`@tool class_name Inventory extends Resource`：
- `ItemTypes` 列舉（`inventory.gd:6`）：KEY / COIN / BOMB / RED_WAND / BLUE_WAND / GREEN_WAND。
- `_items: Dictionary`（`inventory.gd:27`）為 `@export`，會序列化進 `.tres`。
- `add()` / `remove()`（`inventory.gd:54-67`）改數量並 emit `item_changed(type)`。
- **存檔**：`save()` 用 `ResourceSaver.save(self, "user://inventory.tres")`（`inventory.gd:81-82`）。

---

## B. 場景／場域系統

### B.1 兩大狀態：field 與 combat

| 狀態 | 根節點 | 性質 | 載入時機 |
| :--- | :--- | :--- | :--- |
| **探索（field）** | `Field` (`Node2D`)，主場景 | 常駐 | 開機即在（`project.godot` main_scene） |
| **戰鬥（combat）** | `Combat` (`CanvasLayer`) | 常駐但 `hide()` | 開機即在，戰鬥時 `show()` |

兩者**同時存在於場景樹**，靠 `show()`/`hide()` 切換可見性，而非 `change_scene`。切換的唯一觸發點是 §B.2 的事件接力。

### B.2 場域切換的事件接力

1. 玩家踩到 `CombatTrigger`（繼承 `Cutscene`），`Cutscene.run()` 先 emit `FieldEvents.input_paused(true)` 鎖輸入（`cutscene.gd:46`→`30-35`）。
2. `CombatTrigger._execute()` emit `FieldEvents.combat_triggered(arena)`（`combat_trigger.gd:9`）。
3. `Combat.setup()` 接手：`Transition.cover` 遮黑 → `show()` → 實例化 arena → emit `CombatEvents.combat_initiated`（`combat.gd:50-72`）。
4. `field.gd:42` 收到 `combat_initiated` → `hide()`。
5. 戰鬥結束 emit `CombatEvents.combat_finished` → `field.gd:43` `show()`，`combat_trigger.gd:11` 的 `await` 取得勝負繼續跑後續 cutscene。
6. Cutscene 結束 → `input_paused(false)` 解鎖（`cutscene.gd:52`→`30-35`）。

> 詳見 `architecture/level_3_signal_bus_and_events.md` §4 的時序圖。

### B.3 Gameboard 格子系統（探索態的空間骨架）

| 元件 | 檔案 | 職責 |
| :--- | :--- | :--- |
| `Gameboard`（autoload） | `gameboard.gd:7` | 格↔像素互轉（`cell_to_pixel`/`pixel_to_cell`, `gameboard.gd:39-49`）、格↔索引、鄰格查詢；持有 `Pathfinder` |
| `GameboardLayer` | `gameboard_layer.gd` | 擴充 `TileMapLayer`，以自訂 data layer 標記阻擋格，`_ready` 自動向 Gameboard 註冊（`gameboard.gd:105-121`） |
| `Pathfinder` | `pathfinder.gd:4` | 包裝 `AStar2D`，`get_path_to_cell()`（`pathfinder.gd:55-91`）支援以旗標忽略佔用格 |
| `GamepieceRegistry`（autoload） | `gamepiece_registry.gd` | `Dictionary[Vector2i, Gamepiece]`，一格一棋子，`gamepiece_moved`/`gamepiece_freed` 驅動 Pathfinder enable/disable（`pathfinder.gd:22-38`） |

**自動化資料流**：地圖的 `GameboardLayer` 在 `_ready` 自動把可走格灌進 `Pathfinder`（`gameboard.gd:127-144`），格子變化時 emit `pathfinder_changed`。棋子移動時 `GamepieceRegistry` emit `gamepiece_moved`，`Pathfinder` 自動把舊格 enable、新格 disable。**整套無需手動同步**。

### B.4 Gamepiece — 探索態的「笨物件」

`gamepiece.gd:13`，`@tool class_name Gamepiece extends Path2D`：
- 自身只負責「佔格 + 沿 `Curve2D` 平滑移動」（`gamepiece.gd:125-151`），是 docstring 自稱的 *"dumb object"*（`gamepiece.gd:6-7`）。
- 移動：`move_to(target)`（`gamepiece.gd:159-173`）把目標加進 curve，`_process` 每幀推進 `PathFollow2D.progress`，到點 `stop()`。
- 「主動行為」由子節點 `GamepieceController` 提供（`PlayerController` / `path_loop_ai_controller`），實踐組合優於繼承。

### B.5 隊伍（party）與存檔現況

- **隊伍**：戰鬥中的「隊伍」即 `BattlerRoster` 下 `is_player == true` 的 Battler 集合（`battler_roster.gd:20-24`）。探索態的「當前操控者」由 `Player.gamepiece`（autoload）單一持有（`player.gd`），`gamepiece_changed` 時換控制器（`field.gd:19-35`）。沒有獨立的「party 資料結構」——隊員即場景中擺好的 Battler 節點。
- **存檔**：**只有 `Inventory` 有持久化**（`user://inventory.tres`，`inventory.gd:21, 81-82`）。Battler 數值、進度、地圖位置**目前都不存檔**——這與 README「角色成長」是教學留白、`target/ARCHITECTURE.md` §7「不做存檔」一致。

---

## C. GDExtension 遷移點（C++ 後端化建議）

| 適合移往 C++（純資料/邏輯） | 留在 Godot（表現/序列化） |
| :--- | :--- |
| **資料模型本身**：BattlerStats/Action 的數值結構與 modifier 計算（`battler_stats.gd:128-161`） | `.tres` 仍可作為「設計時資料來源」，由載入器轉成 C++ struct |
| **原型→實例複製語意**：C++ 後端用值型別 struct，自然每個 battler 一份，免去 `duplicate()` 陷阱 | 前端只持有顯示用的輕量 mirror（血量、名字、icon key） |
| **Gameboard / Pathfinder**：格子座標、A*、佔用判定（`gameboard.gd`、`pathfinder.gd`）——`target/` 計畫初期前端用、後期可移入後端 | `GameboardLayer`（TileMapLayer 渲染）、`Gamepiece` 的 tween 移動演出留前端 |
| **物品欄邏輯與存檔**：item 數量、增減規則（`inventory.gd:54-67`） | 存檔格式：可改由後端寫二進位，或前端續用 `.tres` 鏡像 |
| **隊伍/世界狀態的權威持有** | `Player.gamepiece` 換成「後端送的 entity_id → 前端 Gamepiece 節點」映射（沿用 `GamepieceRegistry` 心智模型） |

### 切割原則

- **`.tres` 留作「設計時資料」、不留作「執行時狀態」**：後端啟動時讀 `.tres`（或轉出的 JSON/二進位）建立權威狀態，之後狀態變更全在 C++，前端只收事件鏡像。如此就**徹底消除 Godot Resource 共享/複製的心智負擔**。
- **格子座標系統可漸進遷移**：`target/00_master_guide.md` 建議初期直接複製 `gameboard.gd` / `pathfinder.gd` / `gamepiece_registry.gd` 到前端當骨架（§一「直接複製」表），待後端成熟再把 A* 與佔用判定移入 C++，前端只負責把 `cell` 轉像素與播 tween。
- **存檔權威歸後端**：後端持有完整世界狀態，存檔 = 序列化後端狀態；前端不再用 `ResourceSaver`，避免「兩份真相」。

詳細的提取/改造清單見 `analysis/godot-open-rpg/target/01_extraction_and_modification_guide.md` 與 `tutorial/01_extraction_and_modification_guide.md`。
