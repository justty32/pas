# Cogito 整體架構速查表

> 涵蓋 Level 1–5 所有主要系統 + 小工具組件清單。  
> 每個系統的深度分析見 `architecture/level*.md` 對應文件。

---

## 一、技術棧與 Autoload

| 項目 | 說明 |
|---|---|
| 引擎 | Godot 4.4，GDScript |
| 核心 Autoload | `CogitoGlobals`、`CogitoSceneManager`、`CogitoQuestManager`、`Audio`（quick_audio）、`InputHelper` |
| 物品欄資料 | `CogitoInventory`（Resource，存於玩家節點） |
| 存檔格式 | JSON（`user://cogito_save_*.json`） |
| 主要 Addon | Cogito（本體）、quick_audio、input_helper |
| 選用 Addon | Dialogic（時間軸對話）、Dialogue Nodes（泡泡對話） |

---

## 二、核心類別速查

### 2A 玩家相關

| 類別 | 檔案 | 職責 |
|---|---|---|
| `CogitoPlayer` | `CogitoObjects/cogito_player.gd` | 主角移動、屬性容器、信號樞紐 |
| `PlayerInteractionComponent` | `Components/PlayerInteractionComponent.gd` | 射線互動、持武器管理、搬運狀態 |
| `CogitoQuickSlots` | `InventoryPD/CogitoQuickSlots.gd` | 快捷槽管理、武器循環切換 |
| `AutoPickUpZone` | `Components/AutoPickUpZone.gd` | 玩家附近自動撿取指定物品 |

### 2B 屬性系統

| 類別 | 檔案 | 重點 |
|---|---|---|
| `CogitoAttribute` | `Components/Attributes/cogito_attribute.gd` | 基類，響應式 setter，`is_locked` 穿透 |
| `cogito_health_attribute` | `…/cogito_health_attribute.gd` | `death` 信號，`spawn_on_death`，三種音效 |
| `cogito_stamina_attribute` | `…/cogito_stamina_attribute.gd` | 坡度感知耗盡，`regen_timer`，bunny_hop_speed |
| `cogito_sanity_attribute` | `…/cogito_sanity_attribute.gd` | 持續衰減/恢復，零理智扣血，Visibility 連線 |
| `cogito_light_meter_attribute` | `…/cogito_light_meter_attribute.gd` | SubViewport 單像素採樣，Lanczos 1×1 |
| `cogito_visibility_attribute` | `…/cogito_visibility_attribute.gd` | 空殼，外部 LightzoneComponent 設值 |

### 2C 物品欄資料層

| 類別 | 檔案 | 重點 |
|---|---|---|
| `CogitoInventory` | `InventoryPD/cogito_inventory.gd` | Grid 空間管理，pick_up/combine 邏輯 |
| `InventoryItemPD` | `InventoryPD/CustomResources/InventoryItemPD.gd` | `item_size`（多格物品），`get_region()` 裁切圖示 |
| `InventorySlotPD` | `InventoryPD/CustomResources/InventorySlotPD.gd` | `origin_index` 格子編碼，`can_merge_with()` |
| `WieldableItemPD` | `…/WieldableItemPD.gd` | 雙態 `use()`（裝備/放下） |
| `ConsumableItemPD` | `…/ConsumableItemPD.gd` | `use()` → 屬性修改 |
| `AmmoItemPD` | `…/AmmoItemPD.gd` | `reload_amount` 子彈數 |
| `KeyItemPD` | `…/KeyItemPD.gd` | 鑰匙型物品，`key_name` 比對 |

### 2D 物品欄 UI 層

