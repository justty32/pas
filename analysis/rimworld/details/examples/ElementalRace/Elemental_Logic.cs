using Verse;
using RimWorld;
using UnityEngine;
using System.Collections.Generic;
using System.Linq;

namespace MyMod.Examples;

// ==========================================
// 1. 混沌火焰效果 (Hediff)
// ==========================================

/// <summary>
/// 混沌火焰的狀態效果：隨機引發痛苦或功能障礙。
/// </summary>
public class Hediff_ChaosBurn : HediffWithComps
{
    public override void Tick()
    {
        base.Tick();
        
        // 每隔 500 Ticks (約 8 秒) 有機率引發隨機效應
        if (pawn.IsHashIntervalTick(500) && Rand.Value < 0.2f)
        {
            ApplyChaosEffect();
        }
    }

    private void ApplyChaosEffect()
    {
        int effectType = Rand.Range(0, 3);
        switch (effectType)
        {
            case 0: // 短暫眩暈
                pawn.stances.stunner.StunFor(120, pawn);
                MoteMaker.ThrowText(pawn.DrawPos, pawn.Map, "混亂！", Color.magenta);
                break;
            case 1: // 劇痛加深
                pawn.health.AddHediff(HediffDefOf.PsychicHangover);
                break;
            case 2: // 傳送 (混沌特性：隨機小幅度位移)
                IntVec3 targetCell = CellFinder.RandomClosewalkCellNear(pawn.Position, pawn.Map, 3);
                pawn.Position = targetCell;
                pawn.pather.StopDead();
                FleckMaker.ThrowMetaIcon(pawn.Position, pawn.Map, FleckDefOf.PsycastAreaEffect);
                break;
        }
    }
}

// ==========================================
// 2. 技能組件 (Ability Comps)
// ==========================================

/// <summary>
/// 召喚閃電效果。
/// </summary>
public class CompProperties_AbilityLightningStrike : CompProperties_AbilityEffect { }
public class CompAbilityEffect_LightningStrike : CompAbilityEffect
{
    public override void Apply(LocalTargetInfo target, LocalTargetInfo dest)
    {
        base.Apply(target, dest);
        map.weatherManager.eventHandler.AddEvent(new WeatherEvent_LightningStrike(map, target.Cell));
    }
}

/// <summary>
/// 呼吸攻擊：混沌火焰。
/// </summary>
public class CompProperties_AbilityChaosBreath : CompProperties_AbilityEffect
{
    public float range = 8f;
    public float coneAngle = 45f;
    public CompProperties_AbilityChaosBreath() => compClass = typeof(CompAbilityEffect_ChaosBreath);
}

public class CompAbilityEffect_ChaosBreath : CompAbilityEffect
{
    public new CompProperties_AbilityChaosBreath Props => (CompProperties_AbilityChaosBreath)props;

    public override void Apply(LocalTargetInfo target, LocalTargetInfo dest)
    {
        base.Apply(target, dest);
        Pawn caster = parent.pawn;
        Vector3 direction = (target.CenterVector3 - caster.DrawPos).normalized;
        float centerAngle = direction.AngleFlat();

        // 獲取錐形範圍內的所有目標
        IEnumerable<Pawn> targets = map.mapPawns.AllPawnsSpawned.Where(p => 
            p != caster && 
            p.Position.DistanceTo(caster.Position) <= Props.range &&
            Mathf.Abs(Mathf.DeltaAngle(centerAngle, (p.DrawPos - caster.DrawPos).AngleFlat())) < Props.coneAngle / 2f
        );

        foreach (Pawn p in targets)
        {
            // 造成火焰傷害並施加混沌 Hediff
            p.TakeDamage(new DamageInfo(DamageDefOf.Burn, 15, 0.5f, -1, caster));
            p.health.AddHediff(DefDatabase<HediffDef>.GetNamed("MyMod_Hediff_ChaosBurn"));
            
            // 視覺效果：紫色的火花
            FleckMaker.ThrowMicroSparks(p.DrawPos, map);
        }

        // 噴射路徑上的視覺特效
        for (int i = 0; i < 5; i++)
        {
            Vector3 effectPos = caster.DrawPos + direction * (i * 1.5f);
            FleckMaker.ThrowAirPuff(effectPos, map);
        }
    }
}

/// <summary>
/// 生成牆壁效果 (冰牆/火牆)。
/// </summary>
public class CompProperties_AbilitySpawnWall : CompProperties_AbilityEffect
{
    public ThingDef wallDef;
    public int width = 3;
    public CompProperties_AbilitySpawnWall() => compClass = typeof(CompAbilityEffect_SpawnWall);
}

public class CompAbilityEffect_SpawnWall : CompAbilityEffect
{
    public new CompProperties_AbilitySpawnWall Props => (CompProperties_AbilitySpawnWall)props;

    public override void Apply(LocalTargetInfo target, LocalTargetInfo dest)
    {
        base.Apply(target, dest);
        IntVec3 center = target.Cell;
        Pawn caster = parent.pawn;
        
        // 根據施放方向決定牆壁的橫向延伸
        Vector3 dir = (target.CenterVector3 - caster.DrawPos).normalized;
        IntVec3 sideDir = new IntVec2(Mathf.RoundToInt(-dir.z), Mathf.RoundToInt(dir.x)).ToIntVec3;

        int halfWidth = Props.width / 2;
        for (int i = -halfWidth; i <= halfWidth; i++)
        {
            IntVec3 cell = center + sideDir * i;
            if (cell.InBounds(map) && cell.Walkable(map))
            {
                GenSpawn.Spawn(Props.wallDef, cell, map);
                FleckMaker.ThrowAirPuff(cell.ToVector3Shifted(), map);
            }
        }
    }
}

/// <summary>
/// 火牆燃燒組件：讓站上去的小人著火。
/// </summary>
public class CompProperties_FireWallBurn : CompProperties { }
public class CompFireWallBurn : ThingComp
{
    public override void CompTick()
    {
        base.CompTick();
        if (parent.IsHashIntervalTick(60)) // 每秒檢查一次
        {
            foreach (Thing t in parent.Position.GetThingList(parent.Map))
            {
                if (t is Pawn p && !p.Downed)
                {
                    p.TryAttachFire(0.5f);
                }
            }
        }
    }
}
