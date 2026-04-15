using Verse;

namespace SimpleItemMod
{
    public class CompShinyRock : ThingComp
    {
        public override void PostSpawnSetup(bool respawningAfterLoad)
        {
            base.PostSpawnSetup(respawningAfterLoad);
            Log.Message("A shiny rock has appeared!");
        }
    }
}
