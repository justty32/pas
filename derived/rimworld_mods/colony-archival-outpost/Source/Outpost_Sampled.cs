using System.Collections.Generic;
using Outposts;
using UnityEngine;
using Verse;

namespace ColonyArchivalOutpost
{
    // 採樣封存而成的抽象哨站：
    //  - 正成長：override ResultOptions → VOE base.Produce()/Deliver() 照玩家全域 DeliveryMethod 投遞
    //    （預設 Teleport = 送回最近主基地，同普通 VOE 產出型哨站）。
    //  - 負成長：override Produce()，每週期用公開 TakeItems 從 containedItems 緩衝扣，扣到 0 為止。
    public class Outpost_Sampled : Outpost
    {
        private ProductivitySnapshot snapshot = new ProductivitySnapshot();

        public void SetSnapshot(ProductivitySnapshot s) => snapshot = s ?? new ProductivitySnapshot();

        public override List<ResultOption> ResultOptions
        {
            get
            {
                var list = new List<ResultOption>();
                if (snapshot == null || snapshot.IsEmpty) return list;
                float daysPerCycle = TicksPerProduction / 60000f; // GenDate.TicksPerDay
                foreach (var kv in snapshot.dailyRates)
                {
                    if (kv.Value <= 0f) continue; // 只有正成長走產出投遞
                    int amount = Mathf.RoundToInt(kv.Value * daysPerCycle);
                    if (amount <= 0) continue;
                    list.Add(new ResultOption { Thing = kv.Key, BaseAmount = amount, AmountPerPawn = 0, AmountsPerSkills = null });
                }
                return list;
            }
        }

        public override void Produce()
        {
            if (snapshot != null && !snapshot.IsEmpty)
            {
                float daysPerCycle = TicksPerProduction / 60000f;
                foreach (var kv in snapshot.dailyRates)
                {
                    if (kv.Value >= 0f) continue; // 只處理負成長
                    int want = Mathf.RoundToInt(-kv.Value * daysPerCycle);
                    if (want <= 0) continue;
                    // VOE 公開 API：從 containedItems 取出最多 want 個；不足則取到 0。取出即消耗，Destroy 之。
                    List<Thing> removed = TakeItems(kv.Key, want);
                    if (removed == null) continue;
                    foreach (var t in removed)
                        if (t != null && !t.Destroyed) t.Destroy();
                }
            }
            base.Produce(); // 產出正成長並依玩家全域 DeliveryMethod 投遞
        }

        public override void ExposeData()
        {
            base.ExposeData();
            Scribe_Deep.Look(ref snapshot, "caoSnapshot");
            if (Scribe.mode == LoadSaveMode.PostLoadInit && snapshot == null)
                snapshot = new ProductivitySnapshot();
        }
    }
}
