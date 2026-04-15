# 檢查面板 (Inspect Pane) 與指令按鈕 (Gizmos)

擴充原版功能的最快途徑。

## 1. 檢查字串 (`GetInspectString`)
在 `Thing` 或 `ThingComp` 中重寫此方法，可以在選中物體時顯示特定資訊（如當前電量、溫度）。
```csharp
public override string GetInspectString()
{
    return base.GetInspectString() + "\n我的自定義資訊";
}
```

## 2. 指令按鈕 (`GetGizmos`)
在面板上方顯示可點擊的按鈕。
*   **Command_Action**: 最常用的按鈕，點擊後執行一個 `Action`。
*   **Command_Toggle**: 開關按鈕，點擊後切換一個 `bool`。

## 3. 檢查分頁 (`ITab`)
做成像「健康」或「社交」那樣的分頁。
1.  繼承 `ITab` 並重寫 `FillTab()`。
2.  在 XML 中的 `inspectorTabs` 加入該類別。

---
*由 Gemini CLI 分析 RimWorld.Gizmo 與 Verse.ITab 生成。*
