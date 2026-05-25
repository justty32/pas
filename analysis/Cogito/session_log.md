# Cogito 分析日誌

## 2026-05-25（生成 HTML 導覽層）

- 生成 `html/` 導覽層（`_shared.css`、`index.html`、`architecture.html`、`tutorial.html`、`details.html`），涵蓋 15 篇架構、25 篇教學、2 篇細節的全量索引，含信號流視覺化、難度分級、分析涵蓋範圍交叉表。

## 2026-05-25（新增 6 份 tutorial）

- **新增 `paper_doll_equipment.md`**：`EquipmentItemPD`（繼承 `InventoryItemPD`，新增 `equip_slot`/`defense_bonus`/`equip_mesh`）、`EquipmentManager`（BoneAttachment3D 掛載、`equip`/`unequip`/`get_total_defense`）、`decrease_attribute` 防禦攔截、`use()` 觸發裝備/卸下、存讀檔整合。
- **新增 `quest_creation_workflow.md`**：`CogitoQuest` 資源欄位說明（`cogito_quest.gd`）、計數型 vs 直接完成型任務設計、`CogitoQuestUpdater` 兩種觸發方式（Area3D/NPC 死亡）、`CogitoQuestManager` 完整 API 速查、Dialogic 整合（QuestBridge Autoload、Timeline `[call]` 語法）、`ui_quest_hud.gd` 自動更新機制解析。
- **新增 `shop_merchant_system.md`**：`CogitoCurrency`（`cogito_currency.gd`）設定、`player.increase_currency`/`decrease_currency`（`cogito_player.gd:306-321`）、`ItemValue` 資源、`ShopData` + `ShopEntry` 商品資源設計、`ShopComponent`（`try_buy`/`try_sell`）、`ShopBridge` Autoload 接 Dialogic、簡化版直接互動商店。
- **新增 `skill_tree_ui.md`**：`PerkData` 資源（`required_level`/`prerequisite_perk_id`/`effect_type`）、`PerkManager` Autoload（`can_unlock`/`unlock`/`get_total_effect`）、`PerkNode` 場景（灰/白/金三種狀態）、`SkillTreeUI` 主控腳本、天賦效果套用到傷害/耐力計算、K 鍵開啟入口。
- **新增 `day_night_cycle_visual.md`**：`DayNightController`（`DirectionalLight3D` 旋轉、`ProceduralSkyMaterial` 顏色插值、月光強度）、`TimeSystem` 補充 `minute_changed` 信號、霧氣密度隨時段變化、時鐘 HUD `Label`。
- **新增 `shout_system.md`**：`ShoutData` 資源（三段充能/各段冷卻）、`ShoutManager` Autoload（連按窗口 0.6s/`press_shout`/`_execute_shout`）、Input Map 獨立 Z 鍵（`_unhandled_input` 接入點）、`ShoutExecutor`（推飛/慢動作/火焰/瞬移四種效果）、冷卻條 HUD。

## 2026-05-25（details 深化）

- **`dynamic_generation_implementation.md` 深化**：補充兩套群組機制（`Persist` vs `save_object_state`）對比表、`save_scene_state`/`load_scene_state` 原始碼逐行解析（含行號）、`CogitoObject.save()` 完整字典格式（`cogito_object.gd:91-119`）、`set_state()` 行為（`cogito_object.gd:70-77`）、存檔暫存機制（temp→slot 流程）、`CogitoSpawnZone` 完整原始碼解析（BoxShape3D 限制/父節點固定為場景根/Persist 由物件自身決定）、常見陷阱更新（`set()` 反射型別問題）。
- **`skyrim_clone_roadmap.md` 深化**：為六大系統各補充具體 COGITO 接入點與完整代碼——(1) ChunkManager 非同步載入核心迴圈；(2) TimeSystem + ScheduleComponent 完整代碼（含 Dictionary String→int 轉換）；(3) SkillManager Autoload 完整實作 + 近戰命中/受傷 XP 注入點（對應 `HitboxComponent.gd:48`）；(4) EquipmentManager + BoneAttachment3D 全流程（ItemPD 擴充、equip/unequip、`decrease_attribute` 防禦攔截）；(5) MagickaAttribute + 投射物法術 + 龍吼獨立鍵位；(6) CogitoQuestManager 實際 API（`start_quest` 接資源不接字串、`change_quest_counter` 計數器機制）+ Dialogic QuestBridge 橋接。

