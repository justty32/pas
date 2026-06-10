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
        public Dictionary<ThingDef, int> startCounts = new Dictionary<ThingDef, int>();

        // N7：技能採樣——期初各殖民者累積 XP 與熱情等級
        public List<PawnSkillSnapshot> startSkillSnapshots = new List<PawnSkillSnapshot>();

        public ColonyArchivalTracker(Map map) : base(map) { }

        public void BeginSampling()
        {
            isSampling = true;
            startTick = Find.TickManager.TicksGame;
            startCounts = new Dictionary<ThingDef, int>(map.resourceCounter.AllCountedAmounts);

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
            startCounts = new Dictionary<ThingDef, int>();
            startSkillSnapshots = new List<PawnSkillSnapshot>();
        }

        public override void ExposeData()
        {
            base.ExposeData();
            Scribe_Values.Look(ref isSampling, "caoIsSampling", false);
            Scribe_Values.Look(ref startTick, "caoStartTick", -1);
            Scribe_Collections.Look(ref startCounts, "caoStartCounts", LookMode.Def, LookMode.Value);
            Scribe_Collections.Look(ref startSkillSnapshots, "caoStartSkillSnapshots", LookMode.Deep);
            if (Scribe.mode == LoadSaveMode.PostLoadInit)
            {
                if (startCounts == null) startCounts = new Dictionary<ThingDef, int>();
                if (startSkillSnapshots == null) startSkillSnapshots = new List<PawnSkillSnapshot>();
            }
        }
    }
}
