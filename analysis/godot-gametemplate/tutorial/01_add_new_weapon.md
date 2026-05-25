# 教學 01: 如何新增一個自定義遠程武器 (以 Plasma Gun 為例)

> 核對於 2026-05-25（Claude Code, Opus 4.7）：修正了 `ProjectileSpawner`/`ItemResource`/`weapon_database.tres` 的實際欄位名稱（原稿的 `instance_resource`/`fire_rate`/`item_name`/`weapon_scene`/`items` 與源碼不符，已更正）。

本教學將引導您利用 Godot Game Template 的解耦架構，建立一個具備電屬性傷害的等離子槍。

## 1. 前置知識
在開始之前，請確保您已閱讀 `architecture/level2_modules.md`，了解以下核心組件：
- **ResourceNode**: 用於獲取輸入軸與傷害上報回呼。
- **DamageDataResource**: 負責傷害矩陣計算。
- **InstanceResource**: 負責高效場景實例化（搭配 `PoolNode`）。

## 2. 原始碼導航
- **武器基類**: `addons/top_down/scripts/weapon_system/Weapon.gd`
- **彈幕基類**: `addons/top_down/scripts/weapon_system/projectile/Projectile2D.gd`
- **發射器**: `addons/top_down/scripts/weapon_system/projectile/ProjectileSpawner.gd`
- **傷害屬性枚舉**: `addons/top_down/scripts/damage/properties/DamageTypeResource.gd`（含 `LIGHTNING`）
- **物品資源**: `addons/top_down/scripts/pickups/ItemResource.gd`（欄位：`icon`/`scene_path`/`type`/`unlocked`）、`WeaponItemResource.gd`（空子類）
- **武器總表**: `addons/top_down/resources/ItemCollectionResource/weapon_database.tres`（欄位為 `list`，非 `items`）

## 3. 實作步驟

### 步驟 A: 建立傷害與屬性配置
1. 在 `resources/` 目錄下新建一個 `DamageDataResource` (.tres)。
2. 設置 `base_damage`（`Array[DamageTypeResource]`）：
    - 加入一個 `DamageTypeResource`，將 `type` 設為 `LIGHTNING`（屬於 `DamageTypeResource.DamageType`），`value` 設為 `15`。
3. 設置 `critical_chance`: `0.2` (20% 爆擊率，預設值為 0.3)；可一併調整 `critical_multiply`（預設 1.5）。

### 步驟 B: 建立彈幕實體 (Projectile)
1. 建立一個新場景 `plasma_bullet.tscn`，根節點掛上 `Projectile2D.gd`（可參考既有 `scenes/projectiles/bullet.tscn`）。
2. 配置 `Projectile2D` 屬性：
    - `speed`: `500.0`
    - `damage_data_resource`: 引用剛才建立的傷害資源。
    - 確認 `pool_node` 指向場景內的 `PoolNode`（`auto_free` 預設 true，回收時走 `pool_return()`）。
3. **重要**：為此場景建立一個 `InstanceResource` (.tres)，將其 `scene_path` 指向此 `.tscn`（對照 `resources/InstanceResources/projectiles/` 既有範例，並視需要啟用對象池）。

### 步驟 C: 組建武器場景 (Weapon)
1. 建立新場景 `plasma_gun.tscn`，繼承自 `scenes/weapons/weapon.tscn`（內含 `Weapon` + `ProjectileSpawner` 等組件）。
2. 配置 `Weapon` 節點（`Weapon.gd`）：
    - `damage_data_resource`: 引用步驟 A 的資源（`_ready()` 會自動把 `report_callback` 接到使用者的 damage 資源）。
3. 配置 `ProjectileSpawner` 節點（`ProjectileSpawner.gd`，實際欄位）：
    - `projectile_instance_resource`: 引用步驟 B 的 InstanceResource。
    - `damage_data_resource`: 引用步驟 A 的資源；如需每次擊發產生新世代可勾選 `new_damage`。
    - `projectile_angles`: 預設 `[0.0]`（單發）；多發散射可加入多個角度（或用 `SpreadShot.gd` 透過 `prepare_spawn` 信號動態填充）。
    - 射速由場景中的計時/觸發組件（如 `WeaponTrigger.gd`、`ProjectileInterval.gd`）控制，`ProjectileSpawner` 本身不含 `fire_rate` 欄位。

### 步驟 D: 註冊至物品資料庫
1. 打開 `weapon_database.tres`（`resources/ItemCollectionResource/`，腳本為 `ItemCollectionResource`）。
2. 在其 `list` 陣列（**注意是 `list`，非 `items`**）中新增一個 `WeaponItemResource` 子資源，設定：
    - `resource_name`: "Plasma Gun"（顯示名稱即用 Resource 的 `resource_name`，並無獨立 `item_name` 欄位）。
    - `icon`: 武器圖示 Texture2D。
    - `scene_path`: 指向步驟 C 的 `plasma_gun.tscn`（武器場景由基類的 `scene_path` 指定，**無 `weapon_scene` 欄位**）。
    - `type`: `WEAPON`（`ItemResource.ItemType`，整數 0）；`unlocked`: 視需要設 true。

## 4. 驗證方式
1. 進入 `scenes/levels/room_template.tscn` 或任何戰鬥關卡。
2. 在 `Player` 的 `WeaponManager`（`scripts/weapon_system/WeaponManager.gd`）中，暫時將預設武器加入此 `Plasma Gun`。
3. 啟動遊戲，按下攻擊鍵確認：
    - [ ] 彈幕是否正確生成。
    - [ ] 命中敵人後是否顯示電屬性傷害數值。
    - [ ] 爆擊時是否有正確的傷害倍率與視覺回饋。
