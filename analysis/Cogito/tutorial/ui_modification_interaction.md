# 教學：如何自訂互動提示（Interaction）與 HUD

本教學說明如何修改玩家 HUD 中的互動提示外觀、準心、屬性條樣式，以及如何新增自訂屬性條。

## 前置知識
- 已閱讀 [Level 1: 初始探索](../architecture/level1_overview.md)。
- 已閱讀 [Level 5D: 玩家 HUD 管理器](../architecture/level5d_player_hud.md)。

---

## 一、HUD 節點總覽

`Player_HUD.tscn` 的關鍵節點路徑（`player_hud_manager.gd:56-64`）：

- **Player_HUD** (Control + player_hud_manager.gd)
  - **DamageOverlay** — 受傷紅色閃爍
  - **InventoryInterface** — 物品欄介面（@onready inventory_interface）
  - **PromptUI**
    - **PromptArea** — 互動提示容器（@onready prompt_area）
    - **HoldUI** — 長按進度環
  - **HintArea** — 升級/狀態提示容器（@onready hint_area）
  - **Crosshair** — 準心
    - **TextureRect** — 實際準心圖片（@onready crosshair_texture）
  - **MarginContainer_BottomUI**
    - **WieldableHud** — 武器資訊面板
    - **PlayerAttributes**
      - **MarginContainer**
        - **VBoxContainer** — 屬性條排列區（@onready ui_attribute_area）

---

## 二、修改互動提示樣式（UI_PromptComponent）

`UiPromptComponent`（`UI_PromptComponent.gd:1-17`）節點結構：
- **UiPromptComponent** (Control)
  - **HBoxContainer**
    - **Container**
      - **InteractionButton** — 按鍵圖示（InputHelper 自動更換為手把/鍵盤圖示）
    - **InteractionText** (RichTextLabel) — 互動動作文字

**修改步驟**：
1. 打開 `addons/cogito/Components/UI/UI_PromptComponent.tscn`。
2. 選取根節點 `UiPromptComponent`（Control）→ 修改 `Theme Overrides` 下的 `Styles/Panel` 換底框樣式。
3. 選取 `InteractionText`（RichTextLabel）→ 修改 `Theme → Fonts` 或加入 BBCode 支援（`bbcode_enabled = true`）。
4. 注意：`InteractionButton` 的圖示由 `InputHelper` 在執行時自動更換為當前輸入裝置的圖示，**不要直接修改貼圖**，只能修改尺寸（`custom_minimum_size`）。

**按鍵圖示對應**：InputHelper 插件的 `device_changed` 信號觸發 `player_hud_manager.gd:_on_input_device_change()`，自動更新所有按鍵圖示。

---

## 三、修改準心（Crosshair）

`player_hud_manager.gd:38` 提供兩個可設定的準心貼圖：
- `default_crosshair`：預設準心（玩家看向空白牆壁時）
- `interaction_crosshair`：看向可互動物件時切換的準心

**修改方式**：
1. 在場景中選取 `Player_HUD` 節點（或在 `Player_HUD.tscn` 中選取根節點）。
2. Inspector → `HUD` 分組 → 更換 `Default Crosshair` 和 `Interaction Crosshair` 貼圖。
3. 若要改變準心**大小**，打開 `Player_HUD.tscn` 找到 `Crosshair/TextureRect` 節點，調整 `Custom Minimum Size`。

**動態隱藏準心**（在選單或對話時）：
```gdscript
# 在 player_hud_manager.gd 加入
func set_crosshair_visible(visible: bool) -> void:
    crosshair.visible = visible
```

---

## 四、修改屬性條（Health, Stamina, etc.）

`CogitoAttributeUi`（`UI_AttributeComponent.gd`）的結構（`UI_AttributeComponent.gd:3-6`）：
```gdscript
@onready var attribute_icon: TextureRect = $HBoxContainer/AttributeIcon
@onready var attribute_bar: CogitoDynamicBar = $HBoxContainer/AttributeBar
@onready var attribute_label: Label = $HBoxContainer/AttributeLabel
```

屬性條顏色來自 `CogitoAttribute.attribute_color`，在 `initiate_attribute_ui()` 時寫入 `bar_stylebox.bg_color`（`UI_AttributeComponent.gd:19-20`）。

**修改屬性條外觀**：
1. 打開 `addons/cogito/Components/UI/UI_AttributeComponent.tscn`。
2. 修改 `AttributeBar`（`CogitoDynamicBar`，繼承 `ProgressBar`）的 `theme_overrides`。
3. `AttributeIcon`（`TextureRect`）的圖示來自 `CogitoAttribute.attribute_icon`，在 Inspector 直接設定屬性節點的圖示即可。

**改變屬性條排列方向**：
`ui_attribute_area` 是 `VBoxContainer`（`player_hud_manager.gd:61`），改成 `HBoxContainer` 即可讓屬性條橫向排列：
1. 打開 `Player_HUD.tscn`。
2. 找到 `MarginContainer_BottomUI/PlayerAttributes/MarginContainer/VBoxContainer`。
3. 右鍵 → Change Type → 選 `HBoxContainer`。

---

## 五、自訂屬性條（添加新屬性）

當您根據 [教學：魔法系統](./magic_and_magicka_system.md) 添加 `Magicka` 屬性後，HUD 自動整合流程如下：

1. **`cogito_player.gd:230`**：`find_children("","CogitoAttribute",false)` 掃描玩家所有直接子節點，以 `attribute_name` 為鍵存入 `player_attributes`。
2. **`player_hud_manager.gd:121-137`**：`instantiate_player_attribute_ui()` 為每個 `attribute_visibility == Hud` 的屬性實例化 `ui_attribute_prefab`（即 `UI_AttributeComponent.tscn`）並加入 `ui_attribute_area`。

**因此：只需讓屬性節點是 CogitoPlayer 的直接子節點、設定正確的 `attribute_name` 和 `attribute_visibility = Hud`，色條自動出現。**

若要讓特定屬性有**獨立位置**（如耐力條固定在螢幕中央下方）：
1. 在 `Player_HUD.tscn` 中手動添加一個 `CogitoAttributeUi` 節點，調整位置。
2. 在 `player_hud_manager.gd:37`：`@export var fixed_stamina_bar : CogitoAttributeUi` 欄位中指向它。
3. `instantiate_player_attribute_ui()` 會偵測到 `fixed_stamina_bar` 並跳過自動生成耐力條（`player_hud_manager.gd:127-128`）。

---

## 六、自訂升級提示 Hint（UI_HintComponent）

`UI_HintComponent.gd:25-33`：
```gdscript
func set_hint(passed_hint_icon: Texture2D, passed_hint_text: String):
    hint_text.text = passed_hint_text
    hint_icon.set_texture(passed_hint_icon if passed_hint_icon else default_hint_icon)
    hint_timer.start()  # 預設顯示 4.5 秒後淡出
```

**修改顯示時間**：
```gdscript
# 在 UI_HintComponent.tscn 的 HintTimer 節點調整 wait_time，或在腳本中：
@export var hint_time : float = 4.5  # 修改此值
```

---

## 七、驗證清單

| 測試步驟 | 預期結果 |
|---|---|
| 走向 CogitoDoor 互動 | 互動提示出現且樣式符合修改 |
| 使用手把時互動 | 按鍵圖示自動換成手把按鍵圖示 |
| 準心更換後走向可互動物件 | 準心切換到 interaction_crosshair |
| 加入 Magicka 屬性且 visibility=Hud | HUD 底部出現藍色魔力條 |
| `fixed_stamina_bar` 設定後 | 耐力條不再出現在通用屬性區，改在固定位置 |
