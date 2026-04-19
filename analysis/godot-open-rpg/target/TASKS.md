# TASKS：執行模型的任務清單

> 這是一份**可直接指派**的任務清單。
> 每個任務都有：ID、前置任務、參考文件、具體交付物、驗收標準。
> 規劃者（你）從上往下依序指派，執行模型一次做一個。
> 若任務太大，規劃者先拆分再指派。

## 指派規則

1. **任務有依賴順序**。`dep` 欄列的任務必須先完成才能開始。
2. **規格從 `00_master_guide.md` 查**，不從記憶寫。規格不清楚就回報，別猜。
3. **mock 數據先寫死**。M1-M6 用 GDScript mock `GameEngine`，M7 之後才換 GDExtension。
4. **驗收未過就 debug 不新增功能**。

---

## M0：專案骨架

### T0.1 建立 Godot 專案
- **前置**：無
- **參考**：`ARCHITECTURE.md` §3.1
- **交付**：新建 Godot 4.5 專案，建立目錄 `src/autoload/`、`src/field/`、`src/hud/`、`src/ui/`、`src/mock/`。
- **驗收**：`project.godot` 存在，目錄結構符合規格。

### T0.2 複製可直接複用的素材
- **前置**：T0.1
- **參考**：`00_master_guide.md` §1「直接複製」表；`01_extraction_and_modification_guide.md`
- **交付**：從 `projects/godot-open-rpg` 複製以下檔案到對應位置：
  - `src/field/gameboard/` 整個目錄
  - `src/field/gamepieces/gamepiece_registry.gd`
  - `src/field/gamepieces/animation/gamepiece_animation.gd`
  - `src/common/directions.gd`
  - `src/common/screen_transitions/`、`src/common/music/`
- **驗收**：檔案存在、路徑 `class_name` 無錯誤、編輯器不報紅。

### T0.3 建立契約檔案
- **前置**：T0.1
- **參考**：`00_master_guide.md` §4、§5
- **交付**：
  - `src/contract/game_event.gd`：定義 13 種 `GameEvent` 類別與欄位。
  - `src/contract/player_action.gd`：定義 11 種 `PlayerAction` 類別與欄位。
  - `src/contract/query_request.gd`、`query_result.gd`：query 的輸入輸出結構。
  - 專案根目錄 `visual_keys.md`：空表，先列 §4 範例中出現的 key。
- **驗收**：所有類別 `class_name` 註冊成功，欄位對應規格表。

### T0.4 註冊 Autoload
- **前置**：T0.2、T0.3
- **參考**：`ARCHITECTURE.md` §3.1
- **交付**：建立以下 autoload 檔案（**空殼**，只有 `extends Node` 與 `class_name`）：
  - `GameEngine`（先指向 `src/mock/mock_game_engine.gd`）
  - `DisplayAPI`、`InputHandler`、`VisualRegistry`、`MapManager`
  - `Gameboard`、`GamepieceRegistry`、`Transition`、`Music`（已有檔案，只需註冊）
- **驗收**：專案啟動不報錯，Autoload 面板顯示所有項目。

---

## M1：靜態地圖 + 玩家移動

### T1.1 實作 DisplayAPI
- **前置**：T0.4
- **參考**：`00_master_guide.md` §6；`02_frontend_design.md` DisplayAPI 章節
- **交付**：`src/autoload/display_api.gd`：
  - 宣告 §6 列出的 13 個 signal。
  - `_process(delta)` 每幀呼叫 `GameEngine.tick(delta)`。
  - 把回傳的事件陣列依 `type` 派發到對應 signal。
- **驗收**：印出 log 可看到每幀呼叫了 `tick` 並正確拆事件。

### T1.2 實作 VisualRegistry
- **前置**：T0.4
- **參考**：`00_master_guide.md` §4「命名約定」；`02_frontend_design.md` VisualRegistry 章節
- **交付**：`src/autoload/visual_registry.gd`：
  - `register(key: StringName, resource)` / `get_visual(key: StringName)`。
  - 在 `_ready()` 先註冊至少 2 個 visual_key：`&"player"`、`&"wall_stone"`，對應 godot-open-rpg 的美術。
- **驗收**：`VisualRegistry.get_visual(&"player")` 回傳非空值。

