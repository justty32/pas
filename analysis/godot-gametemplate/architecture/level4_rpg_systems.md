# Level 4 Analysis: 遊戲性與 RPG 系統

> 核對於 2026-05-25（Claude Code, Opus 4.7）：本層發現數處與源碼不符，已修正——傷害屬性枚舉、傷害公式、`ItemResource`/`WeaponItemResource` 欄位、背包序列化方式。

## 1. 深度傷害體系
專案的戰鬥邏輯高度模擬了傳統 RPG 的計算方式。

### 1.1 傷害數據結構 (DamageDataResource)
- **檔案路徑**: `addons/top_down/scripts/damage/properties/DamageDataResource.gd`（繼承 `TransmissionResource`）。
- **多重屬性**: 注意專案中存在**兩套 DamageType 枚舉，請勿混淆**：
  - 傷害結算實際使用的是 `DamageTypeResource.DamageType`（`scripts/damage/properties/DamageTypeResource.gd:6-19`）：`PHYSICAL, FIRE, ICE, LIGHTNING, POISON, ACID, MAGNETIC, BLOOD, DARK, ARCANE`（10 種 + `COUNT`）。`base_damage` 陣列中每個 `DamageTypeResource` 帶 `value:float` 與 `type`，並以 `type` 作為 `resistance_value_list` 的索引（`DamageDataResource.gd:105`）。
  - 另有一套 `GameEnums.DamageType`（`scripts/game/GameEnums.gd:4-5`）：`NONE, FIRE, ICE, WATER, LIGHTNING, EARTH, STEAM, SHADOW, CURSE, TOXIC, BLUNT, PIERCE, SLASH, ARCANE`（14 種 + `COUNT`），與前者**不一致**，目前看似為另一組設計枚舉（傷害管線並未引用它）。
- **計算公式**（`DamageDataResource.gd:104-107`）：對每個 `base_damage:Array[DamageTypeResource]` 累加
  `total_damage += max(damage.value * damage_multiply - resistance_value_list[damage.type], 0.0)`，
  並對總傷害 `_health_resource.add_hp(-total_damage)`。`damage_multiply` 預設 1.0，命中時若 `randf() < critical_chance`（預設 0.3，`:11`）則乘上 `critical_multiply`（預設 1.5，`:13`）。
- **攻擊世代 (Generation)**: 
    - `new_generation()` 以 `duplicate_deep(DEEP_DUPLICATE_ALL)` 複製傷害數據並清空 `hit_list`（`DamageDataResource.gd:57-64`）；`new_split()` 則用於同世代分裂（如榴彈碎片，`:67-70`）。
    - 透過 `hit_list` 紀錄已命中對象（`process()` 中 `hit_list.append(...)`，`:91`），避免穿透彈對同一目標重複扣血。

### 1.2 狀態效果 (Status Effects)
- 傷害數據中包含 `status_list:Array[DamageStatusResource]`（`DamageDataResource.gd:16`）。
- 結算時於 `process()` 末段對每個狀態呼叫 `_status.process(resource_node, _damage_resource)`（`:112-113`），由各狀態自行實作（例：`scripts/damage/properties/StatusEffects/TickHealthResource.gd`）。

## 2. 物品與清單管理 (Item System)
物品系統採用了典型的「配置與實例」分離模式。

### 2.1 拾取物機制 (Pickups)
- **ItemPickup**（`scripts/pickups/ItemPickup.gd`）: 負責處理世界中掉落物的物理碰撞與視覺。
- **ItemResource**（`scripts/pickups/ItemResource.gd`）: 實際欄位僅 `icon:Texture2D`、`scene_path:String`、`type:ItemType{WEAPON}`、`unlocked:bool`（`ItemResource.gd:4-14`）。**注意：並無 `id` / `item_name` / `name` 欄位**——物品要實例化的場景由 `scene_path` 字串指定。
- **WeaponItemResource**（`scripts/pickups/WeaponItemResource.gd`）: 目前**僅是空的子類**（`class_name WeaponItemResource extends ItemResource`，全檔 2 行），無額外欄位；武器場景同樣經由繼承自基類的 `scene_path` 指定，而非獨立的 `weapon_scene` 屬性。

### 2.2 清單管理 (ItemCollectionResource)
- **檔案路徑**: `scripts/pickups/ItemCollectionResource.gd`（繼承 `SaveableResource`）。
- 這是玩家的「背包」，核心欄位為 `list:Array[ItemResource]` + `selected:int` + `max_items:int`（`ItemCollectionResource.gd:8-12`），提供 `append` / `swap` / `drop` / `take` / `set_selected` 等操作並發出 `updated` / `removed` / `selected_changed` 信號。
- 因繼承 `SaveableResource`，序列化走 Godot 的 `ResourceSaver`（`.tres`，存於 `user://`）——**並非 JSON**。實體資源範例：`resources/ItemCollectionResource/weapon_database.tres`（武器總表）、`weapon_inventory.tres`（當前背包）。

## 3. 數值平衡 (Stats Balancing)
透過 `ActorStatsResource`（`scripts/actor/ActorStatsResource.gd`），開發者可以在編輯器中調整移動相關數值（`max_speed`、`acceleration`，由 `MoverTopDown2D` 以 `get_resource("movement")` 讀取）。生命與防禦另由 `HealthResource`（`scripts/damage/HealthResource.gd`）與 `DamageResource.resistance_value_list` 承載。實體範例：`resources/ActorStatsResource/player_stats.tres`、`zombie_stats.tres`。
- 這種數據與邏輯分離的設計，讓非程序人員也能透過 `.tres` 參與數值平衡。
