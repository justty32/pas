using System;
using System.Collections.Generic;
using System.Reflection;
using HarmonyLib;
using RimWorld;
using Verse;

namespace BodyFortificationHediff
{
    /// <summary>
    /// Harmony prefix patch for DamageWorker_AddInjury.ApplyDamageToPart.
    ///
    /// DamageInfo is a struct passed by value inside RimWorld internals; the private
    /// method receives it by value as well.  We use reflection to write to the private
    /// backing field `amount` so the reduced value propagates through the rest of the
    /// damage-application logic.
    ///
    /// Signature targeted (RimWorld 1.6, decompiled):
    ///   private void ApplyDamageToPart(
    ///       DamageInfo dinfo, Pawn pawn, BodyPartRecord part,
    ///       ref float totalDamageDealt, List<Hediff_Injury> injuries)
    ///
    /// If AccessTools cannot locate the method (signature drift), the patch silently
    /// skips via a null-check guard and logs a one-time warning.
    /// </summary>
    [HarmonyPatch]
    public static class DamageWorker_AddInjury_ApplyDamageToPart_Patch
    {
        // Reflected field for DamageInfo.amount (private float backing field).
        private static readonly FieldInfo s_amountField =
            typeof(DamageInfo).GetField("amount", BindingFlags.NonPublic | BindingFlags.Instance);

        private static bool s_warnedMissingMethod = false;
        private static bool s_warnedMissingField  = false;

        static MethodBase TargetMethod()
        {
            // Private method — must be fetched manually.
            var method = AccessTools.Method(
                typeof(DamageWorker_AddInjury),
                "ApplyDamageToPart",
                new Type[]
                {
                    typeof(DamageInfo),
                    typeof(Pawn),
                    typeof(BodyPartRecord),
                    typeof(float).MakeByRefType(),
                    typeof(List<Hediff_Injury>)
                });

            if (method == null && !s_warnedMissingMethod)
            {
                s_warnedMissingMethod = true;
                Log.Warning("[BodyFortificationHediff] Could not find DamageWorker_AddInjury.ApplyDamageToPart — patch not applied. Damage reduction will NOT work.");
            }
            return method;
        }

        // Prefix: runs before ApplyDamageToPart.
        // dinfo is passed by VALUE (struct copy) — we mutate it here via reflection.
        // The modified copy is what the rest of the method sees.
        static void Prefix(ref DamageInfo dinfo, Pawn pawn)
        {
            if (pawn == null || pawn.health == null) return;

            // Find the BFH hediff on this pawn.
            var hediff = pawn.health.hediffSet?.GetFirstHediffOfDef(
                DefDatabase<HediffDef>.GetNamedSilentFail("BFH_BodyFortification"));
            if (hediff == null) return;

            // Retrieve the comp to get the current multiplier.
            var comp = hediff.TryGetComp<HediffComp_BodyFortification>();
            if (comp == null) return;

            float mult = comp.CurrentMultiplier;
            if (mult <= 1f) return;

            // DamageInfo.Amount is a get-only property backed by private field `amount`.
            if (s_amountField == null)
            {
                if (!s_warnedMissingField)
                {
                    s_warnedMissingField = true;
                    Log.Warning("[BodyFortificationHediff] DamageInfo.amount private field not found — cannot reduce damage.");
                }
                return;
            }

            float original = dinfo.Amount;
            float reduced  = original / mult;

            // DamageInfo is a struct; ref parameter means we're editing the caller's copy.
            s_amountField.SetValue(dinfo, reduced);
        }
    }
}
