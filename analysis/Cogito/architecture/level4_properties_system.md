# Cogito — Level 4A CogitoProperties 物質反應系統分析

## 一、系統概覽

**位置**：`addons/cogito/Components/Properties/cogito_properties.gd`

`CogitoProperties` 是一個 `Node3D` 組件，掛載於任何 `CogitoObject` 或 `CogitoNPC` 子節點下，賦予宿主「物質屬性」與「元素反應」能力。系統採用**位元旗標（Bitflag）**編碼屬性狀態，以**閾值計時器（Reaction Threshold Timer）**過濾瞬間接觸，達成可組合的物質反應鏈。

---

## 二、屬性編碼：雙層位元旗標

### ElementalProperties（元素屬性）
```
CONDUCTIVE = 1  (0b001)  ← 導電
FLAMMABLE  = 2  (0b010)  ← 易燃
WET        = 4  (0b100)  ← 溼潤
```

### MaterialProperties（材質屬性）
```
SOFT = 1  (0b001)  ← 柔軟（影響投射物穿透邏輯）
```

二者分別以 `@export_flags` 暴露在 Inspector，可以任意組合（如一個木桶可同時為 FLAMMABLE + CONDUCTIVE）。

位元運算範例：
```
# 檢查是否易燃
if elemental_properties & ElementalProperties.FLAMMABLE: ...

# XOR 切換（Toggle）
elemental_properties = elemental_properties ^ ElementalProperties.WET
```

---

## 三、組件偵測機制（find_cogito_properties）

**所有宿主**（CogitoObject、CogitoNPC）的 `_ready()` 均呼叫：
```
find_cogito_properties():
  var property_nodes = find_children("", "CogitoProperties", true)
  if property_nodes:
    cogito_properties = property_nodes[0]  // 取第一個子節點
```

設計者只需在物件節點下加入 `CogitoProperties.tscn` 子場景，宿主會自動偵測並持有參照。屬性完全選配——無 CogitoProperties 子節點則 `cogito_properties` 為 `null`，碰撞邏輯會跳過。

---

## 四、兩條觸發路徑

### 路徑 A：接觸型（CogitoObject 的 body_entered/body_exited）

**位置**：`cogito_object.gd:131-140`

```
_on_body_entered(body):
  if body.has_method("save") and cogito_properties:  // 只處理 CogitoObject（有 save 方法）
    cogito_properties.start_reaction_threshold_timer(body)

_on_body_exited(body):
  if body.has_method("save") and cogito_properties:
    cogito_properties.check_for_reaction_timer_interrupt(body)
```

**閾值計時器（Reaction Threshold Timer）**：
```
start_reaction_threshold_timer(passed_collider):
  reaction_collider = passed_collider
  add_systemic_body(passed_collider)            // 加入 reaction_bodies 陣列
  if reaction_timer.is_stopped():
    reaction_timer.wait_time = reaction_threshold_time  // 預設 1.0 秒
    reaction_timer.start()

// 計時器到期 → check_for_systemic_reactions()

check_for_reaction_timer_interrupt(passed_collider):
  remove_systemic_body(passed_collider)
  if passed_collider == reaction_collider:
    reaction_timer.stop()             // 接觸中斷，取消反應
  if reaction_bodies.size() == 0:
    if !electric_on_ready: loose_electricity()  // 無任何接觸 → 失去電力
```

**設計意圖**：防止瞬間擦過就觸發反應，要求持續接觸至少 `reaction_threshold_time`（預設 1 秒）才點火/導電。

### 路徑 B：投射物型（直接呼叫，繞過計時器）

**位置**：`cogito_projectile.gd:86-87`

```
// 投射物命中 → 同時雙方都有 properties
collider.cogito_properties.reaction_collider = self   // 設定反應來源
collider.cogito_properties.check_for_systemic_reactions()  // 立即執行
```

投射物不需等待閾值——箭矢命中物體時即時觸發反應（例如火焰箭矢立刻點燃）。

---

## 五、反應邏輯（check_for_systemic_reactions）

**位置**：`cogito_properties.gd:134-173`

