using System.Collections.Generic;
using Verse;

namespace ColonyArchivalOutpost
{
    // 採樣結果：每種資源的「每日有號淨流」(正=產出投遞回主基地, 負=從哨站庫存緩衝消耗)。
    // 封存當下算好、隨 Outpost_Sampled 存檔。
    public class ProductivitySnapshot : IExposable
    {
        public Dictionary<ThingDef, float> dailyRates = new Dictionary<ThingDef, float>();

        // N4：per-pawn 縮放。perPawnScaling=true 時 dailyRates 仍存絕對速率，
        // 但 basePawnCount 記錄封存當下殖民者數，產出用 AmountPerPawn 配合 VOE 縮放，消耗乘當前 PawnCount。
        public bool perPawnScaling;
        public int basePawnCount = 1;

        public ProductivitySnapshot() { }

        public ProductivitySnapshot(Dictionary<ThingDef, float> rates)
        {
            dailyRates = rates ?? new Dictionary<ThingDef, float>();
        }

        public bool IsEmpty => dailyRates == null || dailyRates.Count == 0;

        public void ExposeData()
        {
            Scribe_Collections.Look(ref dailyRates, "dailyRates", LookMode.Def, LookMode.Value);
            Scribe_Values.Look(ref perPawnScaling, "perPawnScaling", false);
            Scribe_Values.Look(ref basePawnCount, "basePawnCount", 1);
            if (Scribe.mode == LoadSaveMode.PostLoadInit && dailyRates == null)
                dailyRates = new Dictionary<ThingDef, float>();
        }
    }
}
