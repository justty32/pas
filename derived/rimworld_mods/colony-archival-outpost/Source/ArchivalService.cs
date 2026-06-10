using System;
using System.Collections.Generic;
using System.Linq;
using Outposts;
using RimWorld;
using RimWorld.Planet;
using UnityEngine;
using Verse;

namespace ColonyArchivalOutpost
{
    // 封存核心轉換：算有號率 → 建 outpost → 搬玩家 pawn/儲存物資 → 銷毀地圖與舊據點。
    public static class ArchivalService
    {
        public static bool CanArchive(Map map, out string reason)
        {
            reason = null;
            if (map == null || !map.IsPlayerHome)
            {
                reason = "CAO.NotPlayerHome".Translate();
                return false;
            }
            // 唯一基地防呆：最後一張玩家家園地圖不可封存(正成長無處投遞)。
            int homeCount = Find.Maps.Count(m => m.IsPlayerHome);
            if (homeCount <= 1)
            {
                reason = "CAO.LastBase".Translate();
                return false;
            }
            return true;
        }

        public static ProductivitySnapshot ComputeSnapshot(Map map, ColonyArchivalTracker tracker)
        {
            var end = map.resourceCounter.AllCountedAmounts;
            int elapsedTicks = Find.TickManager.TicksGame - tracker.startTick;
            float elapsedDays = Mathf.Max(elapsedTicks, 60000) / 60000f;
            var allDefs = new HashSet<ThingDef>(end.Keys);
            allDefs.UnionWith(tracker.startCounts.Keys);
            var rates = new Dictionary<ThingDef, float>();
            foreach (var def in allDefs)
            {
                end.TryGetValue(def, out int e1);
                tracker.startCounts.TryGetValue(def, out int s0);
                int delta = e1 - s0;
                if (delta == 0) continue;
                rates[def] = delta / elapsedDays;
            }

            var snapshot = new ProductivitySnapshot(rates);

            // N7：技能速率——平均各 pawn 的 passion 修正後基礎 XP/天；只統計採樣期始末都在場的 pawn
            if (tracker.startSkillSnapshots.Count > 0)
            {
                var skillDeltas = new Dictionary<SkillDef, List<float>>();
                foreach (var psnap in tracker.startSkillSnapshots)
                {
                    var pawn = map.mapPawns.FreeColonistsSpawned.FirstOrDefault(p => p.ThingID == psnap.pawnId);
                    if (pawn?.skills == null) continue;
                    foreach (var kv in psnap.cumulativeXP)
                    {
                        var skill = pawn.skills.GetSkill(kv.Key);
                        if (skill == null || skill.TotallyDisabled) continue;
                        float endCumXP = skill.XpTotalEarned + skill.xpSinceLastLevel;
                        float deltaXP = endCumXP - kv.Value;
                        psnap.skillPassions.TryGetValue(kv.Key, out Passion startPassion);
                        float baseRate = deltaXP / PassionFactor(startPassion) / elapsedDays;
                        if (!skillDeltas.ContainsKey(kv.Key)) skillDeltas[kv.Key] = new List<float>();
                        skillDeltas[kv.Key].Add(baseRate);
                    }
                }
                var skillRates = new Dictionary<SkillDef, float>();
                foreach (var kv in skillDeltas)
                {
                    float sum = 0f;
                    foreach (float r in kv.Value) sum += r;
                    float avg = sum / kv.Value.Count;
                    if (avg != 0f) skillRates[kv.Key] = avg;
                }
                snapshot.dailySkillXP = skillRates;
            }

            // N6：傷勢速率——統計採樣期始末都在場的 pawn 的平均可癒傷勢變化量/天
            if (tracker.startInjurySeverity.Count > 0)
            {
                float totalDelta = 0f;
                int count = 0;
                foreach (var pair in tracker.startInjurySeverity)
                {
                    var pawn = map.mapPawns.FreeColonistsSpawned.FirstOrDefault(p => p.ThingID == pair.Key);
                    if (pawn == null) continue;
                    float endSev = TotalHealableSeverity(pawn);
                    totalDelta += endSev - pair.Value; // 負=淨治癒
                    count++;
                }
                if (count > 0) snapshot.avgHealthDeltaPerDay = totalDelta / count / elapsedDays;
            }

            return snapshot;
        }

