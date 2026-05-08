# Mod 設定整合：自定義 ARPG 體驗

為了讓玩家能根據喜好調整 ARPG 模式（如總頁數、WASD 開關等），我們需要利用 RimWorld 的 `ModSettings` 系統。

## 1. 定義設定數據 (ModSettings)

建立一個繼承自 `ModSettings` 的類別，用於儲存所有用戶自定義參數。

```csharp
public class ARPG_Settings : ModSettings
{
    // 移動設定
    public bool enableWASD = true;
    public float cameraSmoothness = 0.1f;

    // 快捷欄設定
    public int totalActionPages = 5;
    public bool showHotkeyList = true;

    // 戰鬥設定
    public float globalManaRegenMultiplier = 1.0f;

    public override void ExposeData()
    {
        base.ExposeData();
        Scribe_Values.Look(ref enableWASD, "enableWASD", true);
        Scribe_Values.Look(ref cameraSmoothness, "cameraSmoothness", 0.1f);
        Scribe_Values.Look(ref totalActionPages, "totalActionPages", 5);
        Scribe_Values.Look(ref showHotkeyList, "showHotkeyList", true);
        Scribe_Values.Look(ref globalManaRegenMultiplier, "globalManaRegenMultiplier", 1.0f);
    }
}
```

## 2. 建立 Mod 類別與 UI 界面

這是玩家在遊戲「選項 -> Mod 設定」中看到的界面。

```csharp
public class ARPG_Mod : Mod
{
    public static ARPG_Settings settings;

    public ARPG_Mod(ModContentPack content) : base(content)
    {
        settings = GetSettings<ARPG_Settings>();
    }

    // 繪製設定界面
    public override void DoSettingsWindowContents(Rect inRect)
    {
        Listing_Standard listing = new Listing_Standard();
        listing.Begin(inRect);

        // WASD 設定
        listing.CheckboxLabeled("啟用 WASD 移動", ref settings.enableWASD, "開啟後可使用鍵盤控制角色位移。");
        listing.Label($"鏡頭平滑度: {settings.cameraSmoothness:F2}");
        settings.cameraSmoothness = listing.Slider(settings.cameraSmoothness, 0.01f, 0.5f);

        listing.Gap();

        // 快捷欄設定
        listing.Label($"快捷欄總頁數: {settings.totalActionPages}");
        // 使用整數滑桿或輸入框
        float tempPages = settings.totalActionPages;
        listing.IntSetter(ref settings.totalActionPages, 1, 1, 20); // 1~20 頁

        listing.Gap();

        // 數值平衡
        listing.Label($"能量恢復倍率: {settings.globalManaRegenMultiplier:P0}");
        settings.globalManaRegenMultiplier = listing.Slider(settings.globalManaRegenMultiplier, 0.1f, 5.0f);

        listing.End();
        base.DoSettingsWindowContents(inRect);
    }

    // 設定選單中的標籤名稱
    public override string SettingsCategory() => "RimWorld ARPG 化轉換";
}
```

## 3. 在邏輯中引用設定

現在，我們之前的系統應該從 `ARPG_Mod.settings` 讀取數值。

### A. 移動邏輯檢測
```csharp
private void HandleWASDMovement(Pawn pawn)
{
    if (!ARPG_Mod.settings.enableWASD) return; // 若設定關閉則不執行
    // ... 原有的 WASD 邏輯 ...
}
```

### B. 動態頁數初始化
```csharp
public void InitializePages() {
    int pages = ARPG_Mod.settings.totalActionPages; // 從設定讀取
    actionPages = new SkillDef[pages][];
    // ...
}
```

## 4. 進階：即時生效與數據同步

*   **即時生效**: `DoSettingsWindowContents` 關閉時會自動呼叫 `Write`。若某些設定需要立即刷新（如 UI 位置），可以在 `DoSettingsWindowContents` 的結尾加入刷新邏輯。
*   **多檔兼容**: `ModSettings` 是全域存儲的（存放在 `Config` 資料夾），意味著所有存檔都會共用同一套偏好設定。

---
*文件路徑: analysis/rimworld/details/mod_settings_integration.md*
