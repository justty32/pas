using HarmonyLib;
using Verse;

namespace VOEOutpostEnhancement
{
    [StaticConstructorOnStartup]
    public static class VOEEnhanceMod
    {
        static VOEEnhanceMod()
        {
            new Harmony("justty32.VOEOutpostEnhancement").PatchAll();
        }
    }
}
