# 教學：龍吼系統（Shout / Power Attack System）

本教學說明如何在 COGITO 中實作 Skyrim 風格的「龍吼」：獨立按鍵觸發、多段充能、各自冷卻計時器，以及如何與現有 Wieldable 系統共存。

## 前置知識
- 已閱讀 [教學：Skyrim 戰鬥機制](./skyrim_combat_mechanics.md)。
- 了解 `CogitoWieldable` 基礎。

---

## 一、ShoutData：龍吼資源定義

建立 `res://scripts/shout_data.gd`：

```gdscript
# res://scripts/shout_data.gd
extends Resource
class_name ShoutData

## 龍吼名稱（如 "Fus Ro Dah"）
@export var shout_name: String
## 描述
@export_multiline var description: String
## 圖示
@export var icon: Texture2D

## 龍吼效果類型
enum ShoutEffect {
    KNOCKBACK,      # 推飛敵人
    TIME_SLOW,      # 慢動作
    FIRE_BREATH,    # 噴火
    WHIRLWIND,      # 瞬移
}
@export var effect: ShoutEffect = ShoutEffect.KNOCKBACK

## 龍吼的影響半徑（或射程）
@export var radius: float = 8.0
## 基礎威力數值（用途依效果類型而異）
@export var power: float = 20.0

## 三段充能的冷卻時間（秒）
## Skyrim 風格：只按一下用第一段，快速按兩下用第二段，等等
@export var cooldown_tier1: float = 4.0
@export var cooldown_tier2: float = 12.0
@export var cooldown_tier3: float = 30.0

## 解鎖的段數（1~3）
@export var unlocked_tiers: int = 1
```

---

## 二、ShoutManager：全域龍吼管理

建立 `res://scripts/shout_manager.gd`（Autoload：`ShoutManager`）：

```gdscript
# res://scripts/shout_manager.gd (Autoload: ShoutManager)
extends Node

signal shout_used(shout: ShoutData, tier: int)
signal shout_cooldown_changed(shout: ShoutData, remaining: float)
signal equipped_shout_changed(shout: ShoutData)

## 已解鎖的龍吼列表
var unlocked_shouts: Array[ShoutData] = []

## 目前裝備的龍吼
var equipped_shout: ShoutData = null

## 各龍吼的冷卻剩餘時間（resource_path → float）
var _cooldowns: Dictionary = {}

## 目前充能等級（玩家連按幾次）
var _pending_tier: int = 0
var _tier_window_timer: float = 0.0
const TIER_WINDOW: float = 0.6  # 充能窗口：0.6 秒內連按才累加等級


func _process(delta: float) -> void:
    # 更新所有冷卻計時
    for key in _cooldowns.keys():
        if _cooldowns[key] > 0.0:
            _cooldowns[key] -= delta
            if _cooldowns[key] <= 0.0:
                _cooldowns[key] = 0.0

    # 充能窗口計時
    if _tier_window_timer > 0.0:
        _tier_window_timer -= delta
        if _tier_window_timer <= 0.0:
            # 窗口到期，實際執行龍吼
            _execute_shout(_pending_tier)
            _pending_tier = 0


func equip_shout(shout: ShoutData) -> void:
    equipped_shout = shout
    equipped_shout_changed.emit(shout)


func press_shout() -> void:
    if not equipped_shout:
        return
    if is_on_cooldown(equipped_shout):
        return

    _pending_tier += 1
    _tier_window_timer = TIER_WINDOW

    # 超過解鎖段數：限制到最大
    if _pending_tier > equipped_shout.unlocked_tiers:
        _pending_tier = equipped_shout.unlocked_tiers
        _tier_window_timer = 0.0  # 直接執行最大段
        _execute_shout(_pending_tier)
        _pending_tier = 0


func _execute_shout(tier: int) -> void:
    if not equipped_shout:
        return
    var cooldown = _get_cooldown_for_tier(equipped_shout, tier)
    _cooldowns[equipped_shout.resource_path] = cooldown
    shout_used.emit(equipped_shout, tier)


func _get_cooldown_for_tier(shout: ShoutData, tier: int) -> float:
    match tier:
        1: return shout.cooldown_tier1
        2: return shout.cooldown_tier2
        _: return shout.cooldown_tier3


func is_on_cooldown(shout: ShoutData) -> bool:
    return _cooldowns.get(shout.resource_path, 0.0) > 0.0


func get_remaining_cooldown(shout: ShoutData) -> float:
    return _cooldowns.get(shout.resource_path, 0.0)


func unlock_shout(shout: ShoutData) -> void:
    if shout not in unlocked_shouts:
        unlocked_shouts.append(shout)
```

---

## 三、輸入：獨立按鍵（不干擾 Wieldable）

**在 Input Map 加入**：`Project Settings → Input Map → 新增 "shout"` → 設為 Z 鍵。

**在 `cogito_player.gd` 的 `_unhandled_input()` 加入**：

```gdscript
# cogito_player.gd - _unhandled_input() 的末尾加入
if event.is_action_pressed("shout"):
    ShoutManager.press_shout()
    get_viewport().set_input_as_handled()  # 防止事件繼續傳遞
```

---

## 四、龍吼效果執行器

龍吼效果由 `ShoutManager.shout_used` 信號觸發，在另一個節點（或 Autoload）中處理：

建立 `res://scripts/shout_executor.gd`（掛在場景中，或加為 Autoload 的一部分）：

