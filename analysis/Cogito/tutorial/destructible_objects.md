# 教學：如何實作可破壞場景與物件

本教學深度說明如何結合 COGITO 的血量系統（`CogitoHealthAttribute`）、命中箱（`HitboxComponent`）與戰利品系統（`LootComponent`），製作血量歸零後生成碎片並掉落物品的可破壞物件。

## 前置知識
- 已閱讀 [Level 5B: Attribute 屬性系統](../architecture/level5b_attributes.md)。
- 已閱讀 [Level 5C: Loot 系統](../architecture/level5c_loot_system.md)。

---

## 一、系統傷害流程（完整路徑）

理解傷害流程是建立可破壞物件的關鍵：

```
武器/投射物觸發傷害
│
├─ 投射物（CogitoProjectile._on_body_entered）
│   └─ collider.damage_received.emit(damage_amount, direction, position)
│       ← 要求 collider 有 damage_received signal
│
└─ 近戰（wieldable_pickaxe._on_body_entered）
    └─ collider.damage_received.emit(wieldable_damage, direction, position)
        ← 同上

collider.damage_received 信號被觸發
│
└─ HitboxComponent._ready() 在 parent 的 damage_received 上連接了 damage()
    └─ HitboxComponent.damage(amount) 呼叫
        └─ 找到 parent 下的 CogitoHealthAttribute
           health_attribute.subtract(amount)
               └─ value_current -= amount
                  attribute_changed.emit() → attribute_reached_zero.emit() → death.emit()
```

**關鍵結論**：
- 根節點**必須宣告 `signal damage_received(damage_value: float)`**（`CogitoObject` 已內建，`cogito_object.gd:6`）
- `HitboxComponent` 本身沒有 `damage_received` 信號——它監聽**父節點**的信號（`HitboxComponent.gd:19-21`）
- 不需要手動連接 `HitboxComponent → HealthAttribute`，`HitboxComponent._ready()` 自動完成

---

## 二、可破壞物件節點結構

### 基礎結構（靜態可破壞物件，如牆壁裝飾、木箱）

```
CogitoObject (Node3D + cogito_object.gd)   ← 必須：提供 damage_received signal + Persist 群組
└── StaticBody3D  （或 RigidBody3D 若要物理）
    ├── MeshInstance3D
    ├── CollisionShape3D                    ← Layer 2 (Interactables)，讓武器射線能打到
    ├── HitboxComponent                    ← 橋接傷害
    └── CogitoHealthAttribute              ← 血量管理
```

若要加入掉落物：
```
CogitoObject
└── RigidBody3D
    ├── MeshInstance3D
    ├── CollisionShape3D
    ├── HitboxComponent
    ├── CogitoHealthAttribute
    └── LootComponent                      ← 死亡時生成戰利品
```

---

## 三、步驟詳解

### 3.1 使用 CogitoObject 作根節點（最簡單方式）

`CogitoObject` 繼承 `Node3D` 並已宣告 `signal damage_received`（`cogito_object.gd:6`），直接使用即可：
1. 建立一個空 Node3D，附加 `cogito_object.gd` 腳本。
2. 在 Inspector 設定 `cogito_name`（用於存檔識別）與 `display_name`（互動顯示名稱，可留白）。

或者，若為 RigidBody3D 根節點（要讓物件可以被推動/攜帶），可使用繼承：
```gdscript
# my_destructible_crate.gd
extends RigidBody3D

signal damage_received(damage_value: float)  # 手動宣告，讓 HitboxComponent 能連接
# （此時不需要 cogito_object.gd）
```

### 3.2 HitboxComponent 設定

- 將 `HitboxComponent` 節點加到根節點（`CogitoObject` 或含 `damage_received` 信號的節點）**下一層**。
- `HitboxComponent._ready()` 自動執行（`HitboxComponent.gd:18-23`）：
  ```gdscript
  if get_parent().has_signal("damage_received"):
      get_parent().damage_received.connect(damage)
  else:
      # 會印出警告訊息
  ```
- **無需設定任何欄位**，它完全自動運作。

### 3.3 CogitoHealthAttribute 設定

在 Inspector 設定：

| 欄位 | 說明 | 建議值 |
|---|---|---|
| `attribute_name` | 屬性識別名（任意字串） | `"health"` |
| `value_start` | 初始血量 | `50.0`（木箱）/ `200.0`（牆壁） |
| `value_max` | 最大血量 | 同上 |
| `sound_on_hit` | 受擊音效（每次被打響） | 撞擊聲 .wav |
| `sound_on_damage_taken` | 受傷音效（未死亡時） | 木材破裂聲 |
| `sound_on_death` | 死亡音效 | 重擊聲 |
| `spawn_on_death` | 死亡時生成的場景（Array） | 碎片場景 |
| `destroy_on_death` | 血量歸零時 queue_free 的節點路徑 | `[NodePath(".")]`（自己） |

