# 整合實作：從天賦解鎖到技能欄同步

要實作「點擊天賦 -> 獲得技能 -> 技能欄顯示」的流程，需要一套結構化的數據管理方案，確保 UI、邏輯與存檔三方同步。

## 1. 數據結構定義 (Data Definitions)

首先，我們需要將「技能」定義為 RimWorld 的 `Def`，以便於配置與擴充。

### A. SkillDef (XML 配置)
```xml
<RimWorldARPG.SkillDef>
    <defName>Fireball</defName>
    <label>火球術</label>
    <description>向目標發射一顆爆炸火球。</description>
    <iconPath>UI/Skills/Fireball</iconPath>
    <manaCost>20</manaCost>
    <cooldownTicks>300</cooldownTicks> <!-- 5秒 -->
    <workerClass>RimWorldARPG.SkillWorker_Fireball</workerClass>
</RimWorldARPG.SkillDef>
```

### B. TalentDef (天賦節點)
```xml
<RimWorldARPG.TalentDef>
    <defName>Talent_Fireball_Unlock</defName>
    <label>火焰初心</label>
    <unlocksSkill>Fireball</unlocksSkill>
    <prerequisites>
        <li>Talent_ManaBasics</li>
    </prerequisites>
</RimWorldARPG.TalentDef>
```

## 2. 核心組件：Pawn_SkillTracker

我們需要一個掛載在 Pawn 上的 `ThingComp` 來管理其擁有的技能與快捷欄配置。

```csharp
public class CompSkillTracker : ThingComp
{
    // 已解鎖的天賦
    public HashSet<TalentDef> unlockedTalents = new HashSet<TalentDef>();
    
    // 目前快捷欄配置 (槽位 -> 技能)
    public SkillDef[] actionBar = new SkillDef[5];

    // 當天賦解鎖時呼叫
    public void UnlockTalent(TalentDef talent)
    {
        if (unlockedTalents.Contains(talent)) return;

        unlockedTalents.Add(talent);
        
        // 如果該天賦會解鎖技能，自動尋找空槽位加入
        if (talent.unlocksSkill != null)
        {
            AssignSkillToEmptySlot(talent.unlocksSkill);
        }
    }

    private void AssignSkillToEmptySlot(SkillDef skill)
    {
        for (int i = 0; i < actionBar.Length; i++)
        {
            if (actionBar[i] == null)
            {
                actionBar[i] = skill;
                Messages.Message($"{skill.label} 已加入快捷欄槽位 {i+1}", MessageTypeDefOf.PositiveEvent);
                break;
            }
        }
    }

    public override void PostExposeData()
    {
        base.PostExposeData();
        Scribe_Collections.Look(ref unlockedTalents, "unlockedTalents", LookMode.Def);
        // 存檔快捷欄 (略)
    }
}
```

## 3. UI 交互流程 (The Loop)

1.  **天賦界面 (Talent Window)**:
    *   玩家點擊「解鎖」按鈕。
    *   代碼呼叫 `pawn.GetComp<CompSkillTracker>().UnlockTalent(selectedTalent)`。
2.  **邏輯層 (Logic Layer)**:
    *   `UnlockTalent` 將天賦標記為已擁有。
    *   檢查 `unlocksSkill` 欄位。
    *   掃描 `actionBar` 數組，找到第一個為 `null` 的位置並填入。
3.  **快捷欄界面 (Action Bar Window)**:
    *   `Window_ActionBar` 在每幀的 `DoWindowContents` 中讀取 `pawn.GetComp<CompSkillTracker>().actionBar`。
    *   因為是 IMGUI，下一幀 UI 就會自動繪製出新獲得的技能圖示。

## 4. 進階：技能拖拽與替換

如果 5 個槽位都滿了，玩家需要手動管理。這可以透過 RimWorld 的 `Widgets.ButtonInvisible` 結合 `Event.current` 實作：

*   **開始拖拽**: 當點擊技能圖示且移動滑鼠時，將 `SkillDef` 存入一個全域的 `DraggingSkill` 變量。
*   **放置技能**: 當在另一個槽位放開滑鼠時，交換 `actionBar` 數組中的對應元素。

---
*文件路徑: analysis/rimworld/details/talent_skill_integration.md*
