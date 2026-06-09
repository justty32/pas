using HarmonyLib;
using Verse;

namespace ColonyArchivalOutpost
{
    public class CAOMod : Mod
    {
        public CAOMod(ModContentPack content) : base(content)
        {
            var harmony = new Harmony("pas.colonyarchival.outpost");
            harmony.PatchAll();
            Log.Message("[ColonyArchivalOutpost] Harmony patches applied");
        }
    }
}
