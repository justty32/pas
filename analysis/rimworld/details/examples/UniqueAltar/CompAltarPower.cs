using Verse;
using RimWorld;
using UnityEngine;
using System.Collections.Generic;
using System.Linq;

namespace MyMod.Examples;

/// <summary>
/// 實戰範例：強化版祭壇組件。
/// 支持能量積累、引導儀式、動態視覺效果以及多樣化的祭典結果。
/// </summary>
public class CompAltarPower : ThingComp
{
    private float currentEnergy = 0f;
    private bool isActivated = false;

    public CompProperties_AltarPower Props => (CompProperties_AltarPower)props;
    public float EnergyPct => currentEnergy / Props.maxEnergy;

    public override void PostExposeData()
    {
        base.PostExposeData();
        Scribe_Values.Look(ref currentEnergy, "currentEnergy", 0f);
        Scribe_Values.Look(ref isActivated, "isActivated", false);
    }

    public void AddEnergy(float amount)
    {
        if (isActivated) return;
        currentEnergy = Mathf.Clamp(currentEnergy + amount, 0f, Props.maxEnergy);
        
        // 能量每增加 10%，更新一次地圖亮度 (強迫重新渲染 Glow)
        if (Mathf.FloorToInt(currentEnergy) % 10 == 0)
        {
            parent.Map?.glowGrid.MarkGlowGridDirty(parent.Position);
        }
    }

    /// <summary>
    /// 動態改變發光強度。
    /// </summary>
    public override void CompTick()
    {
        base.CompTick();
        if (parent.IsHashIntervalTick(60) && currentEnergy > 0)
        {
            // 在祭壇周圍產生環境特效，能量越高特效越密集
            if (Rand.Value < EnergyPct)
            {
                FleckMaker.ThrowMetaIcon(parent.Position, parent.Map, Props.fleckDef ?? FleckDefOf.PsycastAreaEffect);
            }
        }
    }

    public override IEnumerable<Gizmo> CompGetGizmosExtra()
    {
        // 儀式引導按鈕
        if (!isActivated && currentEnergy < Props.maxEnergy)
        {
            yield return new Command_Action
            {
                defaultLabel = "開始祭禮引導",
                defaultDesc = "指派一名小人在此引導祭壇能量。",
                icon = ContentFinder<Texture2D>.Get("UI/Icons/StudyPath"),
                action = () => {
                    // 打開小人選擇器 (簡單起見，這裡假設點擊後直接讓選中小人執行)
                    Pawn p = Find.Selector.SingleSelectedThing as Pawn;
                    if (p != null && p.IsColonistPlayerControlled)
                    {
                        Job job = JobMaker.MakeJob(DefDatabase<JobDef>.GetNamed("MyMod_PerformAltarRitual"), parent);
                        p.jobs.TryTakeOrderedJob(job);
                    }
                    else
                    {
                        Messages.Message("請先選中一名殖民者。", MessageTypeDefOf.RejectInput);
                    }
                }
            };
        }

        // 觸發祭壇能量
        if (currentEnergy >= Props.maxEnergy && !isActivated)
        {
            yield return new Command_Action
            {
                defaultLabel = "釋放祭壇能量",
                defaultDesc = "釋放累積的靈能，引發巨大的變革。",
                icon = ContentFinder<Texture2D>.Get("UI/Icons/SpecialAbilities/AnimaTree"),
                action = () => ActivateAltar()
            };
        }
    }

    private void ActivateAltar()
    {
        isActivated = true;
        Map map = parent.Map;

        // 全螢幕震撼與音效
        Find.CameraDriver.shaker.DoShake(2.0f);
        SoundDefOf.PsychicPulseGlobal.PlayOneShotOnCamera(map);
        FleckMaker.Static(parent.Position, map, FleckDefOf.PsycastAreaEffect, 15f);

        // 根據類型執行不同邏輯
        switch (Props.type)
        {
            case AltarType.Healing:
                ApplyHealing(map);
                break;
            case AltarType.Destruction:
                ApplyDestruction(map);
                break;
        }

        Messages.Message($"祭壇發出了耀眼的光芒，{Props.ritualLetterLabel} 已經完成！", MessageTypeDefOf.PositiveEvent);
        
        // 釋放完畢後祭壇損毀或進入冷卻
        parent.Destroy();
    }

    private void ApplyHealing(Map map)
    {
        foreach (Pawn pawn in map.mapPawns.AllPawnsSpawned)
        {
            if (pawn.RaceProps.IsFlesh)
            {
                // 1. 治癒所有輕微傷口
                pawn.health.hediffSet.hediffs.RemoveAll(h => h is Hediff_Injury && h.Severity < 10);
                
                // 2. 施加祭壇祝禱 (Hediff)
                pawn.health.AddHediff(DefDatabase<HediffDef>.GetNamed("MyMod_AltarBlessing"));
                
                // 3. 特效
                FleckMaker.AttachedStatic(pawn, FleckDefOf.PsycastAreaEffect, Vector3.zero);
            }
        }
    }

    private void ApplyDestruction(Map map)
    {
        // 1. 觸發雷暴
        map.gameConditionManager.RegisterCondition(GameConditionMaker.MakeCondition(GameConditionDefOf.Flashstorm, 15000));
        
        // 2. 在祭壇周圍引發連環爆炸 (僅針對敵對目標)
        IEnumerable<Thing> enemies = map.listerThings.AllThings.Where(t => t.Faction != null && t.Faction.HostileTo(Faction.OfPlayer));
        foreach (Thing enemy in enemies.Take(10))
        {
            GenExplosion.DoExplosion(enemy.Position, map, 3.9f, DamageDefOf.Bomb, null);
        }
    }

    public override string CompInspectStringExtra()
    {
        return $"能量儲備: {currentEnergy:F1} / {Props.maxEnergy} ({EnergyPct:P0})";
    }
}
