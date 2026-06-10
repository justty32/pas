using System;
using System.Collections.Generic;
using System.Linq;
using Outposts;
using RimWorld;
using RimWorld.Planet;
using UnityEngine;
using Verse;

namespace ColonyArchivalOutpost
{
    // 封存核心轉換：算有號率 → 建 outpost → 搬玩家 pawn/儲存物資 → 銷毀地圖與舊據點。
    public static class ArchivalService
    {
        public static bool CanArchive(Map map, out string reason)
        {
            reason = null;
            if (map == null || !map.IsPlayerHome)
            {
                reason = "CAO.NotPlayerHome".Translate();
                return false;
            }
            // 唯一基地防呆：最後一張玩家家園地圖不可封存(正成長無處投遞)。
            int homeCount = Find.Maps.Count(m => m.IsPlayerHome);
            if (homeCount <= 1)
            {
                reason = "CAO.LastBase".Translate();
                return false;
            }
            return true;
        }

        public static ProductivitySnapshot ComputeSnapshot(Map map, ColonyArchivalTracker tracker)
        {
            var end = map.resourceCounter.AllCountedAmounts;
            int elapsedTicks = Find.TickManager.TicksGame - tracker.startTick;
            float elapsedDays = Mathf.Max(elapsedTicks, 60000) / 60000f; // 數學防呆下限 = 1 遊戲天
            var allDefs = new HashSet<ThingDef>(end.Keys);
            allDefs.UnionWith(tracker.startCounts.Keys);
            var rates = new Dictionary<ThingDef, float>();
            foreach (var def in allDefs)
            {
                end.TryGetValue(def, out int e1);
                tracker.startCounts.TryGetValue(def, out int s0);
                int delta = e1 - s0; // 有號淨流：正=產出, 負=消耗
                if (delta == 0) continue;
                rates[def] = delta / elapsedDays;
            }
            return new ProductivitySnapshot(rates);
        }

        public static void Archive(Map map, string name = null, string iconPath = null, bool perPawn = false)
        {
            var tracker = map.GetComponent<ColonyArchivalTracker>();
            if (tracker == null || !tracker.isSampling) return;
            if (!CanArchive(map, out string reason))
            {
                Messages.Message(reason, MessageTypeDefOf.RejectInput, false);
                return;
            }

            MapParent parent = map.Parent;
            var tile = map.Tile;
            var snapshot = ComputeSnapshot(map, tracker);

            // N4：per-pawn 縮放——封存前記錄當下殖民者數，後續 Outpost_Sampled 用此基準縮放速率。
            if (perPawn)
            {
                snapshot.perPawnScaling = true;
                snapshot.basePawnCount = Math.Max(1, map.mapPawns.FreeColonistsCount);
            }

            // 1) 建 outpost(掛玩家陣營, 餵 snapshot)
            var outpost = (Outpost_Sampled)WorldObjectMaker.MakeWorldObject(
                DefDatabase<WorldObjectDef>.GetNamed("pas_archival_Outpost"));
            outpost.Tile = tile;
            outpost.SetFaction(Faction.OfPlayer);
            outpost.SetSnapshot(snapshot);
            if (!name.NullOrEmpty()) outpost.Name = name;
            if (!iconPath.NullOrEmpty()) outpost.chosenIconPath = iconPath;
            Find.WorldObjects.Add(outpost);

            // 2) 搬玩家 pawn(殖民者+玩家動物+殖民地囚犯)。我們的 def 無 <Event> → CanAddPawn 恆過。
            //    先 DeSpawn 再 AddPawn(脫離地圖、occupants.Add、RecachePawnTraits)；不清 guest → 囚犯保留身分。
            var pawns = map.mapPawns.AllPawnsSpawned
                .Where(p => p.Faction == Faction.OfPlayer || p.IsPrisonerOfColony)
                .ToList();
            foreach (var pawn in pawns)
            {
                pawn.DeSpawn();
                outpost.AddPawn(pawn);
            }

            // 3) 搬儲存區可計物資 → containedItems 緩衝(枚舉實際 Thing, 非 counter 數字)
            var items = map.listerThings.AllThings
                .Where(t => t.def.CountAsResource && t.Spawned && !t.Destroyed && t.IsInAnyStorage())
                .ToList();
            foreach (var t in items)
            {
                t.DeSpawn();
                outpost.AddItem(t);
            }

            // 4) 銷毀地圖 + 舊據點世界物件(pawn/物資已脫離地圖, 安全)
            Current.Game.DeinitAndRemoveMap(map, false);
            if (parent != null && !parent.Destroyed)
                parent.Destroy();

            Messages.Message("CAO.Archived".Translate(), outpost, MessageTypeDefOf.PositiveEvent, false);
        }
    }
}