```
check_for_systemic_reactions():
  if !reaction_collider or !reaction_collider.cogito_properties: return

  ### 火焰反應
  if reaction_collider.cogito_properties.is_on_fire:
    if self FLAMMABLE:  → set_on_fire()          // 被點燃
    if self WET:        → reaction_collider.extinguish()  // 撲滅對方

  ### 電力反應（雙向傳導）
  if self CONDUCTIVE:
    if self.is_electric:
      → reaction_collider.cogito_properties.make_electric()  // 傳電給對方
    if reaction_collider.cogito_properties.is_electric:
      → make_electric()                                       // 從對方獲電

  ### 水反應（match 語法，僅 WET）
  match reaction_collider.cogito_properties.elemental_properties:
    ElementalProperties.WET:
      if self is_on_fire:
        → extinguish(); make_wet()    // 被水澆熄 + 自身變溼
      else:
        → make_wet()                  // 直接變溼
```

### 反應矩陣總覽

| 觸發者狀態 | 自身屬性 | 結果 |
|---|---|---|
| 接觸物 is_on_fire | FLAMMABLE | 自身點燃 |
| 接觸物 is_on_fire | WET | 撲滅接觸物 |
| 接觸物 is_electric | CONDUCTIVE | 自身帶電 |
| 自身 is_electric | 接觸物 CONDUCTIVE | 傳電給接觸物 |
| 接觸物 WET | 自身 is_on_fire | 熄滅 + 自身變溼 |
| 接觸物 WET | 自身非著火 | 自身變溼 |

---

## 六、狀態變更函數

### 燃燒系列
```
set_on_fire():
  if NOT FLAMMABLE: return (防衛檢查)
  is_on_fire = true
  spawn_elemental_vfx(spawn_on_ignite)   // 生成火焰 VFX 場景
  Audio.play_sound_3d(audio_igniting)
  has_ignited.emit()
  if burn_damage_amount > 0:
    start_burn_damage_timer()             // 啟動週期傷害計時器
  audio_stream_player_3d.stream = audio_burning
  audio_stream_player_3d.play()

apply_burn_damage():                      // 每 burn_damage_interval 秒觸發一次
  deal_burn_damage.emit(burn_damage_amount)
  get_parent().damage_received.emit(burn_damage_amount)  // 直接通知宿主扣血
  if is_on_fire: start_burn_damage_timer()  // 循環計時

extinguish():
  is_on_fire = false
  damage_timer.stop()
  clear_spawned_effects()  // 移除所有 VFX 節點
  has_been_extinguished.emit()
```

### 溼潤系列
```
make_wet():
  XOR 設置 WET 旗標（避免重複設置）
  if is_on_fire: extinguish()   // 溼 → 自動滅火
  spawn_elemental_vfx(spawn_on_wet)
  has_become_wet.emit()

make_dry():
  XOR 清除 WET 旗標
  clear_spawned_effects()
  has_become_dry.emit()
```

### 電力系列
```
make_electric():
  if NOT CONDUCTIVE: return
  is_electric = true
  spawn_elemental_vfx(spawn_on_electrified)
  has_become_electric.emit()
  recheck_systemic_reactions()   // 立即對所有 reaction_bodies 重新傳導

loose_electricity():
  is_electric = false
  clear_spawned_effects()
  has_lost_electricity.emit()
```

---

## 七、VFX 管理

```
spawn_elemental_vfx(vfx_packed_scene):
  var spawned_object = vfx_packed_scene.instantiate()
  get_parent().add_child.call_deferred(spawned_object)
  
  // ⚠ Bug：條件邏輯反向
  if spawned_effects.size() <= max_spawned_vfx + 1:
    clear_spawned_effects()     // 應為 >= 才觸發清除
  
  spawned_effects.append(spawned_object)
  spawned_object.position = Vector3(0,0,0)  // 放置於宿主本地原點

clear_spawned_effects():
  for node in spawned_effects: node.queue_free()
  spawned_effects.clear()
```

**Bug 說明**：`spawn_elemental_vfx` 中，當 `spawned_effects.size() <= max_spawned_vfx + 1` 時清除所有 VFX，邏輯反向。正確意圖應為超過上限才清除（`>=`），目前行為是在剛開始生成時就清除，直到數量超過上限後反而不清除。

