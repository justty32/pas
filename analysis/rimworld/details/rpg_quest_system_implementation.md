# RPG 任務系統：冒險者公會與程序化任務的 C# 實作

RimWorld 原生的 `Quest` 系統非常強大但寫起來相對複雜（基於 `QuestScriptDef`）。為了實作「RPG 冒險者公會」，我們需要簡化流程，並實作自定義的任務節點。

## 1. 任務數據結構：QuestPart_CustomReward

我們需要將任務完成與我們先前實作的「名望 (Renown)」與「天賦解鎖」掛鉤。

```csharp
public class QuestPart_GiveRenown : QuestPart
{
    public Pawn leader;
    public float renownAmount;

    // 當任務成功完成時觸發
    public override void Notify_QuestSignalReceived(Signal signal)
    {
        base.Notify_QuestSignalReceived(signal);
        if (signal.tag == quest.AddedSignalTag("Success"))
        {
            var authComp = leader.GetComp<CompAuthority>();
            if (authComp != null)
            {
                authComp.renown += renownAmount;
                Messages.Message($"任務完成！領袖 {leader.LabelShort} 獲得了 {renownAmount} 點名望。", MessageTypeDefOf.PositiveEvent);
            }
        }
    }

    public override void ExposeData()
    {
        base.ExposeData();
        Scribe_References.Look(ref leader, "leader");
        Scribe_Values.Look(ref renownAmount, "renownAmount");
    }
}
```

## 2. 討伐任務邏輯：QuestPart_BossHunt

實作一個追蹤大地圖上特定目標（如 Boss 或 據點）被擊毀的任務部分。

```csharp
public class QuestPart_BossHunt : QuestPart
{
    public WorldObject targetSite;

    public override void Notify_QuestSignalReceived(Signal signal)
    {
        // 監聽世界物體被摧毀的信號
        if (targetSite != null && targetSite.Destroyed)
        {
            // 向任務系統發送成功信號
            Find.SignalManager.SendSignal(new Signal(quest.AddedSignalTag("Success")));
        }
    }
}
```

## 3. 公會佈告欄 UI (Guild Noticeboard)

這是一個特殊的 `Building` 交互 UI，讓玩家能主動「領取」任務。

```csharp
public class Building_GuildNoticeboard : Building
{
    public override IEnumerable<Gizmo> GetGizmos()
    {
        foreach (var g in base.GetGizmos()) yield return g;

        yield return new Command_Action
        {
            defaultLabel = "檢視佈告欄",
            defaultDesc = "瀏覽公會當前發布的冒險任務。",
            icon = ContentFinder<Texture2D>.Get("UI/Icons/QuestBoard"),
            action = () => Find.WindowStack.Add(new Window_QuestBoard())
        };
    }
}

public class Window_QuestBoard : Window
{
    public override void DoWindowContents(Rect inRect)
    {
        Listing_Standard listing = new Listing_Standard();
        listing.Begin(inRect);
        
        listing.Label("--- 當前委託 ---");
        
        // 這裡可以動態生成幾個隨機任務選項
        if (listing.ButtonText("討伐任務：機械族收割者 (難度: 高)"))
        {
            GenerateBossQuest();
            this.Close();
        }

        listing.End();
    }

    private void GenerateBossQuest()
    {
        // 使用 QuestMaker 程式化生成任務
        Quest quest = QuestMaker.MakeQuest(YourQuestScriptDefOf.BossHuntBase);
        quest.name = "鋼鐵收割者的終結";
        Find.QuestManager.Add(quest);
    }
}
```

## 4. 程序化生成流程 (Scripting)

1.  **觸發**: 玩家點擊佈告欄。
2.  **生成**: `QuestMaker` 根據玩家當前的「公會聲望」選擇難度係數。
3.  **選址**: 在大地圖上隨機挑選一個 5-10 格內的 Tile，生成一個 `Site` (Boss 據點)。
4.  **連結**: 將 `QuestPart_BossHunt` 與該 `Site` 連結。
5.  **獎勵**: 加入 `QuestPart_GiveItem` 與我們自定義的 `QuestPart_GiveRenown`。

## 5. 技術難點：地圖封存下的任務結算

如果任務目標在一個「哨站」所在的 Tile，且該地圖未載入：
*   **解決方案**: 必須在 `WorldComponent` 中監聽該 Tile 的狀態變更。當哨站的「虛擬防禦邏輯」判定成功擊退襲擊時，手動向 `QuestManager` 發送信號，確保玩家不在場時也能完成護衛或防禦任務。

---
*文件路徑: analysis/rimworld/details/rpg_quest_system_implementation.md*
