using Verse;
using RimWorld;
using Verse.AI;
using System.Collections.Generic;

namespace MyMod.Examples;

/// <summary>
/// 祭壇組件屬性。
/// </summary>
public class CompProperties_AltarPower : CompProperties
{
    public AltarType type;
    public float maxEnergy = 100f;
    public FleckDef fleckDef;
    public string ritualLetterLabel;

    public CompProperties_AltarPower()
    {
        compClass = typeof(CompAltarPower);
    }
}

public enum AltarType { Healing, Destruction, Harvest }

/// <summary>
/// 執行祭壇儀式的 JobDriver。
/// 小人會站在祭壇前進行引導，增加祭壇能量。
/// </summary>
public class JobDriver_PerformAltarRitual : JobDriver
{
    private const TargetIndex AltarInd = TargetIndex.A;

    public override bool TryMakePreToilReservations(bool errorOnFailed)
    {
        return pawn.Reserve(job.targetA, job, 1, -1, null, errorOnFailed);
    }

    protected override IEnumerable<Toil> MakeNewToils()
    {
        // 1. 走到祭壇旁邊
        yield return Toils_Goto.GotoThing(AltarInd, PathEndMode.Touch);

        // 2. 執行儀式 (持續性動作)
        Toil ritual = new Toil();
        ritual.tickAction = () =>
        {
            Pawn actor = ritual.actor;
            Thing altar = actor.CurJob.targetA.Thing;
            CompAltarPower comp = altar.TryGetComp<CompAltarPower>();

            if (comp != null)
            {
                // 增加能量 (每 Tick 0.1)
                comp.AddEnergy(0.1f);
                
                // 視覺特效：偶爾產生一點靈能火花
                if (Find.TickManager.TicksGame % 60 == 0)
                {
                    FleckMaker.ThrowMetaIcon(actor.Position, actor.Map, FleckDefOf.PsycastAreaEffect);
                }
            }
        };
        ritual.defaultCompleteMode = ToilCompleteMode.Never; // 由玩家手動取消或能量滿時結束
        ritual.WithProgressBar(AltarInd, () => 
        {
            CompAltarPower comp = job.targetA.Thing.TryGetComp<CompAltarPower>();
            return comp != null ? comp.EnergyPct : 0f;
        });
        
        // 能量滿時自動結束
        ritual.AddEndCondition(() =>
        {
            CompAltarPower comp = job.targetA.Thing.TryGetComp<CompAltarPower>();
            return (comp != null && comp.EnergyPct >= 1f) ? JobCondition.Succeeded : JobCondition.Ongoing;
        });

        yield return ritual;
    }
}
