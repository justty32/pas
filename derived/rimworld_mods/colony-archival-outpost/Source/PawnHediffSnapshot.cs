using System.Collections.Generic;
using RimWorld;
using Verse;

namespace ColonyArchivalOutpost
{
    // N6b：每個 pawn 採樣開始時的非傷勢 hediff severity 快照
    public class PawnHediffSnapshot : IExposable
    {
        public string pawnId;
        public Dictionary<HediffDef, float> hediffSeverities = new Dictionary<HediffDef, float>();

        public void ExposeData()
        {
            Scribe_Values.Look(ref pawnId, "pawnId");
            Scribe_Collections.Look(ref hediffSeverities, "hediffSeverities", LookMode.Def, LookMode.Value);
            if (Scribe.mode == LoadSaveMode.PostLoadInit && hediffSeverities == null)
                hediffSeverities = new Dictionary<HediffDef, float>();
        }
    }
}
