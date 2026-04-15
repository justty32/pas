using Verse;
using RimWorld;
using Verse.AI;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace MyMod.Examples;

/// <summary>
/// 實戰範例：自定義「盟友建設區」。
/// </summary>
public class Zone_AllyBuild : Zone
{
    public Zone_AllyBuild() { }
    public Zone_AllyBuild(ZoneManager zoneManager) : base("盟友建設區", zoneManager) { }

    public override Color IconColor => new Color(0.2f, 0.8f, 0.4f, 0.5f);
    
    // 這裡可以加入區域特有的邏輯，例如：區域內的建築優先級
}

/// <summary>
/// 實戰範例：區域設計器。
/// 讓玩家能在介面上「畫出」這個區域。
/// </summary>
public class Designator_ZoneAdd_AllyBuild : Designator_ZoneAdd
{
    protected override string NewZoneLabel => "盟友建設區";

    public Designator_ZoneAdd_AllyBuild()
    {
        this.defaultLabel = "劃定盟友建設區";
        this.defaultDesc = "劃定一個特定的區域，盟友只會在這個區域內尋找藍圖並取用資源進行建設。";
        this.icon = ContentFinder<Texture2D>.Get("UI/Designators/ZoneCreate_Stockpile"); // 借用圖示
        this.soundSucceeded = SoundDefOf.Designate_ZoneAdd;
    }

    protected override Zone MakeNewZone()
    {
        return new Zone_AllyBuild(Find.CurrentMap.zoneManager);
    }
}

/// <summary>
/// 實戰範例：AI 任務給予器 - 嚴格區域鎖定。
/// </summary>
public class JobGiver_AllyBuildInZone : ThinkNode_JobGiver
{
    protected override Job TryGiveJob(Pawn pawn)
    {
        Map map = pawn.Map;

        // 核心邏輯：AI 遍歷「區域」而非「全圖藍圖」
        List<Zone> allyZones = map.zoneManager.AllZones.Where(z => z is Zone_AllyBuild).ToList();
        
        if (!allyZones.Any()) return null;

        foreach (var zone in allyZones.Cast<Zone_AllyBuild>())
        {
            // 只有在區域內的格子進行掃描
            foreach (IntVec3 cell in zone.Cells)
            {
                // 1. 尋找區域內的建設目標
                Thing construction = cell.GetFirstThing<Blueprint>(map) ?? (Thing)cell.GetFirstThing<Frame>(map);
                
                if (construction != null && pawn.CanReserve(construction))
                {
                    // 2. 尋找「同一個區域」內的資源
                    // 這實現了雙重區域鎖定：建設點必須在區域內，資源也必須在區域內
                    Thing resource = FindResourceInZone(construction, zone, pawn);
                    
                    if (resource != null)
                    {
                        return JobMaker.MakeJob(DefDatabase<JobDef>.GetNamed("MyMod_Job_AllyBuildInZone"), construction, resource);
                    }
                }
            }
        }
        return null;
    }

    private Thing FindResourceInZone(Thing construction, Zone_AllyBuild zone, Pawn pawn)
    {
        Map map = pawn.Map;
        foreach (IntVec3 cell in zone.Cells)
        {
            // 1. 檢查地上的散落物與儲存建築 (如置物架) 上的物體
            List<Thing> things = cell.GetThingList(map);
            foreach (Thing t in things)
            {
                if (IsValidResource(t, pawn)) return t;

                // 2. 檢查容器內部 (支援 IThingHolder，如箱子、深層儲存)
                if (t is IThingHolder holder)
                {
                    Thing innerResource = holder.GetDirectlyHeldThings().FirstOrDefault(x => IsValidResource(x, pawn));
                    if (innerResource != null) return innerResource;
                }
            }
        }
        return null;
    }

    private bool IsValidResource(Thing t, Pawn pawn)
    {
        // 排除食物、活物，且必須有堆疊數量，且小人可以預約
        return t.def.IsNutritionGiving == false && 
               t.def.category == ThingCategory.Item && 
               t.stackCount > 0 && 
               pawn.CanReserve(t);
    }
}

/// <summary>
/// 實戰範例：AI 工作驅動 - 支援從容器搬運。
/// </summary>
public class JobDriver_AllyBuildInZone : JobDriver
{
    protected Thing Construction => job.GetTarget(TargetIndex.A).Thing;
    protected Thing Resource => job.GetTarget(TargetIndex.B).Thing;

    public override bool TryMakePreToilReservations(bool errorOnFailed)
    {
        // 如果資源在容器內，預約容器本身或其中的資源
        return pawn.Reserve(Construction, job, 1, -1, null, errorOnFailed) &&
               pawn.Reserve(Resource, job, 1, -1, null, errorOnFailed);
    }

    protected override IEnumerable<Toil> MakeNewToils()
    {
        // 1. 走到資源所在地 (可能是容器所在的格子)
        yield return Toils_Goto.GotoThing(TargetIndex.B, PathEndMode.Touch);

        // 2. 核心邏輯：如果資源在容器內，執行「取出」動作
        Toil takeFromContainer = new Toil();
        takeFromContainer.initAction = () =>
        {
            if (Resource.ParentHolder is IThingHolder holder && !(holder is Map))
            {
                // 從容器中彈出資源到地上，以便後續搬運
                holder.GetDirectlyHeldThings().TryDrop(Resource, pawn.Position, pawn.Map, ThingPlaceMode.Near, out _);
            }
        };
        yield return takeFromContainer;

        // 3. 正常搬運與建造流程
        yield return Toils_Haul.StartCarryThing(TargetIndex.B);
        yield return Toils_Goto.GotoThing(TargetIndex.A, PathEndMode.Touch);
        
        Toil build = Toils_General.Wait(300);
        build.WithProgressBarToilDelay(TargetIndex.A);
        yield return build;

        yield return Toils_General.Do(() =>
        {
            IntVec3 pos = Construction.Position;
            ThingDef buildDef = (Construction is Blueprint_Build b) ? (ThingDef)b.def.entityDefToBuild : ThingDefOf.Barricade;
            Construction.Destroy();
            Resource.SplitStack(10);
            GenSpawn.Spawn(buildDef, pos, pawn.Map, pawn.Faction);
        });
    }
}

/// <summary>
/// 實戰範例：AI 任務給予器 - 區域內巡邏防守。
/// 確保建設者在閒置時不會亂跑，而是留在自己建好的陣地內保持警戒。
/// </summary>
public class JobGiver_WanderInAllyZone : ThinkNode_JobGiver
{
    protected override Job TryGiveJob(Pawn pawn)
    {
        Map map = pawn.Map;
        var zones = map.zoneManager.AllZones.OfType<Zone_AllyBuild>().ToList();
        
        if (zones.Any())
        {
            // 隨機挑選一個建設區進行巡邏
            Zone_AllyBuild targetZone = zones.RandomElement();
            if (targetZone.Cells.Count > 0)
            {
                // 從區域內選一個合法的點走過去
                IntVec3 targetCell = targetZone.Cells.RandomElement();
                if (pawn.CanReach(targetCell, PathEndMode.OnCell, Danger.Some))
                {
                    Job wanderJob = JobMaker.MakeJob(JobDefOf.GotoWander, targetCell);
                    wanderJob.locomotionUrgency = LocomotionUrgency.Amble; // 散步速度
                    wanderJob.expiryInterval = Rand.Range(300, 600); // 徘徊一段時間後重新思考
                    return wanderJob;
                }
            }
        }
        
        // 如果找不到區域，就待在原地防守
        return JobMaker.MakeJob(JobDefOf.Wait_Wander);
    }
}
