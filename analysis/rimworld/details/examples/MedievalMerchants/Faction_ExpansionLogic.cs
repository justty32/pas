using Verse;
using RimWorld;
using RimWorld.Planet;
using System.Collections.Generic;
using System.Linq;

namespace MyMod.Examples;

/// <summary>
/// 實戰範例：大地圖商貿驛站。
/// 定期向附近的玩家基地派發商隊。
/// </summary>
public class WorldObject_MerchantOutpost : WorldObject
{
    private int nextCaravanTicks = 0;
    private const int CaravanInterval = 120000; // 每兩天檢查一次

    public override void PostAdd()
    {
        base.PostAdd();
        nextCaravanTicks = Find.TickManager.TicksGame + CaravanInterval;
    }

    public override void Tick()
    {
        base.Tick();
        if (Find.TickManager.TicksGame > nextCaravanTicks)
        {
            TrySendCaravanToPlayer();
            nextCaravanTicks = Find.TickManager.TicksGame + CaravanInterval;
        }
    }

    private void TrySendCaravanToPlayer()
    {
        // 尋找距離 15 格內的玩家基地
        Settlement playerSettlement = Find.WorldObjects.Settlements.FirstOrDefault(s => s.Faction.IsPlayer && Find.WorldGrid.TraversalDistanceBetween(this.Tile, s.Tile) < 15);
        
        if (playerSettlement != null)
        {
            IncidentDef incident = IncidentDefOf.TraderCaravanArrival;
            IncidentParms parms = StorytellerUtility.DefaultThreatPointsNow(playerSettlement.Map);
            parms.target = playerSettlement.Map;
            parms.faction = this.Faction;
            
            // 根據派系信用度決定貿易清單
            var merchantFaction = (Faction_MedievalMerchants)this.Faction;
            parms.traderKind = merchantFaction.tradeCount >= 20 ? 
                DefDatabase<TraderKindDef>.GetNamed("MyMod_TraderKind_Medieval_Elite") : 
                DefDatabase<TraderKindDef>.GetNamed("MyMod_TraderKind_Medieval");

            incident.Worker.TryExecute(parms);
            Log.Message($"MyMod: 來自 {this.Label} 的商隊已出發前往玩家基地。");
        }
    }

    public override void ExposeData()
    {
        base.ExposeData();
        Scribe_Values.Look(ref nextCaravanTicks, "nextCaravanTicks", 0);
    }
}

/// <summary>
/// 實戰範例：受困的商隊事件。
/// 生成一隊正在逃命的商人，以及尾隨其後的劫匪。
/// </summary>
public class IncidentWorker_MerchantDistress : IncidentWorker
{
    protected override bool TryExecuteWorker(IncidentParms parms)
    {
        Map map = (Map)parms.target;
        Faction merchantFaction = Find.FactionManager.FirstFactionOfDef(DefDatabase<FactionDef>.GetNamed("MyMod_MedievalMerchantFaction"));
        Faction enemyFaction = Find.FactionManager.RandomEnemyFaction();

        if (merchantFaction == null || enemyFaction == null) return false;

        // 1. 在地圖一側生成商人商隊
        IntVec3 spawnLoc = CellFinder.RandomEdgeCell(map);
        PawnGroupMakerParms merchantGroup = IncidentParmsUtility.GetDefaultPawnGroupMakerParms(PawnGroupKindDefOf.Trader, parms);
        merchantGroup.faction = merchantFaction;
        List<Pawn> merchants = PawnGroupMakerUtility.GeneratePawns(merchantGroup).ToList();
        
        foreach (Pawn p in merchants)
        {
            GenSpawn.Spawn(p, spawnLoc, map);
        }

        // 2. 在同一側稍後位置生成劫匪
        PawnGroupMakerParms enemyGroup = IncidentParmsUtility.GetDefaultPawnGroupMakerParms(PawnGroupKindDefOf.Combat, parms);
        enemyGroup.faction = enemyFaction;
        enemyGroup.points *= 1.5f; // 劫匪點數多一點
        List<Pawn> enemies = PawnGroupMakerUtility.GeneratePawns(enemyGroup).ToList();
        
        foreach (Pawn p in enemies)
        {
            GenSpawn.Spawn(p, spawnLoc, map);
            // 劫匪目標：商人
            p.mindState.duty = new PawnDuty(DutyDefOf.HuntEnemiesIndividual);
        }

        // 3. 設定商人任務：逃往地圖另一側
        IntVec3 escapeLoc = CellFinder.RandomEdgeCell(map);
        foreach (Pawn p in merchants)
        {
            p.mindState.duty = new PawnDuty(DutyDefOf.TravelOrLeave, escapeLoc);
        }

        Find.LetterStack.ReceiveLetter(def.letterLabel, def.letterText, def.letterDef, merchants[0]);
        return true;
    }
}
