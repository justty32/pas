# 教學：實作魔法系統（魔力與法術施放）

本教學說明如何添加魔力屬性（Magicka）、建立瞬發/持續/增益法術，以及讓魔力條自動出現在 HUD 上。

## 前置知識
- 已閱讀 [Level 3C: Wieldable 玩家動作](../architecture/level3_wieldables.md)。
- 已閱讀 [Level 5A: 物品欄 UI 系統](../architecture/level5a_inventory_ui.md)。

---

## 一、添加魔力屬性

### 1.1 屬性類型選擇

| 選項 | 適用情境 |
|---|---|
| 複用 `CogitoStaminaAttribute` | 快速實作，自動再生邏輯已內建 |
| 自訂 `cogito_magicka_attribute.gd` | 需要特殊再生規則（戰鬥中停止再生等）|

推薦路徑：**自訂**，以避免與耐力邏輯耦合。

### 1.2 建立 cogito_magicka_attribute.gd

```gdscript
# addons/cogito/Components/Attributes/cogito_magicka_attribute.gd
extends CogitoAttribute
class_name CogitoMagickaAttribute

@export var regen_speed : float = 3.0     # 每秒再生量
@export var regen_delay : float = 2.0     # 施法後多久開始再生
@export var regen_in_combat : bool = false  # 戰鬥中是否再生

var _regen_timer : float = 0.0
var _can_regen : bool = true


func _ready() -> void:
    value_current = value_start


func _process(delta: float) -> void:
    if _regen_timer > 0:
        _regen_timer -= delta
        _can_regen = false
        return
    else:
        _can_regen = true

    if _can_regen and value_current < value_max:
        add(regen_speed * delta)


## 施法後呼叫此函數重置再生延遲
func notify_cast() -> void:
    _regen_timer = regen_delay
    _can_regen = false
```

### 1.3 加入玩家場景

在 `cogito_player.tscn` 的 **Attributes** 容器下新增子節點：
```
CogitoPlayer
└── Attributes
    ├── Health (CogitoHealthAttribute)
    ├── Stamina (CogitoStaminaAttribute)
    └── Magicka (CogitoMagickaAttribute)   ← 新增
        ├── attribute_name = "magicka"
        ├── attribute_display_name = "Magicka"
        ├── attribute_color = Color(0.3, 0.5, 1.0)   # 藍色
        ├── value_max = 100
        ├── value_start = 100
        └── attribute_visibility = Hud  ← 自動出現在 HUD
```

**HUD 自動整合原理**（`cogito_player.gd:230`）：玩家 `_ready()` 用 `find_children("","CogitoAttribute",false)` 掃描所有直接子節點，並以 `attribute_name` 為鍵存入 `player_attributes`。`player_hud_manager.gd:121-137` 接著為每個可見屬性實例化一個 `ui_attribute_prefab` 色條。**只要是 CogitoPlayer 直接子節點，名稱正確，即會自動出現**。

---

## 二、瞬發法術（火球）

### 2.1 建立 wieldable_spell_fireball.gd

```gdscript
# addons/cogito/Wieldables/wieldable_spell_fireball.gd
extends CogitoWieldable

@export var fireball_scene : PackedScene
@export var magicka_cost : float = 20.0
@export var projectile_speed : float = 20.0

var _magicka : CogitoMagickaAttribute = null


func _ready() -> void:
    if wieldable_mesh:
        wieldable_mesh.hide()
    _magicka = _find_magicka()


func _find_magicka() -> CogitoMagickaAttribute:
    var player = CogitoSceneManager._current_player_node
    if player:
        return player.player_attributes.get("magicka")
    return null


func action_primary(_item, _is_released: bool) -> void:
    if _is_released:
        return
    if animation_player.is_playing():
        return

    # 魔力檢查
    if not _magicka or _magicka.value_current < magicka_cost:
        player_interaction_component.send_hint(null, "魔力不足！")
        return

    _magicka.subtract(magicka_cost)
    _magicka.notify_cast()  # 重置再生延遲

    animation_player.play(anim_action_primary)  # 施法手勢動畫
    audio_stream_player_3d.play()

    _spawn_fireball()


func _spawn_fireball() -> void:
    if not fireball_scene:
        push_warning("wieldable_spell_fireball: 未設定 fireball_scene")
        return

    var camera := get_viewport().get_camera_3d()
    if not camera:
        return

    var fireball := fireball_scene.instantiate()
    get_tree().current_scene.add_child(fireball)

    # 從鏡頭前方生成
    fireball.global_position = camera.global_position + camera.global_basis.z * -1.5
    fireball.global_basis = camera.global_basis  # 朝向與相機一致

    # 若火球繼承 cogito_projectile.gd 的速度屬性
    if fireball.get("bullet_speed") != null:
        fireball.bullet_speed = projectile_speed
```

### 2.2 火球 PackedScene 設定

