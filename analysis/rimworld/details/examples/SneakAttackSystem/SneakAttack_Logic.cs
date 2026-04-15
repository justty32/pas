using Verse;
using RimWorld;
using RimWorld.Planet;
using System.Collections.Generic;
using System.Linq;

namespace MyMod.Examples;

/// <summary>
/// 實戰範例：可被偷襲的戰略據點。
/// 展示如何在大地圖右鍵選單中添加自定義交互選項。
/// </summary>
public class WorldObject_StrategicOutpost : MapParent
{
    private bool isSneakAttacked = false;

    public override void ExposeData()
    {
        base.ExposeData();
        Scribe_Values.Look(ref isSneakAttacked, "isSneakAttacked", false);
    }

    /// <summary>
    /// 當玩家選中商隊 (Caravan) 並右鍵點擊此據點時觸發。
    /// </summary>
    public override IEnumerable<FloatMenuOption> GetFloatMenuOptions(Caravan caravan)
    {
        // 1. 保留原有的選項（如「進入」、「攻擊」）
        foreach (var o in base.GetFloatMenuOptions(caravan)) yield return o;

        // 2. 只有在與該據點派系敵對時顯示「偷襲」
        if (this.Faction.HostileTo(Faction.OfPlayer))
        {
            yield return new FloatMenuOption("偷襲 (深夜潛入)", () =>
            {
                // 執行移動：商隊必須先到達該 Tile
                // 如果已經到達，則直接觸發偷襲
                if (caravan.Tile == this.Tile)
                {
                    InitiateSneakAttack(caravan);
                }
                else
                {
                    // 設置商隊目的地，並給予一個回調任務 (Arrival Action)
                    caravan.pather.SetDestination(this.Tile);
                    caravan.arrivalAction = new CaravanArrivalAction_AttackSettlement(this);
                    Messages.Message("商隊正秘密向據點行進，準備發動偷襲。", MessageTypeDefOf.TaskCompletion);
                }
            }, MenuOptionPriority.High);
        }
    }

    private void InitiateSneakAttack(Caravan caravan)
    {
        isSneakAttacked = true;

        // 1. 生成地圖：使用偷襲專用的 MapGeneratorDef
        Map map = GetOrGenerateMapUtility.GetOrGenerateMap(this.Tile, new IntVec2(100, 100), DefDatabase<MapGeneratorDef>.GetNamed("MyMod_SneakAttackMapGen"));

        // 2. 將玩家部隊傳送進去（設置為「隱密進入」模式）
        CaravanEnterMapUtility.Enter(caravan, map, CaravanEnterMode.Edge, CaravanDropInventoryMode.DoNotDrop, true);

        // 3. 全局通知
        Find.LetterStack.ReceiveLetter(
            "夜襲開始", 
            "你的部隊藉著夜色潛入了敵方前哨站。大部分守衛都在睡夢中，這是一個絕佳的機會！", 
            LetterDefOf.PositiveEvent, 
            this
        );
    }
}

/// <summary>
/// 實戰範例：偷襲地圖設置步驟。
/// 這是偷襲的核心邏輯——讓敵人變弱。
/// </summary>
public class GenStep_SneakAttackSetup : GenStep
{
    public override int SeedPart => 987654321;

    public override void Generate(Map map, GenStepParams parms)
    {
        List<Pawn> guards = map.mapPawns.AllPawnsSpawned.Where(p => p.Faction != null && p.Faction.HostileTo(Faction.OfPlayer)).ToList();
        
        // 隨機挑選 1-2 名「哨兵」，他們保持清醒並具備更高的偵測能力
        int sentryCount = Rand.RangeInclusive(1, 2);
        for (int i = 0; i < sentryCount && guards.Any(); i++)
        {
            Pawn sentry = guards.RandomElement();
            guards.Remove(sentry);
            // 哨兵保持清醒並巡邏中心區域
            sentry.mindState.duty = new PawnDuty(DutyDefOf.DefendBase, map.Center, 20f);
            FleckMaker.ThrowMetaIcon(sentry.Position, map, FleckDefOf.PsycastAreaEffect);
        }

        // 其餘守衛全部睡著
        foreach (Pawn pawn in guards)
        {
            if (pawn.needs.rest != null)
            {
                pawn.needs.rest.CurLevel = 0f; // 強制睡眠
            }

            // 施加「驚愕」狀態 (尚未醒來，所以此狀態暫時不會生效直到醒來)
            pawn.health.AddHediff(DefDatabase<HediffDef>.GetNamed("MyMod_SneakAttackSurprise"));

            // 傳送到床上
            Building_Bed bed = (Building_Bed)GenClosest.ClosestThingReachable(pawn.Position, map, ThingRequest.ForDef(ThingDefOf.Bed), Verse.AI.PathEndMode.OnCell, TraverseParms.For(pawn));
            if (bed != null && !bed.Occupied) pawn.Position = bed.Position;
        }
    }
}

