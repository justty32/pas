# 道具與物品欄系統 深入分析

## 類別繼承樹

```
Item (src/items/item.gd)                     ← 基底（純資料類，非 Node）
├── Consumable (src/items/consumable.gd)     ← 可使用消耗品
│   ├── Potion   (consumables/potion.gd)
│   ├── Whetstone(consumables/whetstone.gd)
│   ├── Meat     (consumables/meat.gd)
│   ├── Barrel   (consumables/barrel.gd)
│   ├── CannonBall(consumables/cannon_ball.gd)
│   └── Firework (consumables/firework.gd)
└── Collectible  (src/items/collectibles.gd) ← 收集材料（採集/掉落物）
```

**注意**：Item 系列不繼承 Node，是純 GDScript 物件（Reference 型別）。

---

## Item 基底類別（item.gd）

```gdscript
class_name Item
var name: String
var icon: Texture2D
var quantity: int
var rarity: int    # 0-99，稀有度越高數值越大

func clone() -> Item:
    return get_script().new(name, icon, quantity, rarity)
```

`clone()` 使用 `get_script().new()` 實現多型複製，子類各自覆寫傳入正確參數。

---

## Consumable 消耗品基底（consumable.gd）

```gdscript
var max_quantity: int   # 最大攜帶量（堆疊上限）

func use(player):
    if quantity > 0 and effect(player):  # effect() 回傳 false 表示無法使用
        quantity -= 1

func add(n: int) -> int:
    # 回傳溢出的數量
    var max_n := max_quantity - quantity
    quantity += min(n, max_n)
    return max(0, n - max_n)

func set_label_color(label: Label):
    # 數量滿了顯示紅色，否則白色
    if quantity >= max_quantity:
        label.add_theme_color_override("font_color", Color.RED)
```

**Template Method 設計**：`use()` 呼叫抽象方法 `effect()`，子類只需覆寫 `effect()` 實作具體效果。

---

## 各消耗品詳解

### Potion（potion.gd）
```gdscript
# _init: max_quantity=10, rarity=50
func effect(target: Player):
    if target.can_consume() and target.hp < target.hp_max:  # 滿血不消耗
        target.heal(heal)                # heal=20 HP
        target.state_machine.travel("drink")  # 播放喝藥水動畫
        return true
    return false
```
- 只在 `idle-loop` 狀態可使用（`can_consume()` 檢查）
- 觸發 drink 動畫，動畫結束後 entity.gd `_on_animation_tree_animation_finished` 自動 `stop()`

### Whetstone（whetstone.gd）
```gdscript
# _init: max_quantity=20, rarity=10
func effect(_player: Player):
    if _player.equipment.weapon != null and not _player.equipment.weapon.is_sharpened():
        _player.equipment.weapon.sharpen(sharp)   # sharp=20
        _player.consume_item_animation("whetstone")
        return true
    return false
```
- 武器已完全銳利時不消耗（`is_sharpened()` 回傳 true）

### Meat（meat.gd）
```gdscript
# _init: max_quantity=10, rarity=50
func effect(target: Player):
    if target.stamina_max < target.MAX_STAMINA and target.is_idle():
        target.stamina_max_increase(stamina)   # stamina=25，增加最大耐力上限
        target.state_machine.travel("eat")
        return true
    return false
```
- 只在 idle 且未達最大耐力上限（200）時有效
- 是唯一永久提升角色數值的消耗品

### Barrel（barrel.gd）
```gdscript
# _init: max_quantity=5, rarity=10
func effect(player):
    var barrel = scene.instantiate()    # 生成 3D 物理爆炸桶
    player.drop_item_on_floor(barrel)  # 放置在玩家前方 $drop_item 標記位置
    return true
```
爆炸桶邏輯（barrel-scene.gd）：
```gdscript
# Timer 倒數後爆炸
func _on_timer_timeout():
    $"explosion/animation".play("explode")
    for body in $"explosion".get_overlapping_bodies():
        if body is Entity:
            var d = body.global_transform.origin - global_transform.origin
            var dmg = int((r - d.length()) * 20 + 1)  # 距離越近傷害越高
            body.damage(dmg, 0.1)
        elif body.is_in_group("explosive"):
            # 連鎖爆炸：給其他爆炸物施加動量並縮短引信
            body.apply_central_impulse(momentum)
            body_timer.set_wait_time(0.5 - randf_range(0, 0.4))
```

