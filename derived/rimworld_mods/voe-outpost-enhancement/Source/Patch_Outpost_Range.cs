using HarmonyLib;
using Outposts;
using VOE;

namespace VOEOutpostEnhancement
{
    [HarmonyPatch(typeof(Outpost), "Range", MethodType.Getter)]
    public static class Patch_Outpost_Range
    {
        static void Postfix(ref int __result, Outpost __instance)
        {
            if (!(__instance is Outpost_Artillery)) return;
            if (__result <= 0) return;
            var rec = WorldComponent_OutpostUpgrades.Instance?.GetOrCreate(__instance);
            if (rec == null || rec.artRangeLevel <= 0) return;
            __result += UpgradeService.RangeBonus[rec.artRangeLevel];
        }
    }
}
