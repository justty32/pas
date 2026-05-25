# 教學：如何把本模板的選單接到既有 Godot 專案

> 目標：在一個**已存在**的 Godot 4.x 專案中，加入本模板的主選單／選項選單／暫停選單／設定持久化，而不破壞原有遊戲邏輯。
> 對應官方文件：`docs/ExistingProject.md`、`docs/BasicSetup.md`、`docs/MainMenuSetup.md`、`docs/GameSceneSetup.md`。

## 前置知識

- 本模板的「邏輯層 vs 呈現層」分離觀念 → `architecture/level1_overview.md`（`scenes/` 繼承自 `addons/`）。
- 4 個 autoload 與設定持久化 → `architecture/level2_core_modules.md` 第 1、2 節。
- 場景載入流程 → `architecture/level3_scene_loading.md`。

## 原始碼導航（會接觸到的檔案）

| 檔案（相對 `projects/Godot-Game-Template/`） | 為何重要 |
|---|---|
| `project.godot` `[autoload]`（第 17-22 行附近） | 要把 4 個 autoload 複製到目標專案 |
| `addons/maaacks_game_template/installer/setup_wizard.gd` | 安裝精靈，自動複製範例場景 |
| `addons/maaacks_game_template/base/nodes/autoloads/app_config/app_config.gd:4-6` | 設定主選單／遊戲／結尾三個場景路徑 |
| `addons/maaacks_game_template/base/nodes/menus/main_menu/main_menu.gd:34-44` | 主選單的 New Game → `SceneLoader.load_scene(game_scene_path)` |
| `addons/maaacks_game_template/base/nodes/utilities/pause_menu_controller.gd` | 把暫停選單掛進你的遊戲場景 |

## 實作步驟

### 步驟 1：安裝 addon
1. 把 `addons/maaacks_game_template/` 整個資料夾複製到目標專案的 `addons/`。
2. 重新載入專案（`Project > Reload Current Project`）。可能出現暫時錯誤，重載後消失。
3. `Project Settings > Plugins` 啟用 "Maaack's Game Template"。首次啟用會跳出 **Setup Wizard**（`installer/setup_wizard.gd`）。

### 步驟 2：執行 Setup Wizard
- 選單 `Project > Tools > Run Maaack's Game Template Setup...`。
- 精靈會把 `addons/.../examples/` 的範例場景**以繼承場景**複製到你指定的資料夾（預設專案根 `scenes/`）。
- 確認 4 個 autoload 已加入 `project.godot`（`AppConfig`、`SceneLoader`、`ProjectMusicController`、`ProjectUISoundController`）。若手動加入，順序與路徑參照本專案 `project.godot:17-22`。

### 步驟 3：設定場景路徑（AppConfig）
本模板靠 `AppConfig` 集中三個關鍵路徑：
1. 開啟 autoload 場景 `addons/.../base/nodes/autoloads/app_config/app_config.tscn`（或其在 `scenes/` 的覆寫版）。
2. 在 Inspector 的 Scenes 群組（`app_config.gd:4-6`）填：
   - `main_menu_scene_path` → 你的主選單場景（通常用範例的 `scenes/menus/main_menu/main_menu.tscn`）。
   - `game_scene_path` → **你的遊戲主場景**。
   - `ending_scene_path` → 結尾畫面（可留空）。
3. 把 `project.godot` 的 `run/main_scene` 設為 `scenes/opening/opening.tscn`（或直接主選單，視需求）。

> 這樣 MainMenu 的 New Game 會 `load_game_scene()` → 讀 `AppConfig.game_scene_path` 進你的遊戲（`main_menu.gd:34-44`）。

### 步驟 4：把暫停選單掛進你的遊戲場景
1. 在你的遊戲主場景加一個 Node，掛上 `pause_menu_controller.gd`（或使用範例 `scenes/windows/pause_menu_layer.tscn`）。
2. 設 `pause_menu_packed` 為暫停選單場景（範例 `scenes/windows/pause_menu.tscn`）。
3. 執行後按 `ui_cancel`（Esc / 手把 Back）即可開啟暫停選單（`pause_menu_controller.gd:24-26`）。

### 步驟 5：讓背景音樂跨場景延續（選用）
- 在「想播放音樂的場景」放一個 `AudioStreamPlayer`，設 `bus = "Music"`、`autoplay = true`。
- `ProjectMusicController` 會自動接管並在場景切換時 blend（`music_controller.gd:154-169`）。**無需任何程式碼**。

### 步驟 6：UI 音效（選用）
- 範例選單已內建 `ProjectUISoundController`。若要讓你自己的 UI 也有音效，確保它們在 controller 管理的子樹下；`persistent=true` 時連動態生成的控件也會自動接上（`ui_sound_controller.gd:80-89`）。

## 驗證方式

1. **冒煙測試**：F5 執行 → 看到 opening logo → 進主選單 → New Game 進入你的遊戲場景 → 按 Esc 出現暫停選單。
2. **設定持久化**：進 Options 改音量/解析度 → 關閉遊戲 → 重開，設定保留。
   - 檢查 `user://player_config.cfg`（Windows：`%APPDATA%\Godot\app_userdata\<專案名>\player_config.cfg`），應出現對應 `[AudioSettings]` / `[VideoSettings]`（見 `level3_settings_persistence.md` 的 .cfg 範例）。
3. **輸入重綁定**：Options > Input/Controls 改某動作的按鍵 → 重開遊戲後綁定仍在（寫入 `[InputSettings]`）。
4. **音樂延續**：在主選單與遊戲場景各放不同 Music bus 的 autoplay player，切換時應聽到 blend 而非中斷/重頭。

## 常見坑

- **autoload 順序**：`AppConfig` 需先於用到設定的場景初始化；維持 `project.godot` 既有順序最保險。
- **renderer 不符**：本模板預設 `gl_compatibility`。若你的專案用 Forward+/Mobile，主題與部分效果仍可用，但匯出設定請以你的專案為準。
- **路徑為空的 fallback**：許多元件（MainMenu、LevelManager、Opening）路徑為空時會讀 AppConfig，故務必把 AppConfig 設好（見步驟 3）。