### CannonBall（cannon_ball.gd）
```gdscript
const fire_speed = 200
const fire_angle = deg_to_rad(5)  # 略微向上仰角

func fire(from_cannon: CannonNode, spawn=null):
    var cannon_ball: CannonBallNode = CannonBallScene.instantiate()
    var position := from_cannon.ball_spawn.global_position
    spawn.add_child(cannon_ball)
    cannon_ball.global_transform.origin = position
    # 從大砲 Basis 旋轉 5° 計算發射方向
    var a: Basis = from_cannon.global_transform.basis.rotated(Vector3.RIGHT, fire_angle)
    var velocity := Vector3(-a.x.z, a.y.z, a.z.z) * fire_speed
    cannon_ball.fire(velocity)
    self.quantity -= 1
```
碰撞傷害（cannon_ball-scene.gd）：
```gdscript
func _on_CannonBall_body_entered(body):
    var momentum = velocity_last_frame.length() * mass
    if momentum > 200:       # 速度夠快才爆炸
        $AnimationPlayer.play("explode")
        if body is Entity:
            body.damage(momentum, 0.1)
```
- 使用上一幀速度計算動能（避免碰撞後速度已歸零）
- 動能門檻設計防止低速滾動觸發爆炸

### Firework（firework.gd + firework-scene.gd）
```gdscript
# 道具效果
func effect(_player):
    var firework = scene.instantiate()
    _player.drop_item_on_floor(firework)
    firework.launch()    # 立即發射
    return true

# 場景節點
func launch():
    linear_velocity = Vector3(0, 70, 0)          # 向上 70 m/s
    linear_velocity.x += randf_range(-20, 20)    # 隨機散佈
    $animation.play("launch")
    await get_tree().create_timer(randf_range(4, 5)).timeout
    $animation.play("boom")
    await $animation.animation_finished
    queue_free()
```

---

## Inventory 物品欄系統（inventory.gd）

### 資料結構

```gdscript
extends Panel           # 是 Control 節點，同時負責資料和 UI
var items := []         # Item 物件陣列
var max_slots: int      # 總格數（含空格）
var dragging            # 當前拖曳中的物件
```

### 新增物品邏輯（add_item）

```
add_item(item, slot=null):
    if slot == null:
        found = find_item_by_name(item.name)
        if found != null:            ← 同名物品：堆疊
            overflow = found.add(item.quantity)
            更新 UI slot 顯示
        else:                        ← 新物品：佔用空槽
            clone = item.clone()
            items.append(clone)
            find_free_slot().set_item(clone)
    elif slot.item != null:          ← 指定槽有物品：強制堆疊（須同名）
        overflow = slot.item.add(item.quantity)
    else:                            ← 指定槽空著：直接放入
        clone = item.clone()
        items.append(clone)
        slot.set_item(clone)
    emit_signal("modified", self)
    return overflow                  ← 超出上限的數量
```

### 拖放系統（Slot 內部類）

```gdscript
class Slot extends Panel:
    # 開始拖曳：從物品欄移除道具，加入 dragging 記錄
    func _get_drag_data(_at_position):
        if item != null:
            var preview = ItemStack.new(); preview.layout(item)
            set_drag_preview(preview)
            inventory.erase_item(item, self)
            inventory.dragging = {'item': ret_item, 'slot': self, 'in_flight': true}
            return inventory.dragging

    # 接受條件：目標格空，或同名且不超量
    func _can_drop_data(_at, data):
        return item == null or (data.item.name == item.name and
            data.item.quantity + item.quantity <= data.item.max_quantity)

    # 放下：呼叫 add_item 完成轉移
    func _drop_data(_at, data):
        data.in_flight = false
        inventory.add_item(data.item, self)
        inventory.dragging = null
```

