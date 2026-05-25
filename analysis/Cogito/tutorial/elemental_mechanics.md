# 教學：如何擴充元素機制與物質反應系統

COGITO 的 `CogitoProperties` 組件內建火 (Flammable)、水 (Wet)、電 (Conductive) 三種基礎元素，並透過「反應矩陣」處理元素交互。本教學說明系統的完整運作路徑，以及如何正確擴充——以「冰凍 (Frozen)」為完整範例。

## 前置知識
- 已閱讀 [Level 4A: CogitoProperties 物質反應系統](../architecture/level4_properties_system.md)。

---

## 一、系統架構回顧（實際程式碼路徑）

```
觸發來源
│
├─ 物理碰撞（CogitoObject._on_body_entered）
│   └─ cogito_properties.start_reaction_threshold_timer(collider)
│       └─ reaction_timer.start() → timeout → check_for_systemic_reactions()
│
└─ 投射物直接碰撞（CogitoProjectile._on_body_entered）
    └─ collider.cogito_properties.reaction_collider = self
       collider.cogito_properties.check_for_systemic_reactions()  ← 跳過計時器
```

**`reaction_threshold_time`**（預設 1.0 秒）：物理接觸後要持續多久才觸發反應，投射物直接呼叫可跳過。

---

## 二、現有元素反應矩陣（`cogito_properties.gd:134-172`）

```
reaction_collider 的狀態         自身狀態                 結果
-----------------------------------------------------------------
is_on_fire == true              有 FLAMMABLE              自身著火
is_on_fire == true              有 WET                    澆熄 reaction_collider
is_electric == true             自身有 CONDUCTIVE          自身通電
自身通電                         reaction_collider 有 CONDUCTIVE  傳遞電力
elemental_properties == WET     自身 is_on_fire == true   自身被澆熄 + 變濕
elemental_properties == WET     自身非著火                自身變濕
```

---

## 三、完整範例：添加「冰凍 (Frozen)」元素

### 3.1 擴充 ElementalProperties 枚舉

打開 `addons/cogito/Components/Properties/cogito_properties.gd`，第 14 行：

```gdscript
# 修改前
enum ElementalProperties {
    CONDUCTIVE = 1,
    FLAMMABLE = 2,
    WET = 4,
}

# 修改後（位元旗標，必須是 2 的幕次）
enum ElementalProperties {
    CONDUCTIVE = 1,
    FLAMMABLE = 2,
    WET = 4,
    COLD = 8,    # 新增：可結冰/低溫
    ACID = 16,   # 新增：腐蝕
}
```

同時更新第 29 行的 `@export_flags`（決定 Inspector 的勾選項目）：
```gdscript
# 修改前
@export_flags("CONDUCTIVE", "FLAMABLE", "WET") var elemental_properties: int = 0

# 修改後（注意：字串要與 enum 鍵名一致）
@export_flags("CONDUCTIVE", "FLAMABLE", "WET", "COLD", "ACID") var elemental_properties: int = 0
```

### 3.2 新增狀態追蹤變數與信號

在現有 signal 區塊下（約第 13 行後）加入：
```gdscript
# cogito_properties.gd 新增
signal has_frozen()
signal has_thawed()

@export_group("Freeze Parameters")
@export var spawn_on_frozen : PackedScene
@export var freeze_move_speed_multiplier : float = 0.0  # 0 = 完全停止

var is_frozen : bool = false
```

### 3.3 擴充 check_for_systemic_reactions()

在 `check_for_systemic_reactions()` 末尾（第 172 行後）加入：
```gdscript
# cogito_properties.gd:check_for_systemic_reactions() 末尾加入
# ── 冰凍反應：WET + COLD 碰撞 → 結冰 ──
if (elemental_properties & ElementalProperties.WET):
    if reaction_collider.cogito_properties and \
       (reaction_collider.cogito_properties.elemental_properties & ElementalProperties.COLD):
        if not is_frozen:
            make_frozen()

# ── 解凍反應：FROZEN + FIRE 碰撞 → 解凍 ──
if is_frozen:
    if reaction_collider.cogito_properties and reaction_collider.cogito_properties.is_on_fire:
        thaw()
```

### 3.4 實作狀態轉變方法

