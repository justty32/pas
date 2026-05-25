# 教學：商店與貨幣系統（Shop & Merchant System）

本教學說明如何在 COGITO 中建立 NPC 商店：玩家用金幣購買道具、賣出背包物品，並與對話系統整合。

## 前置知識
- 已閱讀 [教學：任務系統工作流程](./quest_creation_workflow.md)（`QuestBridge` Autoload 建立方式可類比）。
- 已取消注解 `DialogicInteraction.gd`。

---

## 一、CogitoCurrency：玩家貨幣設定

`CogitoCurrency`（`cogito_currency.gd`）是掛在 `CogitoPlayer` 下的 Node，類似 `CogitoAttribute`。

### 加入金幣節點

在 `CogitoPlayer` 的子節點加入：
```
CogitoPlayer
└── GoldCurrency (Node + cogito_currency.gd)
    ├── currency_name: "gold"           ← 程式邏輯用（全小寫）
    ├── currency_display_name: "金幣"
    ├── currency_color: Color(1.0, 0.8, 0.0)
    ├── value_start: 100                ← 初始金幣
    └── value_max: 99999
```

`cogito_player.gd:250` 在 `_ready()` 中自動掃描所有 `CogitoCurrency` 子節點：
```gdscript
for currency in find_children("", "CogitoCurrency", false):
    player_currencies[currency.currency_name] = currency
```

之後即可用：
```gdscript
player.increase_currency("gold", 50.0)   # cogito_player.gd:306
player.decrease_currency("gold", 30.0)   # cogito_player.gd:316
player.player_currencies["gold"].value_current  # 直接讀取
```

---

## 二、ItemValue：為物品定義售價

`ItemValue`（`ItemValue.gd`）是一個 Resource，記錄物品對應哪種貨幣及其價值：

```gdscript
# ItemValue 欄位
currency_name: "gold"    # 對應 CogitoCurrency.currency_name
currency_value: 25.0     # 售價
```

在 `InventoryItemPD` 本身並沒有內建 `item_value` 欄位，需要在自訂物品資源中加入，或統一由 `ShopData` 資源管理（見下方）。

---

## 三、ShopData：商店庫存資源

建立 `res://scripts/shop_data.gd`：

```gdscript
# res://scripts/shop_data.gd
extends Resource
class_name ShopData

## 商店名稱
@export var shop_name: String = "村莊商店"

## 商品列表，每個 ShopEntry 定義一個商品
@export var stock: Array[ShopEntry] = []


# --- ShopEntry 內部類別 ---
class ShopEntry:
    extends Resource
    
    ## 商品的物品資源（InventoryItemPD 子類）
    @export var item: InventoryItemPD
    ## 每次只能購買的數量
    @export var quantity: int = 1
    ## 購買價格（金幣）
    @export var buy_price: float = 10.0
    ## 玩家賣給商店的回收價格（通常 < buy_price）
    @export var sell_price: float = 5.0
    ## 庫存數量（-1 = 無限）
    @export var stock_count: int = -1
```

在 Editor 中建立 `shop_blacksmith.tres` 並填入商品。

---

## 四、ShopComponent：掛在 NPC 上的交易組件

建立 `res://scripts/shop_component.gd`，掛在商人 NPC 的子節點：

```gdscript
# res://scripts/shop_component.gd
extends Node
class_name ShopComponent

@export var shop_data: ShopData

## 購買指定索引的商品
## 回傳 true=成功，false=金幣不足或庫存為 0
func try_buy(entry_index: int) -> bool:
    if entry_index >= shop_data.stock.size():
        return false

    var entry: ShopData.ShopEntry = shop_data.stock[entry_index]
    var player = CogitoSceneManager._current_player_node

    if not player:
        return false

    # 庫存檢查
    if entry.stock_count == 0:
        return false

    # 金幣檢查
    var gold = player.player_currencies.get("gold")
    if not gold or gold.value_current < entry.buy_price:
        # 通知玩家金幣不足
        player.player_interaction_component.send_hint(null, "金幣不足！")
        return false

    # 扣款
    player.decrease_currency("gold", entry.buy_price)

    # 給予物品（建立 InventorySlotPD 並放入背包）
    var slot_data = InventorySlotPD.new()
    slot_data.inventory_item = entry.item
    slot_data.quantity = entry.quantity
    player.inventory_data.pick_up_slot_data(slot_data)

    # 更新庫存
    if entry.stock_count > 0:
        entry.stock_count -= 1

    player.player_interaction_component.send_hint(
        entry.item.icon,
        "購買了 " + entry.item.name
    )
    return true


## 玩家賣出物品
## item_slot: 玩家背包中的 InventorySlotPD
## 回傳實際獲得金幣數
func try_sell(item_slot: InventorySlotPD) -> float:
    var player = CogitoSceneManager._current_player_node
    if not player or not item_slot:
        return 0.0

    # 找此物品在商店的回收價
    var sell_value := 0.0
    for entry in shop_data.stock:
        if entry.item.resource_path == item_slot.inventory_item.resource_path:
            sell_value = entry.sell_price
            break

    # 若商店沒有此物品，用物品本身的固定回收價（若有設定）
    if sell_value == 0.0:
        sell_value = 5.0  # 預設回收價

    # 移除背包物品
    player.inventory_data.remove_slot_data(item_slot)

    # 給予金幣
    player.increase_currency("gold", sell_value)

    player.player_interaction_component.send_hint(
        null,
        "賣出 " + item_slot.inventory_item.name + "，獲得 " + str(sell_value) + " 金幣"
    )
    return sell_value


## 取得目前玩家金幣量
func get_player_gold() -> float:
    var player = CogitoSceneManager._current_player_node
    if not player:
        return 0.0
    var gold = player.player_currencies.get("gold")
    return gold.value_current if gold else 0.0
```

