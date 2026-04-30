# Cogito — Level 1 初始探索：技術棧與整體架構概覽

## 專案基本資訊

| 項目 | 內容 |
|---|---|
| 類型 | Godot 4.4 第一人稱沉浸模擬 (Immersive Sim) 模板 |
| 引擎版本 | Godot 4.4 stable / Forward Plus 渲染器 |
| 物理引擎 | Jolt Physics |
| 作者 | Philip Drobar (Phazorknight) |
| 版本 | v1.1.5 |
| 原始倉庫 | 已遷移至 Codeberg |

---

## 頂層目錄結構

```
Cogito/
├── addons/
│   ├── cogito/           # 核心插件（所有功能主體）
│   ├── input_helper/     # 輸入重新綁定輔助插件
│   └── quick_audio/      # 簡易音頻 Autoload 插件
├── project.godot         # 專案設定（Autoload、Input Map、Physics Layer）
└── default_bus_layout.tres
```

---

## Autoload 全域單例清單（`project.godot`）

| 單例名稱 | 腳本路徑 | 職責 |
|---|---|---|
| `Audio` | `quick_audio/Audio.gd` | 全域音效播放 |
| `InputHelper` | `input_helper/input_helper.gd` | 輸入重新綁定、手把偵測 |
| `CogitoGlobals` | `cogito/cogito_globals.gd` | 全域設定快取、除錯日誌、Debug 形狀繪製 |
| `CogitoSceneManager` | `cogito/SceneManagement/cogito_scene_manager.gd` | 場景切換、存檔/讀檔 |
| `CogitoQuestManager` | `cogito/QuestSystem/cogito_quest_manager.gd` | 任務狀態管理 |
| `MenuTemplateManager` | `cogito/EasyMenus/Nodes/menu_template_manager.tscn` | 主選單/暫停選單/選項選單控制 |

---

## `addons/cogito/` 子模組一覽

```
addons/cogito/
├── Assets/                  # 音效、模型、材質、著色器、VFX
├── CogitoNPC/               # NPC 基類 + 狀態機 + 各狀態節點
├── CogitoObjects/           # 所有互動物件（Door, Switch, Player, Container…）
├── Components/              # 可組合式組件（屬性、互動、UI、戰利品表）
│   ├── Attributes/          # Health / Stamina / Visibility / Sanity / LightMeter
│   ├── Interactions/        # InteractionComponent（基類）及各種互動子類
│   ├── UI/                  # HUD 屬性顯示組件
│   ├── AutoConsumes/        # 自動消耗邏輯（血量/耐力自動恢復）
│   ├── LootTables/          # 戰利品表資源
│   └── Properties/          # 系統屬性（濕/乾、易燃等，WIP）
├── DemoScenes/              # 主選單、遊玩關卡示範場景
├── DynamicFootstepSystem/   # 動態腳步音效系統（材質偵測）
├── EasyMenus/               # 主選單/暫停/選項選單框架
├── InventoryPD/             # 物品欄系統（Resource 驅動，Grid-based）
│   ├── CustomResources/     # InventoryItemPD 基類及各子類
│   ├── Inventories/         # 物品欄 .tres 資源
│   ├── Items/               # 具體物品 .tres 資源
│   └── UiScenes/            # 物品欄 UI 場景
├── Localization/            # 多語言（EN / DE）
├── PackedScenes/            # 玩家HUD、死亡畫面、撿取物等預製場景
├── QuestSystem/             # 任務系統（Manager + Resource + UI + Updater）
├── SceneManagement/         # 場景切換、存/讀檔、持久化
├── Scripts/                 # 各種通用腳本（Wieldable基類、交互RayCast、HUD管理器…）
├── Theme/                   # UI 主題
├── Wieldables/              # 具體武器/道具實作（手電筒、手槍、鐵鎬…）
├── cogito_globals.gd        # Autoload：全域設定快取
├── cogito_plugin.gd         # 插件入口
└── cogito_settings.gd       # 設定資源類別
```

---

## 核心架構模式

### 1. 組件式互動系統 (Component-based Interactions)
- **`InteractionComponent`**（`Components/Interactions/InteractionComponent.gd`）為所有互動的基類。
- 子類包含：`BasicInteraction`、`PickupComponent`、`CarryableComponent`、`LockInteraction`、`HoldInteraction`、`DualInteraction`、`ReadableComponent`、`DialogicInteraction` 等。
- 每個組件透過 `input_map_action`、`interaction_text`、`attribute_check` 三個核心 @export 屬性即可在 Inspector 設定互動行為。

### 2. 玩家系統 (`CogitoPlayer`)
- 繼承 `CharacterBody3D`，腳本位於 `CogitoObjects/cogito_player.gd`。
- 分層節點結構：`Body → Neck → Head → Eyes → Camera`。
- 大量 @export 屬性（移動速度、頭部晃動、跑跳蹲滑梯樓梯、手把靈敏度…）可在 Inspector 微調。
- 持有 `PlayerInteractionComponent`、`player_attributes`（Dictionary）、`inventory_data`（CogitoInventory Resource）。

### 3. Resource 驅動的物品欄 (Resource-based Inventory)
- 物品定義為 `InventoryItemPD`（及其子類：`ConsumableItemPD`、`WieldableItemPD`、`KeyItemPD`、`AmmoItemPD`、`CombinableItemPD`、`CurrencyItemPD`）的 `.tres` 資源。
- `CogitoInventory` Resource 儲存 `Array[InventorySlotPD]`，UI 與邏輯分離。
- 快速使用槽（`CogitoQuickSlots`）另外管理 Wieldable 裝備順序。

### 4. NPC 狀態機 (`CogitoNPC`)
- NPC 繼承 `CharacterBody3D`，狀態機節點 `NPC_State_Machine`（`npc_state_machine.gd`）以子節點管理各狀態。
- 狀態列表：`idle`、`patrol_on_path`、`move_to_random_pos`、`chase`、`attack`、`switch_stance`。
- 狀態間切換透過 `States.goto("state_name")` 呼叫，支援 `_state_enter` / `_state_exit` hook。

### 5. Wieldable（可持用物件）基類
- `CogitoWieldable`（`Scripts/cogito_wieldable.gd`）定義介面：`equip()`、`unequip()`、`action_primary()`、`action_secondary()`、`reload()`。
- 具體實作繼承此類並覆寫對應函數（`wieldable_toy_pistol.gd`、`wieldable_flashlight.gd` 等）。

### 6. 場景管理與存檔
- `CogitoSceneManager`（Autoload）統一處理場景切換與存/讀檔。
- 玩家狀態存至 `CogitoPlayerState` Resource，場景狀態存至 `CogitoSceneState` Resource。

### 7. 任務系統
- `CogitoQuestManager`（Autoload）管理 active/available/completed/failed 四個 QuestGroup。
- 任務定義為 `CogitoQuest` Resource（`.tres`），透過 `CogitoQuestUpdater` 組件觸發進度更新。

---

## Physics Layers（`project.godot`）
- Layer 1：`Environment`（環境碰撞）
- Layer 2：`Interactables`（可互動物件）

---

## 主入口場景
`res://addons/cogito/DemoScenes/COGITO_0_MainMenu.tscn`
