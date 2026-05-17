# Freeciv 地圖生成細節：高度圖生成 (Heightmap Generation)

高度圖是 Freeciv 生成類地球地形的核心。它決定了大陸的輪廓、山脈的走向以及平原的分佈。

## 核心演算法：偽分形遞歸分割 (Pseudo-fractal Recursive Division)

位於 `server/generator/height_map.c` 的 `make_pseudofractal1_hmap` 函數實作了此機制。它並非傳統的 Midpoint Displacement，而是針對地圖包裹性優化的變體。

### 邏輯流程
1.  **初始網格化**: 將地圖劃分為 $5 \times 5$ (加上 `extra_div`) 的大區塊。
2.  **種子賦值**: 為網格的頂點賦予隨機高度，並對極地與邊緣進行「懲罰」(降低高度) 以避免大陸堵塞邊界。
3.  **遞歸分割 (`gen5rec`)**:
    *   計算矩形四個角落的平均高度。
    *   計算四條邊的中點高度 = 兩端平均值 + 隨機偏移 ($\text{step}$)。
    *   計算矩形中心高度 = 四個角落平均值 + 隨機偏移。
    *   將矩形分割為四個子矩形，將偏移範圍 $\text{step}$ 乘以 $2/3$ (粗糙度因子)，然後遞歸。
4.  **後處理**:
    *   加入隨機噪音 (Fuzz)。
    *   使用 `adjust_int_map` 將所有高度正規化至 $0 \sim 1000$。

### 偽代碼 (Pseudo-code)

```python
def make_heightmap():
    # 1. 初始化
    height_map = array(size=MAP_SIZE, fill=0)
    step = MAP_WIDTH + MAP_HEIGHT
    
    # 2. 設置初始網格頂點
    for x in range(0, grid_x):
        for y in range(0, grid_y):
            tile = get_tile(x * block_w, y * block_h)
            h = rand(-step, step)
            # 懲罰邊緣與極地
            if is_near_edge(tile): h -= avoid_edge_penalty
            if is_polar(tile): h -= flat_poles_penalty
            height_map[tile] = h

    # 3. 遞歸细分
    for block in all_initial_blocks:
        recursive_subdivide(block, step)

    # 4. 正規化與噪音
    apply_noise(height_map)
    normalize(height_map, 0, 1000)

def recursive_subdivide(rect, step):
    if rect.is_too_small(): return

    # 計算中點 (插值 + 隨機位移)
    mid_top = avg(rect.top_left, rect.top_right) + rand_jitter(step)
    mid_left = avg(rect.top_left, rect.bottom_left) + rand_jitter(step)
    # ... 其他邊的中點與中心點
    
    # 遞歸處理四個子區域，降低隨機位移幅度 (決定地形平滑度)
    new_step = step * 0.66
    recursive_subdivide(sub_rect_tl, new_step)
    recursive_subdivide(sub_rect_tr, new_step)
    # ...
```

## 工程見解
- **包裹性處理 (Wrapping)**: 在計算頂點高度時，系統會檢查 `WRAP_X` 與 `WRAP_Y` 標記，確保地圖在左右或上下連接處的高度是連續的。
- **極地扁平化 (`flatpoles`)**: 透過 `server.flatpoles` 設定，可以強制降低兩極的高度，從而生成被海洋包圍的極地，而非延伸到邊緣的大陸。
- **高度圖範圍**: $0$ 代表最低點 (深海)，$1000$ 代表最高點 (高山)。海平面由 `landpercent` 設定動態決定。
