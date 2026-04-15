# 實體子類分析：15_entity_subclass_object (交互物件)

`Object` 代表世界中佔據固定瓦片位置的實體（如工作檯、儲物箱、開關）。

## 1. 瓦片空間鎖定
物件與一般的實體（Entity）不同，它們與 `TileArray` 深度綁定。
- **佔用區域 (Tile Mapping)：** 每個物件定義了一個 `orientations` 與 `tiles` 佔用圖。
- **靜態網格整合：** 物件在放置時會鎖定其覆蓋的瓦片區域，防止在該區域放置其他方塊或物件。

## 2. 功能子類 (Functional Subclasses)
物件通過繼承實現了多樣化的功能：
- **ContainerObject：** 擴展了背包功能，提供 UI 容器供玩家存放道具。
- **PhysicsObject：** 具有物理碰撞邊界的物件（如門）。
- **FarmableObject：** 具有生長周期的農作物，負責計時並切換生長階段的精靈圖。
- **LoungeableObject：** 允許玩家「坐下」或「躺下」的物件，管理實體的座標錨點（Anchor Points）。

## 3. 接線系統 (Wiring System)
`Object` 是引擎中自動化邏輯的核心。
- **輸入/輸出節點 (Wire Nodes)：** 物件可以定義多個 Wire In/Out 點。
- **信號傳遞：** `WireProcessor` 負責在世界 Tick 期間傳遞邏輯信號（0 或 1），實現電路與邏輯門。

## 4. 交互機制 (Interaction)
物件實現了 `InteractiveEntity` 接口。
- **交互回調：** 當玩家按下交互鍵（預設為 E）時，觸發 C++ 或 Lua 端的 `onInteraction` 事件。
- **配置驅動：** 物件的交互行為（如打開 UI、播放音效、切換開關狀態）完全由其 `.object` 配置文件與腳本決定。
