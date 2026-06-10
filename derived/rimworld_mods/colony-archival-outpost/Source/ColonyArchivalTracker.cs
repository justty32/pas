using System;
using System.Collections.Generic;
using RimWorld;
using Verse;

namespace ColonyArchivalOutpost
{
    // 掛在每張地圖上(MapComponent 子類由遊戲自動實例化)。記錄採樣窗的期初狀態。
    public class ColonyArchivalTracker : MapComponent
    {
        public bool isSampling;
        public int startTick = -1;
        public int startColonistCount = 1; // N4：採樣開始時的殖民者數，作為 per-pawn 基準
        public Dictionary<ThingDef, int> startCounts = new Dictionary<ThingDef, int>();

        // N7：技能採樣——期初各殖民者累積 XP 與熱情等級
        public List<PawnSkillSnapshot> startSkillSnapshots = new List<PawnSkillSnapshot>();

        // N6：傷勢採樣——期初各殖民者可癒傷勢（Hediff_Injury 且 CanHealNaturally）severity 總和
        public Dictionary<string, float> startInjurySeverity = new Dictionary<string, float>();

        // N6b：非傷勢 hediff 採樣——期初各殖民者的非 Injury/MissingPart hediff severity
        public List<PawnHediffSnapshot> startHediffSnapshots = new List<PawnHediffSnapshot>();

        public ColonyArchivalTracker(Map map) : base(map) { }

        public void BeginSampling()
        {
            isSampling = true;
            startTick = Find.TickManager.TicksGame;
            startColonistCount = Math.Max(1, map.mapPawns.FreeColonistsCount);
            startCounts = new Dictionary<ThingDef, int>(map.resourceCounter.AllCountedAmounts);

            // N6：snapshot 每個自由殖民者的可癒傷勢 severity 總和
            startInjurySeverity = new Dictionary<string, float>();
            foreach (var pawn in map.mapPawns.FreeColonistsSpawned)
                startInjurySeverity[pawn.ThingID] = TotalHealableSeverity(pawn);

            // N6b：snapshot 每個自由殖民者的非傷勢 hediff severity
            startHediffSnapshots = new List<PawnHediffSnapshot>();
            foreach (var pawn in map.mapPawns.FreeColonistsSpawned)
            {
                var snap = new PawnHediffSnapshot { pawnId = pawn.ThingID };
                foreach (var h in pawn.health.hediffSet.hediffs)
                {
                    if (h is Hediff_Injury || h.def == null) continue; // 保留 MissingPart（缺損）
                    // Bug 1 fix：與 ComputeSnapshot 的 endSeverities 累加方式一致
                    snap.hediffSeverities.TryGetValue(h.def, out float cur);
                    snap.hediffSeverities[h.def] = cur + h.Severity;
                }
                if (snap.hediffSeverities.Count > 0)
                    startHediffSnapshots.Add(snap);
            }

            // N7：snapshot 每個自由殖民者的技能累積 XP 及熱情
            startSkillSnapshots = new List<PawnSkillSnapshot>();
            foreach (var pawn in map.mapPawns.FreeColonistsSpawned)
            {
                if (pawn.skills == null) continue;
                var snap = new PawnSkillSnapshot { pawnId = pawn.ThingID };
                foreach (var skill in pawn.skills.skills)
                {
                    if (skill.TotallyDisabled) continue;
                    snap.cumulativeXP[skill.def] = skill.XpTotalEarned + skill.xpSinceLastLevel;
                    snap.skillPassions[skill.def] = skill.passion;
                }
                startSkillSnapshots.Add(snap);
            }
        }

        public void Reset()
        {
            isSampling = false;
            startTick = -1;
            startColonistCount = 1;
            startCounts = new Dictionary<ThingDef, int>();
            startSkillSnapshots = new List<PawnSkillSnapshot>();
            startInjurySeverity = new Dictionary<string, float>();
            startHediffSnapshots = new List<PawnHediffSnapshot>();
        }

        private static float TotalHealableSeverity(Pawn pawn)
        {
            float total = 0f;
            foreach (var h in pawn.health.hediffSet.hediffs)
                if (h is Hediff_Injury hd && hd.CanHealNaturally())
                    total += h.Severity;
            return total;
        }

        public override void ExposeData()
        {
            base.ExposeData();
            Scribe_Values.Look(ref isSampling, "caoIsSampling", false);
            Scribe_Values.Look(ref startTick, "caoStartTick", -1);
            Scribe_Values.Look(ref startColonistCount, "caoStartColonistCount", 1);
            Scribe_Collections.Look(ref startCounts, "caoStartCounts", LookMode.Def, LookMode.Value);
            Scribe_Collections.Look(ref startSkillSnapshots, "caoStartSkillSnapshots", LookMode.Deep);
            Scribe_Collections.Look(ref startInjurySeverity, "caoStartInjurySeverity", LookMode.Value, LookMode.Value);
            Scribe_Collections.Look(ref startHediffSnapshots, "caoStartHediffSnapshots", LookMode.Deep);
            if (Scribe.mode == LoadSaveMode.PostLoadInit)
            {
                if (startCounts == null) startCounts = new Dictionary<ThingDef, int>();
                if (startSkillSnapshots == null) startSkillSnapshots = new List<PawnSkillSnapshot>();
                if (startInjurySeverity == null) startInjurySeverity = new Dictionary<string, float>();
                if (startHediffSnapshots == null) startHediffSnapshots = new List<PawnHediffSnapshot>();
            }
        }
    }
}
