# 教學：如何添加元素機制與物理現象

COGITO 的 `CogitoProperties` 組件內建了火 (Flammable)、水 (Wet)、電 (Conductive) 三種基礎元素屬性。本教學將引導您如何擴充此系統，加入新的元素（如：冰凍）以及複雜的化學反應。

## 前置知識
- 已閱讀 [Level 4A: CogitoProperties 物質反應系統](../architecture/level4_properties_system.md)。

## 實作步驟

### 1. 擴充元素枚舉 (Enum)
打開 `addons/cogito/Components/Properties/cogito_properties.gd`。
找到 `ElementalProperties` 枚舉並加入新的位元旗標：
```gdscript
enum ElementalProperties {
    CONDUCTIVE = 1,
    FLAMMABLE = 2,
    WET = 4,
    COLD = 8,  # 新增：寒冷/結冰屬性
    ACID = 16  # 新增：酸性腐蝕屬性
}
```
*注意：在 Inspector 中，您需要同時更新 `@export_flags` 的字串陣列才能在編輯器中勾選。*

### 2. 定義新狀態變數
在 `cogito_properties.gd` 中新增狀態追蹤變數與信號：
```gdscript
signal has_frozen()
var is_frozen : bool = false
@export var spawn_on_frozen : PackedScene # 結冰特效
```

### 3. 編寫反應邏輯 (Reaction Matrix)
COGITO 使用 `check_for_systemic_reactions()` 來處理碰撞時的元素交互。在此函數中加入新的判斷分支：
```gdscript
func check_for_systemic_reactions():
    for body in reaction_bodies:
        if !body.cogito_properties: continue
        
        # 範例：水 + 寒冷 = 結冰
        if (elemental_properties & ElementalProperties.WET) and body.cogito_properties.is_emitting_cold:
            if !is_frozen:
                make_frozen()
```

### 4. 實作狀態轉變方法
```gdscript
func make_frozen():
    is_frozen = true
    has_frozen.emit()
    # 移除水屬性，加入冰屬性
    elemental_properties &= ~ElementalProperties.WET
    elemental_properties |= ElementalProperties.COLD
    
    if spawn_on_frozen:
        var vfx = spawn_on_frozen.instantiate()
        add_child(vfx)
    
    # 若掛載在 NPC 上，可透過信號將其速度歸零或暫停動畫
```

## 驗證方式
1. 建立一個帶有 `WET` 屬性的木箱 (`CogitoProperties`)。
2. 建立一個帶有 `COLD` 屬性的投射物（修改自 `CogitoProjectile`）。
3. 發射投射物擊中木箱，觀察木箱是否觸發 `spawn_on_frozen` 特效並改變屬性。
