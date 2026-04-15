# 05 - 地圖與區域管理系統

## 5.1 概述

OpenNefia 的地圖系統分為兩個層次：
- **Map（地圖）** — 一個具體的磁磚網格，實體可以在上面存在
- **Area（區域）** — 由多個地圖組成的邏輯位置（如：一個地城有多層）

相關檔案：
- `OpenNefia.Core/Maps/MapManager.cs` — 地圖管理器
- `OpenNefia.Core/Maps/Map.cs` — 地圖資料結構
- `OpenNefia.Core/Areas/AreaManager.cs` — 區域管理器
- `OpenNefia.Core/Maps/MapCoordinates.cs` — 地圖座標
- `OpenNefia.Core/Maps/EntityCoordinates.cs` — 實體座標

## 5.2 Map（地圖）

### IMap 介面
```csharp
public interface IMap
{
    MapId Id { get; }                    // 唯一識別碼
    EntityUid MapEntityUid { get; }      // 對應的實體 UID（地圖也是一個實體）
    int Width { get; }                   // 地圖寬度（格子數）
    int Height { get; }                  // 地圖高度（格子數）
    
    // 磁磚存取
    Tile GetTile(Vector2i pos);
    void SetTile(Vector2i pos, Tile tile);
    
    // 視野 / FOV
    int LastSightId { get; set; }
    bool IsInWindowFov(Vector2i pos);
    
    // 記憶系統
    TileMemory[,] TileMemory { get; }
    MapObjectMemory MapObjectMemory { get; }
    
    // 臟位追蹤（增量更新）
    HashSet<Vector2i> DirtyTiles { get; }
}
```

### Map 內部實作（Map.cs）
```csharp
internal sealed class Map : IMap
{
    // 磁磚資料（二維陣列）
    private Tile[,] _tiles;
    
    // 磁磚標誌（用於快速查詢，如是否可通行）
    private TileFlag[,] _tileFlags;
    
    // 視野記憶（玩家曾見過的磁磚）
    public TileMemory[,] TileMemory { get; }
    
    // 實體記憶（玩家曾見過的實體位置）
    public MapObjectMemory MapObjectMemory { get; }
    
    // 需要重繪的磁磚集合（增量渲染優化）
    public HashSet<Vector2i> DirtyTiles { get; } = new();
}
```

### MapId — 地圖識別碼
```csharp
public readonly struct MapId : IEquatable<MapId>
{
    private readonly int Value;
    
    public static readonly MapId Nullspace = new(0);  // 無效地圖
    public static readonly MapId Global = new(1);     // 全域地圖（永不活動）
    public static readonly MapId FirstId = new(2);    // 第一個可用 ID
}
```

**特殊地圖：**
- `MapId.Nullspace` — 表示「無地圖」（剛建立但尚未放置到地圖的實體）
- `MapId.Global` — 全域地圖，用於存放不屬於任何地圖的全域實體（不能被設為活動地圖）

## 5.3 MapManager — 地圖管理器

```csharp
public sealed partial class MapManager : IMapManagerInternal
{
    [Dependency] private readonly IEntityManager _entityManager = default!;
    
    // 所有已載入的地圖（MapId → IMap）
    private protected readonly Dictionary<MapId, IMap> _maps = new();
    
    // 地圖對應的實體（MapId → EntityUid）
    private protected readonly Dictionary<MapId, EntityUid> _mapEntities = new();
    
    // 當前活動地圖（玩家所在的地圖）
    public IMap? ActiveMap { get; private set; } = null;
    
    // 下一個可用的地圖 ID
    public int NextMapId { get; set; } = (int)MapId.FirstId;
}
```

### 地圖與實體的關聯
每個地圖都有一個對應的**地圖實體（Map Entity）**，這個實體持有 `MapComponent`，並作為所有在此地圖上的實體的**父節點**：

```
地圖實體（MapEntity）
    └─ 玩家實體
    └─ NPC 實體 1
    └─ NPC 實體 2
    └─ 物品實體
    └─ ...
```

```csharp
// 建立新地圖
private EntityUid RebindMapEntity(MapId actualID, IMap map)
{
    var newEnt = _entityManager.CreateEntityUninitialized(null);
    
    // 添加 MapComponent，設定 MapId
    var mapComp = _entityManager.AddComponent<MapComponent>(newEnt);
    mapComp.MapId = actualID;
    
    // 發送 MapCreatedEvent
    var ev = new MapCreatedEvent(map, loadedFromSave: false);
    _entityManager.EventBus.RaiseLocalEvent(map.MapEntityUid, ev);
    
    return newEnt;
}
```

