using System.Collections.Generic;
using RimWorld;
using Verse;

namespace ColonyArchivalOutpost
{
    // N7：記錄單個 pawn 在採樣期初的技能累積 XP 及熱情等級，供封存時計算基礎速率。
    public class PawnSkillSnapshot : IExposable
    {
        public string pawnId;
        public Dictionary<SkillDef, float> cumulativeXP = new Dictionary<SkillDef, float>();
        public Dictionary<SkillDef, Passion> skillPassions = new Dictionary<SkillDef, Passion>();

        public PawnSkillSnapshot() { }

        public void ExposeData()
        {
            Scribe_Values.Look(ref pawnId, "pawnId");
            Scribe_Collections.Look(ref cumulativeXP, "cumulativeXP", LookMode.Def, LookMode.Value);
            Scribe_Collections.Look(ref skillPassions, "skillPassions", LookMode.Def, LookMode.Value);
            if (Scribe.mode == LoadSaveMode.PostLoadInit)
            {
                if (cumulativeXP == null) cumulativeXP = new Dictionary<SkillDef, float>();
                if (skillPassions == null) skillPassions = new Dictionary<SkillDef, Passion>();
            }
        }
    }
}
