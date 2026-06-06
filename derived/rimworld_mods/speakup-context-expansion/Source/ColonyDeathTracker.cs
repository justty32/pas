using RimWorld;   // GenDate.TicksPerDay
using Verse;

namespace SpeakUpContextExpansion
{
    /// <summary>
    /// 以 GameComponent 持久化「最近一次玩家殖民者死亡的遊戲 tick」。
    /// 由 Harmony patch（Pawn_Kill_Patch）在殖民者死亡時呼叫 NotifyColonistDied 寫入。
    /// ExtraRulesInjector 讀取它換算「距離上次死亡的天數」。
    ///
    /// 之所以用 GameComponent 而非 static 欄位：
    ///  - 需要隨存檔保存（讀檔後仍知道幾天前死過人）。
    ///  - 多個存檔互不污染。
    /// 參考 RimWorld GameComponent 慣例（ExposeData 走 Scribe）。
    /// </summary>
    public class ColonyDeathTracker : GameComponent
    {
        // 以 -1 表示「本局尚無殖民者死亡紀錄」。
        private int lastColonistDeathTick = -1;

        public ColonyDeathTracker(Game game) { }

        public void NotifyColonistDied(int currentTick)
        {
            lastColonistDeathTick = currentTick;
        }

        /// <summary>
        /// 回傳距離上次殖民者死亡的天數；若本局從未死過人回傳 -1。
        /// </summary>
        public float DaysSinceLastDeath(int currentTick)
        {
            if (lastColonistDeathTick < 0) return -1f;
            int delta = currentTick - lastColonistDeathTick;
            if (delta < 0) delta = 0; // 防讀檔/時間異常
            return (float)delta / GenDate.TicksPerDay;
        }

        public override void ExposeData()
        {
            base.ExposeData();
            Scribe_Values.Look(ref lastColonistDeathTick, "speakupCE_lastColonistDeathTick", -1);
        }

        /// <summary>取得目前遊戲的 tracker（不存在時 RimWorld 不會自動建立舊存檔的元件，故做 null 防護）。</summary>
        public static ColonyDeathTracker Current
        {
            get
            {
                return Verse.Current.Game?.GetComponent<ColonyDeathTracker>();
            }
        }
    }
}
