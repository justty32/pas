# Pawn 渲染系統：圖層與渲染樹 (Rendering)

在 RimWorld 中，小人是一組多層圖像的動態疊加。

## 1. 渲染樹：`PawnRenderTree` (1.5 版本新特性)
小人的視覺結構被拆解為樹狀節點。
*   **Root**: 核心座標與基礎方向。
*   **BodyNode**: 繪製身體。
*   **HeadNode**: 繪製頭部。
*   **ApparelNode**: 繪製服飾（根據層次分佈在身體與頭部周圍）。

## 2. 旋轉與方向 (`Rot4`)
*   每個節點都有 4 個方向的 Texture。
*   `PawnRenderer` 會根據 `pawn.Rotation` 來決定繪製哪一組圖集。

## 3. 動畫與特效 (`PawnRenderNode_Animated`)
*   **Wiggler**: 處理小人倒地時的掙扎動畫。
*   **Flasher**: 當小人受傷時，紅色閃爍效果。
*   **Overlays**: 傷口、火燒、血跡等覆蓋層。

## 4. Mod 開發建議
*   **新增裝飾**: 透過 `PawnRenderNode` 插入自定義圖層（如：角、翅膀、機械眼）。
*   **修改顏色**: 透過 `Graphic.Color` 與 `Shader` 實現自定義著色。
*   **特殊渲染**: 攔截 `PawnRenderer.RenderPawnAt` 來實現完全自定義的視覺效果。

---
*由 Gemini CLI 分析 Verse.PawnRenderer 生成。*
