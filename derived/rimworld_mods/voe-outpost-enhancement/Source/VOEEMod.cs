using UnityEngine;
using Verse;

namespace VOEOutpostEnhancement
{
    public class VOEE_ModSettings : ModSettings
    {
        public int prodSilverPerLevel   = 200;
        public int ammoCapSteelPerLevel = 200;
        public int ammoRateCompPerLevel = 20;
        public int rangeSteelPerLevel   = 150;
        public int rangeCompPerLevel    = 20;
        public int restockSteelPerShell = 8;

        public override void ExposeData()
        {
            Scribe_Values.Look(ref prodSilverPerLevel,   "prodSilverPerLevel",   200);
            Scribe_Values.Look(ref ammoCapSteelPerLevel, "ammoCapSteelPerLevel", 200);
            Scribe_Values.Look(ref ammoRateCompPerLevel, "ammoRateCompPerLevel",  20);
            Scribe_Values.Look(ref rangeSteelPerLevel,   "rangeSteelPerLevel",   150);
            Scribe_Values.Look(ref rangeCompPerLevel,    "rangeCompPerLevel",     20);
            Scribe_Values.Look(ref restockSteelPerShell, "restockSteelPerShell",   8);
        }
    }

    public class VOEE_Mod : Mod
    {
        public static VOEE_ModSettings Settings { get; private set; }

        public VOEE_Mod(ModContentPack content) : base(content)
        {
            Settings = GetSettings<VOEE_ModSettings>();
        }

        public override string SettingsCategory() => "VOEE.Settings.Category".Translate();

        public override void DoSettingsWindowContents(Rect inRect)
        {
            var s = Settings;
            var listing = new Listing_Standard();
            listing.Begin(inRect);

            listing.Label("VOEE.Settings.Prod.Silver".Translate(s.prodSilverPerLevel));
            s.prodSilverPerLevel = (int)listing.Slider(s.prodSilverPerLevel, 0f, 2000f);

            listing.Gap(8f);
            listing.Label("VOEE.Settings.AmmoCap.Steel".Translate(s.ammoCapSteelPerLevel));
            s.ammoCapSteelPerLevel = (int)listing.Slider(s.ammoCapSteelPerLevel, 0f, 2000f);

            listing.Gap(8f);
            listing.Label("VOEE.Settings.AmmoRate.Comp".Translate(s.ammoRateCompPerLevel));
            s.ammoRateCompPerLevel = (int)listing.Slider(s.ammoRateCompPerLevel, 0f, 500f);

            listing.Gap(8f);
            listing.Label("VOEE.Settings.Range.Steel".Translate(s.rangeSteelPerLevel));
            s.rangeSteelPerLevel = (int)listing.Slider(s.rangeSteelPerLevel, 0f, 2000f);

            listing.Gap(8f);
            listing.Label("VOEE.Settings.Range.Comp".Translate(s.rangeCompPerLevel));
            s.rangeCompPerLevel = (int)listing.Slider(s.rangeCompPerLevel, 0f, 500f);

            listing.Gap(8f);
            listing.Label("VOEE.Settings.Restock.Steel".Translate(s.restockSteelPerShell));
            s.restockSteelPerShell = (int)listing.Slider(s.restockSteelPerShell, 0f, 100f);

            listing.End();
        }
    }
}
