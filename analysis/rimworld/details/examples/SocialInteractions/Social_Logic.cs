using Verse;
using RimWorld;
using Verse.AI;
using System.Collections.Generic;
using UnityEngine;

namespace MyMod.Examples;

/// <summary>
/// 實戰範例：撓癢癢組件。
/// 當此組件附加在小人身上時，允許玩家對其發起交互。
/// </summary>
public class CompTickleable : ThingComp
{
    public override IEnumerable<FloatMenuOption> CompGetFloatMenuOptions(Pawn selPawn)
    {
        Pawn targetPawn = (Pawn)parent;

        // 1. 基本條件檢查：選中的小人必須是殖民者且不是被選中的目標本人
        if (selPawn != null && selPawn != targetPawn && selPawn.IsColonistPlayerControlled)
        {
            // 2. 關係檢查：如果不熟，增加一點拒絕機率
            float opinion = selPawn.relations.OpinionOf(targetPawn);
            string label = "撓癢癢 (友情互動)";
            
            yield return new FloatMenuOption(label, () =>
            {
                // 3. 建立並發送 Job
                Job job = JobMaker.MakeJob(DefDatabase<JobDef>.GetNamed("MyMod_Job_Tickle"), targetPawn);
                selPawn.jobs.TryTakeOrderedJob(job);
            });
        }
    }
}

/// <summary>
/// 實戰範例：撓癢癢的具體行動邏輯。
/// </summary>
public class JobDriver_Tickle : JobDriver
{
    private const TargetIndex TargetPawnInd = TargetIndex.A;

    public override bool TryMakePreToilReservations(bool errorOnFailed)
    {
        return pawn.Reserve(job.targetA, job, 1, -1, null, errorOnFailed);
    }

    protected override IEnumerable<Toil> MakeNewToils()
    {
        // 1. 走到目標小人身邊
        yield return Toils_Goto.GotoThing(TargetPawnInd, PathEndMode.Touch);

        // 2. 進行交互過程
        Toil interact = new Toil();
        interact.tickAction = () =>
        {
            Pawn actor = interact.actor;
            Pawn victim = (Pawn)job.targetA.Thing;

            // 每隔一段時間播放一個「笑聲」視覺特效
            if (Find.TickManager.TicksGame % 40 == 0)
            {
                FleckMaker.ThrowMetaIcon(victim.Position, victim.Map, FleckDefOf.PsycastAreaEffect);
                MoteMaker.ThrowText(victim.DrawPos, victim.Map, "Hahaha!", Color.yellow);
            }

            // 讓受害者偶爾亂動一下（模擬掙扎）
            if (Find.TickManager.TicksGame % 20 == 0)
            {
                victim.Drawer.renderer.rootContext.shaker.DoShake(0.5f);
            }
        };
        
        // 持續 120 Ticks (約 2 秒)
        interact.defaultDuration = 120;
        interact.defaultCompleteMode = ToilCompleteMode.Delay;
        interact.WithProgressBarToilDelay(TargetPawnInd);
        
        yield return interact;

        // 3. 互動完成後的結果
        yield return Toils_General.Do(() =>
        {
            Pawn actor = interact.actor;
            Pawn victim = (Pawn)job.targetA.Thing;

            // A. 給予受害者心情加成 (Thought)
            victim.needs.mood?.thoughts.memories.TryAddMemory(DefDatabase<ThoughtDef>.GetNamed("MyMod_Thought_Tickled"));

            // B. 增加雙方關係值
            actor.relations.ChangeRelationValue(PawnRelationDefOf.Friend, 2, true);

            // C. 播放一個小小的音效
            SoundDefOf.Interact_Tend.PlayOneShot(victim);

            Messages.Message($"{actor.LabelShort} 把 {victim.LabelShort} 逗樂了！", victim, MessageTypeDefOf.PositiveEvent);
        });
    }
}
