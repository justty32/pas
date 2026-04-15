# 任務步驟與目標管理深度分析

每個任務由多個「步驟」(`QuestStep`) 組成，每個步驟都有其特定的目標與後果。

## 1. 步驟生命週期 (`QuestStep.java`)
- **`duration` (持續時間)**：定義了玩家完成該步驟的時限。如果逾時，會觸發 `descriptionsTimeUp`。
- **目標類型**：
    - **物品需求 (`requiredGood`)**：玩家必須向特定 NPC 交付一定數量的物資。
    - **位置抵達**：玩家必須到達特定的座標或建築。

## 2. 成功與失敗的後果
任務步驟的結果會直接改變世界與玩家狀態：
- **聲望獎勵/懲罰 (`rewardReputation` / `penaltyReputation`)**：直接影響玩家在該文化中的地位。
- **標籤操作 (`setPlayerTagsSuccess` / `clearPlayerTagsFailure`)**：這是控制劇情分支的核心機制。
- **NPC 關係變化 (`QuestStepRelationChange`)**：可以改變兩個 NPC 之間的關係值（例如：調解糾紛）。

## 3. 獎勵機制
- **物品獎勵 (`rewardGoods`)**：給予玩家稀有物資或任務專屬物品。
- **金錢獎勵 (`rewardMoney`)**：給予 Deniers (錢幣)。

## 4. 原始碼位置
- **步驟定義**：`OldSource/java/org/millenaire/common/quest/QuestStep.java`
- **NPC 關聯**：`OldSource/java/org/millenaire/common/quest/QuestVillager.java` (定義任務中涉及的特定 NPC 角色)
