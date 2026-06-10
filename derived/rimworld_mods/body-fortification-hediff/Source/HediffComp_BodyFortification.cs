using Verse;

namespace BodyFortificationHediff
{
    /// <summary>
    /// Comp properties that carry the multiplier value.
    /// The actual multiplier used at runtime is resolved from the current stage
    /// via DamageWorker_Patch, which reads the pawn's hediff severity to pick the right tier.
    /// The multiplier field here acts as a fallback default (stage 0 = ×2).
    /// </summary>
    public class HediffCompProperties_BodyFortification : HediffCompProperties
    {
        public float multiplier = 2f;

        public HediffCompProperties_BodyFortification()
        {
            compClass = typeof(HediffComp_BodyFortification);
        }
    }

    public class HediffComp_BodyFortification : HediffComp
    {
        public HediffCompProperties_BodyFortification Props =>
            (HediffCompProperties_BodyFortification)props;

        /// <summary>
        /// Returns the effective multiplier for the current severity stage.
        /// Stage thresholds mirror the HediffDef XML (0.0 / 0.34 / 0.67).
        /// </summary>
        public float CurrentMultiplier
        {
            get
            {
                float sev = parent?.Severity ?? 0f;
                if (sev >= 0.67f) return 10f;
                if (sev >= 0.34f) return 5f;
                return 2f;
            }
        }
    }
}
