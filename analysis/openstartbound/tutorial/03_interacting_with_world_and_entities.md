# 教學 03：與世界與實體交互

這是 Lua Modding 最強大的部分：透過 `world` 命名空間與 C++ 核心引擎進行通信。

## 1. `world` 命名空間常用 API
`world` 表提供了查詢與修改世界狀態的接口：

### 實體查詢
- `world.entityQuery(pos, radius, options)`：返回半徑內符合條件的實體 ID 列表。
- `world.closestEntity(pos, radius)`：返回最近的實體 ID。
- `world.entityType(entityId)`：返回實體類型（如 `"player"`, `"monster"`）。

### 物理與幾何
- `world.magnitude(pos1, pos2)`：計算兩點之間的距離（考慮星球環面幾何）。
- `world.distance(pos1, pos2)`：返回兩點之間的位移向量。
- `world.lineTileCollision(pos1, pos2)`：檢查兩點連線是否穿過方塊碰撞。

### 狀態修改
- `world.sendEntityMessage(entityId, messageName, ...)`：跨實體發送異步消息。這是 Mod 間通信的核心。
- `world.spawnProjectile(type, position, sourceId, direction, ...)`：生成彈射物。

## 2. 實體屬性獲取
- `world.entityPosition(entityId)`：獲取位置。
- `world.entityHealth(entityId)`：獲取血量（若實體有生命值）。

## 3. 實作練習：光環治療
以下腳本展示了如何每秒搜尋附近的玩家並進行治療：

```lua
local timer = 0

function update(dt)
  timer = timer + dt
  if timer >= 1.0 then
    timer = 0
    -- 搜尋半徑 10 內的實體
    local players = world.entityQuery(entity.position(), 10, {
      includedTypes = {"player"}
    })

    for _, playerId in ipairs(players) do
      -- 向玩家發送消息，讓玩家自身的腳本處理治療
      world.sendEntityMessage(playerId, "applyHealing", 5)
    end
  end
end
```

這套機制展示了 C++ 負責高效的空間查詢，而 Lua 負責定義靈活的交互邏輯。
