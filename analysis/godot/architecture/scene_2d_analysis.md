# Scene 2D 渲染系統分析 - Level 2 & 3

## 1. 核心基底：CanvasItem (`scene/main/canvas_item.h`)
`CanvasItem` 是所有 2D 物件（包括 `Node2D` 與 `Control`）的基底類別。它直接與底層渲染引擎對接。

### 關鍵機制：
- **`RID canvas_item`**：在 `RenderingServer` 中對應的實體 ID。
- **渲染指令繪製**：
    - 透過虛擬函數 `_draw()` (或 `NOTIFICATION_DRAW`) 提交繪製指令。
    - 常用指令：`draw_texture()`, `draw_rect()`, `draw_line()`。
- **視覺屬性**：
    - **Modulate**：顏色調製（全域與自身）。
    - **Visibility**：控制可見性與繼承關係。
    - **Z-Index & Y-Sort**：控制 2D 渲染順序，`Y-Sort` 允許根據 Y 座標自動排序。
- **材質與著色器**：支援關聯 `Material` 並處理 `instance_shader_parameters`。

## 2. 空間變換：Node2D (`scene/2d/node_2d.h`)
`Node2D` 繼承自 `CanvasItem`，為 2D 物件增加了位置、旋轉與縮放等空間屬性。

### 關鍵特性：
- **`Transform2D`**：管理本地與全域的 2D 變換矩陣。
- **變換更新機制**：使用 `xform_dirty` 標記來延遲更新變換矩陣，優化效能。
- **輔助方法**：提供 `look_at()`, `to_local()`, `to_global()` 等空間計算工具。

## 3. 重要 2D 渲染節點
- **`Sprite2D`**：顯示靜態貼圖的核心節點，支援 Region 與 Atlas。
- **`AnimatedSprite2D`**：基於 `SpriteFrames` 的序列幀動畫。
- **`Polygon2D`**：繪製多邊形網格，常用於 2D 角色蒙皮或地形。
- **`Line2D`**：繪製具有厚度的線條。
- **`TileMapLayer` / `TileMap`**：高效的瓦片地圖渲染系統（Godot 4 的核心更新）。
- **`GPUParticles2D` / `CPUParticles2D`**：粒子系統。

## 4. 2D 渲染管線概覽
1. **變換更新**：`Node2D` 更新其 `Transform2D` 並通知 `RenderingServer`。
2. **指令提交**：當 `CanvasItem` 需要重繪時，呼叫 `NOTIFICATION_DRAW` 收集指令。
3. **後台渲染**：`RenderingServer` 接收 `RID` 與指令集，在渲染執行緒中執行具體的 GPU 繪製。

---
*檔案位置：`scene/main/canvas_item.h`, `scene/2d/node_2d.h`*
