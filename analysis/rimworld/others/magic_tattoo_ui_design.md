# 魔紋 Mod (Magic Tattoo) UI 與資訊顯示設計

由於魔紋是程序化生成的，我們不能依賴 XML 的靜態描述。UI 必須能夠動態讀取 `Comp` 或 `Hediff` 中的數據並呈現給玩家。

## 1. 魔紋汁液 (Item) 的資訊顯示

當玩家點擊熬煮好的「魔紋汁液」時，需要看到它具體有哪些效果。

### A. 物品說明 (Description) 擴充
*   **實作方式**: 覆蓋 `Thing.GetDescriptionPart()` 或在 `ThingComp` 中使用 `TransformValue`。
*   **顯示內容**: 
    ```text
    [成分總結]
    - 龍血 (提供: +10% 血量)
    - 疾風草 (提供: +0.2 移速)
    [熬煮品質: 優秀 (1.2x)]
    -----------------------
    預計強化效果:
    - 最大生命值: +12%
    - 移動速度: +0.24
    ```

### B. 選單按鈕 (Gizmos)
*   **實作方式**: 在 `CompMagicInk` 中實現 `GetGizmos()`。
*   **功能**: 可以增加一個「預覽紋身效果」的按鈕，彈出一個小視窗顯示若紋在不同部位的加成。

## 2. Pawn 健康面板 (Health Tab)

魔紋作為一個 Hediff，會出現在 Pawn 的健康狀態欄。

### A. 懸停詳細資訊 (Tooltip)
*   **實作方式**: 在 `Hediff_MagicTattoo` 中覆蓋 `TipStringExtra` 屬性。
*   **顯示內容**: 列出所有當前的屬性加成，讓玩家清楚知道這個紋身帶來了什麼好處。

### B. 自定義圖標 (Icon)
*   為了在列表中區分普通受傷和魔紋，我們可以為 `HediffDef` 指定一個獨特的圖標（如一個發光的符文）。

## 3. 外觀表現 (Visual Tattoo) - 進階功能

如果您希望在 Pawn 的小人模型上看到紋身：

### A. 靜態紋身圖層
*   **實作方式**: 使用 `HediffComp_DrawTattoo`。
*   **邏輯**: 當 Pawn 擁有該 Hediff 時，在渲染流程中注入一個額外的圖層。
*   **挑戰**: 需要根據 Pawn 的身體類型 (BodyType) 和旋轉角度 (Rotation) 調整圖樣。

### B. 顏色與發光
*   **動態顏色**: 汁液的顏色可以決定紋身的顏色（如龍血汁液產生紅色紋身）。
*   **Glow 效果**: 在夜晚讓紋身發出微光，這可以透過修改渲染器的 `Shader` 來實現（使用 `TransparentPostRender`）。

## 4. 鍊藥鍋交互 UI (Interactive Cauldron UI)

這是一個非標準的自定義介面，將提供比普通工作台更具沉浸感的體驗。

### A. 介面組成 (UI Components)
*   **畫布 (Window)**: 繼承自 `Verse.Window`。
*   **背景圖案**: 顯示一張大鍋 (Cauldron) 的藝術圖。
*   **素材槽位 (Ingredient Slots)**: 
    *   在鍋子圖案上方或周圍定義 3-5 個圓形區域。
    *   每個區域是一個 `Rect`，用於顯示已選中素材的圖示。
*   **右鍵菜單 (FloatMenu)**: 
    *   點擊槽位時，調用 `FloatMenu` 列出當前地圖/倉庫中可用的素材。
    *   玩家點擊後，該槽位會「預定」該素材。

### B. 技術實作邏輯
1.  **數據儲存**: 在鍊藥鍋建物的 `ThingComp` 中維護一個 `List<ThingDefCount>`，記錄玩家選定的配方。
2.  **右鍵邏輯**:
    ```csharp
    // 偽代碼示例
    if (Event.current.type == EventType.MouseDown && Event.current.button == 1) { // 右鍵
        List<FloatMenuOption> options = new List<FloatMenuOption>();
        foreach (var material in Map.resourceCounter.AllCountedAmounts) {
            options.Add(new FloatMenuOption(material.Key.LabelCap, () => SelectMaterial(slotId, material.Key)));
        }
        Find.WindowStack.Add(new FloatMenu(options));
    }
    ```
3.  **任務觸發**: 
    *   當玩家填滿槽位並點擊「開始熬煮」時，生成一個 `JobDef_FillCauldron` 給殖民者。
    *   Pawn 會依次搬運選定的素材到大鍋。
    *   最後執行 `JobDef_BrewInk` 進行熬煮。

### C. 視覺反饋
*   **進度條**: 在大鍋 UI 中顯示一個發光的進度條，顯示當前熬煮進度。
*   **顏色變化**: 根據放入素材的主色調，動態混合大鍋中「汁液」的顏色。

---
*文件路徑: analysis/rimworld/others/magic_tattoo_ui_design.md*
