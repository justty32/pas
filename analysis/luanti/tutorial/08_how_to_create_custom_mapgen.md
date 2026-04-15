# 開發教學 8：如何修改與創建自定義地形生成器 (Mapgen)

## 目標
本教學將引導你如何修改現有的 `MapgenV7` 參數，以及如何在 C++ 層面定義一個全新的地形生成邏輯。

## 1. 前置知識
- 了解 C++ 基礎與 CMake 構建流程。
- 了解 Perlin 噪聲的基本概念（頻率、振幅、八度音 Octaves）。
- 了解 `VoxelManipulator` 是如何操作地圖數據的。

## 2. 原始碼導航 (核心參考)
- **核心邏輯**：`src/mapgen/mapgen_v7.cpp` (行號 400, `baseTerrainLevelAtPoint`)。
- **配置參數**：`src/defaultsettings.cpp` (搜尋 `mgv7_np_terrain_base`)。
- **基底類別**：`src/mapgen/mapgen.h`。

## 3. 實作步驟

### 方法 A：修改現有生成器 (快速調整)
如果你只想改變地形的高度或起伏，不需要修改代碼，只需在 `minetest.conf` 中調整噪聲參數：
```ini
# 修改 V7 基礎地形高度
# 格式：offset, scale, (spread_x, spread_y, spread_z), seed, octaves, persistence, lacunarity
mgv7_np_terrain_base = -4, 70, (600, 600, 600), 82341, 5, 0.6, 2.0
```
- **scale**: 數值越大，山越高。
- **spread**: 數值越大，地貌越開闊平緩。

### 方法 B：在 C++ 中創建全新的生成邏輯
假設你要實作一個簡單的「垂直條紋」地形：

1. **開啟 `src/mapgen/mapgen_v7.cpp`**。
2. **尋找 `generateTerrain()` 函數 (約 480 行)**。
3. **修改填充邏輯**：
```cpp
// 在 for 迴圈遍歷 y 座標的內部
for (s16 y = node_min.Y - 1; y <= node_max.Y + 1; y++) {
    // 範例：每 10 格產生一個垂直石柱
    bool is_pillar = (x % 10 == 0) && (z % 10 == 0);
    
    if (y <= surface_y || is_pillar) {
        vm->m_data[vi] = n_stone; // 放置石頭
    } else if (y <= water_level) {
        vm->m_data[vi] = n_water; // 放置水
    } else {
        vm->m_data[vi] = n_air;   // 放置空氣
    }
}
```

### 方法 C：註冊一個全新的 Mapgen 類別
若要建立完全獨立的 `MapgenCustom`：
1. **繼承 `Mapgen` 基底類別**。
2. **實作 `makeChunk(BlockMakeData *data)`**。
3. **在 `src/mapgen/mapgen.cpp` 的 `Mapgen::createMapgen` 中註冊你的新類型**：
```cpp
if (mgname == "custom")
    return new MapgenCustom(params, emerge);
```

## 4. 驗證方式
1. **編譯專案**：使用 `cmake --build .` 重新編譯引擎。
2. **啟動並測試**：
    - 在建立世界時選擇對應的生成器（如果是修改 V7 則直接選擇 v7）。
    - 進入遊戲後使用飛模式 (`K`) 觀察地形是否符合預期。
3. **檢查日誌**：查看控制台是否有噪聲計算錯誤或記憶體溢出的警告。
