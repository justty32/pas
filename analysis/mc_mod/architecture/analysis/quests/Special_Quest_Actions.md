# 特殊任務行為與世界互動深度分析

除了基礎的物資交付，Millénaire 還包含許多與世界地理、生態相關的「特殊行為」任務。

## 1. 地理感應任務 (`SpecialQuestActions.java`)
- **世界頂端與底部**：
    - `TOPOFTHEWORLD` / `BOTTOMOFTHEWORLD`：偵測玩家的 `posY`。例如印度任務中要求玩家抵達世界最深處 (Y < 4)。
- **生物群系探索 (`EXPLORE_TAG`)**：
    - 追蹤玩家是否探索了特定的生物群系（如 Desert, Jungle）。
    - 實作於 `indianCQHandleContinuousExplore` 方法中。

## 2. 動態結構生成
- **`NORMANMARVEL_GENERATE`**：
    - 這是最複雜的任務動作之一，它會在任務進行到特定階段時，動態在世界中生成一個巨大的特殊結構（如諾曼奇蹟建築）。
    - 涉及 `WorldGenVillage` 的動態調用。

## 3. 戰鬥與特殊實體
- **召喚特殊敵對實體**：
    - 例如召喚 `EntityTargetedBlaze` 或 `EntityTargetedWitherSkeleton` 作為任務 Boss。
    - 這些實體通常具有針對特定玩家的鎖定邏輯。

## 4. 1.21.8 的移植挑戰
- **Reflection 替代**：舊版使用了大量的反射 (`ReflectionHelper`) 來獲取生物群系名稱，新版應改為使用 `Registry.BIOME` 與標籤系統。
- **結構生成**：應與 1.21.8 的 `Structure` 與 `Jigsaw` API 結合，以獲得更好的效能與相容性。

## 5. 原始碼位置
- **行為實作**：`OldSource/java/org/millenaire/common/quest/SpecialQuestActions.java`
