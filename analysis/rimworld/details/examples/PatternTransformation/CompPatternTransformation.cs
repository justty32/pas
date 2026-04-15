using Verse;
using RimWorld;
using UnityEngine;
using System.Collections.Generic;
using System.Linq;

namespace MyMod.Examples;

public class CompProperties_PatternTransformation : CompProperties
{
    public CompProperties_PatternTransformation()
    {
        compClass = typeof(CompPatternTransformation);
    }
}

/// <summary>
/// 實戰範例：圖案轉化組件。
/// 檢測周圍的空間佈局，如果符合特定圖案，則將自身轉化為黃金。
/// </summary>
public class CompPatternTransformation : ThingComp
{
    private bool hasTransmuted = false;

    public override void PostExposeData()
    {
        base.PostExposeData();
        Scribe_Values.Look(ref hasTransmuted, "hasTransmuted", false);
    }

    /// <summary>
    /// 提供一個手動檢測按鈕，方便玩家確認儀式。
    /// </summary>
    public override IEnumerable<FloatMenuOption> CompGetFloatMenuOptions(Pawn selPawn)
    {
        if (hasTransmuted) yield break;

        yield return new FloatMenuOption("檢索符文共鳴", () =>
        {
            if (CheckPattern(out string reason))
            {
                TransformToGold();
            }
            else
            {
                Messages.Message($"儀式失敗：{reason}", MessageTypeDefOf.RejectInput);
            }
        });
    }

    /// <summary>
    /// 每 250 Ticks 自動檢查一次，實現自動轉化。
    /// </summary>
    public override void CompTick()
    {
        base.CompTick();
        if (!hasTransmuted && parent.IsHashIntervalTick(250))
        {
            if (CheckPattern(out _))
            {
                TransformToGold();
            }
        }
    }

    /// <summary>
    /// 核心邏輯：檢查 3x3 圖案。
    /// 需求：
    /// 1. 雕像下方的 3x3 必須全是「符文銀磚 (MyMod_RunicFloor)」。
    /// 2. 四個對角線角落必須放置「銀質柱子 (Column, Stuff: Silver)」。
    /// </summary>
    private bool CheckPattern(out string failReason)
    {
        Map map = parent.Map;
        IntVec3 center = parent.Position;

        // 1. 檢查 3x3 的地板
        for (int x = -1; x <= 1; x++)
        {
            for (int z = -1; z <= 1; z++)
            {
                IntVec3 cell = center + new IntVec3(x, 0, z);
                TerrainDef terrain = map.terrainGrid.TerrainAt(cell);
                if (terrain.defName != "MyMod_RunicFloor")
                {
                    failReason = "地板圖案不完整。3x3 區域必須全部舖設符文銀磚。";
                    return false;
                }
            }
        }

        // 2. 檢查四角柱子 (偏移量: (-1, -1), (-1, 1), (1, -1), (1, 1))
        IntVec3[] cornerOffsets = new IntVec3[] {
            new IntVec3(-1, 0, -1), new IntVec3(-1, 0, 1),
            new IntVec3(1, 0, -1), new IntVec3(1, 0, 1)
        };

        foreach (var offset in cornerOffsets)
        {
            IntVec3 cell = center + offset;
            Thing building = cell.GetFirstBuilding(map);
            
            // 檢查是否為柱子且材質為銀
            if (building == null || building.def != ThingDefOf.Column || building.Stuff != ThingDefOf.Silver)
            {
                failReason = "能量溢散。四個對角線角落必須放置銀質柱子。";
                return false;
            }
        }

        failReason = "";
        return true;
    }

    private void TransformToGold()
    {
        hasTransmuted = true;

        // 1. 修改材質為黃金 (Stuff)
        // 在 RimWorld 中，Stuff 直接決定了外觀顏色和數值
        parent.SetStuffDirect(ThingDefOf.Gold);

        // 2. 視覺特效與音效
        FleckMaker.Static(parent.Position, parent.Map, FleckDefOf.PsycastAreaEffect, 10f);
        SoundDefOf.PsychicPulseGlobal.PlayOneShot(new TargetInfo(parent.Position, parent.Map));

        // 3. 重新通知渲染引擎更新模型外觀
        parent.DirtyMapMesh(parent.Map);
        parent.Map.glowGrid.MarkGlowGridDirty(parent.Position); // 如果是發光物體

        // 4. 拋出「點石成金」文字特效
        MoteMaker.ThrowText(parent.DrawPos, parent.Map, "點石成金！", Color.yellow);
        
        Messages.Message("在一陣強烈的靈能波動中，平凡的石材昇華為了永恆的黃金！", MessageTypeDefOf.PositiveEvent);
    }
}
