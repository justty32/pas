using UnityEngine;
using Verse;

namespace ColonyArchivalOutpost
{
    // N1：封存前確認視窗。計算 snapshot、讓玩家命名與挑選圖標後執行封存。
    // N3：視窗內嵌圖標 gallery（VOE 既有世界物件貼圖）。
    public class Dialog_ArchivalConfirm : Window
    {
        private readonly Map map;
        private readonly ProductivitySnapshot snapshot;
        private readonly int elapsedTicks;
        private readonly float daysPerCycle;

        private string outpostName;
        private string chosenIconPath;
        private bool scalePawnCount;
        private readonly int currentPawnCount;
        private bool applySkillXP;

        private Vector2 previewScroll;
        private float previewContentH;

        private static readonly string[] IconPaths =
        {
            "WorldObjects/OutpostFarming",
            "WorldObjects/OutpostMining",
            "WorldObjects/OutpostHunting",
            "WorldObjects/OutpostLogging",
            "WorldObjects/OutpostScavenging",
            "WorldObjects/OutpostDrilling",
            "WorldObjects/OutpostProduction",
            "WorldObjects/OutpostFactory",
            "WorldObjects/OutpostScience",
            "WorldObjects/OutpostTown",
            "WorldObjects/OutpostTrading",
            "WorldObjects/OutpostEncampment",
            "WorldObjects/OutpostDefensive",
            "WorldObjects/OutpostArtillery",
            "WorldObjects/OutpostFishing",
        };

        private const float IconSlot = 40f; // 36px icon + 4px gap
        private const float IconSize = 36f;

        public override Vector2 InitialSize => new Vector2(500f, 580f);

        public Dialog_ArchivalConfirm(Map map)
        {
            this.map = map;
            var tracker = map.GetComponent<ColonyArchivalTracker>();
            elapsedTicks = Find.TickManager.TicksGame - tracker.startTick;
            snapshot = ArchivalService.ComputeSnapshot(map, tracker);
            daysPerCycle = 900000f / 60000f; // 15 遊戲天，對應 def TicksPerProduction=900000
            currentPawnCount = map.mapPawns.FreeColonistsCount;
            outpostName = map.Parent?.Label ?? "CAO.DefaultOutpostName".Translate();
            chosenIconPath = IconPaths[0];

            doCloseX = true;
            forcePause = true;
            absorbInputAroundWindow = false;
            closeOnClickedOutside = false;
            previewContentH = SnapshotPreviewDrawer.CalcHeight(snapshot, elapsedTicks);
        }

        public override void DoWindowContents(Rect inRect)
        {
            float x = inRect.x;
            float w = inRect.width;
            float y = inRect.y;

            // 標題
            Text.Font = GameFont.Medium;
            Widgets.Label(new Rect(x, y, w, 32f), "CAO.ArchivalConfirm.Title".Translate());
            Text.Font = GameFont.Small;
            y += 36f;

            // 預覽 scroll view（固定高度 180px）
            const float previewOuterH = 180f;
            Rect outerRect = new Rect(x, y, w, previewOuterH);
            Widgets.DrawBoxSolid(outerRect, new Color(0f, 0f, 0f, 0.12f));
            Rect viewRect = new Rect(0f, 0f, w - 20f, Mathf.Max(previewOuterH, previewContentH));
            Widgets.BeginScrollView(outerRect, ref previewScroll, viewRect);
            SnapshotPreviewDrawer.Draw(new Rect(4f, 4f, viewRect.width - 8f, viewRect.height), snapshot, elapsedTicks, daysPerCycle, previewScroll, previewOuterH);
            Widgets.EndScrollView();
            y += previewOuterH + 10f;

            // 命名欄
            Widgets.Label(new Rect(x, y, 110f, 26f), "CAO.ArchivalConfirm.OutpostName".Translate() + ":");
            outpostName = Widgets.TextField(new Rect(x + 114f, y, w - 114f, 26f), outpostName);
            y += 34f;

            // N4：per-pawn 開關
            Widgets.CheckboxLabeled(new Rect(x, y, w, 26f),
                "CAO.ArchivalConfirm.ScalePawn".Translate(currentPawnCount), ref scalePawnCount);
            y += 32f;

            // N7：技能採樣開關（只在有技能資料時顯示）
            if (snapshot.dailySkillXP?.Count > 0)
            {
                Widgets.CheckboxLabeled(new Rect(x, y, w, 26f),
                    "CAO.ArchivalConfirm.ApplySkillXP".Translate(snapshot.dailySkillXP.Count), ref applySkillXP);
                y += 32f;
            }

            // N3：圖標 gallery
            Widgets.Label(new Rect(x, y, w, 22f), "CAO.ArchivalConfirm.ChooseIcon".Translate() + ":");
            y += 24f;

            int iconsPerRow = Mathf.Max(1, Mathf.FloorToInt(w / IconSlot));
            for (int i = 0; i < IconPaths.Length; i++)
            {
                int col = i % iconsPerRow;
                int row = i / iconsPerRow;
                float ix = x + col * IconSlot;
                float iy = y + row * IconSlot;

                Rect slotRect = new Rect(ix, iy, IconSize, IconSize);
                bool selected = IconPaths[i] == chosenIconPath;

                if (selected)
                    Widgets.DrawBoxSolid(slotRect.ExpandedBy(2f), new Color(1f, 0.8f, 0.1f, 0.45f));

                Texture2D tex = ContentFinder<Texture2D>.Get(IconPaths[i], false);
                if (tex != null)
                    GUI.DrawTexture(slotRect, tex);
                else
                    Widgets.DrawBoxSolid(slotRect, Color.gray * 0.4f);

                if (Widgets.ButtonInvisible(slotRect))
                    chosenIconPath = IconPaths[i];

                string iconName = IconPaths[i].Contains("/") ? IconPaths[i].Substring(IconPaths[i].LastIndexOf('/') + 1) : IconPaths[i];
                TooltipHandler.TipRegion(slotRect, iconName);
            }

            int iconRows = Mathf.CeilToInt((float)IconPaths.Length / iconsPerRow);
            y += iconRows * IconSlot + 10f;

            // 按鈕列（貼視窗底部）
            float btnY = inRect.yMax - 36f;
            float halfW = (w - 8f) / 2f;

            if (Widgets.ButtonText(new Rect(x, btnY, halfW, 32f), "CAO.ArchivalConfirm.Cancel".Translate()))
                Close();

            if (Widgets.ButtonText(new Rect(x + halfW + 8f, btnY, halfW, 32f), "CAO.ArchivalConfirm.Confirm".Translate()))
            {
                Close();
                string name = outpostName.NullOrEmpty() ? null : outpostName.Trim();
                ArchivalService.Archive(map, name, chosenIconPath, scalePawnCount, applySkillXP);
            }
        }
    }
}