| 類別 | 檔案 | 重點 |
|---|---|---|
| `inventory_interface` | `InventoryPD/UiScenes/inventory_interface.gd` | 頂層協調，`grabbed_slot_data` 拖放狀態，ShapeCast3D 安全丟棄 |
| `InventoryUI` | `InventoryPD/UiScenes/InventoryUI.gd` | Grid 全量重建，`highlight_slots()`，`out_of_bounds()` |
| `SlotPanel` | `InventoryPD/UiScenes/Slot.gd` | 單格 UI，`origin_index` 格子編碼，手把輸入 |
| `hot_bar_inventory` | `InventoryPD/UiScenes/hot_bar_inventory.gd` | Grid/Non-Grid 雙模式快捷欄 |
| `CogitoQuickslotContainer` | `InventoryPD/UiScenes/CogitoQuickslotContainer.gd` | 單格快捷槽容器，右鍵清除 |

### 2E 互動組件基類與子類

```
InteractionComponent（基類）
  ├─ BasicInteraction       — 轉發 parent.interact()，可選 AttributeCheck
  ├─ HoldInteraction        — 長按互動，觸發 HUD 計時 UI
  │    ├─ DualInteraction   — 快按 + 長按雙操作（整合 LockInteraction）
  │    └─ ExtendedPickupInteraction — 地上物品直接使用/裝填/裝備
  ├─ CustomInteraction      — 代理，呼叫 parent_node 指定方法名
  ├─ ReadableComponent      — 書本/告示 UI（RichTextLabel + 捲軸）
  ├─ BackpackComponent      — 擴充玩家物品欄大小
  ├─ CarryableComponent     — 物理搬運（RigidBody 浮動 + 手動旋轉）
  ├─ PickupComponent        — 撿起物品
  ├─ LockInteraction        — 橋接鎖定機制
  ├─ DialogicInteraction    — Dialogic 插件整合（需安裝 + 取消注解）
  └─ DialogueNodesInteraction — Dialogue Nodes 插件整合（需安裝 + 取消注解）
```

### 2F 場景物件

| 類別 | 檔案 | 重點 |
|---|---|---|
| `CogitoObject` | `CogitoObjects/cogito_object.gd` | 基類，AABB 提示位置，持久化群組 |
| `CogitoStaticInteractable` | `CogitoObjects/cogito_static_interactable.gd` | 不可移動的可互動物件 |
| `CogitoDoor` | `CogitoObjects/cogito_door.gd` | 旋轉/滑動/動畫三型態，鎖定，雙門同步 |
| `CogitoSwitch` | `CogitoObjects/cogito_switch.gd` | 觸發鏈，物品條件，節點顯隱 |
| `CogitoContainer` | `CogitoObjects/cogito_container.gd` | 外部物品欄信號模式 |
| `CogitoKeypad` | `CogitoObjects/cogito_keypad.gd` | 密碼 UI，直連 CogitoDoor |
| `CogitoVendor` | `CogitoObjects/cogito_vendor.gd` | 貨幣交易，動態生成物品 |
| `CogitoPressurePlate` | `CogitoObjects/cogito_pressure_plate.gd` | 物理位移偵測，雙重策略 |
| `CogitoSnapSlot` | `CogitoObjects/cogito_snap_slot.gd` | cogito_name 識別，凍結吸附 |
| `CogitoProjectile` | `CogitoObjects/cogito_projectile.gd` | 四情境碰撞，PinJoint3D 黏附 |
| `CogitoButton` | `CogitoObjects/cogito_button.gd` | 單次/重複按鈕，物品檢查，觸發鏈，貨幣消費 |
| `CogitoSittable` | `CogitoObjects/cogito_sittable.gd` | 坐下系統，四種 PlacementOnLeave 模式 |
| `CogitoVehicle` | `CogitoObjects/cogito_vehicle.gd` | 繼承 CogitoSittable，momentum 物理移動 |
| `CogitoSecurityCamera` | `CogitoObjects/cogito_security_camera.gd` | 四態偵測狀態機，可選 Lightmeter 感光加成 |

### 2G NPC

