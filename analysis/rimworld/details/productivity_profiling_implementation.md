# 效能監控與優化工具：哨所產出分析器的 C# 實作

在大規模 Mod 中，效能與公平性是長久運行的基石。本系統實作了一套「產出剖析器 (Productivity Profiler)」，用於監控哨所的 CPU 負載與產出真實性。

## 1. 效能監控器：OutpostProfiler

我們需要追蹤每個哨所在 `Tick` 時消耗的 CPU 時間。

```csharp
public class OutpostProfiler
{
    private static Stopwatch stopwatch = new Stopwatch();
    public static Dictionary<WorldObject_Outpost, float> tickTimes = new Dictionary<WorldObject_Outpost, float>();

    public static void StartProfiling()
    {
        stopwatch.Restart();
    }

    public static void EndProfiling(WorldObject_Outpost outpost)
    {
        stopwatch.Stop();
        float ms = (float)stopwatch.Elapsed.TotalMilliseconds;
        // 使用平滑移動平均法紀錄耗時
        tickTimes[outpost] = Mathf.Lerp(tickTimes.ContainsKey(outpost) ? tickTimes[outpost] : 0, ms, 0.1f);
    }
}
```

## 2. 防作弊：資源來源驗證 (Source Validation)

攔截資源計數器，區分「本地產出」與「外部搬入」。

```csharp
[HarmonyPatch(typeof(Thing), "SpawnSetup")]
public static class Patch_TrackResourceOrigin
{
    public static void Postfix(Thing __instance, Map map)
    {
        if (__instance.def.IsResource())
        {
            // 檢查該物品是否由「採礦」、「收穫」或「製作」產生
            if (Current.ProgramState == ProgramState.Playing && IsLocalProduction())
            {
                map.GetComponent<MapComponent_ProductionTracker>().RecordLocalGain(__instance);
            }
        }
    }

    private static bool IsLocalProduction()
    {
        // 檢查當前 Job 是否為挖掘、收割或在工作台操作
        return ChildPawnJobMatching(); 
    }
}
```

## 3. 理論產出計算 (Theoretical Yield)

不依賴物資數量，而是依賴「工作點數」。

```csharp
public class MapComponent_ProductionTracker : MapComponent
{
    public Dictionary<ThingDef, float> workPoints = new Dictionary<ThingDef, float>();

    public void RecordWork(ThingDef product, float points)
    {
        if (!workPoints.ContainsKey(product)) workPoints[product] = 0;
        workPoints[product] += points;
    }

    public float GetDailyYield(ThingDef def, int samplingDays)
    {
        // 根據工作點數換算為實際產出量
        // 例如：100 點採礦工作點 = 75 個鋼鐵
        return (workPoints[def] * GetConversionRate(def)) / samplingDays;
    }
}
```

## 4. 效能報表 UI (Profiling UI)

在 Debug 模式下顯示的詳細效能視窗。

```csharp
public class Window_OutpostDebug : Window
{
    public override void DoWindowContents(Rect inRect)
    {
        Listing_Standard listing = new Listing_Standard();
        listing.Begin(inRect);

        listing.Label("--- 哨所效能分析 (ms/tick) ---");
        foreach (var entry in OutpostProfiler.tickTimes)
        {
            listing.Label($"{entry.Key.Label}: {entry.Value:F4} ms");
        }

        listing.Label("--- 真實產出校驗 ---");
        // 顯示 T1 - T0 的實測值 vs 理論產出值的偏差
        
        listing.End();
    }
}
```

## 5. 數據分析與自動調節

*   **偏差檢警**: 若「實際物資增加量」遠大於「理論產出值」，系統會發出警告，並在封存時以「理論值」為準（防止玩家在最後一刻搬入大量黃金）。
*   **效能熔斷 (Performance Circuit Breaker)**: 若某個哨所的平均 Tick 耗時超過 0.5ms，自動將其 Tick 間隔從 1 幀提升至 30 幀，犧牲即時性以換取流暢度。
*   **數據壓縮**: 哨所封存時，將所有細碎的採樣數據扁平化為一個 `Def` 映射表，釋放內存。

---
*文件路徑: analysis/rimworld/details/productivity_profiling_implementation.md*
