using HarmonyLib;
using RimWorld;
using UnityEngine;
using Verse;

namespace BodyHPX10
{
    public class BodyHPX10_Settings : ModSettings
    {
        public float multiplier = 10f;
        public override void ExposeData()
        {
            Scribe_Values.Look(ref multiplier, "multiplier", 10f);
        }
    }

    public class BodyHPX10_Mod : Mod
    {
        public static BodyHPX10_Settings Settings { get; private set; }
        public BodyHPX10_Mod(ModContentPack content) : base(content)
        {
            Settings = GetSettings<BodyHPX10_Settings>();
        }
        public override string SettingsCategory() => "BodyHPX10.Settings.Category".Translate();
        public override void DoSettingsWindowContents(Rect inRect)
        {
            var listing = new Listing_Standard();
            listing.Begin(inRect);
            listing.Label("BodyHPX10.Settings.Multiplier".Translate((int)Settings.multiplier));
            Settings.multiplier = listing.Slider(Settings.multiplier, 1f, 100f);
            listing.End();
        }
    }

    [StaticConstructorOnStartup]
    static class BodyHPX10Mod
    {
        static BodyHPX10Mod()
        {
            var harmony = new Harmony("justty32.BodyHPX10");
            harmony.PatchAll();
            Log.Message("[BodyHPX10] Harmony patches applied.");
        }
    }

    static class BodyHPX10Defs
    {
        private static HediffDef? cached;
        public static HediffDef Hediff => cached ??= DefDatabase<HediffDef>.GetNamed("BodyHPX10");
        public static bool Has(Pawn? pawn) =>
            pawn?.health?.hediffSet?.HasHediff(Hediff) == true;
    }

    [HarmonyPatch(typeof(BodyPartDef), "GetMaxHealth")]
    static class Patch_GetMaxHealth
    {
        static void Postfix(ref float __result, Pawn pawn)
        {
            if (BodyHPX10Defs.Has(pawn))
                __result *= BodyHPX10_Mod.Settings?.multiplier ?? 10f;
        }
    }

    // 不死之身第二層：擋「直接呼叫 Kill()」的路徑（處決、獻祭、劇情事件等）。
    // 第一層是 HediffDef 的 preventsDeath=true（vanilla 機制，擋 ShouldBeDead 的
    // 失血/疾病/致死傷害閾值判定），無需 Harmony。
    [HarmonyPatch(typeof(Pawn), nameof(Pawn.Kill))]
    static class Patch_Pawn_Kill
    {
        static bool Prefix(Pawn __instance)
        {
            return !BodyHPX10Defs.Has(__instance); // 有 hediff → return false 跳過 Kill
        }
    }
}
