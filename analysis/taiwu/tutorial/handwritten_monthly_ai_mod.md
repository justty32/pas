# 教學：手寫「過月行為」backend mod（AdvanceMonthFinish 事件鉤）

> 範例專案：`~/repo/pas/projects/taiwu/MonthlyAiDemo/`（已對實裝 0.0.79.60 編譯通過）。
> 事實來源：反編譯原始碼 `~/dev/taiwu-src/backend/`，本檔 path:line 皆已覆核。
> 背景調查：[`details/npc_ai_and_advance_month.md`](../details/npc_ai_and_advance_month.md)。
> 狀態（2026-05-23）：程式完成、`Build succeeded` 0/0；尚未實機測試。

---

## 0. 範例做什麼（與「NPC AI」的關係）

**每次「過月完成」，把太吾自身的所有資源（食材/木材/金鐵/玉石/織物/藥材/金錢/威望，共 8 種）補滿。**

> 註：本範例原為「每月 +50 金錢」（已實機驗證可運作），後依需求改為「補滿所有資源」。兩者走同一條 `AddResource` 路徑，差別只在迴圈 8 種資源＋改用封頂值。

這是「過月時改動世界狀態」**最乾淨、最安全**的切入點示範。需要說清楚的取捨：

- 過月模擬的核心 NPC 自主決策（`PeriAdvanceMonth_ExecutePrioritizedAction` 等）跑在 **worker thread 的平行段**，遵守「先算後套用」兩段式；直接 Harmony patch 那裡、又寫全域狀態＝偶發崩潰（見 `npc_ai_and_advance_month.md`「平行執行緒鐵則」）。
- 本範例刻意**不碰平行段**，改掛在 `AdvanceMonthFinish` 事件——它在過月全部結束、回主執行緒後才觸發，串行、安全。
- 因此本範例示範的是「**過月事件鉤如何安全改世界狀態**」這條骨架。若要進一步「改 NPC 行為」，只需在同一個 handler 內把 `AddResource` 換成走 `DomainManager.Character` / AI 相關的串行 API 即可——骨架不變。

---

## 1. 事件鉤 API（已覆核）

`GameData/DomainEvents/Events.cs`：

| 行 | 內容 |
|---|---|
| `:220` | `public delegate void OnAdvanceMonthFinish(DataContext context);` |
| `:2686` | `public static void RegisterHandler_AdvanceMonthFinish(OnAdvanceMonthFinish handler)` |
| `:2691` | `public static void UnRegisterHandler_AdvanceMonthFinish(OnAdvanceMonthFinish handler)` |
| `:2696` | `RaiseAdvanceMonthFinish(DataContext context)` — 觸發點，由 `WorldDomain` 在過月尾段呼叫（主執行緒） |

handler 簽章固定為 `void(DataContext context)`，`context` 要轉手給後續寫操作（如 `AddResource`）。

---

## 2. plugin 生命週期接法

```csharp
[PluginConfig("MonthlyAiDemoBackend", "lorkhan", "1.0.0.0")]
public class Plugin : TaiwuRemakePlugin
{
    public override void Initialize() { /* 本範例不需 Harmony patch */ }

    // 進入新世界 / 載入存檔後才註冊（此時 backend 世界已就緒）
    public override void OnEnterNewWorld()     => RegisterAdvance();
    public override void OnLoadedArchiveData() => RegisterAdvance();

    private void RegisterAdvance()
    {
        // 先解除再註冊：OnEnterNewWorld / OnLoadedArchiveData 可能都被呼叫，避免掛兩次
        Events.UnRegisterHandler_AdvanceMonthFinish(OnAdvanceMonthFinish);
        Events.RegisterHandler_AdvanceMonthFinish(OnAdvanceMonthFinish);
    }

    public override void Dispose()  // 離開 / 卸載時務必解除，避免對失效 context 觸發
        => Events.UnRegisterHandler_AdvanceMonthFinish(OnAdvanceMonthFinish);
}
```