火球應繼承 COGITO 的投射物腳本（`cogito_projectile.gd`）並掛上傷害區域：

```
FireballProjectile (RigidBody3D 或 Area3D + cogito_projectile.gd)
├── MeshInstance3D (球形網格 + 火焰材質)
├── CollisionShape3D
├── GPUParticles3D (火焰粒子)
└── OmniLight3D (動態光效)
```

---

## 三、持續法術（閃電鏈）

持續施法：按住不放持續扣魔力與造傷，放開停止：

```gdscript
# addons/cogito/Wieldables/wieldable_spell_lightning.gd
extends CogitoWieldable

@export var dps : float = 15.0              # 每秒傷害
@export var magicka_per_second : float = 8.0  # 每秒魔力消耗
@export var max_range : float = 8.0

var _magicka : CogitoMagickaAttribute = null
var _is_channeling : bool = false
var _ray : RayCast3D


func _ready() -> void:
    _magicka = _find_magicka()
    # 建立射線檢測範圍
    _ray = RayCast3D.new()
    add_child(_ray)
    _ray.target_position = Vector3(0, 0, -max_range)
    _ray.enabled = true


func _find_magicka() -> CogitoMagickaAttribute:
    var player = CogitoSceneManager._current_player_node
    return player.player_attributes.get("magicka") if player else null


func action_primary(_item, _is_released: bool) -> void:
    if _is_released:
        _is_channeling = false
        animation_player.play("idle")
    else:
        if _magicka and _magicka.value_current > 0:
            _is_channeling = true
            animation_player.play("channel_lightning")


func _process(delta: float) -> void:
    if not _is_channeling:
        return

    # 每幀扣魔力
    if not _magicka or _magicka.value_current <= 0:
        _is_channeling = false
        animation_player.play("idle")
        return

    _magicka.subtract(magicka_per_second * delta)
    _magicka.notify_cast()

    # 射線命中檢查
    if _ray.is_colliding():
        var target = _ray.get_collider()
        if target.has_signal("damage_received"):
            target.damage_received.emit(dps * delta, Vector3.ZERO, _ray.get_collision_point())
```

---

## 四、增益法術（速度強化）

增益法術不發射任何投射物，直接修改玩家屬性再計時還原：

```gdscript
# addons/cogito/Wieldables/wieldable_spell_speed.gd
extends CogitoWieldable

@export var magicka_cost : float = 30.0
@export var speed_multiplier : float = 1.8
@export var duration : float = 10.0

var _magicka : CogitoMagickaAttribute = null
var _original_speed : float = 0.0
var _active : bool = false


func _ready() -> void:
    _magicka = _find_magicka()


func _find_magicka() -> CogitoMagickaAttribute:
    var p = CogitoSceneManager._current_player_node
    return p.player_attributes.get("magicka") if p else null


func action_primary(_item, _is_released: bool) -> void:
    if _is_released or _active:
        return
    if not _magicka or _magicka.value_current < magicka_cost:
        player_interaction_component.send_hint(null, "魔力不足！")
        return

    _magicka.subtract(magicka_cost)
    _magicka.notify_cast()
    _activate_buff()


func _activate_buff() -> void:
    var player = CogitoSceneManager._current_player_node
    if not player:
        return

    _active = true
    _original_speed = player.SPRINTING_SPEED
    player.SPRINTING_SPEED *= speed_multiplier
    player.player_interaction_component.send_hint(null, "速度強化！（%.0f 秒）" % duration)

    animation_player.play(anim_action_primary)

    await get_tree().create_timer(duration).timeout
    player.SPRINTING_SPEED = _original_speed
    _active = false
    player.player_interaction_component.send_hint(null, "速度強化結束")
```

---

## 五、法術作為物品欄物品

在 `InventoryPD` 資源中建立 `InventoryItemPD`：

| 欄位 | 值 |
|---|---|
| `item_name` | "Fire Bolt" |
| `item_type` | `Wieldable` |
| `wieldable_item` | 指向 `wieldable_spell_fireball.tscn` 的 PackedScene |
| `item_icon` | 火球圖示 Texture2D |

玩家即可從物品欄拖曳到快捷欄，用數字鍵切換施法。

---

## 六、驗證清單

| 測試步驟 | 預期結果 |
|---|---|
| 開啟遊戲，HUD 底部 | 出現藍色魔力條（自動整合）|
| 裝備火球術，按左鍵 | 魔力減少 20，火球飛出 |
| 魔力耗盡後按左鍵 | 顯示「魔力不足！」提示，不施法 |
| 停止施法 2 秒後 | 魔力開始以 3/秒速度恢復 |
| 裝備閃電鏈，長按左鍵 | 每秒扣 8 魔力，命中目標扣 15 HP/秒 |
| 速度強化 buff 激活 | 快跑明顯加速，10 秒後恢復 |