### T1.3 改造 Gamepiece
- **前置**：T0.2、T1.2
- **參考**：`00_master_guide.md` §7；`01_extraction_and_modification_guide.md` Gamepiece 章節
- **交付**：`src/field/gamepieces/gamepiece.gd`：
  - 繼承 `Node2D`（**不是** `Path2D`）。
  - `entity_id: int`、`direction: Directions.Points`、`animation: GamepieceAnimation`。
  - `move_to_cell(cell) -> void`：Tween 動畫（0.2s）+ `await`。
  - `play_animation(name, wait) -> Variant`：呼叫 `animation.play`，`wait=true` 時回傳可 `await` 的 Signal。
- **驗收**：手動建立 Gamepiece 實例，呼叫 `move_to_cell` 能看到 Tween 動畫。

### T1.4 實作 MapDisplay 骨架
- **前置**：T1.1、T1.3
- **參考**：`00_master_guide.md` §2「場景節點」、§6
- **交付**：`src/field/map_display.tscn` + `map_display.gd`：
  - 場景層級：`TerrainLayer`（TileMapLayer）/ `EntityLayer`（Node2D）/ `EffectLayer` / `FogLayer`。
  - `_ready()` connect `DisplayAPI` 的 `entity_spawned` / `entity_moved` / `entity_removed`。
  - `_on_entity_spawned`：查 `VisualRegistry`，實例化 Gamepiece 加到 `EntityLayer`，登記到 `GamepieceRegistry`。
  - `_on_entity_moved`：查 `GamepieceRegistry` 取 Gamepiece，呼叫 `move_to_cell`。
- **驗收**：下一個任務跑起來後，玩家 Gamepiece 能顯示並移動。

### T1.5 實作 InputHandler
- **前置**：T0.4
- **參考**：`00_master_guide.md` §9；`02_frontend_design.md` InputHandler 章節
- **交付**：`src/autoload/input_handler.gd`：
  - `_can_act: bool = false`。
  - `_unhandled_input`：WASD/方向鍵判斷，若 `_can_act` 送 `MOVE`，否則送 `REQUEST_TURN`。
  - connect `DisplayAPI.player_turn_started` 解鎖輸入（依 `force` 決定立即或等動畫）。
- **驗收**：按下方向鍵，console 印出 submit_action 的內容。

### T1.6 Mock GameEngine（M1 版）
- **前置**：T0.3、T1.1
- **參考**：`00_master_guide.md` §10 M1 的 mock 行為
- **交付**：`src/mock/mock_game_engine.gd`：
  - `_ready` 佇列 `ENTITY_SPAWN`（玩家）+ `PLAYER_TURN`。
  - `tick(delta)` 回傳並清空佇列。
  - `submit_action(MOVE)` → 更新內部 player cell，佇列 `ENTITY_MOVE` + `PLAYER_TURN`。
  - 其他 action 先 ignore。
- **驗收**：**M1 驗收** — 啟動遊戲看到玩家，按方向鍵能一格一格移動，每次移完才能再按。

---

## M2：訊息日誌 + 狀態列

### T2.1 MessageLog 元件
- **前置**：T1.1
- **參考**：`00_master_guide.md` §2；`02_frontend_design.md` MessageLog 章節
- **交付**：`src/hud/message_log.tscn` + `.gd`：RichTextLabel 列表顯示 `LOG_MESSAGE`。
- **驗收**：接收 `LOG_MESSAGE` 事件後顯示文字。

### T2.2 StatusPanel 元件
- **前置**：T1.1
- **參考**：`02_frontend_design.md` StatusPanel 章節
- **交付**：`src/hud/status_panel.tscn` + `.gd`：HP/MP/名稱顯示，監聽 `stats_updated`。
- **驗收**：接收 `STATS_UPDATE` 後數值更新。

### T2.3 Mock GameEngine 擴充（M2）
- **前置**：T1.6、T2.1、T2.2
- **交付**：`submit_action(MOVE)` 後加送 `LOG_MESSAGE("你往X走了一步")` + `STATS_UPDATE`（HP - 1 測試）。
- **驗收**：**M2 驗收** — 移動後日誌顯示訊息，HP 條遞減。

---

## M3：視野霧 FOV