## 2026-05-25（續）

- **教學文件深化（10 份完整重寫）**：依序深化以下教學，以原始碼對照確保準確性：(1) `skyrim_combat_mechanics.md`：加入完整 `wieldable_sword.gd`，含長按計時重擊、格擋旗標、`apply_knockback()` NPC 失衡、玩家 `decrease_attribute` 攔截；(2) `npc_radiant_ai_schedule.md`：完整 `TimeSystem.gd` Autoload、`ScheduleComponent.gd`（Dictionary 鍵型轉換）、`npc_state_sleep.gd`（尋找最近 Bed Marker、`States.save_state_as_previous`）、`npc_state_work.gd`（工作台導航＋循環動畫）、虛擬模擬整合 `set_state()`；(3) `magic_and_magicka_system.md`：自訂 `CogitoMagickaAttribute`（`notify_cast()` 重置再生延遲）、瞬發/持續/增益三種法術完整代碼、HUD 自動整合原理；(4) `lod_implementation.md`：NPC LOD 腳本（距離閾值停用 `animation_tree.active` 和 `set_physics_process`）、MultiMeshInstance3D 程序化批次；(5) `ui_modification_interaction.md`：完整節點樹路徑、`CogitoAttributeUi` 整合機制、fixed_stamina_bar 用法；(6) `ui_modification_inventory.md`：`SlotPanel` 結構（64px 格子）、InfoPanel 節點路徑、拖放 GrabbedSlot、手把/鍵盤自動切換；(7) `ui_modification_dialogue.md`：明確說明整個橋接腳本被注解、完整取消注解步驟、`toggled_interface` 機制；(8) `open_world_architecture.md`：完整 `ChunkManager.gd` Autoload（非同步載入佇列/卸載/Chunk 存讀）、Origin Rebasing 抖動修正、Terrain3D 腳步聲整合；(9) `genshin_style_rendering.md`：完整 Toon Shader（light() 函數/Rim Light）、Backface Outline Shader、風格化草地 Wind Sway Shader；(10) `visual_presentation_and_rendering.md`：完整環境節點設定路徑、Shadow Mode 建議、FSR 位置、LUT 色彩校正說明。

## 2026-05-25

- **教學文件勘誤（8 處錯誤修正）**：對照原始碼逐一驗證 19 份教學，發現並修正以下錯誤：(1) `adding_character_actions.md`：`Host.navigation_agent` → `navigation_agent_3d`，`Host.set_navigation_target()` 不存在 → 改為直接設定 `navigation_agent_3d.target_position`；(2) `advanced_action_movement.md`：`PlayerInteractionComponent.is_invulnerable` 不存在，`get_current_wieldable()` 不存在 → 改為 `equipped_wieldable_node`；(3) `destructible_objects.md`：`HitboxComponent` 無 `damage_received` 信號（它連接父節點信號），`LootComponent.drop_loot()` 不存在（內部自動連接），`spawn_on_death` 是 `Array[PackedScene]`；(4) `dynamic_generation.md`：`CogitoSpawnZone` 本身即 `Area3D`，`object_to_spawn` 是單一 PackedScene 非陣列；(5) `ui_modification_inventory.md`：`inventory_interface.tscn` 不存在，demo 場景無 COGITO_1；(6) `ui_modification_dialogue.md`：`toggled_interface` emit 已被注解掉；(7) `npc_ai_behavior.md`：補充 NPC 預設不屬於 "Enemy" 群組的前提說明；(8) `magic_and_magicka_system.md`：`auto_regenerate`/`regen_speed` 屬性只在 `CogitoStaminaAttribute` 而非基類 `CogitoAttribute`。

