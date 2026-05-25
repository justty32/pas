# 教學：實作 Skyrim 風格戰鬥機制（格擋、重擊與失衡）

本教學在理解 `wieldable_pickaxe.gd` 的基礎上，實作格擋、消耗耐力的重擊，以及讓 NPC 失衡（Stagger）的機制。

## 前置知識
- 已閱讀 [Level 3C: Wieldable 玩家動作](../architecture/level3_wieldables.md)。
- 已完成 [教學：Skyrim 升級系統](./skyrim_leveling_system.md)（熟悉耐力屬性存取）。

---

## 一、理解傷害流程（攻擊方）

`wieldable_pickaxe.gd` 的傷害流程如下（`wieldable_pickaxe.gd:58-80`）：

```
按下左鍵
  → animation_player.play(anim_action_primary)
  → Area3D.body_entered 信號觸發
  → collider.has_signal("damage_received") → true
  → collider.damage_received.emit(damage, direction, hit_pos)
```

關鍵：傷害是以 `damage_received.emit()` 傳出，NPC 的 `HitboxComponent` 接收後自動觸發 `got_hit` 信號，再由 `cogito_npc.gd:216` 的 `_on_hitbox_component_got_hit()` 切換命中動畫。

---

## 二、建立劍武器腳本（繼承 pickaxe 模式）

建立 `addons/cogito/Wieldables/wieldable_sword.gd`：

```gdscript
# addons/cogito/Wieldables/wieldable_sword.gd
extends CogitoWieldable

@export_group("Sword Settings")
@export var damage_area : Area3D
@export var base_damage : float = 15.0

@export_group("Stamina")
@export var uses_stamina : bool = true
@export var light_attack_cost : float = 5.0
@export var power_attack_cost : float = 20.0

@export_group("Blocking")
@export var block_damage_reduction : float = 0.6  # 格擋減少 60% 傷害
@export var block_stamina_cost : float = 8.0      # 每次被擋的耐力消耗

var player_stamina : CogitoAttribute = null
var is_blocking : bool = false

## 長按計時（重擊判定）
var _press_timer : float = 0.0
var _is_pressed : bool = false
const POWER_ATTACK_THRESHOLD : float = 0.5  # 按住 0.5 秒觸發重擊


func _ready() -> void:
    if wieldable_mesh:
        wieldable_mesh.hide()
    damage_area.body_entered.connect(_on_body_entered)
    if uses_stamina:
        player_stamina = _grab_stamina()


func _grab_stamina() -> CogitoAttribute:
    # 與 wieldable_pickaxe.gd:28 相同模式
    var p = CogitoSceneManager._current_player_node
    if p and p.stamina_attribute:
        return p.stamina_attribute
    push_warning("wieldable_sword: 找不到玩家耐力屬性")
    return null


func _process(delta: float) -> void:
    if _is_pressed:
        _press_timer += delta


func action_primary(_item, _is_released: bool) -> void:
    if _is_released:
        # 放開：判定輕/重擊
        var was_power = _press_timer >= POWER_ATTACK_THRESHOLD
        _is_pressed = false
        _press_timer = 0.0
        if was_power:
            _start_power_attack()
        else:
            _start_light_attack()
    else:
        # 按下：開始計時（已在播放則不允許連點）
        if animation_player.is_playing():
            return
        _is_pressed = true
        _press_timer = 0.0


func action_secondary(is_released: bool) -> void:
    if is_released:
        is_blocking = false
        animation_player.play("idle")
    else:
        is_blocking = true
        animation_player.play("block_pose")  # 需在 AnimationPlayer 中建立此動畫


# ── 輕擊 ──────────────────────────────────────
func _start_light_attack() -> void:
    if uses_stamina and player_stamina:
        if player_stamina.value_current < light_attack_cost:
            return  # 耐力不足，不揮擊
        player_stamina.subtract(light_attack_cost)

    animation_player.play(anim_action_primary)  # 預設 "swing"
    audio_stream_player_3d.play()


# ── 重擊 ──────────────────────────────────────
func _start_power_attack() -> void:
    if uses_stamina and player_stamina:
        if player_stamina.value_current < power_attack_cost:
            return
        player_stamina.subtract(power_attack_cost)

    # 設定本次攻擊為重擊（供 _on_body_entered 讀取）
    _current_is_power_attack = true
    animation_player.play("heavy_attack")  # 需建立此動畫
    audio_stream_player_3d.play()
    # 動畫結束後清除重擊旗標
    await animation_player.animation_finished
    _current_is_power_attack = false

var _current_is_power_attack : bool = false
```

---

## 三、命中處理（含重擊判定）

在同一個 `wieldable_sword.gd` 中加入：

