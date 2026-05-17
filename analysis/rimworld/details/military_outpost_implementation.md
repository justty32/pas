# 軍事哨所與資源採集：高效背景模擬實作指南

在 RimWorld 中，每增加一個活躍地圖 (Active Map) 都會急劇消耗 CPU。軍事哨所系統的核心在於**「在不載入地圖的情況下模擬一切」**。

## 1. 核心載體：WorldObject_Outpost

哨所不應該是一個 Map，而應該是一個 `WorldObject`。

```csharp
public class WorldObject_Outpost : WorldObject
{
    // 駐守人員
    public List<Pawn> garrison = new List<Pawn>();
    
    // 產出類型與進度
    public ThingDef productionTarget;
    public float productionProgress;
    public int lastDeliveryTick;

    public override void Tick()
    {
        base.Tick();
        
        // 每一萬 Tick 處理一次生產 (減少計算頻率)
        if (Find.TickManager.TicksGame % 10000 == 0)
        {
            SimulateProduction();
        }
    }

    public override void ExposeData()
    {
        base.ExposeData();
        Scribe_Collections.Look(ref garrison, "garrison", LookMode.Deep);
        Scribe_Defs.Look(ref productionTarget, "productionTarget");
        Scribe_Values.Look(ref productionProgress, "productionProgress");
        Scribe_Values.Look(ref lastDeliveryTick, "lastDeliveryTick");
    }
}
```

## 2. 非載入地圖模擬 (Off-Map Simulation)

我們不需要真的讓 Pawn 去挖礦，而是根據其屬性計算產出率。

```csharp
private void SimulateProduction()
{
    // 計算總工作效率 (基於駐軍的採礦或技能等級)
    float workSpeed = 0f;
    foreach (var pawn in garrison)
    {
        workSpeed += pawn.skills.GetSkill(SkillDefOf.Mining).Level * 0.1f;
    }

    productionProgress += workSpeed;

    // 若進度達標，則準備發貨
    if (productionProgress >= 100f)
    {
        SendResourcesToColony();
        productionProgress = 0f;
    }
}
```

## 3. 自動物資投送：Drop Pod Delivery

當資源產出後，自動使用空投莢艙發送到玩家的主殖民地。

```csharp
private void SendResourcesToColony()
{
    Map targetMap = Find.AnyPlayerHomeMap;
    if (targetMap == null) return;

    // 產生貨物
    Thing stuff = ThingMaker.MakeThing(productionTarget);
    stuff.stackCount = 75;

    // 執行投送
    DropPodUtility.DropThingsNear(DropCellFinder.TradeDropSpot(targetMap), targetMap, new List<Thing> { stuff }, 110, false, true);
    
    Messages.Message($"來自哨所 {this.Label} 的物資已空投至 {targetMap.Parent.Label}", MessageTypeDefOf.PositiveEvent);
}
```

## 4. 哨所事件：基於概率的防禦 (Simulated Combat)

當哨所遭到攻擊時，不載入地圖進行戰鬥，而是計算雙方實力。

```csharp
public void HandleRaid(int raidStrength)
{
    float garrisonStrength = CalculateGarrisonStrength();
    
    // 勝率計算公式
    float winChance = garrisonStrength / (garrisonStrength + raidStrength);

    if (Rand.Value < winChance)
    {
        // 防禦成功，部分人員受傷 (Hediff 注入)
        ApplyInjuriesToGarrison();
        Messages.Message("哨所防禦成功！", MessageTypeDefOf.PositiveEvent);
    }
    else
    {
        // 防禦失敗，哨所被毀，人員散失
        DestroyOutpost();
        Messages.Message("哨所已被摧毀...", MessageTypeDefOf.NegativeEvent);
    }
}
```

## 5. UI 交互：哨所管理面板

當點擊世界地圖上的哨所時，需要自定義 `Gizmo`。

*   **人員管理**: 彈出視窗顯示駐軍狀態。
*   **產出設定**: 選擇當前要採集的資源類型（取決於該 Tile 的地形）。
*   **撤離按鈕**: 將所有駐軍轉化為一支「商隊 (Caravan)」返回主基地。

---
*文件路徑: analysis/rimworld/details/military_outpost_implementation.md*
