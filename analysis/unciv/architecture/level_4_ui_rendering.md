# Level 4: UI 渲染與佈局深度分析 - Unciv

Unciv 的使用者介面完全基於 LibGDX 的 **Scene2D** 框架。它透過高度模組化與圖層化的方式，處理複雜的 4X 遊戲地圖與 HUD。

## 核心佈局架構 (`WorldScreen`)
`WorldScreen` 是遊戲的主畫面，它將 UI 劃分為多個獨立的 `Actor` 並加入到 `Stage` 中：

1.  **地圖層 (WorldMapHolder)**: 
    - 繼承自 `ZoomableScrollPane`。
    - 負責地圖的縮放 (Zooming)、平移 (Panning) 與慣性滾動。
    - 包含所有的六角格地圖塊。

2.  **HUD 與 控制層**:
    - **Top Bar**: 顯示全局資源（金錢、科學、文化）。
    - **Bottom Unit Table**: 顯示選中單位或城市的詳細資訊。
    - **Minimap**: 顯示縮圖，並提供快速跳轉功能。
    - **Notifications**: 事件通知列表。

## 地圖塊渲染邏輯 (`TileGroup`)
地圖是由無數個 `WorldTileGroup` 組成的。每個六角格並非單一貼圖，而是由 **11 個以上獨立圖層 (Layer)** 疊加而成：

| 圖層名稱 | 內容 |
| :--- | :--- |
| `TileLayerTerrain` | 地形底色（草地、平原、海洋）。 |
| `TileLayerFeatures` | 道路、河流、森林、雨林等地形特徵。 |
| `TileLayerBorders` | 領土邊界線。 |
| `TileLayerResource` | 戰略或奢侈資源圖標。 |
| `TileLayerImprovement` | 改善設施（農田、礦井、貿易站）。 |
| `TileLayerUnitArt` | 單位的主體圖像。 |
| `TileLayerUnitFlag` | 單位的血條 (HP) 與文明旗幟。 |
| `TileLayerOverlay` | 戰爭迷霧 (Fog of War)、選中高亮、滑鼠懸停效果。 |
| `TileLayerCityButton` | 城市名稱標籤與產出進度條。 |

### 渲染優化
- **圖層快取**: 每個圖層都有自己的 `update()` 邏輯，只有在狀態改變（如單位移動、迷霧消散）時才重新計算。
- **非變換組 (Non-Transforming Groups)**: 透過設定 `isTransform = false` 減少矩陣運算，提升渲染大量地圖塊時的 FPS。
- **視口裁剪 (Culling)**: `ScrollPane` 會自動處理不在畫面內的 Actors，避免無謂的渲染。

## 互動與動畫
- **動畫系統**: 使用 LibGDX 的 `Actions` API。單位移動時，會計算路徑並透過 `Actions.moveTo` 與 `Actions.fadeIn/Out` 實現平滑過渡。
- **輸入處理**: `WorldMapHolder` 使用 `ActorGestureListener` 處理點擊、長按與雙指縮放。點擊座標會轉換為地圖索引來識別 `Tile`。

## 總結
Unciv 的 UI 設計體現了「組合優於繼承」的原則。透過將每個六角格拆解為多個專業化圖層，它能夠在保持高效渲染的同時，支援極其複雜的視覺狀態組合（如：迷霧下的森林中有受損的友軍單位且該地塊正在被城市耕種）。

## 接下來的分析方向 (Level 5)
- 探索 AI 決策邏輯：研究 AI 如何評估地圖狀態並決定單位行動。
