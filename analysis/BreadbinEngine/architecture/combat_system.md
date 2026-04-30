# BreadbinEngine — 戰鬥系統深度分析

> 分析日期：2026-04-30

---

## 一、AttackTable：資料驅動攻擊表

### 資料格式
CSV 檔案位於 `Data/AttackTable.tres`，格式如下：

```
AttackID, AnimationPath, DamageMultiplier
100, HumanoidBase/sword_rslash, 1.0
101, HumanoidBase/sword_backslash, 1.0
102, HumanoidBase/sword_twirlslash, 1.0
```

### 載入流程（`Scripts/Globals/AttackTable.gd:16`）
```gdscript
func load_csv():
    var csvfile = FileAccess.open("res://Data/AttackTable.tres", FileAccess.READ)
    while !csvfile.eof_reached():
        var csvdata = csvfile.get_csv_line()
        # ID[0], AnimationPath[1], Multiplier[2]
        dicttoaddto[ID] = [AttackAnimationPath, AttackMultiplier]
    dicttoaddto.erase("AttackID")  # 移除標頭列
```

最終結構（Dictionary）：
```gdscript
attacktable = {
    100: ["HumanoidBase/sword_rslash", 1.0],
    101: ["HumanoidBase/sword_backslash", 1.0],
    ...
}
```

---

## 二、WeaponBase：武器招式陣列

每把武器（`Scripts/Combat/Weapon_Base.gd`）以 Export 陣列儲存各輸入動作的 Attack ID 序列：

```gdscript
@export var Weapon_1H_R1 : Array[int] = [100, 101, 102]  # 三連擊
@export var Weapon_1H_R2 : Array[int] = [100]             # 重攻
@export var Weapon_1H_L1 : Array[int] = [100]
@export var Weapon_1H_L2 : Array[int] = [100]
@export var Weapon_1H_RunningAttack : Array[int] = [100]
@export var Weapon_1H_FallingAttack : Array[int] = [100]
@export var Weapon_1H_R1_Critical : Array[int] = [100]    # 背刺/處決
@export var Weapon_1H_L1_Critical : Array[int] = [100]

# 以上全部有對應 2H 版本
@export var Weapon_2H_R1 : Array[int] = [100]
...
```

**設計意涵**：新增武器只需在 Inspector 中填入 ID 陣列，不需寫任何程式碼。

---

## 三、連擊流程（Combo Pipeline）

```
玩家按 R1
    ↓
PlayerActor.handle_attack_inputs()       # PlayerBase.gd:156
    ↓
setup_attack_animation("R1")             # PlayerBase.gd:104
    ↓
construct_attack_array_to_query("R1")    # PlayerBase.gd:134
    → 判斷是否在地面、是否正在衝刺
    → 回傳字串，例如 "Weapon_1H_R1"
    ↓
Current_Weapon.get("Weapon_1H_R1")[current_combo]
    → 取得 AttackID（例如 100）
    ↓
get_attack_name_from_attacktable(100)    # ActorBase.gd:209
    → 查詢 AttackTable autoload
    → 回傳動畫名稱 "HumanoidBase/sword_rslash"
    → 同時設定武器傷害倍率
    ↓
CurrentAttackAnimation = "HumanoidBase/sword_rslash"
handle_actor_state("attacking")
can_combo = false
current_combo += 1
    ↓
ActorAnimationPlayer 播放動畫
    ↓
動畫軌道 → 呼叫 ActorAnimationPlayer.allow_combo()  # 連擊視窗開啟
        或 → 呼叫 ActorAnimationPlayer.end_combo()   # 連擊結束
```

### 攻擊狀態決策（`construct_attack_array_to_query`）

```gdscript
# PlayerBase.gd:134
if !is_on_floor() and velocity.y < 2:
    InputStatus = "FallingAttack"    # 空中攻擊
elif sprinting == true:
    InputStatus = "RunningAttack"    # 衝刺攻擊（同時停止衝刺）
else:
    InputStatus = inputstring        # 一般 R1/R2/L1/L2
```

---

## 四、Hitbox 激活流程

動畫中的 CallMethod Track 呼叫：

```gdscript
# ActorAnimationPlayer.gd:31
func activate_weapon_hitbox(time:float=0.4, WhichOne:int=0):
    owner.owner.ActivateWeaponHitbox(time, WhichOne)

# ActorBase.gd:255
func ActivateWeaponHitbox(time:float=0.4, whichone:int=0):
    if Current_Weapon != self:
        Current_Weapon.AffectHitbox(whichone, true)          # 開啟 Area3D 監聽
        Current_Weapon.get_node("RemoveHitboxTimerNode").start(time)  # 計時自動關閉
```

### 傷害碰撞規則
- `Hitbox_Damage`（武器）：廣播層 10，監聽層 11
- `ActorHitArea`（角色）：廣播層 11，監聽層 10
- 兩者重疊 → `ActorHitArea` 的 `area_entered` → `_ActorHitArea_entered()`

### 傷害計算（`ActorBase.gd:283`）
```gdscript
func _ActorHitArea_entered(area:Area3D):
    if area.get_collision_layer_value(5) == true:
        take_damage(10, true, true)   # Killbox → 即死
    elif "HitboxDamageMultiplier" in area:
        # 檢查 Teams_CanHurt 矩陣決定是否可傷害
```

---

## 五、Hitbox 傷害倍率系統

每個 `Hitbox_Damage`（`Scripts/Combat/Hitbox_Damage.gd`）有：
- `HitboxLevel`：升級等級（影響基礎倍率）
- `MultiplierPerLevel`：每級增加的倍率
- `HitboxDamageMultiplier`：當前倍率

`WeaponBase.SetHitboxDamageMultiplier()` 在每次攻擊時根據 AttackTable 的倍率更新：

```gdscript
# Weapon_Base.gd:70
func SetHitboxDamageMultiplier(AllHitboxes:bool, WhichHitboxInt:int, NewValue:float):
    HitboxQueried.HitboxDamageMultiplier = NewValue + (HitboxLevel * HitboxDamagePerLevel)
```

---

## 六、武器持有狀態（Two-Handing）

```gdscript
# ActorBase.gd:77
# 0 = 單手，1 = 雙手（右武器），2 = 雙手（左武器）
var Two_Handing_State : int = 0
```

`setup_attack_animation()` 根據狀態決定使用 L_Weapon 或 R_Weapon，並查詢對應的 `Weapon_1H_*` 或 `Weapon_2H_*` 陣列。

---

## 七、動畫系統雙軌架構

| 系統 | 用途 | 控制方式 |
|---|---|---|
| `AnimationPlayer` | 攻擊、翻滾、受傷動畫 | 直接 `play()` |
| `AnimationTree` | 移動混合（走路/靜止） | 設定 `parameters/PlayerState/current` |

`ActorAnimationPlayer` 的 CallMethod Track 可觸發的函式：

| 函式名稱 | 用途 |
|---|---|
| `allow_combo()` | 開啟連擊視窗 |
| `end_combo()` | 結束攻擊回 idle |
| `stop_rolling()` | 翻滾結束 |
| `activate_weapon_hitbox(time, which)` | 開啟武器 Hitbox |
| `push_actor_forward(amount)` | 攻擊時向前衝刺力 |
| `change_actor_rotation_multiplier(rot, move)` | 控制攻擊中的轉向靈敏度 |
