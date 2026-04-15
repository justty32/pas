# 模塊分析：09_game_entity_hierarchy_and_logic (實體體系與邏輯)

## 1. 實體類層次 (Entity Hierarchy)
OpenStarbound 使用深度的類繼承結合組件模式。
- **Entity 基類：** 提供 `entityId`, `position`, `velocity` 等基礎屬性與 `NetElement` 同步接口。
- **Actor 類實體 (Player, Monster, NPC)：**
  - **移動控制 (ActorMovementController)：** 封裝了複雜的平台跳躍物理、摩擦力與重力模擬。
  - **狀態控制器 (StatusController)：** 負責生命值、能量、屬性修改器（Stat Modifiers）與狀態效果（Status Effects）。
  - **動畫器 (NetworkedAnimator)：** 處理基於狀態機的動畫切換，並自動在網路間同步當前動畫狀態。

## 2. Master/Slave 同步模型
- **Master 模式 (服務器端)：** 運行完整的 Lua AI、執行物理判定並產生 `NetDelta`。
- **Slave 模式 (客戶端鏡像)：** 僅接收 Delta 更新。為了平滑顯示，Slave 實體會執行 **Dead Reckoning (航位推算)** 與位置插值。

## 3. Lua 腳本注入 (ScriptComponent)
每個 Actor 實體都嵌入了一個 `ScriptComponent`，它將 C++ 功能暴露給 Lua。
- **回調綁定 (Callbacks)：** 透過 `makeEntityCallbacks`, `makeMonsterCallbacks` 等將 C++ 方法導出。
- **異步邏輯：** AI 行為樹通常在 Lua 中實現，每 Tick 調用 Lua 的 `update` 函數。
- **性能平衡：** 關鍵路徑（如碰撞檢測）在 C++ 中硬編碼，而決策邏輯（如「是否攻擊玩家」）在 Lua 中定義。
