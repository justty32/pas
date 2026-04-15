using Verse;
using Verse.AI;
using RimWorld;

namespace MyMod.Examples;

/// <summary>
/// 實戰範例：自定義 JobGiver。
/// 讓小人在沒事做時，會主動尋找附近的汙垢進行清理。
/// </summary>
public class JobGiver_AutoCleanNearSelf : ThinkNode_JobGiver
{
    private const float SearchRadius = 15f; // 搜尋周圍 15 格

    protected override Job TryGiveJob(Pawn pawn)
    {
        // 1. 基礎檢查：如果小人不能做清潔工作，則跳過
        if (pawn.WorkTagIsDisabled(WorkTags.Cleaning))
        {
            return null;
        }

        // 2. 尋找最近的汙垢 (Filth)
        // 使用 ListerThings 快速過濾地圖上的物體
        Thing filth = GenClosest.ClosestThingReachable(
            pawn.Position, 
            pawn.Map, 
            ThingRequest.ForGroup(ThingRequestGroup.Filth), 
            PathEndMode.Touch, 
            TraverseParms.For(pawn), 
            SearchRadius, 
            (Thing t) => pawn.CanReserve(t) // 確保物體沒被別人預約
        );

        if (filth != null)
        {
            // 3. 返回一個清潔任務 (Clean)
            // JobDefOf.Clean 是原版定義好的清理任務
            Job job = JobMaker.MakeThingJob(JobDefOf.Clean, filth);
            return job;
        }

        return null;
    }
}