| 類別 | 檔案 | 重點 |
|---|---|---|
| `CogitoNpc` | `CogitoNPC/cogito_npc.gd` | 動畫混合，擊退，存讀檔 |
| `NpcStateMachine` | `CogitoNPC/npc_states/npc_state_machine.gd` | 場景樹掛載狀態機，`goto()`/`previous_state` |
| 狀態 | `npc_states/npc_state_*.gd` | idle / patrol_on_path / move_to_random_pos / chase / attack / switch_stance |

### 2H Wieldable（持械）

| 類別 | 檔案 | 重點 |
|---|---|---|
| `cogito_wieldable` | `Scripts/cogito_wieldable.gd` | 基類 |
| `wieldable_toy_pistol` | `Wieldables/wieldable_toy_pistol.gd` | 彈丸池，ADS 瞄準 |
| `wieldable_laser_rifle` | `Wieldables/wieldable_laser_rifle.gd` | Hitscan 連發，BulletDecalPool |
| `wieldable_pickaxe` | `Wieldables/wieldable_pickaxe.gd` | 雙模式命中（射線/AABB），耗耐力 |
| `wieldable_flashlight` | `Wieldables/wieldable_flashlight.gd` | 電量耗盡，防連點 |
| `wieldable_throwable` | `Wieldables/wieldable_throwable.gd` | 物品欄自動管理，投擲後消耗 |

### 2I 存讀檔

| 類別 | 檔案 | 重點 |
|---|---|---|
| `CogitoSceneManager` | `SceneManagement/cogito_scene_manager.gd` | 雙群組持久化（Persist / save_object_state），temp 緩衝槽 |
| `cogito_player_state` | `SceneManagement/cogito_player_state.gd` | Resource 序列化，Vector2 壓縮，坐姿完整保存 |
| `cogito_scene_state` | `SceneManagement/cogito_scene_state.gd` | Persist 再實例化，屬性反射 |
| `loading_screen` | `SceneManagement/loading_screen.gd` | 非同步載入，SceneLoadMode 枚舉 |
| `cogito_scene` | `SceneManagement/cogito_scene.gd` | Connector 傳送點，`save_temp_on_enter` |

### 2J 任務系統

| 類別 | 檔案 | 重點 |
|---|---|---|
| `CogitoQuest` | `QuestSystem/CustomResources/cogito_quest.gd` | `quest_counter` setter，三狀態 |
| `CogitoQuestGroup` | `…/cogito_quest_group.gd` | 群組陣列容器，四子類 |
| `CogitoQuestManager` | `QuestSystem/cogito_quest_manager.gd` | 群組狀態機，反射方法 |
| `CogitoQuestUpdater` | `QuestSystem/Components/cogito_quest_updater.gd` | 四操作類型，`has_been_triggered` 防重複 |

### 2K Loot 系統

| 類別 | 檔案 | 重點 |
|---|---|---|
| `LootDropEntry` | `Components/LootTables/LootDropEntry.gd` | `DropType`：NONE/GUARANTEED/CHANCE/QUEST |
| `LootTable` | `Components/LootTables/BaseLootTable.gd` | drops 陣列容器 |
| `LootGenerator` | `InventoryPD/cogito_loot_generator.gd` | 加權隨機，unique/quest 跨容器掃描，32次 failsafe |
| `LootComponent` | `Components/LootComponent.gd` | SPAWN_ITEM 散射 / SPAWN_CONTAINER 戰利品袋 |

### 2L 物質反應系統

| 類別 | 檔案 | 重點 |
|---|---|---|
| `CogitoProperties` | `Components/Properties/cogito_properties.gd` | 雙層位元旗標，閾值計時器，反應矩陣，VFX 池 |
| `HitboxComponent` | `Components/HitboxComponent.gd` | 傷害橋接到 CogitoProperties |
| `ImpactAttributeDamage` | `Components/ImpactAttributeDamage.gd` | 速度閾值衝擊傷害 |
| `explosion` | `Assets/VFX/Explosion_01/explosion.gd` | Area3D 爆炸，範圍傷害 |

### 2M AutoConsume 子系統

