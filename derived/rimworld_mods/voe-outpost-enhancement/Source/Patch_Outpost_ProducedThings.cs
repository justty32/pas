using System;
using System.Collections.Generic;
using HarmonyLib;
using Outposts;
using Verse;

namespace VOEOutpostEnhancement
{
    [HarmonyPatch(typeof(Outpost), "ProducedThings")]
    public static class Patch_Outpost_ProducedThings
    {
        static IEnumerable<Thing> Postfix(IEnumerable<Thing> __result, Outpost __instance)
        {
            var rec = WorldComponent_OutpostUpgrades.Instance?.GetOrCreate(__instance);
            float mult = rec != null ? UpgradeService.ProdMultiplierForLevel(rec.productionLevel) : 1f;

            foreach (var thing in __result)
            {
                if (mult > 1.01f)
                    thing.stackCount = Math.Max(1, (int)Math.Round(thing.stackCount * mult));
                yield return thing;
            }
        }
    }
}