        private static float TotalHealableSeverity(Pawn pawn)
        {
            float total = 0f;
            foreach (var h in pawn.health.hediffSet.hediffs)
                if (h is Hediff_Injury hd && hd.CanHealNaturally())
                    total += h.Severity;
            return total;
        }

        // passion 倍率：與 SkillRecord.LearnRateFactor(direct=true) 一致
        private static float PassionFactor(Passion passion) => passion switch
        {
            Passion.None => 0.35f,
            Passion.Minor => 1f,
            Passion.Major => 1.5f,
            _ => 1f
        };

        public static void Archive(Map map, string name = null, string iconPath = null,
            bool perPawn = false, bool applySkillXP = false, bool applyHealthDelta = false)
        {
            var tracker = map.GetComponent<ColonyArchivalTracker>();
            if (tracker == null || !tracker.isSampling) return;
            if (!CanArchive(map, out string reason))
            {
                Messages.Message(reason, MessageTypeDefOf.RejectInput, false);
                return;
            }

            MapParent parent = map.Parent;
            var tile = map.Tile;
            var snapshot = ComputeSnapshot(map, tracker);

            // N4：per-pawn 縮放
            if (perPawn)
            {
                snapshot.perPawnScaling = true;
                snapshot.basePawnCount = Math.Max(1, map.mapPawns.FreeColonistsCount);
            }
            // N7：技能採樣開關
            if (applySkillXP && snapshot.dailySkillXP?.Count > 0)
                snapshot.applySkillXP = true;
            // N6：傷勢採樣開關（只有淨治癒才套用）
            if (applyHealthDelta && snapshot.avgHealthDeltaPerDay < 0f)
                snapshot.applyHealthDelta = true;

            // 1) 建 outpost(掛玩家陣營, 餵 snapshot)
            var outpost = (Outpost_Sampled)WorldObjectMaker.MakeWorldObject(
                DefDatabase<WorldObjectDef>.GetNamed("pas_archival_Outpost"));
            outpost.Tile = tile;
            outpost.SetFaction(Faction.OfPlayer);
            outpost.SetSnapshot(snapshot);
            if (!name.NullOrEmpty()) outpost.Name = name;
            if (!iconPath.NullOrEmpty()) outpost.chosenIconPath = iconPath;
            Find.WorldObjects.Add(outpost);

            // 2) 搬玩家 pawn(殖民者+玩家動物+殖民地囚犯)。我們的 def 無 <Event> → CanAddPawn 恆過。
            //    先 DeSpawn 再 AddPawn(脫離地圖、occupants.Add、RecachePawnTraits)；不清 guest → 囚犯保留身分。
            var pawns = map.mapPawns.AllPawnsSpawned
                .Where(p => p.Faction == Faction.OfPlayer || p.IsPrisonerOfColony)
                .ToList();
            foreach (var pawn in pawns)
            {
                pawn.DeSpawn();
                outpost.AddPawn(pawn);
            }

            // 3) 搬儲存區可計物資 → containedItems 緩衝(枚舉實際 Thing, 非 counter 數字)
            var items = map.listerThings.AllThings
                .Where(t => t.def.CountAsResource && t.Spawned && !t.Destroyed && t.IsInAnyStorage())
                .ToList();
            foreach (var t in items)
            {
                t.DeSpawn();
                outpost.AddItem(t);
            }

            // 4) 銷毀地圖 + 舊據點世界物件(pawn/物資已脫離地圖, 安全)
            Current.Game.DeinitAndRemoveMap(map, false);
            if (parent != null && !parent.Destroyed)
                parent.Destroy();

            Messages.Message("CAO.Archived".Translate(), outpost, MessageTypeDefOf.PositiveEvent, false);
        }
    }
}
