using Verse;
using RimWorld;
using Verse.AI;
using Verse.AI.Group;
using System.Collections.Generic;
using System.Linq;

namespace MyMod.Examples;

/// <summary>
/// 實戰範例：AI 任務給予器 - 尋找適合修築掩體的位置。
/// </summary>
public class JobGiver_FortifyArea : ThinkNode_JobGiver
{
    protected override Job TryGiveJob(Pawn pawn)
    {
        // 1. 獲取群組 (Lord) 的資訊：我們想在群組的集合點附近建造
        Lord lord = pawn.GetLord();
        if (lord == null) return null;

        IntVec3 center = lord.curDuty?.focus.Cell ?? pawn.Position;

        // 2. 隨機尋找周圍 5 格內的空地
        for (int i = 0; i < 10; i++)
        {
            IntVec3 cell = center + GenRadial.RadialPattern[Rand.Range(1, 20)];
            if (cell.InBounds(pawn.Map) && cell.Standable(pawn.Map) && cell.GetFirstBuilding(pawn.Map) == null)
            {
                // 檢查是否適合放置掩體 (非水、非牆)
                if (pawn.CanReserve(cell) && !cell.Roofed(pawn.Map))
                {
                    return JobMaker.MakeJob(DefDatabase<JobDef>.GetNamed("MyMod_Job_AllyBuildBarricade"), cell);
                }
            }
        }
        return null;
    }
}

/// <summary>
/// 實戰範例：AI 工作驅動 - 施工過程。
/// </summary>
public class JobDriver_AllyBuildBarricade : JobDriver
{
    public override bool TryMakePreToilReservations(bool errorOnFailed)
    {
        return pawn.Reserve(job.targetA, job, 1, -1, null, errorOnFailed);
    }

    protected override IEnumerable<Toil> MakeNewToils()
    {
        // 1. 走到目標格子
        yield return Toils_Goto.GotoCell(TargetIndex.A, PathEndMode.OnCell);

        // 2. 施工動畫
        Toil build = Toils_General.Wait(180); // 施工 3 秒
        build.WithProgressBarToilDelay(TargetIndex.A);
        build.tickAction = () =>
        {
            // 播放敲擊音效
            if (Find.TickManager.TicksGame % 40 == 0)
            {
                SoundDefOf.Recipe_Sculpt.PlayOneShot(new TargetInfo(TargetA.Cell, pawn.Map));
                FleckMaker.ThrowMetaIcon(TargetA.Cell, pawn.Map, FleckDefOf.DustPuff);
            }
        };
        yield return build;

        // 3. 生成掩體
        yield return Toils_General.Do(() =>
        {
            IntVec3 cell = TargetA.Cell;
            Map map = pawn.Map;
            
            // 生成沙袋 (不消耗任何資源，NPC 專屬邏輯)
            Thing sandbags = ThingMaker.MakeThing(ThingDefOf.Sandbags, ThingDefOf.Steel);
            GenSpawn.Spawn(sandbags, cell, map);
            
            // 視覺特效：陣地完成
            MoteMaker.ThrowText(cell.ToVector3Shifted(), map, "防禦加固！", Color.green);
        });
    }
}

/// <summary>
/// 實戰範例：盟友 AI 指揮官。
/// 偵測地圖上的盟友，並根據戰局賦予他們建造職責。
/// </summary>
public class MapComponent_AllyCommander : MapComponent
{
    public MapComponent_AllyCommander(Map map) : base(map) { }

    public override void MapComponentTick()
    {
        base.MapComponentTick();

        // 每 250 Ticks (約 4 秒) 巡邏一次全圖盟友
        if (map.IsHashIntervalTick(250))
        {
            UpdateAllyDuties();
        }
    }

    private void UpdateAllyDuties()
    {
        // 1. 找到地圖上所有盟友群組 (Lords)
        foreach (Lord lord in map.lordManager.lords)
        {
            // 如果該群組是盟友 (Faction.IsPlayer == false 且不是敵人)
            if (lord.faction != null && !lord.faction.IsPlayer && !lord.faction.HostileTo(Faction.OfPlayer))
            {
                // 如果他們當前只是在發呆 (Wander) 或防守，就強制他們切換到加固模式
                if (lord.curDuty?.def == DutyDefOf.Defend || lord.curDuty?.def == DutyDefOf.WanderClose)
                {
                    PawnDuty newDuty = new PawnDuty(DefDatabase<DutyDef>.GetNamed("MyMod_Duty_AllyFortify"), lord.curDuty.focus);
                    foreach (Pawn p in lord.ownedPawns)
                    {
                        p.mindState.duty = newDuty;
                        // 讓小人立即重新思考當前的 Job
                        p.jobs.EndCurrentJob(JobCondition.InterruptForced);
                    }
                    Log.Message($"MyMod: 已命令盟友群組 ({lord.faction.Name}) 開始加固陣地。");
                }
            }
        }
    }
}
