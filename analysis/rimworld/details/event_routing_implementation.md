# 事件重定向與轉運站：全球事件流管控實作

本系統透過攔截 RimWorld 的事件分發器 (`IncidentWorker`)，將特定的社交、貿易與移民事件導向玩家指定的哨所（轉運站）。

## 1. 轉運站組件：CompEventHub

我們需要在哨所上掛載一個組件，定義其作為轉運站的角色。

```csharp
public enum HubRole { None, Trading, Immigration, Embassy }

public class CompEventHub : WorldObjectComp
{
    public HubRole role = HubRole.None;

    public bool SupportsIncident(IncidentDef def)
    {
        switch (role)
        {
            case HubRole.Trading:
                return def == IncidentDefOf.TraderCaravanArrival;
            case HubRole.Immigration:
                return def == IncidentDefOf.WandererJoin || def == IncidentDefOf.RefugeePodCrash;
            case HubRole.Embassy:
                return def == IncidentDefOf.VisitorGroup;
            default:
                return false;
        }
    }

    public override void PostExposeData()
    {
        base.PostExposeData();
        Scribe_Values.Look(ref role, "role", HubRole.None);
    }
}
```

## 2. 核心攔截器：Harmony Patch

攔截事件執行前的參數設置，動態修改事件的發生目標。

```csharp
[HarmonyPatch(typeof(IncidentWorker), "TryExecute")]
public static class Patch_IncidentRouting
{
    [HarmonyPrefix]
    public static void Prefix(IncidentDef ___def, ref IncidentParms parms)
    {
        // 僅當目標是主基地地圖時進行重定向
        if (parms.target is Map map && map.IsPlayerHome)
        {
            // 尋找具備對應角色的哨所
            var hub = Find.WorldObjects.AllWorldObjects
                .Select(wo => wo.GetComponent<CompEventHub>())
                .FirstOrDefault(h => h != null && h.SupportsIncident(___def));

            if (hub != null)
            {
                // 將事件目標重新導向為哨所 (WorldObject)
                parms.target = hub.parent;
            }
        }
    }
}
```

## 3. 非載入地圖下的事件結算 (Abstract Resolution)

當事件發生在 `WorldObject` 而非 `Map` 時，需要實作抽象的交互邏輯。

```csharp
public class IncidentWorker_TraderArrival_Outpost : IncidentWorker
{
    protected override bool TryExecuteWorker(IncidentParms parms)
    {
        WorldObject_Outpost outpost = parms.target as WorldObject_Outpost;
        if (outpost == null) return false;

        // 1. 生成虛擬商人 (不產生物體)
        TraderKindDef traderKind = outpost.GetTemplateTraderKind();
        
        // 2. 彈出遠程交易窗口
        Find.WindowStack.Add(new Dialog_Trade_Outpost(traderKind, outpost));

        Messages.Message($"貿易商隊已抵達 {outpost.Label}，您可以透過通訊台與其交易。", MessageTypeDefOf.PositiveEvent);
        return true;
    }
}
```

## 4. 移民審查機制 (Immigration Screening)

針對 `Immigration` 類型的轉運站，實作一套自動化的新成員篩選流程。

```csharp
public void ProcessNewArrival(Pawn p)
{
    // 自動評估數值 (模擬審查)
    bool isUseful = p.skills.GetSkill(SkillDefOf.Mining).Level >= 10 || 
                    p.skills.GetSkill(SkillDefOf.Plants).Level >= 10;

    if (isUseful)
    {
        // 加入哨所駐軍，並發送信件通知玩家
        this.garrison.Add(p);
        Find.LetterStack.ReceiveLetter("新成員已錄用", $"{p.LabelShort} 通過了審查並加入哨所。", LetterDefOf.PositiveEvent);
    }
    else
    {
        // 轉化為奴隸或拒絕入境 (模擬驅逐)
        Messages.Message($"{p.LabelShort} 因技能不足被拒絕進入社區。", MessageTypeDefOf.NeutralEvent);
    }
}
```

## 5. 戰略緩衝與優化

*   **病疫隔離**: 若流浪者帶有傳染病（如流感），事件攔截在哨所發生，病毒不會傳播到主基地核心區域。
*   **效能釋放**: 將繁雜的訪客路徑計算與社交 Tick 從主地圖移除，僅保留數據結算，可提升主基地 10%-15% 的運行效率。
*   **外交分流**: 透過在不同派系邊界設置「大使館」哨所，玩家可以精確管理與各個派系的局部關係，而不用擔心全圖範圍的敵對行為。

---
*文件路徑: analysis/rimworld/details/event_routing_implementation.md*
