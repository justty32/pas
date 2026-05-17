# 模擬市民模式：自主社區與 NPC 社會邏輯實作

本系統旨在將 RimWorld 的 NPC 從單純的「數字機器」轉化為具備自主意識的「社區成員」。核心在於攔截玩家指令並強化 AI 的自主決策權。

## 1. 自主行為框架：JobGiver_AutonomousWork

我們需要為 NPC 提供一套不依賴於玩家點擊的自動工作選擇器。

```csharp
public class JobGiver_AutonomousWork : ThinkNode_JobGiver
{
    protected override Job TryGiveJob(Pawn pawn)
    {
        // 1. 優先滿足生理需求 (由原版 ThinkTree 處理)
        
        // 2. 檢查「社區佈告欄」是否有待辦事項
        Job boardJob = GetJobFromNoticeboard(pawn);
        if (boardJob != null) return boardJob;

        // 3. 根據技能專長選擇日常維護工作
        if (pawn.skills.GetSkill(SkillDefOf.Construction).Level >= 8)
        {
            // 自動尋找需要修理的建築
            Thing t = FindRepairTarget(pawn);
            if (t != null) return JobMaker.MakeJob(JobDefOf.Repair, t);
        }

        // 4. 沒事做時進入「社交模式」
        return JobMaker.MakeJob(JobDefOf.SocialRelax, pawn.Position);
    }
}
```

## 2. 限制玩家指令：Harmony Patch

為了實作「模擬市民模式」，我們需要阻止玩家直接命令非核心成員。

```csharp
[HarmonyPatch(typeof(FloatMenuMakerMap), "AddHumanlikeOrders")]
public static class Patch_RestrictDirectControl
{
    [HarmonyPrefix]
    public static bool Prefix(Pawn pawn)
    {
        // 如果該 Pawn 屬於「自主盟友」且不是玩家的核心小隊
        if (pawn.Faction == Faction.OfPlayer && !IsCoreSquadMember(pawn))
        {
            // 屏蔽右鍵選單，不允許直接下令
            return false;
        }
        return true;
    }

    private static bool IsCoreSquadMember(Pawn p)
    {
        // 檢查是否有特定的 Hediff 或 Comp 標記為玩家親自掌控
        return p.TryGetComp<CompCoreMember>() != null;
    }
}
```

## 3. 社區社交強化：SocialInteractionWorker_Gossip

實作更具敘事感的社交互動，讓 NPC 之間會「傳八卦」或「建立小圈子」。

```csharp
public class SocialInteractionWorker_Gossip : SocialInteractionWorker
{
    public override void Interacted(Pawn initiator, Pawn recipient, List<RulePackDef> extraSentencePacks, out string letterText, out string letterLabel, out LetterDef letterDef, out LookTargets lookTargets)
    {
        base.Interacted(initiator, recipient, extraSentencePacks, out letterText, out letterLabel, out letterDef, out lookTargets);
        
        // 隨機產生一個關於第三個人的八卦
        Pawn thirdPerson = initiator.Map.mapPawns.AllPawnsSpawned.RandomElement();
        if (thirdPerson != null && thirdPerson != initiator && thirdPerson != recipient)
        {
            // 影響兩者對第三者的看法 (Opinion)
            float effect = Rand.Range(-5f, 5f);
            recipient.relations.ChangeOpinionBy(thirdPerson, (int)effect);
        }
    }
}
```

## 4. 社區滿意度系統 (Community Mood)

這是一個地圖級別的數值，影響所有 NPC 的工作效率與叛亂機率。

```csharp
public class MapComponent_CommunitySpirit : MapComponent
{
    public float spiritLevel = 0.5f; // 0.0 ~ 1.0

    public override void MapComponentTick()
    {
        if (Find.TickManager.TicksGame % 2500 == 0) // 每小時計算一次
        {
            UpdateSpirit();
        }
    }

    private void UpdateSpirit()
    {
        // 計算所有 NPC 的平均心情
        float avgMood = map.mapPawns.AllPawnsSpawned
            .Where(p => p.Faction == Faction.OfPlayer)
            .Average(p => p.needs.mood.CurLevel);

        // 根據平均心情調整社區氣氛
        spiritLevel = Mathf.Lerp(spiritLevel, avgMood, 0.1f);
    }
}
```

## 5. UI 與氛圍渲染

*   **氣泡對話 (Bubble Dialog)**: 當 NPC 社交時，在頭頂顯示簡短的對話氣泡（如「談論天氣」、「抱怨領袖」）。
*   **動態環境音**: 根據 `spiritLevel` 調整背景音樂或環境音效。高滿意度時有輕快的環境聲，低滿意度時則顯得壓抑。
*   **私有區域顯示**: 使用透明度不同的地圖覆蓋層 (Overlay) 標註出 NPC 的私有房間，玩家進入時會顯示「私闖民宅」的警告提示。

---
*文件路徑: analysis/rimworld/details/sims_mode_community_implementation.md*