/// <summary>
/// 實戰範例：偷襲管理器。
/// 監控地圖上的噪音與視覺，決定是否觸發警報。
/// </summary>
public class MapComponent_SneakAttackManager : MapComponent
{
    private bool alarmSounded = false;
    private float detectionMeter = 0f;
    private const float MaxDetection = 100f;

    public MapComponent_SneakAttackManager(Map map) : base(map) { }

    public override void ExposeData()
    {
        base.ExposeData();
        Scribe_Values.Look(ref alarmSounded, "alarmSounded", false);
        Scribe_Values.Look(ref detectionMeter, "detectionMeter", 0f);
    }

    public override void MapComponentTick()
    {
        base.MapComponentTick();
        if (alarmSounded) return;

        // 每 30 Ticks 檢查一次隱密狀態
        if (map.IsHashIntervalTick(30))
        {
            CheckDetection();
        }
    }

    private void CheckDetection()
    {
        // 1. 偵測小人視線
        foreach (Pawn colonist in map.mapPawns.FreeColonistsSpawned)
        {
            foreach (Pawn enemy in map.mapPawns.AllPawnsSpawned.Where(p => p.Faction != null && p.Faction.HostileTo(Faction.OfPlayer)))
            {
                // 如果敵方哨兵清醒且能看見小人
                if (!enemy.Downed && enemy.Awake() && enemy.CanSee(colonist))
                {
                    detectionMeter += 15f; // 快速增加偵測值
                    MoteMaker.ThrowText(enemy.DrawPos, map, "!!!", Color.red);
                }
            }
        }

        // 2. 槍聲監控 (此處為簡化邏輯，實際應掛鉤在 DamageInfo 或 Verb_LaunchProjectile)
        // 假設如果檢測到正在發生戰鬥且有開火
        if (map.battleLog.RawLogs.Any(log => (Find.TickManager.TicksGame - log.Timestamp) < 30))
        {
             detectionMeter += 10f;
        }

        // 3. 觸發警報
        if (detectionMeter >= MaxDetection)
        {
            TriggerAlarm();
        }
    }

    public void TriggerAlarm()
    {
        if (alarmSounded) return;
        alarmSounded = true;

        Messages.Message("警報響起！你的行動已被敵軍察覺！", MessageTypeDefOf.ThreatBig);
        SoundDefOf.Ambient_Alert_Red.PlayOneShotOnCamera(map);

        // 強制所有敵人醒來並攻擊
        foreach (Pawn enemy in map.mapPawns.AllPawnsSpawned.Where(p => p.Faction != null && p.Faction.HostileTo(Faction.OfPlayer)))
        {
            if (enemy.needs.rest != null) enemy.needs.rest.CurLevel = 1.0f; // 瞬間清醒
            enemy.jobs.EndCurrentJob(Verse.AI.JobCondition.InterruptForced); // 打斷睡眠
            enemy.mindState.duty = new PawnDuty(DutyDefOf.HuntEnemiesIndividual);
        }
    }

    public override void MapComponentOnGUI()
    {
        base.MapComponentOnGUI();
        if (!alarmSounded && detectionMeter > 0)
        {
            // 在螢幕一角繪製簡單的偵測條
            Rect rect = new Rect(200f, 10f, 200f, 30f);
            Widgets.FillableBar(rect, detectionMeter / MaxDetection, Color.yellow, Color.black, true);
            Text.Anchor = TextAnchor.MiddleCenter;
            Widgets.Label(rect, "隱密偵測中...");
            Text.Anchor = TextAnchor.UpperLeft;
        }
    }
}
