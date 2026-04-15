# RimWorld Mod 入口與加載機制

理解 Mod 如何被加載是開發的第一步。RimWorld 支援純 XML Mod 和包含 C# 的程式碼 Mod。

## 1. 檔案結構
一個標準的 Mod 資料夾通常如下：
*   `About/About.xml`: Mod 的元數據（名稱、作者、描述、依賴）。
*   `Assemblies/`: 存放編譯好的 `.dll` 檔案。
*   `Defs/`: 存放 XML 定義。
*   `Patches/`: 存放 XML Patch (XPath)。
*   `Textures/`, `Sounds/`: 資源檔案。

## 2. C# 入口點
如果你需要編寫 C# 代碼，有兩個主要切入點：

### A. 繼承 `Verse.Mod`
如果你的 Mod 需要自定義設置頁面或在啟動時執行一次性邏輯，請繼承 `Mod` 類別。
```csharp
public class MyMod : Mod
{
    public MyMod(ModContentPack content) : base(content)
    {
        Log.Message("MyMod 已加載！");
        // 獲取設置
        this.GetSettings<MySettings>();
    }
}
```
遊戲啟動時，`LoadedModManager.CreateModClasses()` 會搜尋所有繼承自 `Mod` 的類別並實例化它們。

### B. 使用 `[StaticConstructorOnStartup]`
這是最常用的切入點，用於在遊戲數據 (Defs) 全部加載完成後執行邏輯。
```csharp
[StaticConstructorOnStartup]
public static class MyInitializer
{
    static MyInitializer()
    {
        Log.Message("Defs 已加載，現在可以安全地訪問 DefDatabase 了。");
        // 例如：動態修改某個物品的屬性
        ThingDefOf.Steel.stackLimit = 9999;
    }
}
```

## 3. 加載生命週期 (LoadedModManager)
遊戲加載 Mod 的順序（簡化版）：
1. **加載 Assemblies**: 加載所有 Mod 的 DLL 到內存。
2. **實例化 Mod 類別**: 呼叫繼承自 `Mod` 的構造函數。
3. **加載 XML**: 讀取所有 `Defs/` 下的 XML。
4. **應用 Patches**: 執行 `Patches/` 下的 XPath 操作，修改內存中的 XML。
5. **XML 解析**: 將 XML 轉換為真正的 `Def` 物件並存入 `DefDatabase`。
6. **靜態構造函數**: 呼叫標註了 `[StaticConstructorOnStartup]` 的類別。

## 4. 關鍵類別
*   **ModContentPack**: 代表一個 Mod 的內容包，可用於獲取 Mod 的路徑或資源。
*   **LoadedModManager**: 全局管理所有已加載的 Mod。
*   **PatchOperation**: XML 補丁的基類。

---
*這份文件是由 Gemini CLI 透過分析 Verse.LoadedModManager 產生的分析報告。*