| 類別 | 檔案 | 重點 |
|---|---|---|
| `AutoConsume` | `Components/AutoConsumes/auto_consume.gd` | 屬性觸發自動消耗，`threshold_value`，`consume_on_increase` |
| `HealthAutoConsume` | `…/health_auto_consume.gd` | `prevent_death()` 在死亡前攔截消耗 |
| `StaminaAutoConsume` | `…/stamina_auto_consume.gd` | 耐力自動消耗 |

---

## 三、關鍵信號流

```
玩家按下互動鍵
  → PlayerInteractionComponent._handle_interact_input()
  → interaction_raycast._set_interactable(target)
  → target.find_children("","InteractionComponent")
  → InteractionComponent.interact(PIC)

物品撿取
  → PickupComponent.interact(PIC)
  → CogitoInventory.pick_up_slot_data(slot)
  → inventory_updated.emit()
  → InventoryUI.populate_item_grid()   ← 全量重建

敵人死亡
  → CogitoHealthAttribute.death.emit()
  → LootComponent._spawn_loot() / _spawn_loot_container()

屬性歸零
  → CogitoAttribute.attribute_reached_zero.emit()
  → AutoConsume._auto_consume()  （若有掛載）
  → CogitoHealthAttribute.on_death()  （生命值）

場景切換
  → SceneTransitionZone.transition_to_next_scene()
  → CogitoSceneManager.save_scene_state("temp")
  → CogitoSceneManager.load_next_scene(path, connector, "temp", TEMP)
```

---

## 四、存讀檔架構

```
存檔槽（"permanent" | "temp" | 數字索引）
  ├─ player_state.json        ← cogito_player_state.gd（Resource 序列化）
  └─ <scene_name>.json        ← cogito_scene_state.gd

持久化群組：
  "Persist"           → 跨場景重新實例化
  "save_object_state" → 原地呼叫 save() / set_state()
```

---

## 五、互動組件附加規則

- 任何繼承 `InteractionComponent` 的節點，掛在場景物件下即自動被 `PlayerInteractionComponent` 掃描
- `was_interacted_with` 信號由 PIC 監聽，驅動提示消失動畫
- `is_disabled = true` 可在執行期鎖定任何互動組件
- `attribute_check` 欄位讓互動需要玩家具備特定屬性值

---

## 六、小工具組件速查

### 6A InteractionComponent 子類（輕量型）

| 類別 | 檔案 | 一句話說明 |
|---|---|---|
| `BasicInteraction` | `Components/Interactions/BasicInteraction.gd` | 最簡互動：轉發 `parent_node.interact()`；可選屬性門檻（AttributeCheck）；監聽 `object_state_updated` 同步提示文字 |
| `HoldInteraction` | `Components/Interactions/HoldInteraction.gd` | 長按計時互動：觸發 `hud.hold_ui.start_holding(self)`；計時完成後外部決定效果 |
| `DualInteraction` | `Components/Interactions/DualInteraction.gd` | 繼承 `HoldInteraction`；支援快按（`on_quick_press`）+ 長按（`on_hold_complete`）雙操作；整合 `LockInteraction` 的 `start_hold_check()` 前置驗證 |
| `ExtendedPickupInteraction` | `Components/Interactions/ExtendedPickupInteraction.gd` | 繼承 `HoldInteraction`；讓場景中物品可直接「使用/裝填/裝備」（Consumable/Ammo/Wieldable）而無需先撿進背包；會停用同物件的 `PickupComponent`，確保兩者不衝突 |
| `CustomInteraction` | `Components/Interactions/CustomInteraction.gd` | 通用代理：`@export var function_to_call : String`，互動時以 `Callable(parent, func_name)` 呼叫任意方法 |
| `ReadableComponent` | `Components/Interactions/ReadableComponent.gd` | 顯示書本/告示 UI（RichTextLabel + ScrollContainer）；支援 BBCode；互動再按一次 or ESC 關閉；觸發 `toggled_interface`（隱藏準心） |
| `BackpackComponent` | `Components/Interactions/BackpackComponent.gd` | 互動後擴充玩家物品欄大小（`new_inventory_size`）；流程：臨時備份所有槽 → 調整 `inventory_size` → 重新裝入 → 自毀父物件 |

