using Verse;
using RimWorld;
using System.Linq;

namespace MyMod.Examples;

/// <summary>
/// 實戰範例：強化版地圖監控器。
/// 負責根據祭禮進度觸發動態防禦襲擊。
/// </summary>
public class MapComponent_AltarDefender : MapComponent
{
    private bool halfWayRaidFired = false;
    private bool nearCompleteRaidFired = false;

    public MapComponent_AltarDefender(Map map) : base(map) { }

    public override void ExposeData()
    {
        base.ExposeData();
        Scribe_Values.Look(ref halfWayRaidFired, "halfWayRaidFired", false);
        Scribe_Values.Look(ref nearCompleteRaidFired, "nearCompleteRaidFired", false);
    }

    public override void MapComponentTick()
    {
        base.MapComponentTick();

        // 每隔 250 Ticks 檢查一次祭禮進度
        if (map.IsHashIntervalTick(250))
        {
            // 尋找當前地圖上的祭壇及其組件
            CompAltarPower altarComp = map.listerThings.AllThings
                .Select(t => t.TryGetComp<CompAltarPower>())
                .FirstOrDefault(c => c != null);

            if (altarComp != null)
            {
                float progress = altarComp.EnergyPct;

                // 1. 進度達 50%：中型襲擊
                if (progress >= 0.5f && !halfWayRaidFired)
                {
                    TriggerRivalRaid(1.0f, "偵測到靈能爆發");
                    halfWayRaidFired = true;
                }

                // 2. 進度達 90%：強力襲擊
                if (progress >= 0.9f && !nearCompleteRaidFired)
                {
                    TriggerRivalRaid(2.0f, "祭禮即將完成，敵方孤注一擲");
                    nearCompleteRaidFired = true;
                }
            }
        }
    }

    private void TriggerRivalRaid(float multiplier, string reason)
    {
        Faction faction = Find.FactionManager.RandomEnemyFaction();
        if (faction == null) return;

        IncidentParms parms = new IncidentParms
        {
            target = map,
            points = StorytellerUtility.DefaultThreatPointsNow(map) * multiplier,
            faction = faction,
            raidArrivalMode = PawnsArrivalModeDefOf.EdgeWalkIn,
            raidStrategy = RaidStrategyDefOf.ImmediateAttack
        };

        IncidentDefOf.RaidEnemy.Worker.TryExecute(parms);
        
        Find.LetterStack.ReceiveLetter(
            "攔截者抵達", 
            $"{faction.Name} 的部隊偵測到了能量激增 ({reason})，他們正趕來阻止儀式！", 
            LetterDefOf.ThreatBig
        );
    }
}
