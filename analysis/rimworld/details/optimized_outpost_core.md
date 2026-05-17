# 極致性能哨所優化：宏觀產出與快照模擬實作

在大規模遊戲中，精確模擬每個物件是不現實的。本方案實作了一套「黑箱模擬」邏輯，將哨所轉化為純粹的數據增量引擎。

## 1. 全球增量引擎：WorldComponent_MacroOutpost

我們不讓每個哨所自己 Tick，而是由一個全域組件統籌處理。

```csharp
public class WorldComponent_MacroOutpost : WorldComponent
{
    // 每 60,000 Tick (一天) 更新一次所有哨所
    private const int UpdateInterval = 60000;

    public override void WorldComponentTick()
    {
        if (Find.TickManager.TicksGame % UpdateInterval == 0)
        {
            ProcessAllOutposts();
        }
    }

    private void ProcessAllOutposts()
    {
        foreach (var outpost in Find.WorldObjects.AllWorldObjects.OfType<WorldObject_Outpost>())
        {
            outpost.ApplyDailyYield();
        }
    }
}
```

## 2. 物資快照與產出計算 (Inventory Delta)

實作 `ProductivitySnapshot` 類別，用於分析玩家在「封存前」的表現。

```csharp
public class ProductivitySnapshot : IExposable
{
    // 儲存 ThingDef 與其每日產出量的映射
    public Dictionary<ThingDef, float> dailyProduction = new Dictionary<ThingDef, float>();

    public void CreateFromMap(Map map, int samplingDays)
    {
        // 1. 獲取當前地圖所有資源
        // 2. 與 T0 (進入地圖時) 的數據對比
        // 3. 計算平均值並存入 dailyProduction
        foreach (var count in map.resourceCounter.AllCountedAmounts)
        {
            float delta = count.Value - GetT0Count(count.Key);
            dailyProduction[count.Key] = delta / samplingDays;
        }
    }

    public void ExposeData()
    {
        Scribe_Collections.Look(ref dailyProduction, "dailyProduction", LookMode.Def, LookMode.Value);
    }
}
```

## 3. 背景技能訓練 (Off-Map Training)

讓駐守人員在背景中持續獲得 XP，模擬「邊境生活」的磨練。

```csharp
public void ApplyOffMapTraining(List<Pawn> garrison)
{
    foreach (var pawn in garrison)
    {
        foreach (var skill in pawn.skills.skills)
        {
            // 獲取該人員在該哨所的訓練倍率 (由封存前的表現決定)
            float trainingXp = GetTrainingRate(skill.def);
            skill.Learn(trainingXp, true); // 直接增加 XP，不計入日常飽和度
        }
    }
}
```

## 4. 外交脈動 (Diplomatic Pulse)

哨所作為外交前哨，會持續影響與鄰近派系的關係。

```csharp
private void ApplyDiplomacyBonus()
{
    // 尋找距離 10 格內的所有派系據點
    var neighbors = Find.WorldObjects.Settlements
        .Where(s => Find.WorldGrid.TraversalDistanceBetween(this.Tile, s.Tile) <= 10);

    foreach (var settlement in neighbors)
    {
        if (settlement.Faction != null && !settlement.Faction.IsPlayer)
        {
            // 每日增加微量好感度 (0.01 ~ 0.05)
            settlement.Faction.TryAffectGoodwillWith(Faction.OfPlayer, 0.02f, false, false);
        }
    }
}
```

## 5. 性能與擴展性優化 (Scalability)

*   **數據壓縮**: 對於 `dailyProduction` 中產出極小（例如每日 0.001 個）的物品，自動捨棄，保持字典精簡。
*   **非同步計算**: 若哨所數量極多，將 `ProcessAllOutposts` 拆分，每幀只處理一個哨所，避免 Tick 峰值 (Stutter)。
*   **延遲交貨**: 生產出的物資不需要每天空投。可以積累到一定重量（如 50kg）後再一次性發送，減少空投莢艙的動畫開銷。

---
*文件路徑: analysis/rimworld/details/optimized_outpost_core.md*