### 6B Area3D 觸發區域

| 類別 | 檔案 | 一句話說明 |
|---|---|---|
| `LightzoneComponent` | `Components/LightzoneComponent.gd` | 玩家進入 → `increase_attribute("visibility", 1)`；退出 → `decrease_attribute("visibility", 1)`；搭配 `cogito_visibility_attribute` 使用 |
| `LightzoneSwitchComponent` | `Components/LightzoneSwitchComponent.gd` | 附掛在 Lightzone Area3D 下；連接 CogitoSwitch 的 `switched` 信號 → 開關 `lightzone.set_monitoring(is_on)` |
| `SafezoneComponent` | `Components/SafezoneComponent.gd` | 玩家進入 → `brightness_component.add(1)`（安全區光源計數）；退出 → `subtract(1)`；與 Sanity/Visibility 系統聯動 |
| `cogito_attribute_zone` | `Scripts/cogito_attribute_zone.gd` | 可配置的通用屬性增減區域；支援持續（`effect_delay=0` → `amount*delta`）或間隔（`effect_delay>0` → 每N秒觸發）；可增可減；定期顯示提示；支援執行期開關（`interact()` 切換 `is_active`） |
| `hazard_zone` | `Scripts/hazard_zone.gd` | 簡化版持續扣/補屬性區域（`drain_amount*delta`）；不支援間隔觸發；適合毒霧/回血池等簡單場景 |
| `gravity_zone` | `PackedScenes/gravity_zone.gd` | 玩家進入 → `player.override_gravity(gravity, direction)`；退出 → 恢復 ProjectSettings 預設重力 |
| `scene_transition_zone` | `Scripts/scene_transition_zone.gd` | 玩家進入 → 儲存玩家+場景狀態至 "temp" 槽 → `CogitoSceneManager.load_next_scene(path, connector, "temp", TEMP)` |
| `door_setter_zone` | `Scripts/door_setter_zone.gd` | 玩家進入時動態修改門屬性（旋轉角/滑動位置/動畫名）；可選進入自動開、離開自動關（含延遲） |
| `ladder_area` | `Scripts/ladder_area.gd` | 以 `body_shape_entered` 計算梯子朝向，呼叫 `player.enter_ladder(shape_node, dir)`；退出時 `on_ladder = false` 並恢復梯子碰撞 Process Mode |

### 6C 場景工具 Node

| 類別 | 檔案 | 一句話說明 |
|---|---|---|
| `AutoPickUpZone` | `Components/AutoPickUpZone.gd` | 掛在玩家下的 Area3D；物品進入 → 加入 `pickup_item_pool` 佇列 → 每幀逐一撿取（支援 `defer_queue_processing`）；根據蹲伏切換碰撞形狀；以名稱白名單過濾物品 |
| `ImpactSounds` | `Components/ImpactSounds.gd` | 掛在 RigidBody3D 下；碰撞時播放 `AudioStreamRandomizer`；`next_impact_time` 防止連續觸發 |
| `cogito_spawnzone` | `Scripts/cogito_spawnzone.gd` | 在指定 BoxShape3D 範圍內隨機位置生成多個 PackedScene；`spawn_objects()` 由外部信號呼叫（預設連接 `generic_button_pressed`） |
| `inventory_checker` | `Scripts/inventory_checker.gd` | 監聽指定 CogitoContainer 的物品欄；`check_inventory()` 找到目標物品後發射 `item_found` 信號（適合謎題觸發） |

### 6D 動態腳印系統

