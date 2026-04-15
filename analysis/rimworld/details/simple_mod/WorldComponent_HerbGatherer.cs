using System.Collections.Generic;
using RimWorld;
using RimWorld.Planet;
using Verse;

namespace MyMod;

/// <summary>
/// 全局世界組件：負責處理商隊在旅行中自動採藥的邏輯。
/// </summary>
public class WorldComponent_HerbGatherer : WorldComponent
{
    private const int GatherInterval = 60000; // 每天執行一次 (6萬 Ticks)

    public WorldComponent_HerbGatherer(World world) : base(world) { }

    public override void WorldComponentTick()
    {
        base.WorldComponentTick();

        // 使用 HashIntervalTick 優化效能，避免每幀遍歷所有商隊
        if (Find.TickManager.TicksGame % GatherInterval == 0)
        {
            TryGatherHerbsForCaravans();
        }
    }

    private void TryGatherHerbsForCaravans()
    {
        List<Caravan> caravans = Find.WorldObjects.Caravans;
        for (int i = 0; i < caravans.Count; i++)
        {
            Caravan caravan = caravans[i];
            
            // 1. 地形檢查：必須在有植物的地形
            Tile tile = Find.WorldGrid[caravan.Tile];
            if (tile.biome.plantDensity <= 0.1f) continue;

            // 2. 技能檢查：尋找最高種植技能的小人
            float bestSkill = 0f;
            foreach (Pawn p in caravan.PawnsListForReading)
            {
                if (p.skills != null)
                {
                    float level = p.skills.GetSkill(SkillDefOf.Plants).Level;
                    if (level > bestSkill) bestSkill = level;
                }
            }

            // 3. 獲取獎勵 (假設技能等級越高，採到的機率與數量越高)
            if (Rand.Chance(bestSkill * 0.05f)) // 20級種植有 100% 機率
            {
                int count = Rand.Range(1, (int)(bestSkill / 3) + 1);
                Thing herbs = ThingMaker.MakeThing(ThingDefOf.HerbalMedicine);
                herbs.stackCount = count;

                // 直接加入商隊庫存
                CaravanInventoryUtility.GiveThing(caravan, herbs);
                
                // 發送通知 (選配)
                Messages.Message($"{caravan.Label} 的成員在途中採集到了 {count} 株草藥。", 
                    caravan, MessageTypeDefOf.PositiveEvent);
            }
        }
    }
}
