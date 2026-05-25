# 教學：如何新增一個自訂選項（與選項分頁）

> 目標：在選項選單中加入會**自動持久化**的自訂選項（例如「滑鼠靈敏度」「難度」「語言」），並在遊戲程式中讀回該值。
> 對應官方文件：`docs/AddingCustomOptions.md`、`docs/OptionsMenuSetup.md`。

## 前置知識

- 設定持久化三層（OptionControl → PlayerConfig）→ `architecture/level3_settings_persistence.md`。
- `OptionControl` 的零程式碼擴充機制 → `architecture/level2_core_modules.md` 第 2.3 節。

## 核心觀念

新增選項的關鍵元件是 `OptionControl`（`base/nodes/menus/options_menu/option_control/option_control.gd`，`@tool`）。它做兩件事：
1. 把任何子控件（Button/Slider/LineEdit/TextEdit/OptionButton/ColorPicker）的值，依 `section`+`key` 寫進 `user://player_config.cfg`。
2. 場景開啟時讀回該值填入控件（`_ready()`，`option_control.gd:115`）。

→ **大多數情況下，加一個選項不需要寫任何程式碼**，只要在場景裡擺好節點、在 Inspector 填欄位。

## 原始碼導航

| 檔案（相對 `projects/Godot-Game-Template/`） | 重點 |
|---|---|
| `addons/maaacks_game_template/base/nodes/menus/options_menu/option_control/option_control.gd:30-59` | `option_name`/`option_section`/`key`/`section`/`property_type` 等 @export |
| `…/option_control.gd:66` | `_on_setting_changed` → `PlayerConfig.set_config` |
| `…/option_control.gd:74-89` | `_connect_option_inputs`：依控件型別自動接訊號 |
| `…/option_control.gd:91-105` | `set_value`：讀回時依型別填值 |
| `addons/maaacks_game_template/base/nodes/config/app_settings.gd:6-10` | section 常數（INPUT/AUDIO/VIDEO/GAME/CUSTOM…） |
| `scenes/menus/options_menu/master_options_menu_with_tabs.tscn` | 範例：分頁式選項主選單，可在此加分頁 |

## 實作步驟

### A. 加一個會自動持久化的選項控件（無程式碼）

1. 開啟一個選項分頁場景（例如複製 `scenes/menus/options_menu/game/game_options_menu.tscn` 來改，或自建一個 Control）。
2. 在容器下加入 `OptionControl` 節點：
   - 直接用基底 `option_control.tscn`，或用現成的型別變體 `slider_option_control.tscn` / `toggle_option_control.tscn`。
3. 選中該 `OptionControl`，在 Inspector 設定：
   - **Option Name**：顯示名稱，例如 `Mouse Sensitivity`。它會自動把 `key` 預填為 `MouseSensitivity`（PascalCase，`option_control.gd:32-39`）。
   - **Option Section**：選 `INPUT`（對應 `AppSettings.INPUT_SECTION`）或 `GAME`/`CUSTOM`（`option_control.gd:41-46`）。
   - **Property Type**：此選項的型別（`TYPE_FLOAT` / `TYPE_BOOL` / `TYPE_INT`…，`option_control.gd:59`），決定 `value`/`default_value` 的型別。
4. 在這個 `OptionControl` **底下**加一個對應控件（這是它的子節點）：
   - 數值 → `HSlider` 或 `SpinBox`（`Range`）。
   - 開關 → `CheckButton` / `CheckBox`（`Button`）。
   - 多選 → `OptionButton`。
   - 文字 → `LineEdit`。
5. （重要）設 default：官方建議用外部編輯器在 `.tscn` 直接設 `default_value`，因編輯器有快取 bug 可能還原變更（`option_control.gd:61-62` 註解）。
6. 存檔。執行後拖動該控件，`user://player_config.cfg` 即出現對應 section/key（即時寫入，`option_control.gd:66-69`）。

### B. 在遊戲程式中讀回設定

選項只有被遊戲讀取才有效果。用 `PlayerConfig.get_config` 讀：

```gdscript
# 例：讀玩家自訂的滑鼠靈敏度（INPUT section），缺省 1.0
var mouse_sensitivity : float = PlayerConfig.get_config(
    AppSettings.INPUT_SECTION, "MouseSensitivity", 1.0)

# 例：讀自訂難度（CUSTOM section）
var difficulty : int = PlayerConfig.get_config(
    AppSettings.CUSTOM_SECTION, "Difficulty", 1)
```

> 注意 `key` 字串要與 Inspector 中的 `key` 完全一致（PascalCase）。

### C. （進階）需要「改值立即生效」的副作用

若選項變更需要立刻對引擎做事（如即時調靈敏度），連 `OptionControl` 的 `setting_changed` 訊號（`option_control.gd:5`）：

```gdscript
# 在選項頁腳本中
func _ready() -> void:
    %SensitivityControl.setting_changed.connect(_on_sensitivity_changed)

func _on_sensitivity_changed(value : float) -> void:
    # 立即套用到你的相機腳本（值此時已自動寫入 config）
    PlayerCamera.sensitivity = value
```

這正是內建 video/audio 選單的模式——OptionControl 負責寫檔，OptionsMenu 腳本負責即時副作用（參考 `video_options_menu.gd:33`、`audio_options_menu.gd:10`）。

### D. 新增一個完整的選項「分頁」

1. 選項主選單用 `PaginatedTabContainer`（`base/nodes/menus/options_menu/paginated_tab_container.gd`）管理分頁。
2. 把你的新分頁場景（含上面建好的 OptionControl）作為 TabContainer 的一個子頁加入，例如改 `scenes/menus/options_menu/master_options_menu_with_tabs.tscn`。
3. 分頁標題即 tab 名稱，會自動納入鍵盤/手把的 page up/down 導航（InputMap 已定義 `ui_page_up`/`ui_page_down`，見 `project.godot`）。

## 驗證方式

1. **持久化驗證**：執行 → 改你的新選項 → 關閉 → 重開，控件應顯示上次的值。
2. **檔案驗證**：開 `user://player_config.cfg`（路徑見 `level3_settings_persistence.md`），確認出現：
   ```ini
   [InputSettings]
   MouseSensitivity=1.05
   ```
   （未改過的選項不會寫入，需先操作一次，`option_control.gd` 註解亦提及。）
3. **讀回驗證**：在遊戲中 `print(PlayerConfig.get_config(...))`，確認拿到剛存的值。
4. **副作用驗證**（若有 C）：改值當下遊戲行為立即改變（不需重開）。

## 常見坑

- **key 不一致**：Inspector 的 `key` 與程式 `get_config` 的字串需完全相同（大小寫敏感）。
- **section 選錯**：INPUT/AUDIO/VIDEO 有引擎副作用語意；純自訂值請用 `GAME` 或 `CUSTOM` 以免和內建邏輯混淆。
- **default 被還原**：用外部編輯器設 `default_value`，避免 Godot Inspector 快取 bug（官方註解，`option_control.gd:61`）。
- **型別不符**：`property_type` 要對應控件輸出型別，否則 `set_value` 的 `as int/float/bool` 轉換可能不如預期（`option_control.gd:91-105`）。