---

## 八、投射物碰撞的四情境矩陣

**位置**：`cogito_projectile.gd:61-87`

```
投射物命中 → 判斷雙方是否有 CogitoProperties：

情境 1：雙方都無 properties
  → 正常造成傷害（deal_damage）

情境 2：目標有 properties，投射物無
  → 忽略 properties，正常造成傷害（TODO：未來可能擴充）

情境 3：只有投射物有 properties
  match cogito_properties.material_properties:
    SOFT → 軟性投射物不造成傷害，destroy_on_impact 時銷毀

情境 4：雙方都有 properties
  if 雙方都是 SOFT → 造成傷害
  → 直接呼叫 check_for_systemic_reactions()（繞過 1 秒閾值計時器）
```

---

## 九、關聯組件

### HitboxComponent（`Components/HitboxComponent.gd`）
- 掛載於任何有 `damage_received` 信號的節點
- 連接 `damage_received` → 呼叫 `health_attribute.subtract(damage_amount)`
- 支援命中位置 VFX（全域 / 本地座標兩種模式）
- 支援剛體衝擊力（`apply_impulse`）與 CharacterBody3D 擊退（`apply_knockback`）
- 為「傷害信號 → 血量屬性」的標準橋接組件

### ImpactAttributeDamage（`Components/ImpactAttributeDamage.gd`）
- 掛載於 RigidBody3D，偵測物理碰撞速度
- 速度超過 `minimum_velocity` 才觸發，並設 `next_impact_time` 冷卻防止連擊
- 典型用途：高速墜落時扣除玩家體力，或可破壞物件被重物壓碎

### Explosion（`Assets/VFX/Explosion_01/explosion.gd`）
- 繼承 Area3D，以 Tween 動態放大碰撞球形半徑與 Mesh Scale
- `explode_on_spawn = true` 時，`_ready()` 立即觸發爆炸
- `_on_body_entered` 對 CogitoPlayer 直接呼叫 `apply_external_force` + `decrease_attribute`
- 對其他物件發出 `damage_received` 信號（目前**不觸發** systemic properties，標有 TODO）

---

## 十、系統訊號清單

| 訊號 | 觸發時機 | 典型用途 |
|---|---|---|
| `has_ignited()` | 成功點燃 | 觸發周邊可燃物、更新 UI |
| `has_been_extinguished()` | 熄滅 | 停止傷害、清除 VFX |
| `deal_burn_damage(amount)` | 每燃燒週期 | 第二個監聽者可額外處理 |
| `has_become_wet()` | 變溼 | 改變材質、觸發電擊傷害 |
| `has_become_dry()` | 乾燥 | 恢復易燃性 |
| `has_become_electric()` | 帶電 | 觸發電擊玩家邏輯 |
| `has_lost_electricity()` | 失電 | 清除電力 VFX |

---

## 十一、架構模式總結

```
任何物件（CogitoObject / CogitoNPC）
  └─ CogitoProperties（選配子節點）
       ├─ 位元旗標：elemental_properties（CONDUCTIVE/FLAMMABLE/WET）
       ├─ 位元旗標：material_properties（SOFT）
       ├─ 狀態變數：is_on_fire, is_electric
       ├─ 閾值計時器：reaction_threshold_time（過濾瞬間接觸）
       └─ VFX 池：spawned_effects[]（統一管理生命週期）

兩條觸發路徑：
  ① 接觸型（body_entered → 閾值計時器 → 反應）
  ② 投射物型（碰撞 → 直接呼叫，無等待）

反應鏈可無限延伸：
  物件A（燃燒）→ 接觸 物件B（易燃）→ B 點燃
  物件B（燃燒）→ 接觸 物件C（易燃）→ C 點燃  ...
```

**主要設計哲學**：
- 組件式選配：不需要 Properties 的物件不受影響，效能零開銷
- 訊號解耦：狀態變化只發射訊號，上層系統自行訂閱（如 UI、音效、血量）
- 可擴充矩陣：新元素（毒素、冰凍）只需新增 enum 值與對應 `match` 分支