| 類別 | 檔案 | 一句話說明 |
|---|---|---|
| `FootstepSurfaceDetector` | `DynamicFootstepSystem/Scripts/footstep_surface_detector.gd` | 繼承 `AudioStreamPlayer3D`；向下射線找地面；三層優先級：① 子節點 `FootstepSurface` → ② `FootstepMaterialLibrary` 材質比對 → ③ 通用備援音效；支援多面 mesh 的三角形面材質查找 |
| `FootstepSurface` | `DynamicFootstepSystem/Scripts/footstep_surface.gd` | 附掛在地板物件子節點；存放 `footstep_profile : AudioStreamRandomizer`；讓特定物件覆寫材質庫音效 |
| `FootstepMaterialLibrary` | `DynamicFootstepSystem/Scripts/footstep_material_library.gd` | `Material → AudioStreamRandomizer` 的對應字典；`get_footstep_profile_by_material(mat)` 查詢 |

### 6E 安全攝影機

| 類別 | 檔案 | 一句話說明 |
|---|---|---|
| `CogitoSecurityCamera` | `CogitoObjects/cogito_security_camera.gd` | 四態狀態機（OFFLINE/SEARCHING/DETECTING/DETECTED）；`detection_threshold` 秒後發射 `object_detected`；`DetectionMethod.LIGHTMETER` 模式：`detection_time += delta * (light_level * multiplier)`，光越亮越快被偵測；LED 指示燈顏色與狀態同步 |

### 6F 載具

| 類別 | 檔案 | 一句話說明 |
|---|---|---|
| `CogitoVehicle` | `CogitoObjects/cogito_vehicle.gd` | 繼承 `CogitoSittable`（`physics_sittable=true`）；玩家坐上後 WASD 控制 `vehicle_node` 移動與旋轉；`momentum_damping` 提供慣性效果 |

### 6G 互動子類（AutoConsume）

| 類別 | 檔案 | 一句話說明 |
|---|---|---|
| `AutoConsume` | `Components/AutoConsumes/auto_consume.gd` | 掛在玩家下；監聽屬性信號，低於 `threshold_value` 時自動從物品欄取用第一個有效消耗品；支援 `consume_on_increase`（屬性上升時消耗，如吃 max HP 上升藥）；`consume_if_increases_max` 撿取時立即消耗 |
| `HealthAutoConsume` | `Components/AutoConsumes/health_auto_consume.gd` | `AutoConsume` 子類；特化 `prevent_death()`：在 HP 歸零前攔截，嘗試消耗回血道具抵消致死傷害 |
| `StaminaAutoConsume` | `Components/AutoConsumes/stamina_auto_consume.gd` | `AutoConsume` 子類；耐力歸零自動消耗耐力恢復道具 |

---

## 七、常用設計模式索引

| 模式 | 典型實作位置 |
|---|---|
| **響應式 setter**（值改變才發信號） | `CogitoAttribute.value_current` setter |
| **全量重建 UI**（更新時清除重建所有子節點） | `InventoryUI.populate_item_grid()` |
| **場景樹掛載狀態機** | `NpcStateMachine._ready()` + `goto()` |
| **雙群組持久化**（Persist vs save_object_state） | `CogitoSceneManager.save_scene_state()` |
| **浮動物理搬運**（設速度而非位置） | `CarryableComponent._physics_process()` |
| **Raycast 例外管理** | `CarryableComponent.hold()` → `add_exception()` |
| **UI 暫停協議** | `toggled_interface.emit(true/false)` |
| **加權隨機抽取** | `LootGenerator._roll_for_randomized_items()` |
| **ShapeCast3D 安全放置** | `inventory_interface._drop_item()` |
| **resource_local_to_scene** | `LootComponent._spawn_loot_container()` |
| **SubViewport 單像素採樣** | `cogito_light_meter_attribute.get_average_color()` |
| **`find_children("","ClassName")` 反射掃描** | `CogitoPlayer._ready()` 初始化屬性字典 |
| **信號連線保護**（`is_connected` 防重複） | `DialogicInteraction.start_dialogue()` |
| **三次 body_test_motion 階梯判定** | `cogito_player.gd` `_handle_stairs()` |
