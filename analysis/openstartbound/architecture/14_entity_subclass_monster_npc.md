# 實體子類分析：14_entity_subclass_monster_npc (動態 AI 實體)

## 1. 變體生成系統 (Variant System)
`Monster` 與 `NPC` 並非硬編碼的類，而是高度依賴配置生成的實體。
- **MonsterVariant：** 一個 Monster 實體由 `Type` (如 `poptop`)、`Seed` (種子) 與 `Level` 組成。引擎根據種子從 `MonsterDatabase` 計算其外觀、血量與技能。
- **NPC 身份生成：** NPC 包含複雜的身份信息（Identity），包括種族、姓名、對話風格（Personality）以及動態生成的服裝。

## 2. 行為樹與 Lua AI (Scripting)
- **腳本架構：** `Monster.cpp` 與 `Npc.cpp` 本身不包含具體的戰鬥或交互 AI。所有的行為邏輯都在 Lua 中通過 `update` 函數驅動。
- **行為樹回調 (Behavior Callbacks)：** 提供諸如 `monster.setAggressive()`, `npc.say()`, `entity.distanceTo()` 等 API，供 Lua 端快速調用 C++ 的物理與導航功能。

## 3. 導航與路徑規劃 (Platformer A*)
- **A* 尋路：** 針對橫版跳躍環境優化的路徑規劃。考慮了跳躍高度、掉落損傷與方塊間隔。
- **物理控制器 (ActorMovementController)：** 封裝了平滑的路徑跟隨與避障逻辑。

## 4. 掉落與死亡邏輯 (Drop Pools)
當實體死亡時，它會調用 `MonsterDatabase::getDropPool()`。掉落物會根據實體等級與玩家的幸運值進行加成，並實例化為 `ItemDrop` 實體。