在 `loose_electricity()` 之後（約第 268 行後）加入：
```gdscript
func make_frozen() -> void:
    is_frozen = true
    has_frozen.emit()
    
    # 移除 WET，改為 COLD 狀態（水結冰後不再是液態）
    elemental_properties &= ~ElementalProperties.WET  # 清除 WET bit
    elemental_properties |= ElementalProperties.COLD   # 設置 COLD bit
    
    # 生成結冰特效
    if spawn_on_frozen:
        spawn_elemental_vfx(spawn_on_frozen)
    
    # 通知父節點（可選：讓 NPC 或物件凍結移動）
    if get_parent().has_method("on_frozen"):
        get_parent().on_frozen(freeze_move_speed_multiplier)


func thaw() -> void:
    is_frozen = false
    has_thawed.emit()
    
    # 解凍後變濕（冰化水）
    elemental_properties &= ~ElementalProperties.COLD
    elemental_properties |= ElementalProperties.WET
    
    clear_spawned_effects()
    
    if get_parent().has_method("on_thawed"):
        get_parent().on_thawed()
```

### 3.5 整合到 NPC（冰凍使 NPC 停止移動）

在 `cogito_npc.gd` 加入兩個方法：
```gdscript
# cogito_npc.gd 末尾加入
var _pre_freeze_speed : float = 0.0

func on_frozen(speed_multiplier: float) -> void:
    _pre_freeze_speed = move_speed
    move_speed = _pre_freeze_speed * speed_multiplier
    # 若要視覺凍結：改變 AnimationTree 狀態
    animation_tree.set("parameters/Transition/transition_request", "frozen")

func on_thawed() -> void:
    move_speed = _pre_freeze_speed
    animation_tree.set("parameters/Transition/transition_request", "idle")
```

---

## 四、建立冷氣投射物（傳遞 COLD 屬性）

讓某種投射物擊中物件時傳遞冷屬性（而非直接造成傷害）。

### 4.1 建立冷氣彈資源

1. 複製 `addons/cogito/Wieldables/wieldable_toy_pistol.gd` → 改名為 `wieldable_cold_wand.gd`。
2. 修改投射物場景：在 `CogitoProjectile` 節點下掛載一個 `CogitoProperties` 組件，勾選 `COLD`。

### 4.2 冷氣彈擊中後觸發反應

`CogitoProjectile._on_body_entered()` 在命中後，若 collider 有 `CogitoProperties` 且投射物自身也有 `CogitoProperties`，會呼叫（`cogito_projectile.gd:86-87`）：
```gdscript
# 來自 cogito_projectile.gd:86-87
collider.cogito_properties.reaction_collider = self  # self = 冷氣彈（帶 COLD 屬性）
collider.cogito_properties.check_for_systemic_reactions()
```
此路徑**跳過計時器**，立即觸發我們剛才加入的冰凍判斷。只要 collider 帶有 WET 屬性且投射物帶有 COLD，就會立即凍結。

---

## 五、已知 Bug 修正建議

**`spawn_elemental_vfx()` 的 max 判斷錯誤**（`cogito_properties.gd:276`）：
```gdscript
# 原始（錯誤）：幾乎永遠清除特效
if spawned_effects.size() <= max_spawned_vfx + 1:
    clear_spawned_effects()

# 應為：只在超過上限時清除
if spawned_effects.size() >= max_spawned_vfx:
    clear_spawned_effects()
```
此 Bug 會導致特效不斷閃爍——每次 `spawn_elemental_vfx()` 都立即清除所有已生成的特效再重新生成一個。

---

## 六、驗證清單

| 測試步驟 | 預期結果 |
|---|---|
| 建立帶 WET 屬性的物件 A；建立帶 COLD 的投射物 B | |
| 以投射物 B 擊中物件 A | 物件 A 觸發 `make_frozen()`，生成冰凍特效，`is_frozen = true` |
| 以著火物件接觸已凍結的 A（接觸超過 reaction_threshold_time） | 物件 A 觸發 `thaw()`，特效消失，恢復 WET 屬性 |
| 讓凍結 NPC 的 `on_frozen()` 被呼叫 | NPC 速度歸零，動畫切換為凍結狀態 |
| 存檔讀檔後 | `is_frozen` 為 false（屬性狀態目前不持久化，重讀後從初始狀態開始）|

**注意**：`CogitoProperties` 的狀態（`is_frozen`、`is_on_fire`）目前未被存檔系統序列化，若需持久化，需在父節點的 `save()/set_state()` 中手動處理。
