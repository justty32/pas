# 世界大地圖：分層地形貼圖構想

## 遊戲類型

文明類型戰略遊戲（Civilization-like）。
格子類型未定：Hex 或 Square。

---

## 核心問題：地形種類與貼圖複用

傳統做法：每種地形一張貼圖（沙漠、丘陵、森林各一）。
問題：組合爆炸。沙漠丘陵、沙漠丘陵有森林、草地丘陵有森林……每種組合都要出一張圖，維護困難。

**目標**：用分層組合取代一對一貼圖。

```
最終顯示 = 基底地形層 + 地形起伏層 + 生態圈/地物層
例：沙漠基底 + 丘陵 + 森林 → 沙漠丘陵上有稀疏灌木
```

---

## 3D 實現（簡單）

- **基底**：大 Mesh，貼地形 texture（根據高度/biome 混合著色）
- **地形起伏**：Heightmap 直接驅動 mesh displacement
- **地物（森林、城市、山脈）**：在格子中心放 3D instance（Mesh + decal 等）
- 可以用 decal 疊加，或 shader 混合，天然支援多層

## 2D 實現（複雜，待解決）

### 方向一：多 TileMapLayer 堆疊（Godot 4 原生支援）

```
TileMapLayer [地物層]    ← 森林/山峰 icon，稀疏
TileMapLayer [起伏層]    ← 丘陵/山地 紋路疊加（半透明）
TileMapLayer [基底層]    ← 基本地形 tile（海洋/草地/沙漠/...）
```

- 優點：完全利用 Godot 原生 TileMap，最簡單
- 缺點：多層 draw call；起伏層的 tile 需要設計成可與基底混合（alpha 通道要處理）

### 方向二：Shader 混合（單一 TileMapLayer）

- 每個 tile 儲存 (base_id, feature_id, hilliness) 三個值
- 自訂 CanvasItem shader，根據這三個值在 shader 內採樣不同 texture 並混合
- 優點：一個 draw call，混合效果更自然
- 缺點：需要自訂 shader，Godot TileMap 的 shader 整合較麻煩

### 方向三：執行期合併貼圖（ImageTexture 組合）

- 生成地圖時，對每種組合用 CPU/GPU 預先合成 texture，存入 atlas
- 實際渲染仍用普通 TileMapLayer
- 優點：渲染最簡單
- 缺點：組合種類多時記憶體暴增；動態地形（霧、季節）難以處理

---

## 初步評估

| 方向 | 實作難度 | 彈性 | 效能 | 適合時機 |
|------|---------|------|------|---------|
| 多 TileMapLayer | ★☆☆ | ★★☆ | ★★☆ | 快速 prototype |
| Shader 混合 | ★★★ | ★★★ | ★★★ | 正式製作 |
| 執行期合併 | ★★☆ | ★☆☆ | ★★☆ | 組合種類少時 |

**建議路徑**：先用多 TileMapLayer 做 prototype 驗證視覺效果，確認方向後再考慮換 shader。

---

## 與 mapcore_cpp_square 的關係

`mapcore_cpp_square` 輸出的 `Tile` struct 已有分層資料：

```cpp
struct Tile {
    uint16_t  terrain;     // 對應「基底地形層」
    Hilliness hilliness;   // 對應「地形起伏層」
    int32_t   feature_id;  // 對應「地物層」
    float     water_depth;
};
```

GDExtension 包裝層（`MapCoreMapData`）已有對應的查詢 API，可以直接驅動多層 TileMapLayer。

---

## 待決定

- [ ] Hex 或 Square（影響 TileSet 設計）
- [ ] 起伏層的視覺風格（等高線？陰影？pixel art 疊加？）
- [ ] 地物層是 TileMap tile 還是獨立 Node instance（城市、單位等需要互動的物件）

---

*記錄時間：2026-05-22*
