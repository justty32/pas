# 教學：新增一個遊戲選項（Configuration）

> 目標：在 OptionsMenu 加上一個新的可調設定（以「下拉選單 / ListCfg」為例），並讓它自動持久化到 `user://config.cfg`。
> 路徑相對於 `projects/TakinGodotTemplate/`，引擎 `res://root/...` = `godot/root/...`。

---

## 1. 前置知識

先理解設定子系統的運作（詳見架構文件）：
- 整體角色分工：`architecture/level3_configuration_save_system.md` §A。
- Wrapper/Globals 概念：`architecture/level2_core_modules.md` §5。

關鍵心智模型：
1. 每個設定 = 一個 **ConfigurationController 節點**（`_cfg` 場景），負責 save/load/apply。
2. Loader 靠 **節點命名約定** 自動發現它：`<EnumName>` + `<List/Slider/Toggle/Tree>Cfg`。
3. UI 端 = 一個 **MenuConfiguration 節點**（dropdown/slider/toggle/tree），透過 enum 連到 controller。

官方步驟摘要見 `.github/docs/GET_STARTED.md:22-27`，本教學補上原始碼導航與細節。

---

## 2. 原始碼導航（要看/要改的檔案）

| 角色 | 檔案 |
|---|---|
| enum 定義 | `root/autoload/configuration/configuration_enum.gd` |
| List 控制器基類 | `root/autoload/configuration/configuration_controller/_configuration_controller/_list_configuration_controller.gd` |
| 既有範例（照抄） | `root/autoload/configuration/configuration_controller/game/game_mode_list_cfg/game_mode_list_cfg.gd` |
| Loader（自動發現，**通常不用改**） | `root/autoload/configuration/configuration_controller_loader/configuration_controller_loader.gd` |
| Configuration autoload | `root/autoload/configuration/configuration.gd` + `configuration.tscn` |
| UI 節點原型 | `root/scenes/node/menu/menu_configuration/menu_dropdown_node/menu_dropdown_node.gd` |
| 要放 UI 的選項頁 | `root/scenes/scene/menu_scene/options_menu/options_container/game_options/game_options.tscn` |

---

## 3. 實作步驟（以新增「Game 分頁的某個下拉設定」為例）

### 步驟 1：新增 enum 值
編輯 `configuration_enum.gd`，在 `ListCfg` 加上你的值（PascalCase 對應 UPPER_SNAKE）：

```gdscript
enum ListCfg {
    NULL, ANTI_ALIAS, DISPLAY_MODE, FPS_LIMIT, RESOLUTION, VSYNC_MODE,
    GAME_MODE, NUMBER_FORMAT, LOCALE, THEME,
    MY_NEW_OPTION,   # ← 新增
}
```

> 命名要點：之後節點名須叫 `MyNewOptionListCfg`（`EnumUtils.from_name` 會把 `MyNewOption` ↔ `MY_NEW_OPTION` 互轉，見 Loader `..._loader.gd:84-86`）。

### 步驟 2：建立 controller 腳本與場景
參考 `game_mode_list_cfg.gd`，新建 `root/autoload/configuration/configuration_controller/game/my_new_option_list_cfg/my_new_option_list_cfg.gd`：

```gdscript
class_name MyNewOptionListCfg
extends ListConfigurationController

var current_value: int = get_default_value()

func init_cfg_options() -> void:
    init_cfg_option("Option A", 0)
    init_cfg_option("Option B", 1)

func get_default_value() -> int:
    return 0

func get_config_value() -> int:
    return current_value

func apply_config_value(value: Variant) -> void:
    current_value = value
    # TODO: 在此實際套用（改 ProjectSettings / 通知其他節點等）
    configuration_applied.emit()
```

必須覆寫的方法（其餘由 `ConfigurationController` 基類提供）：
- `init_cfg_options()` — 建立有序選項清單（`_list_configuration_controller.gd:75` 要求實作）。
- `get_default_value()`、`get_config_value()`、`apply_config_value()`。

建立同名 `.tscn`（root 節點掛上述腳本），在 Inspector 設定基類的 `config_group`（選 `GAME`）與 `config_id`（如 `"my_new_option"`，作為 INI 的 key）。

### 步驟 3：把 controller 掛進 Configuration autoload
開啟 `configuration.tscn`，把步驟 2 的 `_cfg` 場景 **instance 為 Configuration（或其 controllers root）的子節點**，節點名取 `MyNewOptionListCfg`。

> Loader 在 `_ready()`（`..._loader.gd:35-36`）遞迴掃描所有子節點，依型別與命名自動註冊到 `_list_cfg_map[ConfigurationEnum.ListCfg.MY_NEW_OPTION]`。**不需改 Loader 程式碼。**

### 步驟 4：在選項頁放 UI 節點
開啟 `game_options.tscn`，instance 一個 `menu_dropdown_node.tscn`（`root/scenes/node/menu/menu_configuration/menu_dropdown_node/`）。在 Inspector：
- `list_cfg` 選 `MY_NEW_OPTION`（`menu_dropdown_node.gd:11`）。
- `title` 設標題（可用 i18n key，會經 `TranslationServerWrapper`）。

UI 與 controller 的雙向同步已內建（`menu_dropdown_node.gd:77-97`）：
- 玩家改下拉 → `_on_value_updated` → `controller.update_config_value_index()` → apply + 存 INI。
- 其他來源改設定 → controller emit `configuration_applied` → `_on_configuration_applied` → UI 更新顯示。

---

## 4. 驗證方式

1. **編輯器無錯誤/警告**：依 `GET_STARTED.md:13` 預期「no errors and no warnings」。若有 UID 警告，重存 .tscn。
2. **執行測試**：F5 → 主選單 → Options → Game 分頁，確認新下拉出現、可切換。
3. **持久化驗證**：改值後關閉遊戲，檢查 `user://config.cfg`（Windows 通常在 `%APPDATA%\Godot\app_userdata\TakinGodotTemplate\config.cfg`）出現 `[game]` 區段下的 `my_new_option=...`。重開遊戲應保留上次選擇（由 `ConfigurationController._ready()` → `load_config_value()` 還原）。
4. **重設驗證**：在 Options 按 Reset，當前分頁的設定（含你的新項）應回到 `get_default_value()`（`options_menu.gd:75-77` → `Configuration.reset_options(GAME)`）。
5. **Lint**：存檔時 `format_on_save`/`gdLinter` 會自動跑；push 前確認 `quality_check.yml` 的 gdlint 不報錯（threshold=0）。

---

## 5. 變體：其他控制器型別

| 想做 | 用的基類 / 節點 | enum |
|---|---|---|
| 開關（bool） | `ToggleConfigurationController` / `menu_toggle_node` | `ToggleCfg` |
| 數值滑桿 | `SliderConfigurationController` / `menu_slider_node` | `SliderCfg` |
| 鍵位重綁 | `TreeConfigurationController` / `menu_tree_node` | `TreeCfg` |

流程相同：加 enum 值 → 建命名正確的 `_cfg` 場景 → 掛進 Configuration → 放對應 UI 節點。可參考既有 `audio_slider_cfg`、`autosave_toggle_cfg`、`keybinds_tree_cfg`。
