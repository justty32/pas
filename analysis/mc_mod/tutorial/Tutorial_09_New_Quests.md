# 教學 09：新建任務種類與邏輯 (Quests)

任務分為「村莊隨機任務」與「創世任務線」。

## 1. 任務結構
- **Quest**: 任務主體。
- **QuestStep**: 任務中的具體步驟。
- **Requirements**: 完成任務所需的物品或聲望。

## 2. 定義任務範例 (物資收集)
```java
public class MyQuestDelivery extends Quest {
    public MyQuestDelivery() {
        this.addStep(new QuestStep("bring_wood")
            .addRequiredItem(Items.OAK_LOG, 10)
            .setReward(MillItems.DENIER, 5));
    }
}
```

## 3. 觸發任務
任務通常由特定職業的村民提供。你可以設定聲望門檻：
```java
if (villager.getReputation(player) > 100) {
    villager.offerQuest(MY_QUEST);
}
```

## 4. 參考原始碼位置
- `OldSource/java/org/millenaire/common/quest/Quest.java`
- `OldSource/java/org/millenaire/common/quest/SpecialQuestActions.java` (處理任務完成後的特殊效果)