---

## 五、節點結構（商人 NPC）

```
CogitoNPC (blacksmith)
├── NPC_State_Machine
├── HitboxComponent
├── ShopComponent
│   └── Inspector: shop_data = [shop_blacksmith.tres]
└── DialogicInteraction
    └── Inspector: dialogic_timeline = [shop_blacksmith.dtl]
```

---

## 六、Dialogic 商店對話

### 商店介面（使用 Variable + Choice）

`shop_blacksmith.dtl`：

```
Smith: 歡迎光臨！你需要什麼？

[choice]
  + [查看商品] → show_stock
  + [賣出物品] → sell_mode
  + [離開] → exit
[/choice]

[label show_stock]
Smith: 這是今天的商品：

[choice]
  + [鐵劍 (25金)] → buy_sword
  + [治療藥水 (15金)] → buy_potion
  + [返回] → back_to_main
[/choice]

[label buy_sword]
[call node="ShopBridge" method="buy_from_shop" args=["blacksmith", 0]]
Smith: {ShopBridge.last_result}
→ [label back_to_main]

[label exit]
Smith: 再見！
```

### ShopBridge Autoload

Dialogic 的 `[call]` 只能呼叫場景中的節點，需要一個橋接 Autoload：

```gdscript
# res://scripts/shop_bridge.gd (Autoload: ShopBridge)
extends Node

## 已知商店的 NPC 節點名稱 → ShopComponent 快取
var _shops: Dictionary = {}
var last_result: String = ""


func register_shop(shop_id: String, shop_component: ShopComponent) -> void:
    _shops[shop_id] = shop_component


func buy_from_shop(shop_id: String, entry_index: int) -> void:
    var shop = _shops.get(shop_id)
    if not shop:
        last_result = "商店不存在"
        return
    var success = shop.try_buy(entry_index)
    last_result = "購買成功！" if success else "購買失敗（金幣不足或無庫存）"
```

在商人 NPC 的 `_ready()` 中：
```gdscript
# blacksmith_npc.gd
func _ready() -> void:
    super._ready()
    var shop_comp = find_child("ShopComponent", true, false)
    if shop_comp:
        ShopBridge.register_shop("blacksmith", shop_comp)
```

---

## 七、簡化版：無對話的直接互動商店

若不想用 Dialogic，可改用 `BasicInteraction`：

```gdscript
# simple_shop_interaction.gd extends InteractionComponent
extends InteractionComponent

@export var shop_component: ShopComponent
@export var entry_index: int = 0  # 要購買的商品索引


func interact(_player_interaction_component: PlayerInteractionComponent) -> void:
    if shop_component:
        shop_component.try_buy(entry_index)
```

掛在物件（如貨架上的道具）上，玩家靠近按 E 直接購買該商品，不需要對話流程。

---

## 八、貨幣 HUD 顯示

`CogitoCurrency` 有 `currency_changed` 信號，可連接到 HUD 顯示金幣數：

```gdscript
# 在 player_hud_manager.gd 的 setup_player_hud() 中
func _setup_currency_display() -> void:
    var gold = CogitoSceneManager._current_player_node.player_currencies.get("gold")
    if gold:
        gold.currency_changed.connect(_on_gold_changed)
        _gold_label.text = str(int(gold.value_current)) + " G"


func _on_gold_changed(name: String, current: float, max: float, _increased: bool) -> void:
    _gold_label.text = str(int(current)) + " G"
```

---

## 九、驗證清單

| 測試步驟 | 預期結果 |
|---|---|
| 與商人對話選購劍 | 金幣減少 25；鐵劍出現在背包 |
| 金幣不足時購買 | HUD 顯示「金幣不足！」|
| 賣出背包物品 | 物品消失；金幣增加對應回收價 |
| 限量商品購買後 | 再次嘗試購買：庫存 0，購買失敗 |
| 存讀檔後 | 金幣數量保持（CogitoCurrency 由 CSM 自動存讀）|
