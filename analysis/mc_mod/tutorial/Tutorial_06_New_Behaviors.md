# 教學 06：定義新的行為 (Goals)

如果你想讓村民做一些原版沒有的事（例如：去海邊釣魚或在廣場跳舞），你需要定義一個新的 `Goal`。

## 1. 建立 Goal 類別
你的新類別必須繼承自 `Goal`。

```java
public class GoalVikingDance extends Goal {
    public GoalVikingDance() {
        this.key = "viking_dance";
        this.tags.add("leisure"); // 標記為休閒行為
    }

    @Override
    public boolean isPossibleSpecific(MillVillager villager) {
        // 只有在晚上且在村莊中心時才跳舞
        return villager.getTownHall().isNight() && villager.isInTownHall();
    }

    @Override
    public int priority(MillVillager villager) {
        return 10; // 固定優先級
    }

    @Override
    public boolean performAction(MillVillager villager) {
        // 播放動畫封包
        villager.playAnimation("dance");
        return true; 
    }
}
```

## 2. 註冊行為
在 `MillRegistry` 或專屬的 AI 註冊類別中（Phase 5 規劃中）：
```java
public static Goal VIKING_DANCE = new GoalVikingDance();
```

## 3. 分配給職業
行為必須分配給特定的職業 (`VillagerType`)，否則無人會執行。這通常在文化的 `villagerconfig/*.txt` 中定義。

## 4. 參考原始碼位置
- **休閒行為範例：** `OldSource/java/org/millenaire/common/goal/leisure/`
- **生產行為範例：** `OldSource/java/org/millenaire/common/goal/generic/`
