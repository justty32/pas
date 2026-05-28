# godot_world_map — 進度保存

> 最後更新：2026-05-28。從 `CONCEPT.md` 落地的 2D 分層 TileMapLayer 方案。

## 一句話：這是什麼

CONCEPT.md「方向一（多 TileMapLayer 堆疊）」的落地：基底 / 起伏 / 地物三層 TileMapLayer +
河流自繪 overlay。吃 `MapCoreMapData` 一鍵渲染。

## 真相校準

- 主線已轉向 3D（見 `godot_lowpoly` 2026-05-22 決策），這份的優先級偏低。
- mapcore_godot 端已有 **C++ `MapCoreWorldMap2DRenderer`**（出 RGB8 Image，含河流）
  與 **demo `map_renderer.gd`**（單層 TileMapLayer，純色 tile）。兩者都能跑、已 commit。
- 本檔不取代以上兩者，補的是 CONCEPT 強調的「**分層**」這條方向：
  Image 渲染器 = 截圖式靜態地圖；單層 TileMapLayer = 平面色塊；分層 TileMapLayer = 視覺有層次。

## 檔案清單

```
godot_world_map/
├── gd/
│   ├── world_map_2d.gd          # WorldMap2D 三層 TileMapLayer + 河流 overlay 控制器
│   └── tile_atlas_layout.gd     # 三層各自的 atlas 對映（terrain/hilliness/feature）
└── progress.md
```

## 整體狀態

| 區塊 | 內容 | 狀態 |
|------|------|------|
| 三層 TileMapLayer 渲染 | base + hill + feature 三層獨立 clear/set | ✅ 完成 |
| atlas 對映集中管理 | 11 terrain + 4 hilliness 等級 + 3 地物 icon | ✅ 完成 |
| 河流 draw_rivers_into | 強度過濾 + 分級寬度（mapcore strength 對映） | ✅ 完成 |
| TileSet 美術資源 | 11+4+3 個 atlas 格子的純色 / 紋路 / icon | ❌ 未做（美術側） |
| 真機驗證 | 在有 mapcore .so 的 Godot 4 專案掛三層 TileMapLayer 跑 | ⏸ **待真機驗證** |

## 設計重點

### 1. 三層 TileMapLayer 對應 CONCEPT 的分層哲學
```
FeatureLayer  ← 森林/山脈 icon（稀疏）
HillLayer     ← hilliness ≥ 2 才疊的半透明紋路 tile
BaseLayer     ← terrain 11 種純色基底（與 mapcore demo MapRenderer 一致）
```

層越高越稀疏。BaseLayer 鋪滿，HillLayer 平地（hilliness 0/1）跳過，
FeatureLayer 只在 FOREST/HILL/MOUNTAIN 放 icon。

### 2. atlas 對映抽出成 `TileAtlasLayout` const Dictionary
美術換圖時只動這支：
- 改 BASE_LAYER 第 0 行的對映 → 換基底地形色
- 改 HILLINESS_LAYER → 換起伏紋路
- 改 FEATURE_LAYER → 換 icon

不必動到 `world_map_2d.gd` 的渲染邏輯。

### 3. 河流走獨立 Node2D + _draw
TileMapLayer 不適合畫對角／斜線（tile 是離散格）。`river_overlay: Node2D` 自己寫
`_draw()` 並呼叫 `WorldMap2D.draw_rivers_into(self)`，這支處理：
- strength < `river_min_strength`（預設 80，對齊 mapcore CREEK_THRESHOLD）的細流跳過
- strength 80/160/240 三段對映線寬 1/2/3 px
- (cell, dir) → 像素端點換算（dir 對映 mapcore E/N/W/S 慣例）

### 4. 為何不寫進階方案（Texture2DArray + shader 混合）
CONCEPT.md「方向二」是 shader 混合單一 TileMapLayer，效能與彈性最高但實作最複雜。
**主線已轉 3D**，2D 不做量產級優化，先卡在「方向一」夠用、能跑、能視覺驗證即可。
真要做時再開新分支。

## 場景接線範例

外部需要這樣的場景結構（TileSet 自製，三層共用 source_id=0）：

```
WorldMap2D (Node2D，掛 world_map_2d.gd)
├── BaseLayer    (TileMapLayer)  ← @export base_layer 綁這
├── HillLayer    (TileMapLayer)  ← @export hill_layer 綁這
├── FeatureLayer (TileMapLayer)  ← @export feature_layer 綁這
└── RiverOverlay (Node2D，自寫 _draw)  ← @export river_overlay 綁這
```

`RiverOverlay` 的腳本最短：

```gdscript
extends Node2D
@onready var world_map: WorldMap2D = get_parent()
func _draw() -> void:
	world_map.draw_rivers_into(self)
```

主流程：

```gdscript
var data: MapCoreMapData = generator.generate()
$WorldMap2D.mount(data)
```

## 待決事項（從 CONCEPT.md 帶過來）

- [ ] **Hex 或 Square**：本檔走 Square（與 mapcore_godot 一致）。Hex 要等 mapcore 端切換。
- [ ] **起伏層視覺風格**：等高線 / 陰影 / pixel art 疊加 —— atlas 第 1 行四格美術自決。
- [x] **地物層是 TileMap tile 還是獨立 Node**：本檔走 TileMap tile。城市等需互動的物件
      仍建議獨立 Node 系統（不入這三層）。
- [ ] **Texture2DArray + shader 混合方案**：標為「主線轉 3D 後不投入」，等真要做再開分支。
- [ ] **TileSet 美術資源**：純色測試 tile（11 + 4 + 3 共 18 格）連動 mapcore 顏色，需要產一張
      測試 PNG 或交給美術。

## 與 mapcore_godot 的關係

| 模組 | 角色 |
|------|------|
| C++ `MapCoreWorldMap2DRenderer` | 出整張 RGB8 Image（含河流），minimap 與截圖式快速渲染用 |
| demo `map_renderer.gd` | 單層 TileMapLayer 純色 tile，最小可運行 |
| **本檔 `WorldMap2D`** | 三層 TileMapLayer + 河流 overlay，視覺分層版 |

三者並存，依需求挑：要 minimap 用第一個、要快速 prototype 用第二個、要視覺層次用本檔。

## 下一步（按需）

1. **TileSet 美術資源**：先 18 格純色測試 PNG 跑一次（HillLayer 用半透明白點紋路、
   FeatureLayer 用 icon 形狀），把節點結構接通。
2. **真機驗證**：mount() 後三層應呈現由下到上正確覆蓋；河流 overlay 線寬分級可見。
3. **與 Camera2D 整合**：之後做 `godot_camera_rig` 2D 版時把三層 + overlay 一起包進 Camera 子樹。
