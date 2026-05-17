# Freeciv 地圖生成細節：資源與部落放置 (Resources & Huts)

資源與部落是地圖生成的最後修飾階段，決定了玩家初期的經濟與探索收益。

## 1. 資源放置 (`add_resources`)

### 邏輯流程
1.  **密度控制**: 根據伺服器設定 `riches` (0-1000) 決定每個方格生成資源的基礎機率。
2.  **地形匹配**: 每種地形有其專屬的資源池 (如：草原對應馬、煤炭；海洋對應魚、鯨魚)。
3.  **鄰近性檢查 (`is_resource_close`)**: 為了防止資源過於密集，系統會檢查周遭 1 格範圍內是否已有資源。
4.  **安全性檢查**: 對於海洋資源，除非設定了 `ocean_resources`，否則通常只在靠近陸地的安全海域生成。

## 2. 部落小屋放置 (`make_huts`)

### 邏輯流程
1.  **分佈演算法**: 
    *   使用 `placed_map` (一個標記圖) 來記錄已放置小屋的影響範圍。
    *   隨機挑選位置，檢查是否為陸地且不靠近其他小屋 (`set_placed_near_pos(ptile, 3)`)。
2.  **隨機探索獎勵**: 小屋本身在生成時只是地圖上的「額外物品 (Extras)」，其內容 (技術、金錢、單位) 是在玩家進入時由伺服器動態隨機生成的。

### 偽代碼 (Pseudo-code)

```python
def place_resources(riches_prob):
    for tile in all_tiles:
        # 1. 機率檢查
        if rand(1000) >= riches_prob: continue
        
        # 2. 防擁擠檢查 (周邊不能已有資源)
        if is_resource_close(tile): continue
        
        # 3. 根據地形挑選資源
        resource = pick_resource_from_ruleset(tile.terrain)
        if resource:
            tile.resource = resource

def place_huts(count):
    placed_mask = bit_map(MAP_SIZE)
    while count > 0:
        tile = get_random_land_tile()
        # 3格範圍內不能有其他小屋
        if not is_near_marked(tile, placed_mask, radius=3):
            tile.add_extra(HUT)
            mark_area(tile, placed_mask, radius=3)
            count -= 1
```

## 工程見解
- **規則集驅動**: 資源的放置邏輯高度依賴 `terrain.ruleset` 中的定義，這使得 Freeciv 具有極強的擴展性。
- **平衡性**: 雖然資源放置是隨機的，但「鄰近性檢查」保證了資源在空間上的均勻分佈，避免出現資源貧瘠或過度富裕的極端區域。
- **延遲結算**: 部落的獎勵內容直到觸發時才決定，這不僅節省了初始生成的數據量，也為反作弊提供了一定保障。
