using System;
using System.Collections.Generic;
using System.Linq;
using Outposts;
using RimWorld;
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
                    List<Thing> removed = TakeItems(kv.Key, want);
                    if (removed == null) continue;
                    foreach (var t in removed)
                        if (t != null && !t.Destroyed) t.Destroy();
                }

                // N6b：非傷勢 hediff 採樣——每週期對 occupants 施加 hediff severity 變化
                if (snapshot.applyHediffDeltas && snapshot.dailyHediffDeltas?.Count > 0)
                {
                    foreach (var pawn in AllPawns.ToList())
                        ApplyHediffDeltasToPawn(pawn, snapshot.dailyHediffDeltas, daysPerCycle);
                }

                // N6：傷勢治癒——每週期治癒 occupants 的可癒傷傷勢
                if (snapshot.applyHealthDelta && snapshot.avgHealthDeltaPerDay < 0f)
                {
                    float healPerCycle = -snapshot.avgHealthDeltaPerDay * daysPerCycle;
                    foreach (var pawn in AllPawns.ToList())
                        ApplyHealingToPawn(pawn, healPerCycle);
                }

                // N6 壞傷勢——每週期惡化 occupants 的可癒傷傷勢
                if (snapshot.applyHealthDeterioration && snapshot.avgHealthDeltaPerDay > 0f)
                {
                    float deterioratePerCycle = snapshot.avgHealthDeltaPerDay * daysPerCycle;
                    foreach (var pawn in AllPawns.ToList())
                        ApplyDeteriorationToPawn(pawn, deterioratePerCycle);
                }

                // N7：技能採樣——每週期對 occupants 施加技能 XP（direct=true：只乘 occupant 自身 passion，不計 GlobalLearningFactor/飽和）
                if (snapshot.applySkillXP && snapshot.dailySkillXP?.Count > 0)
                {
                    var pawnList = AllPawns.ToList();
                    foreach (var kv in snapshot.dailySkillXP)
                    {
                        float xpPerCycle = kv.Value * daysPerCycle;
                        if (xpPerCycle == 0f) continue;
                        foreach (var pawn in pawnList)
                        {
                            if (pawn.skills == null) continue;
                            SkillRecord skill = pawn.skills.GetSkill(kv.Key);
                            if (skill == null || skill.TotallyDisabled) continue;
                            skill.Learn(xpPerCycle, direct: true);
                        }
                    }
                }
            }

            base.Produce(); // 產出正成長並依玩家全域 DeliveryMethod 投遞
        }

        // N6：按比例分配 totalHealAmount 到各可癒傷口，使用官方 Heal() 路徑
        private static void ApplyHealingToPawn(Pawn pawn, float totalHealAmount)
        {
            var injuries = new List<Hediff_Injury>();
            foreach (var h in pawn.health.hediffSet.hediffs)
                if (h is Hediff_Injury hd && hd.CanHealNaturally() && hd.Severity > 0f)
                    injuries.Add(hd);
            if (injuries.Count == 0) return;
            float totalSev = 0f;
            foreach (var h in injuries) totalSev += h.Severity;
            if (totalSev <= 0f) return;
            var toRemove = new List<Hediff>();
            foreach (var h in injuries)
            {
                h.Heal(totalHealAmount * (h.Severity / totalSev));
                if (h.ShouldRemove) toRemove.Add(h);
            }
            foreach (var h in toRemove) pawn.health.RemoveHediff(h);
        }

        // N6 壞傷勢：按比例分配 totalDeteriorate 到各可癒傷口，加重 severity
        private static void ApplyDeteriorationToPawn(Pawn pawn, float totalDeteriorate)
        {
            var injuries = new List<Hediff_Injury>();
            foreach (var h in pawn.health.hediffSet.hediffs)
                if (h is Hediff_Injury hd && hd.CanHealNaturally() && hd.Severity > 0f)
                    injuries.Add(hd);
            if (injuries.Count == 0) return;
            float totalSev = 0f;
            foreach (var h in injuries) totalSev += h.Severity;
            if (totalSev <= 0f) return;
            foreach (var h in injuries)
                h.Severity += totalDeteriorate * (h.Severity / totalSev);
        }

        // N6b：按速率對每個 pawn 的非傷勢 hediff 施加 severity 變化（正=加重/新增，負=消退）
        private static void ApplyHediffDeltasToPawn(Pawn pawn, Dictionary<HediffDef, float> dailyDeltas, float days)
        {
            foreach (var kv in dailyDeltas)
            {
                // 缺損（MissingPart）需要 BodyPartRecord 才能正確建立，無法安全套用，略過
                if (kv.Key?.hediffClass != null && typeof(Hediff_MissingPart).IsAssignableFrom(kv.Key.hediffClass))
                    continue;
                float delta = kv.Value * days;
                if (delta == 0f) continue;
                var existing = pawn.health.hediffSet.GetFirstHediffOfDef(kv.Key);
                if (delta > 0f)
                {
                    if (existing == null)
                    {
                        var hediff = HediffMaker.MakeHediff(kv.Key, pawn);
                        hediff.Severity = delta;
                        pawn.health.AddHediff(hediff);
                    }
                    else
                    {
                        existing.Severity += delta;
                    }
                }
                else if (existing != null)
                {
                    existing.Severity += delta; // delta 為負，減少 severity
                    if (existing.ShouldRemove)
                        pawn.health.RemoveHediff(existing);
                }
            }
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
