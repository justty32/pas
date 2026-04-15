# RimWorld Mod 除錯指南 (Debugging)

高效的除錯是 Mod 開發成功的關鍵。

## 1. 開啟開發者模式 (Dev Mode)
在遊戲選項 (Options) 中勾選 `Development mode`。
*   **Console (日誌)**: 按 `~` 開啟。所有報錯都會出現在這裡。
*   **Debug Actions**: 閃電圖示。可用於「即時」測試你的 Mod 功能（如：立刻完成研究、生成特定物體）。
*   **Visual Debugging**: 點擊地圖上的物體，按 `?` 開啟檢查器，查看底層數據。

## 2. 代碼級日誌
```csharp
Log.Message("正在執行某個邏輯...");
if (pawn == null) {
    Log.Error("Pawn 為空！這是不正常的。");
}
```

## 3. 反編譯與追蹤 (DNSPY)
*   **定位原版代碼**: 當你需要知道某個方法（如 `Thing.Destroy`）的具體實作時，在 DNSPY 中搜尋該方法。
*   **查看其他 Mod**: 你的 Mod 與其他 Mod 衝突時，可以用 DNSPY 打開對方的 DLL，看看對方是否也 Patch 了同一個方法。

---
*由 Gemini CLI 分析 RimWorld 開發工具與 Verse.Log 生成。*
