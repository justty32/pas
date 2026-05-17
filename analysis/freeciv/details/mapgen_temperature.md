# Freeciv 地圖生成細節：溫度圖生成 (Temperature Map)

溫度圖決定了方格的氣候類型 (Frozen, Cold, Temperate, Tropical)，直接影響地形映射 (如沙漠 vs 叢林)。

## 核心機制：緯度基礎與環境修正

位於 `server/generator/temperature_map.c` 的 `create_tmap` 函數負責生成此數據。它有兩個模式：「虛擬 (Dummy)」模式與「真實 (Real)」模式。

### 邏輯流程
1.  **基礎溫度**: 以「緯度補角 (`map_colatitude`)」為基礎。赤道最高，兩極最低。
2.  **高度修正 (真實模式)**:
    *   海拔越高，溫度越低。
    *   公式：`高度修正 = -0.3 * (當前高度 - 海平面) / (最高度 - 海平面)`。
    *   這意味著高山即便在赤道也可能呈現 Cold 或 Frozen 狀態。
3.  **海洋調節 (真實模式)**:
    *   靠近海洋的地區溫度會趨向溫和 (調節約 15%)。
    *   這模擬了海洋的熱平衡效應，防止內陸地區過冷或過熱。
4.  **離散化**: 將連續的溫度值劃分為四個等級：
    *   `TT_FROZEN`: 極寒，生成冰原。
    *   `TT_COLD`: 寒冷，生成苔原。
    *   `TT_TEMPERATE`: 溫和，生成草原/平原。
    *   `TT_TROPICAL`: 炎熱，生成沙漠/叢林。

### 偽代碼 (Pseudo-code)

```python
def create_temperature_map(is_real_mode):
    t_map = array(size=MAP_SIZE)
    
    for tile in all_tiles:
        # 1. 緯度基礎 (0 = 北極, 90 = 赤道, 180 = 南極)
        base_temp = get_colatitude(tile)
        
        if not is_real_mode:
            t_map[tile] = base_temp
            continue
            
        # 2. 高度修正 (海拔越高越冷，最大降溫 30%)
        height_factor = calculate_height_cooling(tile)
        
        # 3. 海洋調節 (沿海地區溫度趨向平均)
        ocean_factor = calculate_ocean_buffering(tile)
        
        # 4. 綜合計算
        final_temp = base_temp * (1.0 + height_factor) * (1.0 + ocean_factor)
        t_map[tile] = final_temp

    # 5. 正規化並劃分等級
    normalize(t_map)
    for i in range(len(t_map)):
        t_map[i] = categorize_to_frozen_cold_temperate_tropical(t_map[i])
```

## 工程見解
- **雙階段設計**: 在地圖生成初期陸地尚未成型時，先用 Dummy 模式進行初步規劃；待高度圖與陸塊確定後，再運行 Real 模式進行精確的氣候模擬。
- **氣候一致性**: 透過緯度基礎，Freeciv 保證了地圖具有明顯的氣候帶特徵，這對策略遊戲的沉浸感至關重要。
- **地形聯動**: 溫度圖與後續的 `make_terrains` 緊密配合，例如在 `TT_TROPICAL` 且高濕度區域優先生成叢林。
