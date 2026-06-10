using HarmonyLib;
using Verse;

namespace BodyFortificationHediff
{
    [StaticConstructorOnStartup]
    public static class BodyFortificationMod
    {
        static BodyFortificationMod()
        {
            var harmony = new Harmony("justty32.BodyFortificationHediff");
            harmony.PatchAll();
            Log.Message("[BodyFortificationHediff] Harmony patches applied");
        }
    }
}