**放手未命中槽時的保護**（inventory.gd:36-44）：
```gdscript
func _input(event):
    if event is InputEventMouseButton and not event.is_pressed() and ...:
        call_deferred("give_back_dragged_item")

func give_back_dragged_item():
    if dragging != null and dragging.in_flight:
        inventory.add_item(dragging.item, dragging.slot)  # 歸還原槽
```

### ItemStack 顯示元件

```gdscript
class ItemStack extends TextureRect:
    func layout(item):
        set_texture(item.icon)
        if item.max_quantity > 1:
            label.set_text(str(item.quantity))
            item.set_label_color(label)    # 滿格紅色，未滿白色
```

---

## 快捷物品列（items_bar.gd）

```gdscript
# 循環瀏覽：active_item 索引 0 = null_item（空選）
func get_item(i: int) -> Item:
    if i % (inventory.items.size() + 1) == 0:
        return null_item
    return inventory.get_item(i 相對偏移)

func activate_next():
    active_item = wrapi(active_item + 1, 0, inventory.items.size() + 1)
    $sound.play()
    update()
```

顯示 5 個格子（active_item 為中心，左右各 2 個）：
```gdscript
func update():
    var i = -2
    for child in $bar.get_children():     # 5 個子節點
        var item = get_item(active_item + i)
        child.get_node("icon").set_texture(item.icon)
        i += 1
```

觸控支援：水平拖曳超過 50px 切換物品（適合手機）。

---

## 商店系統（shop.gd + shop-item.gd + NPC.gd）

### 商品價格計算

```gdscript
# shop-item.gd:31
item_cost = int((100 - new_item.rarity) * cost_factor)
```
- rarity 越高（越稀有）→ (100 - rarity) 越小 → 價格越低？
- 實際上 rarity 是「掉落機率比重」，高 rarity = 常見品 = 便宜
- cost_factor（NPC.gd 傳入 10）為倍率

### 購買流程

```
NPC.interact(player, _node):
    player.pause_player()
    camera.set_process_input(false)
    hud_inventory.open_inventories([shop, player.inventory])
    
    for shop_item in shop.shop_items:
        shop_item.buy.connect(player.buy_item)     ← 連接購買 signal
    
    await hud_inventory.popup_hide                 ← 等待關閉
    
    for shop_item in shop.shop_items:
        shop_item.buy.disconnect(player.buy_item)  ← 斷開連接

# player.buy_item(item, cost):
func buy_item(item: Item, cost: int) -> bool:
    if item.quantity > 0 and money >= cost:
        money -= cost
        add_item(item)
        return true
    return false
```

### NPC 行為（NPC.gd）

NPC 平時的隨機轉頭行為：
```gdscript
func _process(delta):
    if player != null:
        slerp_look_at(player.global_transform.origin, delta * 10)  # 面向玩家
    else:
        # 隨機選一個方向，Slerp 插值轉頭，轉完後隨機等待再換方向
        global_transform.basis = global_transform.basis.slerp(random_basis, 10 * delta)
        if remaining_rotation < 5°:
            stare_time += delta
            if stare_time > stare_wait:
                new_random_stare()
```

---

## 系統設計特點

| 特點 | 說明 |
|------|------|
| 道具是純資料物件 | Item 不繼承 Node，不加入場景樹，由 Inventory Panel 管理生命週期 |
| 堆疊機制 | 同名道具自動堆疊，`add()` 回傳溢出量，UI 用 label 顯示數量 |
| Template Method 消耗 | 基類 `use()` 固定流程，子類只實作 `effect()` |
| 拖放完整保護 | 拖到非法位置時 `give_back_dragged_item()` 歸還，避免道具消失 |
| 場景物件雙重性 | CannonBall 同時有「道具類」和「3D 場景節點類」，透過 `fire()` 橋接 |
