# 教學 01: 如何新增一個自定義遠程武器 (以 Plasma Gun 為例)

本教學將引導您利用 Godot Game Template 的解耦架構，建立一個具備電屬性傷害的等離子槍。

## 1. 前置知識
在開始之前，請確保您已閱讀 `architecture/level2_modules.md`，了解以下核心組件：
- **ResourceNode**: 用於獲取輸入軸與傷害上報回呼。
- **DamageDataResource**: 負責傷害矩陣計算。
- **InstanceResource**: 負責高效場景實例化。

## 2. 原始碼導航
- **武器基類**: `addons/top_down/scripts/weapon_system/Weapon.gd`
- **彈幕基類**: `addons/top_down/scripts/weapon_system/projectile/Projectile2D.gd`
- **資料庫路徑**: `addons/top_down/resources/ItemCollectionResource/weapon_database.tres`

## 3. 實作步驟

### 步驟 A: 建立傷害與屬性配置
1. 在 `resources/` 目錄下新建一個 `DamageDataResource` (.tres)。
2. 設置 `base_damage`:
    - 加入一個 `DamageTypeResource`，將 `type` 設為 `LIGHTNING`，`value` 設為 `15`。
3. 設置 `critical_chance`: `0.2` (20% 爆擊率)。

### 步驟 B: 建立彈幕實體 (Projectile)
1. 建立一個新場景 `plasma_bullet.tscn`，根節點繼承自 `Projectile2D`。
2. 配置 `Projectile2D` 屬性：
    - `speed`: `500.0`
    - `damage_data_resource`: 引用剛才建立的傷害資源。
3. **重要**：為此場景建立一個 `InstanceResource` (.tres)，將 `scene_path` 指向此 `.tscn`，並勾選 `use_pool`。

### 步驟 C: 組建武器場景 (Weapon)
1. 建立新場景 `plasma_gun.tscn`，繼承自 `Weapon.tscn`。
2. 配置 `Weapon` 節點：
    - `damage_data_resource`: 引用步驟 A 的資源。
3. 配置 `ProjectileSpawner`：
    - `instance_resource`: 引用步驟 B 的 InstanceResource。
    - `fire_rate`: `0.5` (每秒兩發)。

### 步驟 D: 註冊至物品資料庫
1. 在 `resources/` 下新建一個 `WeaponItemResource` (.tres)。
2. 設置 `item_name`: "Plasma Gun"。
3. 設置 `weapon_scene`: 指向步驟 C 的 `plasma_gun.tscn`。
4. 打開 `weapon_database.tres` (位於 `resources/ItemCollectionResource/`)。
5. 將新建的 `WeaponItemResource` 加入到其 `items` 陣列中。

## 4. 驗證方式
1. 進入 `room_template.tscn` 或任何戰鬥關卡。
2. 在 `Player` 的 `WeaponManager` 中，暫時將預設武器陣列加入此 `Plasma Gun`。
3. 啟動遊戲，按下攻擊鍵確認：
    - [ ] 彈幕是否正確生成。
    - [ ] 命中敵人後是否顯示電屬性傷害數值。
    - [ ] 爆擊時是否有正確的傷害倍率與視覺回饋。
