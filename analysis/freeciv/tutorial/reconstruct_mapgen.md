# 教學：從零復刻 Freeciv 地圖生成系統

本教學旨在指導如何從頭開始，用任何你熟悉的現代程式語言（如 Python, C#, C++, 或 Rust）復刻出類似 Freeciv 的高保真、具備物理邏輯（高度、溫度、河流）的策略遊戲地圖生成系統。

---

## 復刻計畫 (Reconstruction Plan)

要復刻這個系統，我們不能一開始就想著「畫地圖」，而是必須建立一層層的基礎設施。整個復刻計畫分為 **七個階段**：

*   **階段 1：基礎設施 (Infrastructure)** - 建立網格系統、拓樸學 (Wraparound) 與確定性隨機亂數產生器 (RNG)。
*   **階段 2：高度圖生成 (Heightmap)** - 實作核心的分形演算法 (Fractal / Midpoint Displacement) 來生成山脈與深海。
*   **階段 3：海平面與陸地劃分 (Landmass & Oceans)** - 實作動態海平面算法，決定陸地的分佈。
*   **階段 4：溫度圖生成 (Temperature Map)** - 結合緯度與高度，建立全球氣候模型。
*   **階段 5：地形映射 (Terrain Mapping)** - 結合高度與溫度，決定每個方格的具體地形（如叢林、沙漠、冰原）。
*   **階段 6：河流系統 (River Network)** - 實作基於重力與權重的隨機走訪 (Weighted Random Walk) 演算法。
*   **階段 7：資源與細節 (Resources & Polish)** - 實作基於地形機率與避讓機制的資源和聚落放置。

---

## 逐步實作 (Step-by-Step Pseudo-code)

### 階段 1：基礎設施 (Infrastructure)

首先，我們需要一個一維陣列來表示二維地圖，並實作一個能處理「地圖邊界繞回 (Wrapping)」的鄰居取得函數。

```python
class MapGrid:
    def __init__(self, width, height, wrap_x=True, wrap_y=False):
        self.width = width
        self.height = height
        self.wrap_x = wrap_x
        self.wrap_y = wrap_y
        self.size = width * height
        
        # 核心數據層
        self.height_map = [0] * self.size
        self.temp_map = [0] * self.size
        self.terrain_map = [None] * self.size
        
        # 確定性隨機數種子
        self.rng = DeterministicRNG(seed=12345)

    def get_index(self, x, y):
        # 處理拓樸繞回 (Wrapping)
        if self.wrap_x: x = x % self.width
        if self.wrap_y: y = y % self.height
        
        # 邊界檢查
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return None 
        return y * self.width + x

    def get_neighbors(self, x, y):
        # 回傳 8 個方向的合法鄰居
        dirs = [(-1,-1), (0,-1), (1,-1), (-1,0), (1,0), (-1,1), (0,1), (1,1)]
        neighbors = []
        for dx, dy in dirs:
            idx = self.get_index(x + dx, y + dy)
            if idx is not None: neighbors.append(idx)
        return neighbors
```

### 階段 2：高度圖生成 (Heightmap)

使用遞歸中點位移法（Diamond-Square 的變體）生成具備粗糙度的類大陸棚高度。

