# RimWorld 進階教程：實現自定義系統的數據持久化 (Scribe System)

在開發 RimWorld Mod 時，讓你的自定義系統（如：祭壇能量、商隊信用、任務進度）在關閉遊戲後依然存在是至關重要的。RimWorld 使用一套稱為 **Scribe** 的系統來處理 XML 序列化與反序列化。

---

## 1. 核心基礎：`IExposable` 接口

任何需要存入存檔的自定義類別都必須實現 `IExposable` 接口。這個接口只有一個核心方法：`ExposeData()`。

```csharp
public class MyCustomData : IExposable
{
    public int score;
    public string name;
    public List<string> history = new List<string>();

    public void ExposeData()
    {
        // 所有存檔邏輯都在這裡
        Scribe_Values.Look(ref score, "score", 0);
        Scribe_Values.Look(ref name, "name", "Unknown");
        Scribe_Collections.Look(ref history, "history", LookMode.Value);
    }
}
```

---

## 2. 存檔工具家族 (Scribe Tools)

在 `ExposeData()` 內部，你需要根據數據類型選擇正確的 `Scribe` 方法：

### A. `Scribe_Values` (基礎數值)
用於處理簡單的數據類型：`int`, `float`, `bool`, `string`, `Enum`。
*   **用法**: `Scribe_Values.Look(ref 變數, "標籤", 預設值);`
*   **注意**: 標籤必須是唯一的，預設值在加載失敗或新存檔時會被使用。

### B. `Scribe_Collections` (集合與清單)
用於處理 `List`, `Dictionary`, `HashSet`。
*   **用法**: `Scribe_Collections.Look(ref 清單, "標籤", LookMode.Value);`
*   **LookMode**:
    *   `LookMode.Value`: 用於基礎類型（如 `List<int>`）。
    *   `LookMode.Deep`: 用於實現了 `IExposable` 的對象清單（如 `List<MyCustomData>`）。
    *   `LookMode.Reference`: 用於地圖上已存在物體的引用清單（如 `List<Pawn>`）。

### C. `Scribe_Deep` (深層存儲)
將一個完整的對象副本存入 XML。
*   **適用場景**: 當該對象完全屬於你，且不與地圖上的其他物體共享時。
*   **注意**: 加載時會重新實例化一個全新的對象。

### D. `Scribe_References` (引用存儲) - 極其重要
只存儲物體的 **ID (TargetID)**，而不是整個物體。
*   **適用場景**: 引用小人 (`Pawn`)、建築 (`Building`) 或任何在地圖上已存在的 `Thing`。
*   **原因**: 如果你用 `Scribe_Deep` 存儲小人，讀檔後會出現兩個一模一樣的小人，導致存檔損壞。

---

## 3. 數據存在哪裡？(The Hooks)

你需要將你的 `ExposeData()` 掛鉤到遊戲內建的組件中，這樣它們才會隨存檔自動觸發。

### A. 全域數據：`WorldComponent`
適合存儲跨地圖的派系信用、全球災難進度。
```csharp
public class MyWorldData : WorldComponent
{
    public override void ExposeData()
    {
        base.ExposeData();
        Scribe_Values.Look(ref globalValue, "globalValue", 100);
    }
}
```

### B. 地圖局部數據：`MapComponent`
適合存儲該地圖特有的污染等級、祭壇偵測值。
```csharp
public class MyMapData : MapComponent
{
    public override void ExposeData()
    {
        base.ExposeData();
        Scribe_Values.Look(ref localEnergy, "localEnergy", 0f);
    }
}
```

### C. 物體附屬數據：`ThingComp`
適合存儲特定機器或雕像的自定義屬性。
```csharp
public override void PostExposeData()
{
    base.PostExposeData(); // 務必呼叫 base
    Scribe_Values.Look(ref energy, "energy", 0f);
}
```

---

## 4. 存檔開發的「金科玉律」

1.  **標籤匹配**: `Scribe` 方法中的標籤字符串必須在同一個類別中保持唯一。
2.  **雙向運作**: `ExposeData()` 既負責「寫入」也負責「讀取」。所以 `ref` 關鍵字是必不可少的。
3.  **預設值優化**: 如果數據等於預設值，RimWorld 不會將其寫入 XML，這能有效縮小存檔體積。
4.  **加載順序 (Loading Order)**: 引用 (`Scribe_References`) 只有在所有物體都實例化後才能解析。遊戲會自動處理這個順序，你不需要擔心，除非你在 `ExposeData` 中進行複雜的邏輯運算。

---
*這份指南由 Gemini CLI 針對 RimWorld 存檔系統開發而編寫。*
