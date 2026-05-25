# 教學：抽換 GameContent，套上自己的玩法

> 目標：把模板預設的 2D 點擊玩法換成你自己的遊戲（2D 或 3D），同時保留框架既有的暫停/選項/離開/存檔流程。
> 路徑相對於 `projects/TakinGodotTemplate/`，引擎 `res://root/...` = `godot/root/...`。

---

## 1. 前置知識

- 場景流與玩法抽換接縫：`architecture/level3_scene_flow_and_builder.md` §3。
- 玩法來源與設定的關聯（GameModeListCfg）：`architecture/level3_configuration_save_system.md` §A.5。
- 存檔資料如何讀寫：`architecture/level3_configuration_save_system.md` §B。

關鍵心智模型：
- `GameScene` 是 **固定框架**（暫停/選項/離開/存檔），不要改它的骨架。
- `GameContent` 是 **可抽換的玩法本體**，作為 GameScene 的子節點被動態實例化。
- GameScene 用 **鴨子型別**（`"player" in game_content`）與 GameContent 溝通，所以你的玩法只要「按需」提供約定屬性即可。

---

## 2. 原始碼導航

| 角色 | 檔案 |
|---|---|
| 玩法框架 | `root/scenes/scene/game_scene/game_scene.gd`（`_load_game_content_scene` :68-76、鉤子 :47-64） |
| 預設 2D 玩法 | `root/scenes/scene/game_scene/game_content/game_content.gd`（`Control`，有 `pause_menu_button`、`control_grab_focus`） |
| 3D FP 範例玩法 | `root/artifacts/example_3d_fp_controller/scenes/game_content/game_content.gd`（`Node3D`，有 `%Player`） |
| 空白範例 | `root/artifacts/example_empty_project/scenes/game_content/` |
| 玩法來源設定 | `root/autoload/configuration/configuration_controller/game/game_mode_list_cfg/game_mode_list_cfg.gd` |

---

## 3. 玩法與框架的「約定屬性」

GameScene 在這些時機讀取 GameContent 的可選屬性（有才用，沒有就略過）：

| GameContent 提供的屬性 | GameScene 何時用 | 行號 |
|---|---|---|
| `pause_menu_button`（按鈕） | 連到「開啟暫停選單」 | `game_scene.gd:133-135` |
| `player: Player`（含 `capture_mouse()`/`release_mouse()`） | 暫停釋放滑鼠、繼續擷取滑鼠 | `game_scene.gd:47-60` |
| `control_grab_focus: ControlGrabFocus` | 繼續遊戲時抓回 UI 焦點 | `game_scene.gd:54-56` |

> 2D UI 玩法通常提供 `pause_menu_button` + `control_grab_focus`；3D/FP 玩法通常提供 `player`。兩者皆可，缺的就不觸發。

---

## 4. 實作步驟

### 路徑 A：直接改預設 GameContent（最快）
1. 開啟 `game_content.tscn`，把你的玩法節點加進去，或直接替換內容。
2. 若是 UI 型玩法，保留 `%PauseMenuButton` 與 `%ControlGrabFocus`（唯一名 `%`），讓暫停與焦點正常。
3. 改 `game_content.gd` 的遊戲邏輯（讀寫存檔見步驟 6）。

### 路徑 B：新增一個玩法並用 GameMode 切換（推薦，可保留範例）
1. 在 `root/scenes/scene/game_scene/game_content/`（或自訂目錄）建立你的 `my_game_content.tscn` + `.gd`。
   - 2D UI 玩法：root 用 `Control`，命名 `%PauseMenuButton`、`%ControlGrabFocus`。
   - 3D 玩法：root 用 `Node3D`，提供 `@onready var player: Player = %Player`（參考 FP 範例 `game_content.gd`）。
2. 把你的場景加入 `GameModeListCfg` 的 `game_content_scenes` 陣列（在 `game_mode_list_cfg.tscn` 的 Inspector）：
   - index 0 = 空、1 = 預設、2 = 3D FP… 你可把自己的設為 index 3，並在 `init_cfg_options()` 加一行 `init_cfg_option(_get_option_name(3), 3)`，或直接覆蓋既有 index。
3. 在遊戲內 Options → Game → 「Game Mode」下拉選到你的玩法即可（`Configuration.get_game_mode_content_scene()` 會回傳對應 PackedScene，GameScene `_load_game_content_scene()` 實例化它）。

> 若你完全不需要「玩法切換」功能，可移除 GameOptions 的 Game Mode 並把 `game_scene.gd::_load_game_content_scene` 改成直接 `preload` 你的場景（檔頭註解 `game_scene.gd:6-8` 已提示此函式可移除）。

---

## 5. 處理 3D 玩法的滑鼠擷取

若你的玩法是第一人稱（需鎖滑鼠），讓 `player` 提供：
- `capture_mouse()`：`Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)`。
- `release_mouse()`：`Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)`。

GameScene 會在暫停時 `release`、繼續時 `capture`（`game_scene.gd:_after_pause/_after_unpause`）。輸入動作 `move_*`/`look_*`/`jump` 已在 `project.godot:111-160` 定義好。

---

## 6. 把玩法資料接上存檔系統

1. 在 `GameSaveData`（`root/autoload/data/save_data/game_save_data/game_save_data.gd`）加上你的 typed 變數（如 `var level: int`）。因 SaveData 反射式序列化（`_save_data.gd:84-99`），**不需手寫存取碼**，只要變數不以 `_` 開頭。
2. 在 `clear()` 設好預設值。
3. 玩法中讀寫：`Data.game.level = 3`、`var lv := Data.game.level`。
4. 存檔時機：autosave Timer（預設 5 秒）會自動存；離開/退出時 GameScene 也會 `Data.exit_save_file()`/`save_save_file()`。

---

## 7. 驗證方式

1. **進入遊戲**：主選單 → Play → 選一個存檔槽 → 確認你的 GameContent 正確載入（檢查 Remote scene tree 下 GameScene 的子節點是你的玩法）。
2. **暫停流程**：按 Esc → 暫停選單出現；3D 玩法確認滑鼠被釋放、繼續後重新鎖定。
3. **離開流程**：暫停選單 Leave → 回主選單，且這趟的進度已存檔。
4. **存檔持久化**：改變遊戲狀態（如加 coins）→ 等 autosave 或離開 → 重新進同一存檔槽，狀態應還原；檔案在 `user://data/save_N/save_N_game.data`（JSON，結尾有 `§§§` 簽章）。
5. **玩法切換（路徑 B）**：在 Options → Game 切 Game Mode，重新進遊戲確認載入的是對應玩法（注意：遊戲進行中 Game Mode 下拉會被停用，`options_menu.gd:29-31`）。
6. **Lint**：存檔自動格式化/檢查；push 前確認 gdlint 通過。