### 主要操作
```csharp
// 建立地圖（自動分配 ID）
IMap map = _mapManager.CreateMap(width: 60, height: 40);

// 建立地圖（指定 ID）
IMap map = _mapManager.CreateMap(width: 60, height: 40, mapId: specificMapId);

// 設定活動地圖（玩家所在地圖）
_mapManager.SetActiveMap(mapId);

// 卸載地圖（刪除所有在此地圖上的實體）
_mapManager.UnloadMap(mapId);

// 取得地圖
IMap map = _mapManager.GetMap(mapId);
bool exists = _mapManager.TryGetMap(mapId, out IMap? map);

// 刷新視野（FOV）
_mapManager.RefreshVisibility(map);
```

### 視野刷新流程
```csharp
public void RefreshVisibility(IMap map)
{
    map.LastSightId++;    // 增加視野 ID（用於失效快取）
    
    // 發送 RefreshMapVisibilityEvent（各系統可以響應此事件計算 FOV）
    var ev = new RefreshMapVisibilityEvent(map);
    _entityManager.EventBus.RaiseLocalEvent(map.MapEntityUid, ref ev);
    
    // 隱藏不在視野內且標記為「離開視野時隱藏」的物件
    var outOfSightCoords = map.MapObjectMemory.AllMemory.Values
        .Where(memory => memory.HideWhenOutOfSight && !map.IsInWindowFov(memory.Coords.Position))
        .Select(memory => memory.Coords)
        .Distinct();
    
    foreach (var coords in outOfSightCoords)
        map.MapObjectMemory.HideObjects(coords.Position);
}
```

## 5.4 Area（區域）

區域代表遊戲中的一個邏輯位置（如：某個城鎮、某個地城）。一個區域由多個樓層（Floor）組成，每個樓層對應一個地圖。

```csharp
public class Area : IArea
{
    public AreaId Id { get; }            // 區域唯一識別碼
    public EntityUid AreaEntityUid { get; }  // 對應的實體
    public AreaId? ParentId { get; }     // 父區域（如：地城屬於某個城鎮）
    
    // 所有樓層（AreaFloorId → AreaFloor）
    public Dictionary<AreaFloorId, AreaFloor> Floors { get; } = new();
}

public class AreaFloor
{
    public MapId? MapId { get; set; }    // 對應的地圖（null = 尚未生成）
    public AreaFloorId FloorId { get; }  // 樓層識別碼
}
```

### AreaId — 區域識別碼
```csharp
public readonly struct AreaId
{
    private readonly int Value;
}

// GlobalAreaId — 全域識別碼（跨存檔的穩定識別）
public readonly struct GlobalAreaId
{
    private readonly int Value;
}
```

### AreaFloorId — 樓層識別碼
```csharp
public readonly struct AreaFloorId
{
    private readonly int Value;
    
    public static readonly AreaFloorId Default = new(0);  // 預設樓層
}
```

## 5.5 AreaManager — 區域管理器

```csharp
public interface IAreaManager
{
    IReadOnlyDictionary<AreaId, IArea> LoadedAreas { get; }
    IArea? ActiveArea { get; }
    
    event ActiveAreaChangedDelegate? ActiveAreaChanged;
    
    // 建立區域（可選擇指定原型和全域 ID）
    IArea CreateArea(
        PrototypeId<EntityPrototype>? areaEntityProtoId,
        GlobalAreaId? globalId = null,
        AreaId? parent = null
    );
    
    // 刪除區域（同時刪除所有樓層地圖）
    void DeleteArea(AreaId areaId);
    
    // 樓層管理
    void RegisterAreaFloor(IArea area, AreaFloorId floorId, IMap map);
    void RegisterAreaFloor(IArea area, AreaFloorId floorId, MapId mapId);
    void UnregisterAreaFloor(IArea area, AreaFloorId floorId);
    
    // 查詢某個地圖屬於哪個區域
    bool TryGetAreaOfMap(MapId map, out IArea? area);
    bool TryGetAreaAndFloorOfMap(MapId map, out IArea? area, out AreaFloorId floorId);
    
    // 取得或生成樓層的地圖
    MapId? GetOrGenerateMapForFloor(AreaId areaId, AreaFloorId floorId);
    
    // 全域區域（跨存檔識別）
    bool GlobalAreaExists(GlobalAreaId globalId);
    IArea GetGlobalArea(GlobalAreaId globalId);
}
```