```gdscript
func _on_body_entered(collider: Node) -> void:
    if not collider.has_signal("damage_received"):
        return

    # 計算方向（camera-ray 模式）
    var player = player_interaction_component.get_parent()
    var hit_pos = player_interaction_component.Get_Camera_Collision()
    var direction = (hit_pos - player.global_position).normalized()

    # 決定傷害量
    var final_damage = base_damage * (2.5 if _current_is_power_attack else 1.0)
    collider.damage_received.emit(final_damage, direction, hit_pos)

    # 重擊時額外施加擊退（NPC 有 apply_knockback，cogito_npc.gd:173）
    if _current_is_power_attack and collider.has_method("apply_knockback"):
        var knockback_dir = direction * 6.0
        collider.apply_knockback(knockback_dir)
        # 注意：命中動畫由 HitboxComponent → _on_hitbox_component_got_hit() 自動觸發
        # (cogito_npc.gd:216)，無需手動調用
```

### `apply_knockback` 的內部邏輯（`cogito_npc.gd:39-41, 173-175`）

```gdscript
# NPC 的 _physics_process 中，計時器倒數期間直接使用擊退速度
func _physics_process(delta: float) -> void:
    if knockback_timer > 0:
        knockback_timer -= delta
        velocity = knockback_force
        knockback_force = lerp(knockback_force, Vector3.ZERO, delta * 5)
        move_and_slide()
        return

func apply_knockback(direction: Vector3):
    knockback_force = direction.normalized() * knockback_strength  # knockback_strength = @export，預設 10
    knockback_timer = knockback_duration  # knockback_duration = @export，預設 0.5
```

**注意**：`apply_knockback` 使用 NPC 自身的 `knockback_strength`，傳入的 `direction` 只提供方向，強度由 Inspector 的 `knockback_strength` 決定。若想由武器控制強度，需傳入已乘上強度的向量：
```gdscript
# 自訂強度：繞過 knockback_strength，直接設定
collider.knockback_force = direction * 12.0
collider.knockback_timer = collider.knockback_duration
```

---

## 四、格擋減傷（玩家端整合）

NPC 攻擊玩家的路徑（`npc_state_attack.gd:67-71`）：
```gdscript
target.apply_external_force(dir * attack_stagger)    # 擊退
target.decrease_attribute("health", attack_damage)   # 扣血
```

玩家的 `decrease_attribute` 在 `cogito_player.gd:297`，需要在此加入格擋判斷：

```gdscript
# cogito_player.gd 的 decrease_attribute 修改版
func decrease_attribute(attribute_name: String, value: float):
    var attribute = player_attributes.get(attribute_name)
    if not attribute:
        return

    # 格擋減傷：只對 "health" 生效
    if attribute_name == "health":
        var wieldable = player_interaction_component.equipped_wieldable_node
        if wieldable and wieldable.get("is_blocking") == true:
            var reduction = wieldable.get("block_damage_reduction") as float
            if reduction:
                value *= (1.0 - reduction)  # 減傷
            # 消耗格擋耐力
            var block_cost = wieldable.get("block_stamina_cost") as float
            if block_cost and stamina_attribute:
                stamina_attribute.subtract(block_cost)

    attribute.subtract(value)
```

**使用 `get()` 的原因**：`equipped_wieldable_node` 可能不是劍，用 `get()` 安全存取避免腳本報錯。

---

## 五、完整節點結構（wieldable_sword.tscn）

```
wieldable_sword (Node3D + wieldable_sword.gd)
├── SwordMesh (Node3D)
│   └── MeshInstance3D
├── DamageArea (Area3D)           ← 掛載到 damage_area 欄位
│   └── CollisionShape3D          ← 劍刃的碰撞形狀（長 CapsuleShape）
├── AudioStreamPlayer3D
└── AnimationPlayer
    ├── swing       ← 輕擊
    ├── heavy_attack ← 重擊（更大幅度動畫）
    ├── block_pose  ← 格擋姿勢（靜止）
    └── idle
```

`CogitoWieldable` 基類（`cogito_wieldable.gd`）需要的 @export 欄位要在 Inspector 填寫：
- `wieldable_mesh = SwordMesh`
- `anim_action_primary = "swing"`
- `animation_player = AnimationPlayer`（路徑）

---

## 六、驗證清單

| 測試步驟 | 預期結果 |
|---|---|
| 快速點擊左鍵 | 輕擊動畫，扣 5 耐力，NPC 受傷 |
| 長按 0.5 秒後放開 | 重擊動畫，扣 20 耐力，NPC 受到 2.5x 傷害並向後飄移 |
| 右鍵格擋中被 NPC 擊中 | 血量僅扣 40%（減傷 60%），耐力條短暫下降 8 點 |
| 耐力耗盡時長按攻擊 | 不觸發重擊（耐力不足判定）|
| Console 輸出 | 重擊時可見 `apply_knockback` 擊退向量 log |
