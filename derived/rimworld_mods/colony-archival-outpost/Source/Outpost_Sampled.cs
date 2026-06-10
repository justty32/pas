using System;
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
        public string chosenIconPath; // N3：玩家選定的世界地圖圖標路徑（如 "WorldObjects/OutpostMining"）

        // 渲染用的是 ExpandingMaterial（非 ExpandingIcon），須 override 此處才能換圖。
        // ExpandingMaterial 以 def.ExpandingIconTexture 建 material 並 cache，不呼叫 ExpandingIcon。
        public override Material ExpandingMaterial
        {
            get
            {
                if (!chosenIconPath.NullOrEmpty() && def.expandingShader != null)
                {
                    Texture2D tex = ContentFinder<Texture2D>.Get(chosenIconPath, false);
                    if (tex != null)
                        return MaterialPool.MatFrom(new MaterialRequest
                        {
                            mainTex = tex,
                            shader = def.expandingShader.Shader,
                            color = Color.white,
                            maskTex = def.ExpandingIconTextureMask
                        });
                }
                return base.ExpandingMaterial;
            }
        }

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
                    if (snapshot.perPawnScaling)
                    {
                        // N4：per-pawn 模式——AmountPerPawn 由 VOE Amount(CapablePawns) 自動乘以當前 pawn 數縮放。
                        int perPawnAmt = RateToInt(kv.Value / snapshot.basePawnCount, daysPerCycle);
                        if (perPawnAmt <= 0) continue;
                        list.Add(new ResultOption { Thing = kv.Key, BaseAmount = 0, AmountPerPawn = perPawnAmt, AmountsPerSkills = null });
                    }
                    else
                    {
                        int amount = RateToInt(kv.Value, daysPerCycle);
                        if (amount <= 0) continue;
                        list.Add(new ResultOption { Thing = kv.Key, BaseAmount = amount, AmountPerPawn = 0, AmountsPerSkills = null });
                    }
                }
                return list;
            }
        }

        public override void Produce()
        {
            if (snapshot != null && !snapshot.IsEmpty)
            {
                float daysPerCycle = TicksPerProduction / 60000f;

                /* 全有全無：任一負成長緩衝不足 → 本週期不扣料且跳過所有正成長產出
                 * 這是特性，不是 bug，玩得開心！
                 * 啟用方式：取消此 block 注解，並在檔案頂部加 using System.Linq;
                bool allSatisfied = true;
                foreach (var kv in snapshot.dailyRates)
                {
                    if (kv.Value >= 0f) continue;
                    int want = RateToInt(-kv.Value, daysPerCycle);
                    if (want <= 0) continue;
                    // Things 是 VOE Outpost 公開屬性（IEnumerable<Thing>），對應 containedItems
                    int available = 0;
                    foreach (var t in Things) if (t.def == kv.Key) available += t.stackCount;
                    if (available < want) { allSatisfied = false; break; }
                }
                if (!allSatisfied) return;
                */

                foreach (var kv in snapshot.dailyRates)
                {
                    if (kv.Value >= 0f) continue; // 只處理負成長
                    // N4：per-pawn 模式——消耗量依當前 pawn 數縮放（與 ResultOptions 正成長對稱）。
                    int want = snapshot.perPawnScaling
                        ? RateToInt(-kv.Value / snapshot.basePawnCount, daysPerCycle) * PawnCount
                        : RateToInt(-kv.Value, daysPerCycle);
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

        // double 計算再 clamp，防止極端速率 × 週期倍數超出 int32 範圍
        private static int RateToInt(float rate, float days)
        {
            double v = (double)rate * days;
            if (v >= int.MaxValue) return int.MaxValue;
            if (v <= 0.0) return 0;
            return (int)Math.Round(v);
        }

        public override void ExposeData()
        {
            base.ExposeData();
            Scribe_Deep.Look(ref snapshot, "caoSnapshot");
            Scribe_Values.Look(ref chosenIconPath, "caoIconPath", null);
            if (Scribe.mode == LoadSaveMode.PostLoadInit && snapshot == null)
                snapshot = new ProductivitySnapshot();
        }
    }
}