```gdscript
# res://scripts/shout_executor.gd
extends Node


func _ready() -> void:
    ShoutManager.shout_used.connect(_on_shout_used)


func _on_shout_used(shout: ShoutData, tier: int) -> void:
    var player = CogitoSceneManager._current_player_node
    if not player:
        return

    match shout.effect:
        ShoutData.ShoutEffect.KNOCKBACK:
            _execute_knockback(player, shout, tier)
        ShoutData.ShoutEffect.TIME_SLOW:
            _execute_time_slow(shout, tier)
        ShoutData.ShoutEffect.FIRE_BREATH:
            _execute_fire_breath(player, shout, tier)
        ShoutData.ShoutEffect.WHIRLWIND:
            _execute_whirlwind(player, shout, tier)


func _execute_knockback(player: Node3D, shout: ShoutData, tier: int) -> void:
    var force = shout.power * tier
    var radius = shout.radius * tier
    var camera = player.find_child("Camera3D", true, false)
    var forward = -camera.global_basis.z

    # 搜尋範圍內的所有敵人
    for body in _get_bodies_in_cone(player.global_position, forward, radius, deg_to_rad(45)):
        if body.has_method("apply_knockback"):
            body.apply_knockback(forward * force)  # cogito_npc.gd:173
        if body.has_signal("damage_received"):
            body.damage_received.emit(shout.power * 0.5 * tier, forward, body.global_position)


func _execute_time_slow(shout: ShoutData, tier: int) -> void:
    # 慢動作：降低 Engine.time_scale，持續時間依段數
    var duration = 3.0 * tier
    var slow_factor = 0.3 / tier  # 段數越高越慢
    Engine.time_scale = slow_factor
    get_tree().create_timer(duration * slow_factor, true, false, true).timeout.connect(
        func(): Engine.time_scale = 1.0
    )


func _execute_fire_breath(player: Node3D, shout: ShoutData, tier: int) -> void:
    # 實例化投射物（需預備火焰投射物場景）
    if fire_projectile_scene:
        var camera = player.find_child("Camera3D", true, false)
        for i in range(tier * 3):  # 段數越高越多顆
            var proj = fire_projectile_scene.instantiate()
            get_tree().current_scene.add_child(proj)
            proj.global_position = camera.global_position
            proj.linear_velocity = -camera.global_basis.z * 15.0 + Vector3(randf_range(-0.5, 0.5), 0, randf_range(-0.5, 0.5))

@export var fire_projectile_scene: PackedScene


func _execute_whirlwind(player: Node3D, shout: ShoutData, tier: int) -> void:
    # 瞬移：沿視線方向移動 tier * 5 公尺
    var camera = player.find_child("Camera3D", true, false)
    var dash_dist = tier * 5.0
    player.global_position += -camera.global_basis.z * dash_dist


func _get_bodies_in_cone(origin: Vector3, direction: Vector3, radius: float, half_angle: float) -> Array:
    var result := []
    var space_state = get_tree().current_scene.get_world_3d().direct_space_state
    var query = PhysicsShapeQueryParameters3D.new()
    var sphere = SphereShape3D.new()
    sphere.radius = radius
    query.shape = sphere
    query.transform = Transform3D(Basis(), origin)
    query.collision_mask = 0b10  # Layer 2: Enemies

    for hit in space_state.intersect_shape(query, 32):
        var body = hit.collider
        var to_body = (body.global_position - origin).normalized()
        if to_body.dot(direction) > cos(half_angle):  # 在錐形範圍內
            result.append(body)
    return result
```

---

## 五、龍吼 HUD 顯示

在 HUD 加入冷卻條和裝備龍吼圖示：

```gdscript
# shout_hud.gd — 掛在 HUD 控制節點
extends Control

@onready var shout_icon: TextureRect = $ShoutIcon
@onready var cooldown_bar: ProgressBar = $CooldownBar
@onready var shout_name_label: Label = $ShoutName


func _ready() -> void:
    ShoutManager.shout_used.connect(_on_shout_used)
    ShoutManager.equipped_shout_changed.connect(_on_equipped_changed)


func _process(_delta: float) -> void:
    if ShoutManager.equipped_shout:
        var remaining = ShoutManager.get_remaining_cooldown(ShoutManager.equipped_shout)
        var total = ShoutManager.equipped_shout.cooldown_tier1  # 用 tier1 作為最大值顯示
        cooldown_bar.value = 1.0 - (remaining / max(total, 0.001))


func _on_shout_used(_shout: ShoutData, _tier: int) -> void:
    # 可加入使用特效（閃光、震動）
    pass


func _on_equipped_changed(shout: ShoutData) -> void:
    if shout:
        shout_icon.texture = shout.icon
        shout_name_label.text = shout.shout_name
```

---

## 六、裝備/切換龍吼

玩家透過物品欄或快捷鍵裝備龍吼：

```gdscript
# 在 cogito_player.gd 或 PlayerInteractionComponent 中
# 透過物品欄的 ShoutItemPD（繼承 InventoryItemPD）
# use() 呼叫 ShoutManager.equip_shout(self.shout_data)

# 或直接鍵盤切換
if event.is_action_pressed("shout_next"):
    var idx = ShoutManager.unlocked_shouts.find(ShoutManager.equipped_shout)
    var next = (idx + 1) % ShoutManager.unlocked_shouts.size()
    ShoutManager.equip_shout(ShoutManager.unlocked_shouts[next])
```

---

## 七、驗證清單

| 測試步驟 | 預期結果 |
|---|---|
| 按 Z（shout 鍵） | 觸發龍吼，附近敵人被推飛 |
| 在冷卻中再次按 Z | 無反應（`is_on_cooldown` 返回 true）|
| 快速按 Z 兩次（< 0.6 秒） | 觸發第二段龍吼（更強的擊退力）|
| 慢動作龍吼 | `Engine.time_scale` 下降，視覺明顯變慢 |
| 冷卻條 | 隨時間恢復至滿格 |
| 存讀檔後 | 解鎖的龍吼保持（需整合到 player state）|
