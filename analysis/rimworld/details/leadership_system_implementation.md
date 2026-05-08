# 權威與領導力系統：社會階級與 NPC 指揮權的 C# 實作

本系統將 RimWorld 的「全權掌控」拆解為動態的社會地位階梯。技術核心在於如何**條件式地賦予玩家對非殖民者 NPC 的指揮權**。

## 1. 權威數據模型：CompAuthority

我們需要一個掛載在 Pawn 上的組件來追蹤其地位與聲望。

```csharp
public class CompAuthority : ThingComp
{
    public int tier = 1; // 1: 訪客, 2: 盟友, 3: 軍官, 4: 領袖
    public float renown = 0f; // 個人名望
    
    public override void PostExposeData()
    {
        base.ExposeData();
        Scribe_Values.Look(ref tier, "tier", 1);
        Scribe_Values.Look(ref renown, "renown", 0f);
    }

    // 判斷是否具備徵調權限
    public bool CanDraftNPC(Pawn target)
    {
        if (tier >= 4) return true; // 領袖有絕對控制權
        if (tier == 3 && target.kindDef.combatPower < 100) return true; // 軍官只能帶走民兵
        return false;
    }
}
```

## 2. 指揮權攔截：Harmony Patching

這是系統最核心的技術點。我們需要攔截 RimWorld 判斷 Pawn 是否「可徵調」的邏輯。

```csharp
[HarmonyPatch(typeof(Pawn), "get_IsColonistPlayerControlled")]
public static class Patch_NPCControl
{
    [HarmonyPostfix]
    public static void Postfix(Pawn __instance, ref bool __result)
    {
        // 如果原本就是殖民者，保持不變
        if (__result) return;

        // 檢查玩家目前選中的角色是否具備對此 NPC 的權威
        Pawn leader = Find.Selector.SingleSelectedPawn;
        if (leader != null && leader.IsColonistPlayerControlled)
        {
            var authComp = leader.GetComp<CompAuthority>();
            if (authComp != null && authComp.CanDraftNPC(__instance))
            {
                // 如果權威足夠，讓系統認為這個 NPC 目前「受玩家控制」
                __result = true;
            }
        }
    }
}
```

## 3. 指揮官光環 (Leadership Aura)

當領袖在場時，周圍被徵調的 NPC 應獲得戰鬥加成。這可以透過 `Hediff` 與 `Tick` 檢測實作。

```csharp
public class Hediff_LeadershipAura : HediffWithComps
{
    public override void Tick()
    {
        base.Tick();
        if (pawn.IsHashIntervalTick(60)) // 每秒檢查一次
        {
            // 尋找範圍 10 格內的領袖
            Pawn leader = GenRadial.RadialPawnsAround(pawn.Position, pawn.Map, 10f, true)
                .FirstOrDefault(p => p.GetComp<CompAuthority>()?.tier >= 3);

            if (leader != null)
            {
                // 根據領袖魅力 (Social 技能) 給予 Buff 階段
                int socialLevel = leader.skills.GetSkill(SkillDefOf.Social).Level;
                this.Severity = socialLevel / 20f; // 0.0 ~ 1.0
            }
            else
            {
                this.Severity = 0f; // 無領袖在場，Buff 失效
            }
        }
    }
}
```

## 4. 指令 UI (Command Gizmos)

為領袖提供主動技能（如「集結」、「衝鋒」）。

```csharp
public override IEnumerable<Gizmo> CompGetGizmosExtra()
{
    if (this.tier >= 3)
    {
        yield return new Command_Action
        {
            defaultLabel = "全體集結",
            defaultDesc = "強令周圍所有 NPC 向此處靠攏。",
            icon = ContentFinder<Texture2D>.Get("UI/Commands/Rally"),
            action = () => {
                foreach (Pawn p in parent.Map.mapPawns.AllPawnsSpawned)
                {
                    if (CanDraftNPC(p)) p.jobs.TryTakeOrderedJob(JobMaker.MakeJob(JobDefOf.Goto, parent.Position));
                }
            }
        };
    }
}
```

## 5. 聲望懲罰與政治反彈

強制指揮 NPC 不是免費的。

*   **徵調成本**: 每次徵調 NPC，每小時扣除一定量的 `renown`。
*   **傷亡懲罰**: 若被徵調的 NPC 在玩家指揮下死亡，大幅扣除 `renown` 並對派系關係造成紅字影響。
*   **反叛檢測**: 若 `renown` 低於 0 且玩家仍試圖下達命令，觸發 `MentalStateDefOf.SocialFighting` 或讓該據點與玩家敵對。

---
*文件路徑: analysis/rimworld/details/leadership_system_implementation.md*
