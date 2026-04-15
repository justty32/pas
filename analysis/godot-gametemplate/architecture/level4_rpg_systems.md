# Level 4 Analysis: 遊戲性與 RPG 系統

## 1. 深度傷害體系
專案的戰鬥邏輯高度模擬了傳統 RPG 的計算方式。

### 1.1 傷害數據結構 (DamageDataResource)
- **多重屬性**: 支援 `PHYSICAL`, `FIRE`, `ICE`, `POISON` 等 10 幾種屬性。
- **計算公式**: `Total = sum( Damage[i].value * multiplier - Resistance[i] )`。
- **攻擊世代 (Generation)**: 
    - 使用 `new_generation()` 複製一份傷害數據。
    - 透過 `hit_list` 紀錄已命中對象，避免穿透彈對同一目標重複扣血。

### 1.2 狀態效果 (Status Effects)
- 傷害數據中包含一個 `status_list`。
- 這些效果會在傷害結算時，透過 `_status.process()` 掛載到目標的 `resource_node` 上。

## 2. 物品與清單管理 (Item System)
物品系統採用了典型的「配置與實例」分離模式。

### 2.1 拾取物機制 (Pickups)
- **ItemPickup**: 負責處理世界中掉落物的物理碰撞與視覺。
- **ItemResource**: 儲存物品的 ID、名稱與圖標。
- **WeaponItemResource**: 繼承自 `ItemResource`，專門處理武器的拾取，包含對應的武器場景引用。

### 2.2 清單管理 (ItemCollectionResource)
- 這是玩家的「背包」。
- 支援將收集到的物品序列化為 `.tres` 或 JSON 格式，便於 `PersistentData` 進行存檔。

## 3. 數值平衡 (Stats Balancing)
透過 `ActorStatsResource`，開發者可以輕鬆地在編輯器中調整：
- 基礎跑速與加速度。
- 生命值上限與防禦屬性。
- 這種數據與邏輯分離的設計，讓非程序人員也能參與數值平衡。
