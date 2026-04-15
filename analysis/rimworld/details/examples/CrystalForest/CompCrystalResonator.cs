using Verse;
using RimWorld;
using UnityEngine;
using System.Collections.Generic;
using System.Linq;

namespace MyMod.Examples;

/// <summary>
/// 實戰範例：水晶共鳴器屬性。
/// </summary>
public class CompProperties_CrystalResonator : CompProperties
{
    public float radius = 6f;
    public float chargeRatePerTick = 0.05f;

    public CompProperties_CrystalResonator()
    {
        compClass = typeof(CompCrystalResonator);
    }
}

/// <summary>
/// 實戰範例：水晶共鳴器組件。
/// 為周圍的玩家機器人提供無線充電。
/// </summary>
public class CompCrystalResonator : ThingComp
{
    public CompProperties_CrystalResonator Props => (CompProperties_CrystalResonator)props;

    private CompPowerTrader powerTrader;

    public override void PostSpawnSetup(bool respawningAfterLoad)
    {
        base.PostSpawnSetup(respawningAfterLoad);
        powerTrader = parent.TryGetComp<CompPowerTrader>();
    }

    public override void CompTick()
    {
        base.CompTick();

        // 1. 只有在有電的情況下才運作
        if (powerTrader == null || !powerTrader.PowerOn) return;

        // 2. 每 30 Ticks 掃描一次，節省效能
        if (parent.IsHashIntervalTick(30))
        {
            ChargeNearbyMechs();
        }
    }

    private void ChargeNearbyMechs()
    {
        Map map = parent.Map;
        IEnumerable<Pawn> nearbyMechs = map.mapPawns.AllPawnsSpawned.Where(p => 
            p.RaceProps.IsMechanoid && 
            p.Faction == parent.Faction && 
            p.Position.InHorDistOf(parent.Position, Props.radius)
        );

        foreach (Pawn mech in nearbyMechs)
        {
            // 3. 嘗試獲取能量需求 (Biotech DLC 內容)
            Need_Energy energyNeed = mech.needs.TryGetNeed<Need_Energy>();
            if (energyNeed != null && energyNeed.CurLevel < energyNeed.MaxLevel)
            {
                // 執行充電 (30 Ticks 的累積量)
                energyNeed.CurLevel += Props.chargeRatePerTick * 30;

                // 4. 視覺特效：紫色能量閃爍
                FleckMaker.AttachedStatic(mech, FleckDefOf.PsycastAreaEffect, Vector3.zero);
                
                // 偶爾在共鳴器與機器人間拋出一個粒子
                if (Rand.Value < 0.1f)
                {
                    MoteMaker.ThrowLightningGlow(mech.DrawPos, map, 0.5f);
                }
            }
        }
    }

    public override void PostDraw()
    {
        base.PostDraw();
        
        // 5. 繪製影響半徑 (當選中時)
        if (Find.Selector.IsSelected(parent))
        {
            GenDraw.DrawRadiusRing(parent.Position, Props.radius);
        }
    }

    public override string CompInspectStringExtra()
    {
        return $"狀態: 能量共鳴中\n無線充電範圍: {Props.radius} 格";
    }
}