## 2026-04-30

- **Level 1 初始探索**：讀取 README、project.godot、目錄結構、cogito_globals.gd、cogito_player.gd（前段）、InteractionComponent.gd、cogito_wieldable.gd、cogito_npc.gd（前段）、npc_state_machine.gd；撰寫 `architecture/level1_overview.md`，涵蓋技術棧、Autoload 清單、模組一覽、六大核心架構模式。
- **Level 2 核心模組職責**：深度閱讀 cogito_player.gd 完整 `_physics_process` 流程、PlayerInteractionComponent.gd、InteractionComponent.gd（含所有子類清單）、cogito_inventory.gd（Grid 空間管理、pick_up/combine 邏輯）、InventoryItemPD 繼承鏈、WieldableItemPD 雙態 use()、cogito_attribute.gd（setter 驅動響應式數值）、cogito_scene_manager.gd（槽式存讀檔架構）；撰寫 `architecture/level2_core_modules.md`。
- **Level 3A 互動物件系統**：深度閱讀 cogito_object.gd（基類 AABB/持久化）、cogito_door.gd（三型態/雙向旋轉/鎖定/自動關門/雙門同步）、cogito_switch.gd（觸發鏈/物品條件/節點顯隱/子彈觸發）、cogito_container.gd（外部物品欄信號模式）、cogito_keypad.gd（密碼 UI/聚焦管理/直連 CogitoDoor）、cogito_vendor.gd（貨幣交易/動態生成）、cogito_pressure_plate.gd（物理位移偵測/雙重策略）、cogito_snap_slot.gd（cogito_name 識別/凍結吸附/動態信號切換）、cogito_projectile.gd（四情境碰撞/PinJoint3D 黏附/spawn_on_death）、LockInteraction.gd（橋接組件）；撰寫 `architecture/level3_interactive_objects.md`。
- **Level 3B NPC 狀態機行為**：深度閱讀 cogito_npc.gd（face_direction/動畫混合/擊退/存讀檔）、npc_state_machine.gd（場景樹掛載機制/goto/previous_state）、五個狀態（idle/patrol_on_path/move_to_random_pos/chase/attack/switch_stance）；撰寫 `architecture/level3_npc_states.md`。
- **Level 3C Wieldable 玩家動作**：深度閱讀五個 Wieldable 實作（toy_pistol 彈丸池/ADS、laser_rifle Hitscan 連發/BulletDecalPool、pickaxe 雙模式命中偵測/耐力、flashlight 電量耗盡/防連點、throwable 物品欄自動管理）；撰寫 `architecture/level3_wieldables.md`。
- **Level 4A CogitoProperties 物質反應系統**：深度閱讀 cogito_properties.gd（雙層位元旗標/閾值計時器/反應矩陣/VFX 池）、cogito_object.gd 接觸觸發路徑、cogito_projectile.gd 直接呼叫路徑、HitboxComponent.gd（傷害橋接）、ImpactAttributeDamage.gd（速度閾值衝擊）、explosion.gd（Area3D 爆炸）；記錄 VFX Bug（≤ 應為 ≥）；撰寫 `architecture/level4_properties_system.md`。
- **Level 4B 存讀檔完整流程**：深度閱讀 cogito_scene_manager.gd（雙群組持久化/temp緩衝槽/同場景vs跨場景讀取）、cogito_player_state.gd（Resource序列化/Vector2屬性壓縮/坐姿與Transform完整保存）、cogito_scene_state.gd（Persist再實例化/save_object_state屬性反射）、loading_screen.gd（非同步載入/SceneLoadMode枚舉）、cogito_scene.gd（Connector傳送點/save_temp_on_enter）、world_property_setter.gd（全域旗標寫入）、PlayerInteractionComponent.save()/set_state()；撰寫 `architecture/level4_save_load_system.md`。
- **Level 4C 任務系統**：深度閱讀 cogito_quest.gd（響應式 quest_counter setter/三狀態描述/音效）、cogito_quest_group.gd（陣列型群組/四子類）、cogito_quest_manager.gd（群組狀態機流程/start/complete/fail/change_counter/反射方法）、cogito_quest_updater.gd（四操作類型/has_been_triggered防重複/自動啟動/save持久化）、ui_quest_hud.gd（全量重建模式/通知訊號/本地化）、quest_entry.gd；記錄四個已知問題（update未實作/id注解/==vs>=/has_been_triggered不可重置）；撰寫 `architecture/level4_quest_system.md`。
- **Level 5A 物品欄 UI 系統**：深度閱讀 inventory_interface.gd（頂層協調器/grabbed_slot_data拖放/ShapeCast3D安全丟棄/手把二維狀態機）、InventoryUI.gd（全量重建/格子高亮/out_of_bounds偵測）、Slot.gd（origin_index格子編碼/charge_label響應式/手把輸入）、InventorySlotPD.gd（can_merge_with/create_single_slot_data）、InventoryItemPD.gd（item_size/get_region裁切）、hot_bar_inventory.gd（grid/non-grid雙模式）、CogitoQuickSlots.gd（自動快捷槽/武器循環切換）、CogitoQuickslotContainer.gd；撰寫 `architecture/level5a_inventory_ui.md`。
- **Level 5B Attribute 子類深度**：深度閱讀 cogito_attribute.gd（value_current setter/is_locked穿透/字典注冊）、cogito_health_attribute.gd（death信號/spawn_on_death/三種音效）、cogito_stamina_attribute.gd（坡度感知_run_exhaustion/regen_timer/bunny_hop_speed參照）、cogito_sanity_attribute.gd（decay/recover連續計算/零理智扣血/visibility連接）、cogito_light_meter_attribute.gd（SubViewport單像素採樣/get_luminance/效能節流）、cogito_visibility_attribute.gd（空殼/外部LightzoneComponent設值）；撰寫 `architecture/level5b_attributes.md`。
- **Level 5C Loot 系統**：深度閱讀 LootDropEntry.gd（DropType enum/weight/quest_id/quantity_min_max）、BaseLootTable.gd（drops陣列容器）、cogito_loot_generator.gd（三組分類/rand_weighted加權隨機/unique跨容器掃描/quest物品計數/32次failsafe）、LootComponent.gd（SPAWN_ITEM散射vs SPAWN_CONTAINER戰利品袋/resource_local_to_scene）；記錄三個已知問題；撰寫 `architecture/level5c_loot_system.md`。
- **Level 5D CarryableComponent**：深度閱讀 CarryableComponent.gd（hold/leave/throw流程/浮動物理linear_velocity/手動旋轉camera_basis/超距自動丟下/add_exception管理）；撰寫 `architecture/level5d_carryable.md`。
- **Level 5E 玩家完整移動系統**：深度閱讀 cogito_player.gd 完整 _physics_process（蹲伏/滑行/slide_jump/跳躍/bunny_hop/空中控制/自由視角/樓梯三次body_test_motion/坐下四種離開模式/梯子/落地音效/apply_external_force/override_gravity/RigidBody推力）；撰寫 `architecture/level5e_player_movement.md`。
- **Level 5F 對話整合**：閱讀 DialogicInteraction.gd（全注解/Dialogic.start/timeline_ended/toggled_interface協議）、DialogueNodesInteraction.gd（全注解/dialogue_bubble.start/dialogue_ended/menu_pressed中斷）；撰寫 `architecture/level5f_dialogue.md`。
- **整體架構速查表 + 小組件補全**：閱讀所有未深度分析的小組件（BasicInteraction/HoldInteraction/DualInteraction/ExtendedPickupInteraction/CustomInteraction/ReadableComponent/BackpackComponent/SafezoneComponent/AutoPickUpZone/LightzoneComponent/LightzoneSwitchComponent/cogito_attribute_zone/hazard_zone/gravity_zone/scene_transition_zone/door_setter_zone/ladder_area/AutoPickUpZone/ImpactSounds/cogito_spawnzone/inventory_checker/FootstepSurfaceDetector/CogitoSecurityCamera/CogitoStaticInteractable/CogitoVehicle/CogitoButton/AutoConsume）；撰寫 `architecture/quick_reference.md`。
- **撰寫 UI 修改教學**：根據使用者需求，撰寫了三份教學文件：`tutorial/ui_modification_inventory.md`（物品欄 UI）、`tutorial/ui_modification_interaction.md`（互動提示與 HUD）、`tutorial/ui_modification_dialogue.md`（對話介面整合），涵蓋原始碼導航、實作步驟與驗證方式。
- **撰寫角色動作教學**：撰寫了 `tutorial/adding_character_actions.md`，引導如何為玩家添加衝刺 (Dash) 功能以及為 NPC 建立新的隨機遊走 (Wander) 狀態，詳解了 `cogito_player.gd` 的擴充與 NPC 狀態機的掛載模式。
- **撰寫 3D 物件與特效教學**：撰寫了 `tutorial/adding_objects_and_vfx.md`，涵蓋了靜態擺設、可互動物件、物理物件的 Physics Layer 設定，以及如何透過 `CogitoProperties` 與 `CogitoProjectile` 觸發視覺特效 (VFX)。
- **撰寫進階動作教學**：撰寫了 `tutorial/advanced_action_movement.md`，詳解了如何微調內建的快跑、蹲下、滑步，以及如何手動實作趴下 (Prone)、手動翻滾 (Dodge Roll) 與瞄準減速 (ADS Speed reduction) 等動作遊戲機制。
- **撰寫局部時間緩速教學**：撰寫了 `tutorial/selective_time_dilation.md`，引導如何透過 `local_time_scale` 變數與 `TimeSlowComponent` 實現特定 NPC、物理物件或特效的慢動作效果，而不影響全域遊戲速度。
- **撰寫進階系統教學 (四大主題)**：根據需求撰寫了四份教學文件：`tutorial/elemental_mechanics.md`、`tutorial/destructible_objects.md`、`tutorial/npc_ai_behavior.md`、`tutorial/dynamic_generation.md`。
- **深度剖析動態生成持久化**：撰寫了 `details/dynamic_generation_implementation.md`，詳解 `CogitoSceneManager` 如何處理 `Persist` 群組、存讀檔流程及常見陷阱。
- **撰寫視覺表現與渲染教學**：撰寫了 `tutorial/visual_presentation_and_rendering.md`（天空盒、光影、渲染選項）與 `tutorial/genshin_style_rendering.md`（三渲二、描邊、風格化環境設定）。
- **撰寫開放世界架構指南**：撰寫了 `tutorial/open_world_architecture.md`，說明在 Godot 4 結合 Cogito 開發開放世界時的挑戰與解決方案。
- **撰寫 LOD 教學與 Skyrim 復刻藍圖**：撰寫了 `tutorial/lod_implementation.md` 與 `details/skyrim_clone_roadmap.md`。
- **撰寫 Skyrim 深度機制教學 (四大主題)**：根據復刻目標，撰寫了 `tutorial/skyrim_combat_mechanics.md` (格擋/重擊/失衡)、`tutorial/skyrim_leveling_system.md` (做中學等級系統)、`tutorial/npc_radiant_ai_schedule.md` (NPC 作息排程) 與 `tutorial/magic_and_magicka_system.md` (魔力屬性與法術持用物件)。

