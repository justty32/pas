# 教學：如何實作可破壞場景與物件

本教學說明如何結合 COGITO 的血量系統 (`CogitoHealthAttribute`) 與命中箱 (`HitboxComponent`)，將靜態場景（如木箱、脆弱的牆壁）變為可破壞物件，並在破壞時生成碎片與戰利品。

## 前置知識
- 已閱讀 [Level 5B: Attribute 屬性系統](../architecture/level5b_attributes.md)。
- 已閱讀 [Level 5C: Loot 系統](../architecture/level5c_loot_system.md)。

## 實作步驟

### 1. 建立基礎物件
1. 建立一個 `StaticBody3D`（牆壁）或 `RigidBody3D`（木桶）。
2. 添加 `MeshInstance3D` 與 `CollisionShape3D`。
3. 確保 **Physics Layer** 勾選了 `Interactables` (Layer 2) 或武器射線能打到的圖層。

### 2. 添加受擊與血量組件
1. **命中箱**：添加 `addons/cogito/Components/HitboxComponent.gd` 作為子節點。
   - 這能讓武器的射線或近戰判定正確造成傷害。
2. **血量屬性**：添加 `addons/cogito/Components/Attributes/cogito_health_attribute.gd` 作為子節點。
   - 設定 `value_max` 與 `value_current`（例如 50）。
   - 在 `Audio` 分組放入受擊與破壞的音效。

### 3. 連接傷害信號
COGITO 預設需要您將命中箱的傷害傳導給屬性系統：
- 將 `HitboxComponent` 的 `damage_received(amount)` 信號連接到 `CogitoHealthAttribute` 的 `subtract(amount)` 方法。

### 4. 設定死亡 (破壞) 行為
`CogitoHealthAttribute` 有一個 `spawn_on_death` 欄位：
1. 準備一個 **碎片場景 (Fractured Mesh)**：使用 Blender 拆解模型，並匯入成包含多個小 `RigidBody3D` 的 `.tscn`。
2. 將此場景拖入 `spawn_on_death` 欄位。
3. 將 `CogitoHealthAttribute` 的 `death` 信號連接到根節點 (`StaticBody3D`) 的 `queue_free()` 方法，讓原始物件在血量歸零時消失。

### 5. 添加掉落物 (可選)
若破壞木箱後要掉落道具：
1. 在根節點下添加 `addons/cogito/Components/LootComponent.gd`。
2. 設定 `Loot Table`。
3. 將 `CogitoHealthAttribute` 的 `death` 信號也連接到 `LootComponent` 的 `drop_loot()` 方法。

## 驗證方式
1. 使用武器射擊或敲擊木桶。
2. 觀察是否有受擊音效。
3. 血量歸零時，木桶是否消失，並在原地生成碎片模型與掉落物。
