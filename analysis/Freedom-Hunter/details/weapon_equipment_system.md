# 武器裝備系統 深入分析

## 繼承結構

```
Area3D
└── Equipment (src/equipment/equipment.gd)   ← 可偵測碰撞的裝備基底
    ├── Weapon  (src/equipment/weapon.gd)    ← 武器，含銳利度系統
    └── Armour  (src/equipment/armour.gd)    ← 防具，含技能/寶石槽（待開發）
```

**為何繼承 Area3D？**  
武器需要偵測揮砍時是否碰到敵人（`_on_body_entered`），Area3D 提供重疊偵測而不產生物理阻擋。

---

## Equipment 基底（equipment.gd）

```gdscript
extends Area3D

@export_range(-100, 100) var strength  = 0    # 物理攻擊力 / 防禦力
@export_range(-100, 100) var fire      = 0    # 各元素屬性值
@export_range(-100, 100) var water     = 0
@export_range(-100, 100) var ice       = 0
@export_range(-100, 100) var thunder   = 0
@export_range(-100, 100) var dragon    = 0
@export_range(-100, 100) var poison    = 0
@export_range(-100, 100) var paralysis = 0

var elements = {}   # 在 _init 時從上方 export 變數建立字典
```

`@export_range` 使裝備屬性可在 Godot 編輯器 Inspector 面板直接設定，方便關卡設計師調整。

---

## Weapon 武器類別（weapon.gd）

### 銳利度（Sharpness）資料結構

```gdscript
class Sharp:
    var type    # 顏色名稱字串（"purple", "white", ...）
    var value   # 當前剩餘銳利度值
    var max_val # 這個等級的最大值

@onready var sharpness = [
    Sharp.new("purple", purple_sharpness),   # 最高等級（最快傷害加乘）
    Sharp.new("white",  white_sharpness),
    Sharp.new("blue",   blue_sharpness),
    Sharp.new("green",  green_sharpness),
    Sharp.new("yellow", yellow_sharpness),
    Sharp.new("orange", orange_sharpness),
    Sharp.new("red",    red_sharpness)       # 最低等級（負傷害加乘，彈刀）
]
```

7 個等級對應 Monster Hunter 系列原作的銳利度顏色系統，從 export 變數設定各等級初始值，允許不同武器有不同的銳利度分佈。

### 磨損（blunt）流程

```gdscript
func blunt(amount):
    for s in sharpness:              # 從最高等級開始
        if s.value > 0:
            var diff = amount - s.value
            s.value -= amount
            amount = diff            # 剩餘量繼續往下扣
            if s.value < 0:
                s.value = 0
            if amount <= 0:
                break
    update_animation()
```

**範例**：武器有 blue=5, green=10，blunt(7)：
- blue: 5→0（剩餘 amount=2）
- green: 10→8（amount=0，停止）

### 回復（sharpen）流程

```gdscript
func sharpen(amount):
    for s in sharpness:              # 從最高等級開始
        if s.value < s.max_val:
            s.value = s.max_val      # 直接補滿這個等級
            amount -= s.max_val
            if amount <= 0:
                s.value += amount    # 可能補過頭，修正
                break
    update_animation()
    return amount                    # 回傳剩餘量（全滿時 > 0）
```

### HUD 銳利度顯示

```gdscript
func update_animation():
    var anim = sharpness_node.get_current_animation()
    for s in sharpness:
        if s.value > 0:          # 找到第一個有值的等級
            if anim != s.type:
                sharpness_node.play(s.type)  # 播放對應顏色動畫
            return
    if anim != "red":
        sharpness_node.play("red")   # 全部磨完也顯示 red
```

`sharpness_node` 是 `$/root/hud/status/sharpness/fading` 的 AnimationPlayer，每個顏色都有對應動畫。

### 傷害觸發（碰撞偵測）

```gdscript
# weapon.gd:97-101
func _on_body_entered(body):
    if body != player and body is Entity and not body.is_dead():
        body.damage(get_weapon_damage(body, null), 0.0, self, player)
        $audio.play()
        blunt(1)   # 每次命中磨損 1

func get_weapon_damage(body, impact):
    # TODO: 傷害修飾計算（銳利度加成、弱點加成等）
    return strength
```

目前 `get_weapon_damage` 只回傳基礎 strength，銳利度的傷害加乘尚未實作（TODO）。

### 與玩家的關係取得

```gdscript
@onready var player = $"../../../.."   # 武器 → BoneAttachment → Skeleton → Armature → Player
```

依賴固定的節點層級路徑，如果骨架結構改變會斷掉。

---

## Armour 防具類別（armour.gd）

```gdscript
extends "equipment.gd"

var skills = []   # 防具技能（待開發）
var gems = []     # 寶石槽（待開發）

func _ready():
    pass           # 目前無實作
```

防禦值計算在 Player 側：
```gdscript
# player.gd:138-143
func get_defence() -> int:
    var defence := 0
    for piece in equipment.armour.values():   # 5 個部位
        if piece != null:
            defence += piece.strength          # 累加所有防具的 strength
    return defence
```

---

## 裝備插槽分配

```gdscript
# player.gd:15
var equipment = {
    "weapon": null,
    "armour": {
        "head":     null,
        "torso":    null,
        "rightarm": null,
        "leftarm":  null,
        "leg":      null
    }
}
```

| 插槽 | 骨骼名稱 | 說明 |
|------|---------|------|
| weapon | "weapon_L" | 左手武器（目前硬編碼 laser_sword） |
| head | - | 頭部防具（未掛載實作） |
| torso | - | 軀幹防具 |
| rightarm | - | 右臂 |
| leftarm | - | 左臂 |
| leg | - | 腿部 |

目前只有武器有完整實作，防具雖有資料結構但尚未有場景內的裝備流程。

---

## 動態骨架掛載機制

```gdscript
# player.gd:31-43
func set_equipment(model, bone):
    var skel = $Armature/Skeleton3D
    for node in skel.get_children():
        if node is BoneAttachment3D:
            if node.get_bone_name() == bone:
                node.add_child(model)     # 已有此骨骼的附著點，直接加入
                node.set_name(bone)
                return
    # 沒有的話動態建立
    var ba = BoneAttachment3D.new()
    ba.set_name(bone)
    ba.set_bone_name(bone)
    ba.add_child(model)
    skel.add_child(ba)
```

`BoneAttachment3D` 是 Godot 的骨骼追蹤節點，其子節點會跟隨指定骨骼位置/旋轉移動，用於將武器/防具模型「綁定」到角色動畫骨架上。

---

## 系統設計分析

### 優點
1. **Editor 友善**：`@export_range` 讓武器屬性可視化調整
2. **多態繼承**：Equipment 提供統一的元素屬性，子類各自擴展
3. **銳利度陣列設計**：磨損/回復只需遍歷陣列，邏輯簡單清晰

### 待完成（TODO）
| 功能 | 位置 |
|------|------|
| 銳利度傷害加乘 | weapon.gd `get_weapon_damage()` |
| 防具技能系統 | armour.gd `skills []` |
| 寶石槽系統 | armour.gd `gems []` |
| 元素武器傷害計算 | 需與 monster.gd `weakness` 對接 |
| 裝備替換 UI | 無完整的裝備介面，只能透過程式碼 |