要點：
- **註冊放 `OnEnterNewWorld`/`OnLoadedArchiveData`，不放 `Initialize`**——`Initialize` 階段世界尚未建立（與 MySwordArt 送功法同模式）。
- **`Dispose` 一定要解除**，否則重進世界會重複註冊、或對舊 context 觸發。
- 「先解除再註冊」防重複掛載。

---

## 3. handler 內的寫操作（已覆核 API）

```csharp
private const sbyte ResourceTypeCount = 8;        // ResourceType 0..7（含金錢=6）
private const int   MaxResourceValue = 999999999; // ResourceInts.Add 封頂值＝滿

private void OnAdvanceMonthFinish(DataContext context)
{
    int taiwuId = DomainManager.Taiwu.GetTaiwuCharId();
    // 對 8 種資源各加封頂值 → ResourceInts.Add cap 到上限＝補滿（含金錢）
    for (sbyte rt = 0; rt < ResourceTypeCount; rt++)
        DomainManager.Taiwu.AddResource(context, ItemSourceType.Resources, rt, MaxResourceValue);
    AdaptableLog.Info($"[MonthlyAiDemo] 所有資源(0~7)補滿至 {MaxResourceValue} → 太吾(charId={taiwuId})");
}
```

| 呼叫 | 依據 | 安全性 |
|---|---|---|
| `AddResource(DataContext, ItemSourceType, sbyte resourceType, int amount)` | `TaiwuDomain.cs:3075` | `sourceType=Resources` 改太吾自身資源；`amount<=0` 內部 Warn 並 return；`ResourceInts.Add` 對負值丟例外、上限封頂 999999999 |
| `resourceType 0~7`（8 種資源） | `Config/ResourceType.cs:52` `new List<ResourceTypeItem>(8)`：0食材/1木材/2金鐵/3玉石/4織物/5藥材/6金錢/7威望 | — |
| 加 `999999999`＝「補滿」 | `ResourceInts.cs:117-119` `result>999999999 → 999999999`（封頂）；加封頂值 → Add 直接 cap | 不溢位：cap 後上限 9.99 億，+加值仍 < int.MaxValue |
| `AdaptableLog.Info` | `GameData/Utilities/AdaptableLog.cs` | 後端 log，實機可見 |

**加值必為正**（`amount<=0` 會被 `AddResource` Warn 並 return），故用封頂值；重複每月加仍維持滿。

---

## 4. 編譯結果（已驗證）

```
$ dotnet build -c Release   # projects/taiwu/MonthlyAiDemo/Backend
Build succeeded.  0 Warning(s)  0 Error(s)
```
csproj 同 ChenJiaBao：net6.0、普通引用 `GameData / GameData.Shared / GameData.Utilities`、glob Exclude obj/bin。

---

## 5. 使用者實機驗證步驟（待你開遊戲）

> 部署：`dist/Config.lua` 轉 GBK + `MonthlyAiDemo.Backend.dll` → `<遊戲>/Mod/MonthlyAiDemo/{Config.lua, Plugins/MonthlyAiDemo.Backend.dll}`。

1. 啟動遊戲、進入一個世界（新開或讀檔皆可）。
2. 記下太吾當前各項資源（村鎮資源面板：食材/木材/金鐵/玉石/織物/藥材/金錢/威望）。
3. **過 1 個月**。8 種資源應全部變成上限（≈9.99 億），且後端 log 出現 `[MonthlyAiDemo] AdvanceMonthFinish: ... 所有資源(0~7，含金錢)補滿至 999999999`。
4. 連過數月確認穩定維持滿、後端不崩。

---

## 6. 可調 / 可延伸

- 改補滿量/範圍：常數 `MaxResourceValue`（改小＝每月加固定量而非補滿）、`ResourceTypeCount`；或改成只對特定 `resourceType` 加（如單獨金錢=6）。
- **延伸成真正的 NPC 行為**：把 handler 內的 `AddResource` 換成對 `DomainManager.Character` 等的串行寫操作（例如月度調整某群 NPC 的屬性/狀態）。骨架（事件鉤註冊/解除、主執行緒、用 `context`）完全沿用。切記：**仍走 `AdvanceMonthFinish`（串行）而非 patch 平行段**。