```python
def generate_heightmap(grid):
    step = grid.width + grid.height
    
    # 1. 初始化控制點 (例如 5x5 的網格點)
    for x in range(0, grid.width, grid.width // 5):
        for y in range(0, grid.height, grid.height // 5):
            idx = grid.get_index(x, y)
            h = grid.rng.random(-step, step)
            # 懲罰極地與邊緣，避免大陸碰到不可繞回的邊界
            if is_near_edge(x, y) and not grid.wrap_x: h -= step // 2
            if is_polar(y): h -= step // 3
            grid.height_map[idx] = h

    # 2. 遞歸分割
    def recursive_subdivide(x1, y1, x2, y2, current_step):
        if (x2 - x1 <= 1) and (y2 - y1 <= 1): return # 已經最小

        mid_x = (x1 + x2) // 2
        mid_y = (y1 + y2) // 2
        
        # 計算四邊中點高度 (取兩端平均 + 隨機偏移)
        set_height(mid_x, y1, avg(x1,y1, x2,y1) + grid.rng.random(-current_step, current_step))
        set_height(mid_x, y2, avg(x1,y2, x2,y2) + grid.rng.random(-current_step, current_step))
        set_height(x1, mid_y, avg(x1,y1, x1,y2) + grid.rng.random(-current_step, current_step))
        set_height(x2, mid_y, avg(x2,y1, x2,y2) + grid.rng.random(-current_step, current_step))
        
        # 計算中心點高度
        set_height(mid_x, mid_y, avg_4_corners(x1,y1, x2,y2) + grid.rng.random(-current_step, current_step))

        # 遞歸四個子區域，降低偏移幅度 (決定平滑度)
        next_step = current_step * 0.66
        recursive_subdivide(x1, y1, mid_x, mid_y, next_step)
        recursive_subdivide(mid_x, y1, x2, mid_y, next_step)
        recursive_subdivide(x1, mid_y, mid_x, y2, next_step)
        recursive_subdivide(mid_x, mid_y, x2, y2, next_step)

    # 啟動遞歸並正規化 (將值映射到 0~1000)
    recursive_subdivide(0, 0, grid.width-1, grid.height-1, step)
    normalize_array(grid.height_map, 0, 1000)
```

### 階段 3：海平面與陸地劃分 (Landmass & Oceans)

動態計算海平面，確保陸地面積符合預期設定（例如 30% 陸地）。

```python
def define_landmass(grid, land_percent=30):
    # 找到能讓 (100 - land_percent)% 的方格位於其下的高度值
    sorted_heights = sort(grid.height_map)
    shore_level_index = int(len(sorted_heights) * (100 - land_percent) / 100)
    shore_level = sorted_heights[shore_level_index]

    for i in range(grid.size):
        if grid.height_map[i] < shore_level:
            depth = shore_level - grid.height_map[i]
            grid.terrain_map[i] = "OCEAN_DEEP" if depth > 200 else "OCEAN_SHALLOW"
        else:
            grid.terrain_map[i] = "LAND_PLACEHOLDER"
            
    # 移除 1x1 的孤島以優化遊戲體驗
    remove_tiny_islands(grid)
```

### 階段 4：溫度圖生成 (Temperature Map)

建立具有物理邏輯的氣候系統。

```python
def generate_temperature(grid):
    # 赤道最熱 (y = height/2)，兩極最冷 (y = 0 或 height)
    equator = grid.height / 2
    max_lat = equator

    for i in range(grid.size):
        x, y = get_xy_from_index(grid, i)
        
        # 1. 緯度基礎溫度 (0 ~ 100)
        distance_to_equator = abs(y - equator)
        base_temp = 100 * (1.0 - (distance_to_equator / max_lat))
        
        # 2. 海拔降溫 (高山溫度低)
        if is_land(grid, i):
            height_above_sea = grid.height_map[i] - shore_level
            altitude_cooling = 0.3 * (height_above_sea / max_height) # 最多降 30%
            base_temp *= (1.0 - altitude_cooling)
            
        # 3. 海洋調節 (沿海氣候溫和)
        ocean_neighbors = count_ocean_neighbors(grid, x, y)
        if ocean_neighbors > 0:
            # 將極端溫度拉近至平均值
            temperate_factor = 0.15 * (ocean_neighbors / 8.0) 
            base_temp = lerp(base_temp, 50, temperate_factor)

        grid.temp_map[i] = base_temp

    # 離散化為氣候帶
    for i in range(grid.size):
        t = grid.temp_map[i]
        if t > 75: grid.temp_map[i] = "TROPICAL"
        elif t > 40: grid.temp_map[i] = "TEMPERATE"
        elif t > 15: grid.temp_map[i] = "COLD"
        else: grid.temp_map[i] = "FROZEN"
```

### 階段 5：地形映射 (Terrain Mapping)

結合高度與溫度決定具體地形。

