# 高階熱鍵系統與快捷欄切換設計

為了提供真正的 ARPG 操作體驗，技能欄必須支持複雜的熱鍵映射（1-9, Ctrl, Shift）以及多套配置的快速切換。

## 1. 熱鍵映射機制 (Hotkey Mapping)

在 RimWorld 中，我們可以在 `MapComponent` 或 `Window` 的 `Update` 方法中監聽 Unity 的 `Input` API。

### A. 組合鍵監聽邏輯
```csharp
public static bool IsHotkeyPressed(int slotIndex, out string modifier)
{
    modifier = "";
    KeyCode baseKey = KeyCode.Alpha1 + slotIndex; // 映射到 1, 2, 3...
    
    if (Input.GetKeyDown(baseKey))
    {
        if (Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift)) modifier = "Shift";
        else if (Input.GetKey(KeyCode.LeftControl) || Input.GetKey(KeyCode.RightControl)) modifier = "Ctrl";
        return true;
    }
    return false;
}
```

## 2. 動態多頁快捷欄與快速切換 (Dynamic Action Bar Paging)

玩家可能擁有很多技能，限制在兩三頁顯然不足。我們可以實作動態頁數支持，並提供更靈活的切換方式。

### A. 數據結構擴充
使用 `List` 或大容量數組來支持更多頁面，並允許玩家透過設定調整總頁數。
```csharp
public class CompSkillTracker : ThingComp
{
    public int totalPages = 5; // 可由玩家在 Mod 設定中調整，例如 5~10 頁
    public int currentPage = 0;
    
    // 使用字典或交錯數組儲存頁面數據：[頁面索引][槽位索引]
    public SkillDef[][] actionPages;

    public void InitializePages() {
        actionPages = new SkillDef[totalPages][];
        for (int i = 0; i < totalPages; i++) {
            actionPages[i] = new SkillDef[10]; // 每頁 10 個槽位
        }
    }

    public void SwitchToPage(int pageIndex)
    {
        if (pageIndex >= 0 && pageIndex < totalPages) {
            currentPage = pageIndex;
            Messages.Message($"切換至快捷欄第 {currentPage + 1} 頁", MessageTypeDefOf.SilentInput);
        }
    }

    public void CyclePage(int direction)
    {
        currentPage = (currentPage + direction + totalPages) % totalPages;
        Messages.Message($"切換至快捷欄第 {currentPage + 1} 頁", MessageTypeDefOf.SilentInput);
    }
}
```

## 3. 整合觸發邏輯 (The Trigger Loop)

除了循環翻頁，我們還可以實作「快速跳轉」。

```csharp
public override void MapComponentUpdate()
{
    Pawn p = Find.Selector.SingleSelectedPawn;
    if (p == null || !p.IsColonistPlayerControlled) return;

    CompSkillTracker tracker = p.GetComp<CompSkillTracker>();

    // 1. 檢測翻頁熱鍵
    if (Input.GetKeyDown(KeyCode.Tab)) tracker.CyclePage(1); // Tab 循環翻頁
    
    // 2. 檢測跳轉熱鍵 (例如: Alt + 1~5 直接跳轉到對應頁面)
    if (Input.GetKey(KeyCode.LeftAlt)) {
        for (int i = 0; i < tracker.totalPages; i++) {
            if (Input.GetKeyDown(KeyCode.Alpha1 + i)) {
                tracker.SwitchToPage(i);
                break;
            }
        }
        return; // 跳轉頁面後不執行該幀的技能釋放
    }

    // 3. 檢測技能熱鍵 1~9
    for (int i = 0; i < 9; i++)
    {
        // ... 原有的熱鍵觸發邏輯 ...
    }
}
```

## 4. UI 視覺反饋 (Visual Feedback)

快捷欄 UI 需要直觀地顯示當前的熱鍵綁定：

*   **熱鍵標籤**: 在每個技能槽的角落繪製一個微型標籤（如 "1", "S+1", "C+1"）。
*   **翻頁動畫**: 當切換頁面時，可以讓圖標有一個輕微的平移或淡入淡出效果。
*   **當前頁碼指示器**: 在快捷欄旁邊顯示 `Page 1/3`。

## 5. 鍵位自定義與原生整合 (Keybinding Integration)

為了讓玩家能在 RimWorld 的「選項 -> 鍵位設定」中更改熱鍵，我們必須使用 `KeyBindingDef` 而非硬編碼 `KeyCode`。

### A. XML 定義 (KeyBindingDefs.xml)
在 Mod 的 XML 文件中定義這些類別：
```xml
<Defs>
    <!-- 技能槽 1~5 -->
    <KeyBindingDef>
        <defName>ARPG_SkillSlot1</defName>
        <label>ARPG 技能槽 1</label>
        <category>MainTabs</category>
        <defaultKeyCodeA>Alpha1</defaultKeyCodeA>
    </KeyBindingDef>
    
    <!-- 翻頁鍵 -->
    <KeyBindingDef>
        <defName>ARPG_CyclePage</defName>
        <label>ARPG 循環翻頁</label>
        <category>MainTabs</category>
        <defaultKeyCodeA>Tab</defaultKeyCodeA>
    </KeyBindingDef>
</Defs>
```

### B. C# 靜態類別 (KeyBindingDefOf)
建立一個 DefOf 類別以便於在代碼中引用：
```csharp
[DefOf]
public static class ARPG_KeyBindingDefOf
{
    public static KeyBindingDef ARPG_SkillSlot1;
    public static KeyBindingDef ARPG_CyclePage;
    
    static ARPG_KeyBindingDefOf() {
        DefOfHelper.EnsureInitializedInRuntime(typeof(ARPG_KeyBindingDefOf));
    }
}
```

### C. 檢測邏輯更新
使用 `KeyBindingDef.KeyDownEvent` 或 `JustPressed` 來替代 `Input.GetKeyDown`。
```csharp
public override void MapComponentUpdate()
{
    // ... 選中 Pawn 檢查 ...

    // 1. 使用原生鍵位檢測翻頁
    if (ARPG_KeyBindingDefOf.ARPG_CyclePage.JustPressed)
    {
        tracker.CyclePage(1);
    }

    // 2. 使用原生鍵位檢測技能釋放
    if (ARPG_KeyBindingDefOf.ARPG_SkillSlot1.JustPressed)
    {
        // 觸發 Slot 1 技能
    }
}
```

### D. 組合鍵與 KeyBindingDef 的衝突處理
`KeyBindingDef` 本身可以設定包含 Shift/Ctrl 的組合鍵。若要動態判斷，建議為「組合鍵」也定義獨立的 `KeyBindingDef`，或者在檢測到基礎鍵按下時，手動檢查 `Event.current.shift` 等狀態。

---
*文件路徑: analysis/rimworld/details/hotkey_system_design.md*