### T3.1 FogLayer
- **前置**：T1.4
- **參考**：`02_frontend_design.md` FogLayer 章節
- **交付**：`FogLayer`（TileMapLayer）：三種 tile（未知=黑、已探索=半透、可見=透明）。監聽 `fov_updated` 更新。
- **驗收**：接收到 `FOV_UPDATE` 後對應格子狀態改變。

### T3.2 Mock GameEngine 擴充（M3）
- **前置**：T1.6、T3.1
- **交付**：`tick()` 回傳 `FOV_UPDATE`（玩家半徑 5 格為 visible，其餘已探索過的為 remembered）。
- **驗收**：**M3 驗收** — 玩家四周可見，走過處變暗，未走處黑。

---

## M4：NPC 與多實體

### T4.1 Mock GameEngine 擴充（M4）
- **前置**：T1.6
- **交付**：`_ready` 追加若干 NPC 的 `ENTITY_SPAWN`。玩家每動一次，NPC 也隨機動一格（送 `ENTITY_MOVE`），之後才送 `PLAYER_TURN`。
- **驗收**：**M4 驗收** — 畫面上可見多個角色同步演出。

---

## M5：特效與投射物

### T5.1 EffectLayer 與 Projectile
- **前置**：T1.4、T1.2
- **參考**：`02_frontend_design.md` EffectLayer 章節
- **交付**：監聽 `effect_requested` / `projectile_requested`，用 `VisualRegistry` 實例化特效節點（粒子或 Sprite + Tween）。
- **驗收**：接收事件後有視覺表現。

### T5.2 Mock GameEngine 擴充（M5）
- **前置**：T5.1；`ATTACK` action 需能收
- **交付**：
  - 玩家送 `ATTACK` → 依序送：玩家 `ENTITY_ANIMATE(attack, wait=true)`、敵人 `ENTITY_ANIMATE(hurt)`、`ENTITY_REMOVE`（若死）、`LOG_MESSAGE`。
  - 若攻擊為遠程，先送 `PROJECTILE_LAUNCH` + `EFFECT_AT`。
- **驗收**：**M5 驗收** — 玩家按攻擊鍵，動畫序列正確播放，目標被擊殺後消失。

---

## M6：物品欄 UI + query

### T6.1 InventoryDialog
- **前置**：T1.1
- **參考**：`02_frontend_design.md` InventoryDialog 章節
- **交付**：Modal 對話框，開啟時 `GameEngine.query(INVENTORY)` 取資料渲染清單。點擊「使用」送 `PlayerAction.USE_ITEM`。
- **驗收**：物品欄能開、關、不影響 `_can_act`。

### T6.2 Mock GameEngine 擴充（M6）
- **前置**：T1.6、T6.1
- **交付**：`query(INVENTORY)` 回傳固定清單；`USE_ITEM` → 送 `LOG_MESSAGE` + `STATS_UPDATE`。
- **驗收**：**M6 驗收** — 開物品欄時遊戲不前進，使用藥水 HP 回復。

---

## M7：雙層地圖切換

### T7.1 MapManager
- **前置**：T1.4
- **參考**：`00_master_guide.md` §8
- **交付**：`src/autoload/map_manager.gd`：監聽 `map_entered`，切換場景、更新 `Gameboard.properties`、清空 `EntityLayer` 等待重建。
- **驗收**：送入 `MAP_ENTER` 後畫面切換。

### T7.2 Mock GameEngine 擴充（M7）
- **前置**：T1.6、T7.1
- **交付**：玩家走到特定格送 `MAP_ENTER("local_village")` + 重送全部 `ENTITY_SPAWN`。
- **驗收**：**M7 驗收** — 走到邊界能進入局部地圖，格子尺寸改變，實體重建完整。

---

## 任務卡片格式（新增任務時的範本）

```
### T<milestone>.<seq> <任務名稱>
- **前置**：<T-ID 列表，或「無」>
- **參考**：<規格文件章節；盡量指到節號>
- **交付**：<一句話可寫清楚的具體檔案/行為>
- **驗收**：<一個可被觀察/可被點擊的結果>
```

**單一任務原則**：一個任務只改一個檔案或一個元件。若交付條列超過 4 項，拆成兩個任務。