**`destroy_on_death`** 欄位（`cogito_health_attribute.gd:18`）：設為 `[NodePath("..")]`（父節點）即可在死亡時讓整個物件消失。

### 3.4 spawn_on_death（碎片場景）

`spawn_on_death` 是 `Array[PackedScene]`。場景在 `on_death()` 中生成（`cogito_health_attribute.gd:44-56`）：
```gdscript
# cogito_health_attribute.gd:42-56 節錄
func on_death(_attribute_name, _value_current, _value_max):
    death.emit()
    parent_position = get_parent().global_position  # 先記住位置！
    parent_rotation = get_parent().global_rotation
    # ...
    for scene in spawn_on_death:
        var spawned_object = scene.instantiate()
        spawned_object.position = parent_position  # 使用記憶的位置
        get_tree().current_scene.add_child(spawned_object)
    for nodepath in destroy_on_death:
        get_node(nodepath).queue_free()
```

**碎片場景建立方法**：
1. 在 Blender 使用 Cell Fracture 或手動切割模型為 5-10 個碎片。
2. 匯入 Godot 後，建立 `FragmentedCrate.tscn`：
   ```
   Node3D  (根節點，附加自動消失腳本)
   ├── RigidBody3D (碎片 A)
   │   ├── MeshInstance3D
   │   └── CollisionShape3D
   ├── RigidBody3D (碎片 B)
   │   ├── MeshInstance3D
   │   └── CollisionShape3D
   └── ...（更多碎片）
   ```
3. 在根節點加入自動消失邏輯：
   ```gdscript
   # fragment_auto_despawn.gd
   extends Node3D
   @export var lifetime : float = 5.0
   func _ready():
       # 給碎片一個隨機爆炸衝量
       for child in get_children():
           if child is RigidBody3D:
               var impulse = Vector3(randf_range(-3,3), randf_range(2,6), randf_range(-3,3))
               child.apply_central_impulse(impulse)
       await get_tree().create_timer(lifetime).timeout
       queue_free()
   ```

### 3.5 LootComponent 設定（可選）

`LootComponent` 自動連接到 `health_component_to_monitor.death` 信號（`LootComponent.gd:58-61`），無需手動連接：

1. 在根節點下加入 `LootComponent` 節點。
2. 在 Inspector 設定：
   - `spawning_logic`：`SPAWN_ITEM`（散射道具）或 `SPAWN_CONTAINER`（生成一個戰利品袋）。
   - `loot_table`：指定 `BaseLootTable.tres` 資源。
   - `amount_of_items_to_drop`：掉落物品數量。
   - **`health_component_to_monitor`**：拖入同一根節點下的 `CogitoHealthAttribute` 節點。
3. `LootComponent._set_up_references()` 在 `_ready()` deferred 時自動執行連接。

---

## 四、武器設定（確保能打到物件）

### 投射物武器（Hitscan 或彈丸）
`CogitoProjectile._on_body_entered()` 要求（`cogito_projectile.gd:60`）：
```gdscript
if collider.has_signal("damage_received"):
    deal_damage(collider, ...)
```
→ 確認物件根節點有 `damage_received` 信號即可。

### 近戰武器（`wieldable_pickaxe.gd`）
`_on_body_entered()` 同樣檢查 `has_signal("damage_received")`（`wieldable_pickaxe.gd:59`）。

**Physics Layer 提醒**：物件的 `CollisionShape3D` 必須在能被武器的 `damage_area` 偵測到的 Layer 上。以 Pickaxe 為例，`damage_area` 通常掃描 Layer 1 + 2，請在 **Mask** 欄位確認設定。

---

## 五、完整驗證清單

| 測試步驟 | 預期結果 | 若失敗 |
|---|---|---|
| 用武器打擊物件 | 物件血量減少（Console 無報錯） | 確認物件有 `damage_received` 信號；物理 Layer Mask 設定正確 |
| 血量歸零 | `death` 信號觸發 | 確認 `attribute_reached_zero` 連接到 `on_death`（HealthAttribute 的 `_ready()` 自動完成） |
| 血量歸零後 | 碎片場景出現在原位 | 確認 `spawn_on_death` 陣列有設定場景 |
| 血量歸零後 | 原物件消失 | 確認 `destroy_on_death` 含有父節點路徑 |
| 血量歸零後 | 地上出現掉落物 | 確認 `LootComponent.health_component_to_monitor` 已指定；`spawning_logic != NONE` |
| 存檔讀檔後 | 已破壞的物件不再出現 | 物件需是從 `.tscn` 實例化（`Persist` 群組）；`CogitoObject` 自動處理 |
