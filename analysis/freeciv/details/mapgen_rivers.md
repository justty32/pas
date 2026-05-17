# Freeciv 地圖生成細節：河流生成 (River Generation)

Freeciv 的河流生成並非簡單的隨機線條，而是一個模擬物理流向的啟發式搜索演算法。

## 核心演算法：權重引導的隨機走訪 (Weighted Random Walk)

位於 `server/generator/mapgen.c` 的 `make_river` 函數。

### 邏輯流程
1.  **尋找水源 (Spring)**: 隨機在非極地、非海洋的高海拔地區尋找河流起點。
2.  **方向評估**: 對當前位置的四個基數方向 (Cardinal Directions) 進行多項測試，計算「不適合度 (Comparison Value)」：
    *   **防止自交**: 走過的路徑會被標記，禁止回流。
    *   **高度優先**: 優先流向高度較低的方格 (模擬重力)。
    *   **海洋吸引**: 越靠近海洋，權重越高。
    *   **濕度/沼澤吸引**: 優先流向沼澤或現有河流 (模擬匯流)。
3.  **致命性檢查**: 如果某個方向會導致河流「流向高山」且無其他選擇，則該路徑可能被判定為無效。
4.  **隨機選擇**: 在所有得分最高 (不適合度最低) 的有效方向中隨機挑選一個前進。
5.  **終點判定**: 河流流向海洋、現有河流或極地時結束。

### 偽代碼 (Pseudo-code)

```python
def generate_rivers(target_length):
    current_length = 0
    while current_length < target_length:
        start_tile = find_mountain_spring()
        if not start_tile: break
        
        path = trace_river(start_tile)
        if path.is_valid():
            apply_to_map(path)
            current_length += len(path)

def trace_river(current_tile):
    river_path = [current_tile]
    while True:
        candidates = get_cardinal_neighbors(current_tile)
        scores = {}
        
        for next_tile in candidates:
            # 計算權重 (越低越好)
            score = 0
            score += (height_map[next_tile] - height_map[current_tile]) * 10
            if is_near_ocean(next_tile): score -= 50
            if is_swamp(next_tile): score -= 30
            if is_already_river(next_tile): score -= 100
            
            # 檢查非法狀態 (如流向自己)
            if is_blocked(next_tile): score = INFINITY
            scores[next_tile] = score
            
        best_tiles = find_min_score_tiles(scores)
        if not best_tiles: return FAILURE
        
        next_step = random_choice(best_tiles)
        river_path.append(next_step)
        
        if is_terminal(next_step): return SUCCESS
```

## 工程見解
- **拓樸引導**: 河流生成高度依賴高度圖。這保證了河流通常是從山脈流向海洋，增加了地圖的真實感。
- **地形聯動**: 如果河流流經的方格原本不支援河流 (如沙漠)，系統會將其地形修改為支援河流的類型 (如草原)，這保證了規則的一致性。
- **密度控制**: `desirable_riverlength` 公式考慮了地圖大小與 `river_pct` 設定，確保不同規模的地圖河流密度一致。
