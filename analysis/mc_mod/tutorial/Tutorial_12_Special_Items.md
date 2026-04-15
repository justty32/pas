# 教學 12：新建特殊功能物品 (Advanced Items)

除了普通武器，Millénaire 還有許多具備特殊行為的物品。

## 1. 帶有特殊效果的盔甲
例如「瑪雅任務皇冠」：
```java
public class MayanCrownItem extends ArmorItem {
    @Override
    public void inventoryTick(...) {
        // 每秒給予穿戴者幸運效果
        player.addStatusEffect(new StatusEffectInstance(StatusEffects.LUCK, 200, 0));
    }
}
```

## 2. 消耗性工具
例如「錢幣袋」或「任務捲軸」。你可以繼承自 `Item` 並覆寫 `use()` 方法。

## 3. 自動化註冊
記得將你的特殊類別傳遞給 `MillRegistry.registerItem`：
```java
MY_CROWN = MillRegistry.registerItem("mayan_crown", new MayanCrownItem(...));
```

## 4. 參考路徑
- `src/main/java/me/devupdates/millenaireReborn/common/registry/MillItems.java`
- `src/main/java/me/devupdates/millenaireReborn/common/registry/MillFoodItemBuilder.java`