```python
def map_terrains(grid):
    for i in range(grid.size):
        if not is_land(grid, i):
            # 處理極地結冰的海洋
            if grid.temp_map[i] == "FROZEN" and grid.rng.random(100) < 70:
                grid.terrain_map[i] = "ICE"
            continue

        h = grid.height_map[i]
        t = grid.temp_map[i]

        # 高度決定山脈/丘陵
        if h > 800:
            grid.terrain_map[i] = "MOUNTAIN"
        elif h > 600:
            grid.terrain_map[i] = "HILL"
        else:
            # 溫度與濕度 (可用另一個隨機圖或純隨機代替) 決定平地
            wetness = grid.rng.random(100)
            
            if t == "TROPICAL":
                grid.terrain_map[i] = "JUNGLE" if wetness > 50 else "DESERT"
            elif t == "TEMPERATE":
                grid.terrain_map[i] = "SWAMP" if wetness > 80 else ("GRASSLAND" if wetness > 40 else "PLAINS")
            elif t == "COLD":
                grid.terrain_map[i] = "TUNDRA"
            elif t == "FROZEN":
                grid.terrain_map[i] = "GLACIER"
```

### 階段 6：河流系統 (River Network)

模擬水流從高處往低處流，並受到海洋與現有河流的吸引。

```python
def generate_rivers(grid, target_river_count):
    rivers_created = 0
    while rivers_created < target_river_count:
        # 找一個高點當作源頭
        current_idx = find_random_mountain_or_hill(grid)
        if not current_idx: break
        
        path = []
        while True:
            path.append(current_idx)
            neighbors = grid.get_neighbors(get_x(current_idx), get_y(current_idx))
            
            best_next = None
            best_score = float('inf') # 越低越好
            
            for n in neighbors:
                if n in path: continue # 防止自交
                
                score = 0
                # 1. 傾向流向低處 (重力)
                score += (grid.height_map[n] - grid.height_map[current_idx]) * 10
                
                # 2. 傾向流向海洋或現有河流
                if is_ocean(grid, n): score -= 500
                if has_river(grid, n): score -= 200
                if grid.terrain_map[n] == "MOUNTAIN": score += 1000 # 避免爬山
                
                # 加上一點隨機性
                score += grid.rng.random(0, 20)
                
                if score < best_score:
                    best_score = score
                    best_next = n
            
            if not best_next or best_score > 500:
                break # 走投無路，結束這條河
                
            current_idx = best_next
            
            if is_ocean(grid, current_idx) or has_river(grid, current_idx):
                path.append(current_idx) # 匯流或入海
                break
                
        # 標記河流
        if len(path) > 2: # 太短的河不要
            for node in path:
                if is_land(grid, node):
                    mark_as_river(grid, node)
            rivers_created += 1
```

### 階段 7：資源與細節 (Resources & Polish)

最後放置戰略資源與玩家可探索的村落。

```python
def place_resources_and_huts(grid):
    # 放置資源
    for i in range(grid.size):
        if grid.rng.random(100) < 5: # 5% 的整體機率
            # 檢查周遭避免擁擠
            if not has_resource_nearby(grid, i, radius=1):
                terrain = grid.terrain_map[i]
                valid_resources = get_resources_for_terrain(terrain) # 查表
                if valid_resources:
                    grid.add_resource(i, grid.rng.choice(valid_resources))
                    
    # 放置村落 (使用泊松圓盤採樣概念)
    placed_huts = []
    target_huts = grid.size // 100
    
    while len(placed_huts) < target_huts:
        idx = grid.rng.random(0, grid.size - 1)
        if is_land(grid, idx):
            # 檢查半徑 3 格內是否已有村落
            too_close = False
            for hut in placed_huts:
                if distance(grid, idx, hut) <= 3:
                    too_close = True
                    break
            
            if not too_close:
                grid.add_feature(idx, "HUT")
                placed_huts.append(idx)
```

## 結語

按照上述 7 個階段，你可以利用任何語言建構出一個底層邏輯與 Freeciv 幾乎一致的地圖生成引擎。這個架構的優點在於**高度模組化**與**物理驅動**：如果你想要改變地圖風貌，只需要調整溫度公式或是分形演算法的初始網格大小，系統就會自動運算出合理的地形分佈與河流走向。
