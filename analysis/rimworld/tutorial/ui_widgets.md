# RimWorld UI 與 Widgets 繪製指南

在 RimWorld 中，UI 是每一幀都在代碼中繪製的 (IMGUI 模式)。

## 1. 核心類別：`Verse.Window`
所有彈出的對話框都繼承自此類。
*   **`InitialSize`**: 設定視窗大小。
*   **`DoWindowContents(Rect inRect)`**: 繪製內容的主戰場。
*   **`doCloseX` / `doCloseButton`**: 設定是否顯示關閉按鈕。

## 2. 常用元件：`Verse.Widgets`
*   `Widgets.Label(rect, text)`: 顯示文字。
*   `Widgets.ButtonText(rect, label)`: 返回 `bool`，當被點擊時為 `true`。
*   `Widgets.CheckboxLabeled(rect, label, ref boolValue)`: 畫一個帶標籤的勾選框。
*   `Widgets.TextField(rect, stringValue)`: 返回輸入後的字串。
*   `Widgets.FillableBar(rect, percent)`: 畫進度條。

## 3. 自動佈局：`Listing_Standard`
幫助你自動排列 UI 元件，不用手動算座標。
```csharp
Listing_Standard listing = new Listing_Standard();
listing.Begin(rect);
listing.Label("標題");
listing.CheckboxLabeled("選項", ref myValue);
listing.End();
```

---
*由 Gemini CLI 分析 Verse.Window 與 Verse.Widgets 生成。*