### 取得或生成樓層地圖
```csharp
// 若樓層的地圖已存在（載入或記憶體中），直接返回
// 若不存在，觸發地圖生成邏輯
MapId? mapId = _areaManager.GetOrGenerateMapForFloor(areaId, floorId);
```

## 5.6 地圖記憶系統

地圖記憶系統儲存玩家「曾見過」的磁磚和實體，即使它們已不在視野範圍內也能顯示：

### TileMemory
```csharp
public struct TileMemory
{
    public Tile Tile { get; set; }          // 記憶中的磁磚
    public int LastSightId { get; set; }    // 最後看到時的視野 ID
    public bool Remembered { get; set; }    // 是否已被記憶
}
```

### MapObjectMemory
```csharp
public class MapObjectMemory
{
    // 所有記憶中的物件
    public Dictionary<EntityUid, MapObjectMemoryData> AllMemory { get; }
    
    // 隱藏特定位置的物件
    public void HideObjects(Vector2i position);
    
    // 更新記憶中的物件
    public void UpdateObject(EntityUid uid, EntityCoordinates coords, bool hideWhenOutOfSight);
}
```

## 5.7 地圖磁磚系統

### Tile（磁磚）
```csharp
public struct Tile
{
    public ushort TypeId { get; }    // 磁磚類型 ID
    // （磁磚實際資料存在 TileDefinition 中）
}
```

### TileDefinition（磁磚定義）
```csharp
public class TileDefinition
{
    public string ID { get; }           // 磁磚 ID（如 "Elona.FloorNormal"）
    public bool IsOpaque { get; }       // 是否阻擋視線
    public bool IsWall { get; }         // 是否為牆壁
    public bool IsPassable { get; }     // 是否可通行
    public int TileIndex { get; }       // 在圖集中的索引
}
```

### TileDefinitionManager
```csharp
public interface ITileDefinitionManager
{
    TileDefinition this[int tileIndex] { get; }
    TileDefinition this[string tileId] { get; }
    
    void RegisterAll();         // 掃描並注冊所有 TileDefinition
}
```

## 5.8 座標系統詳解

### EntityCoordinates（實體座標）
相對於父實體的座標，用於實體定位：

```csharp
public readonly struct EntityCoordinates
{
    public EntityUid EntityId { get; }   // 父實體（通常是地圖實體）
    public Vector2 Position { get; }     // 在父座標系中的位置
    
    // 驗證座標是否有效
    public bool IsValid(IEntityManager entityManager);
    
    // 轉換為地圖絕對座標
    public MapCoordinates ToMap(IEntityManager entityManager);
    
    // 取得地圖 ID
    public MapId GetMapId(IEntityManager entityManager);
    
    // 計算相對偏移
    public EntityCoordinates Offset(Vector2i offset);
    public EntityCoordinates Offset(int x, int y);
}
```

### MapCoordinates（地圖座標）
地圖上的絕對座標：

```csharp
public readonly struct MapCoordinates
{
    public MapId MapId { get; }          // 地圖 ID
    public Vector2i Position { get; }    // 在地圖格子中的位置（整數）
    
    // 無效座標（用於表示「不在任何地圖上」）
    public static readonly MapCoordinates Nullspace = new(MapId.Nullspace, Vector2i.Zero);
    
    // 相鄰格子
    public MapCoordinates Offset(Direction dir);
    public MapCoordinates Offset(Vector2i offset);
}
```

## 5.9 MapComponent — 地圖組件

每個地圖實體都有此組件：

```csharp
[RegisterComponent]
public class MapComponent : Component
{
    public override string Name => "Map";
    
    public MapId MapId { get; set; }     // 此實體代表的地圖 ID
}
```

## 5.10 事件系統

地圖相關的主要事件：

```csharp
// 地圖建立時發送
public sealed class MapCreatedEvent : EntityEventArgs
{
    public IMap Map { get; }
    public bool LoadedFromSave { get; }
}

// 刷新視野時發送（ref 結構，用於高效處理）
[EventArgsUsage(EventArgsTargets.ByRef)]
public struct RefreshMapVisibilityEvent
{
    public IMap Map { get; }
}

// 活動地圖改變時的委託
public delegate void ActiveMapChangedDelegate(IMap newMap, IMap? oldMap);
```
