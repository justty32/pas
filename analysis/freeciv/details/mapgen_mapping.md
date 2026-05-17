# Freeciv 地圖生成細節：地形映射 (Terrain Mapping)

地形映射是將抽象的高度與溫度數據轉化為具體遊戲地形 (如草原、高山、海洋) 的過程。

## 核心機制：海平面計算與地形放置

主要的邏輯位於 `server/generator/mapgen.c` 的 `make_land` 與 `make_terrains`。

### 1. 海平面計算 (`make_land`)
系統根據設定的 `landpercent` (陸地百分比) 在高度圖中找到一個分界線 `hmap_shore_level`。
*   **公式**: `hmap_shore_level = hmap_max_level * (100 - landpercent) / 100`。
*   所有高度低於此線的為海洋，高於此線的暫定為陸地填充色。

### 2. 海洋深度與冰層
*   根據高度圖與海平面的差值決定海洋深度 (Shallow, Normal, Deep)。
*   結合溫度圖，在 `TT_FROZEN` 區域生成海冰。

### 3. 陸地細節化 (`make_terrains`)
這是一個多遍掃描 (Multi-pass) 的過程：
1.  **基礎地形**: 根據緯度、高度與濕度分配基本地形。
2.  **起伏修正 (`make_relief`)**: 在過於平坦的區域隨機加入丘陵或山脈。
3.  **特殊地形**: 放置沼澤、叢林、沙漠等受氣候限制的地形。

### 偽代碼 (Pseudo-code)

```python
def terrain_mapping():
    # 1. 決定海平面
    shore_level = (max_height * (100 - land_percent)) / 100
    
    # 2. 基礎海洋/陸地劃分
    for tile in all_tiles:
        if height_map[tile] < shore_level:
            depth = shore_level - height_map[tile]
            is_frozen = (temp_map[tile] == TT_FROZEN)
            tile.terrain = pick_ocean_by_depth(depth, is_frozen)
        else:
            tile.terrain = land_fill_terrain # 暫時填充
            
    # 3. 陸地精細化
    for tile in all_land_tiles:
        t = temp_map[tile]
        h = height_map[tile]
        
        if h > mountain_threshold:
            tile.terrain = MOUNTAIN
        elif h > hill_threshold:
            tile.terrain = HILL
        else:
            # 根據溫度與隨機濕度分配
            if t == TT_TROPICAL:
                tile.terrain = JUNGLE if rand() < wetness else DESERT
            elif t == TT_FROZEN:
                tile.terrain = ARCTIC
            # ... 其他邏輯
```

## 工程見解
- **動態海平面**: 這種實作方式比固定機率分佈更優秀，因為它能保證生成的陸地面積精確符合玩家設定。
- **孤島移除 (`remove_tiny_islands`)**: 映射完成後，系統會掃描並移除所有 $1 \times 1$ 的孤島，這通常是為了改善 AI 導航與遊戲節奏。
- **連通性保障**: 透過高度圖的連續性，生成的陸地通常會形成大陸塊而非破碎的點陣。
