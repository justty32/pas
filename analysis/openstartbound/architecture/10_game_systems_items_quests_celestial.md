# 模塊分析：10_game_systems_items_quests_celestial (遊戲系統：道具、任務與宇宙)

## 1. 道具系統 (Item System)
- **ItemDescriptor：** 系統中流動的數據單元。包含 `name` (ID)、`count` 與一個強大的 JSON `parameters` 物件。
- **動態屬性：** 通過 JSON parameters，同一個道具 ID 可以在運行時具有不同的屬性（如隨機生成的武器傷害、剩餘耐久度）。
- **容器管理 (PlayerInventory)：** 處理道具的堆疊、自動合併、過濾與快速訪問索引。

## 2. 任務系統 (QuestManager)
- **基於狀態的任務：** 任務在 C++ 中被建模為一組狀態與條件。
- **腳本化任務：** 複雜任務邏輯（如「保護 NPC 到達 A 點」）完全由 Lua 驅動，`QuestManager` 僅負責生命週期管理與網路同步。

## 3. 宇宙與星系生成 (Celestial Database)
- **過程生成 (ProcGen)：** 整個宇宙基於一個全局 64 位元種子。給定座標 $(x, y)$，系統始終能生成相同的行星屬性。
- **CelestialCoordinate：** 一個緊湊的標識符，定位行星在星系、軌道中的精確位置。
- **數據持久化：** 僅存儲玩家修改過的星球數據。未訪問或未修改的星球僅存在於算法定義中，極大地節省了存儲空間。
