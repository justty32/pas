# 03 - Entity-Component-System（ECS）核心架構

## 3.1 概述

OpenNefia 的遊戲物件系統基於 **ECS（Entity-Component-System）** 架構。這是整個引擎最核心的設計模式。

相關檔案：
- `OpenNefia.Core/GameObjects/EntityManager.cs` — 實體管理器
- `OpenNefia.Core/GameObjects/Component.cs` — 組件基底類別
- `OpenNefia.Core/GameObjects/EntitySystem.cs` — 系統基底類別
- `OpenNefia.Core/GameObjects/EntityEventBus.Broadcast.cs` — 廣播事件匯流排
- `OpenNefia.Core/GameObjects/EntityEventBus.Directed.cs` — 定向事件匯流排
- `OpenNefia.Core/GameObjects/EntityEventBus.Ordering.cs` — 事件排序系統

## 3.2 三大核心概念

### Entity（實體）
- 就是一個整數 ID（`EntityUid`）
- 本身不含任何資料或邏輯
- 是組件的容器

```csharp
// EntityUid 只是一個結構體，包裝一個 int
public readonly struct EntityUid : IEquatable<EntityUid>
{
    internal readonly int Uid;
    public static readonly EntityUid Invalid = new(0);
    public static readonly EntityUid FirstUid = new(1);
    
    public bool IsValid() => Uid > 0;
}
```

### Component（組件）
- 純資料容器，**不含邏輯**
- 以 `[DataField]` 標記可被序列化的欄位
- 以 `[RegisterComponent]` 標記自動注冊

```csharp
[RegisterComponent]
public class SkillsComponent : Component
{
    public override string Name => "Skills";
    
    [DataField] public int HP { get; set; }
    [DataField] public int MaxHP { get; set; }
    [DataField] public Stat<int> DV { get; set; } = new(0);
    [DataField] public Dictionary<PrototypeId<SkillPrototype>, LevelAndPotential> Skills { get; } = new();
}
```

### EntitySystem（系統）
- 包含所有邏輯
- 訂閱事件並處理組件資料
- 透過 `[Dependency]` 注入依賴

```csharp
public sealed class VanillaAISystem : EntitySystem
{
    [Dependency] private readonly IMapManager _mapManager = default!;
    [Dependency] private readonly IRandom _random = default!;
    
    public override void Initialize()
    {
        // 訂閱事件
        SubscribeLocalEvent<VanillaAIComponent, NPCTurnStartedEvent>(HandleNPCTurnStarted);
    }
    
    private void HandleNPCTurnStarted(EntityUid uid, VanillaAIComponent ai, ref NPCTurnStartedEvent args)
    {
        // 處理邏輯
        args.Handle(RunVanillaAI(uid, ai));
    }
}
```

## 3.3 EntityManager — 實體管理器

`EntityManager`（實作 `IEntityManager`）是 ECS 的核心，管理所有實體的生命週期。

### 主要職責
- 建立 / 刪除實體
- 管理實體的組件
- 提供事件匯流排
- 追蹤所有活存實體

### 關鍵狀態
```csharp
public partial class EntityManager : IEntityManager
{
    // 所有活存實體的 UID 集合
    private readonly HashSet<EntityUid> Entities = new();
    
    // 待刪除佇列（延遲刪除以避免迭代時修改集合）
    private readonly Queue<EntityUid> QueuedDeletions = new();
    
    // 事件匯流排
    private EntityEventBus _eventBus = null!;
    
    // 下一個可用的實體 UID（自動遞增）
    public int NextEntityUid { get; set; } = (int)EntityUid.FirstUid;
}
```

### 實體建立流程
```csharp
// 1. 分配實體（設定 MetaData 和 Spatial 組件）
EntityUid AllocEntity(PrototypeId<EntityPrototype>? prototypeId, EntityUid? uid = null)

// 2. 載入組件（從原型定義載入所有組件）
EntityUid CreateEntity(PrototypeId<EntityPrototype>? prototypeName, ...)

// 3. 初始化並啟動
void InitializeAndStartEntity(EntityUid uid, MapId mapId)
    → InitializeEntity(uid)   → 呼叫所有組件的 Initialize()
    → StartEntity(uid)        → 呼叫所有組件的 Startup()
    → MapInitExt.RunMapInit() → 若地圖已初始化，執行地圖初始化

// 完整流程（對外公開 API）：
EntityUid SpawnEntity(PrototypeId<EntityPrototype>? protoId, EntityCoordinates coordinates)
```

### 實體刪除流程
```csharp
void DeleteEntity(EntityUid e)
    ↓
void RecursiveDeleteEntity(EntityUid uid)
    1. 設定 LifeStage = Terminating
    2. 設定 Liveness = DeadAndBuried
    3. 發送 EntityTerminatingEvent
    4. 遞迴刪除所有子實體（children）
    5. 呼叫所有組件的 LifeShutdown()
    6. 從父節點分離（DetachParentToNull）
    7. 銷毀所有組件（DisposeComponents）
    8. 設定 LifeStage = Deleted
    9. 發送 EntityDeletedEvent
    10. 從 Entities 集合中移除
```

## 3.4 Component — 組件生命週期

每個組件都有精確的生命週期狀態機，防止初始化順序錯誤：

```
PreAdd → Adding → Added → Initializing → Initialized → Starting → Running
                                                                      ↓
                                                               Stopping → Stopped → Removing → Deleted
```

| 狀態 | 觸發方法 | 說明 |
|------|---------|------|
| `PreAdd` | — | 剛被分配，尚未加入實體 |
| `Adding` | `LifeAddToEntity()` | 正在加入實體 |
| `Added` | `OnAdd()` → 呼叫者設定 | 已加入，其他組件可能尚未添加 |
| `Initializing` | `LifeInitialize()` | 正在初始化 |
| `Initialized` | `Initialize()` → 呼叫者設定 | 所有組件已添加，但不保證初始化完成 |
| `Starting` | `LifeStartup()` | 正在啟動 |
| `Running` | `Startup()` → 呼叫者設定 | 正常運行中 |
| `Stopping` | `LifeShutdown()` | 正在關閉 |
| `Stopped` | `Shutdown()` → 呼叫者設定 | 已停止 |
| `Removing` | `LifeRemoveFromEntity()` | 正在從實體移除 |
| `Deleted` | `OnRemove()` → 呼叫者設定 | 已刪除 |

### 組件生命週期事件

每個階段轉換都會透過 `EventBus` 發送對應事件：

```csharp
protected virtual void OnAdd()
{
    GetBus().RaiseComponentEvent(this, CompAddInstance);     // ComponentAdd 事件
    LifeStage = ComponentLifeStage.Added;
}

protected virtual void Initialize()
{
    GetBus().RaiseComponentEvent(this, CompInitInstance);    // ComponentInit 事件
    LifeStage = ComponentLifeStage.Initialized;
}

protected virtual void Startup()
{
    GetBus().RaiseComponentEvent(this, CompStartupInstance); // ComponentStartup 事件
    LifeStage = ComponentLifeStage.Running;
}
```

### 覆寫生命週期方法
```csharp
[RegisterComponent]
public class MyComponent : Component
{
    public override string Name => "MyComp";
    
    protected override void Initialize()
    {
        base.Initialize();  // 必須呼叫 base，否則生命週期狀態機會出錯
        // 初始化邏輯...
    }
    
    protected override void Startup()
    {
        base.Startup();
        // 啟動邏輯...
    }
}
```

## 3.5 EntitySystem — 系統基底類別

`EntitySystem` 是所有系統的抽象基底，提供：

### 可覆寫的生命週期方法
```csharp
public abstract partial class EntitySystem : IEntitySystem
{
    public virtual void Initialize() { }          // 系統初始化
    public virtual void Update(float frameTime) { } // 每幀更新（遊戲邏輯）
    public virtual void FrameUpdate(float frameTime) { } // 每幀更新（渲染相關）
    public virtual void Shutdown() { ... }         // 系統關閉（自動取消訂閱）
}
```

### 事件訂閱 API
```csharp
// 訂閱廣播事件（不針對特定實體）
SubscribeLocalEvent<SomeEvent>(HandleSomeEvent);

// 訂閱定向事件（針對有特定組件的實體）
SubscribeLocalEvent<SomeComponent, SomeEvent>(HandleSomeEvent);

// 訂閱組件事件（組件生命週期）
SubscribeLocalEvent<SomeComponent, ComponentInit>(OnSomeComponentInit);
```

### 事件發送 API
```csharp
// 發送廣播事件
RaiseLocalEvent(new SomeEvent());

// 發送定向事件（到特定實體）
RaiseLocalEvent(entityUid, new SomeEvent());

// 發送定向事件（ref 版本，允許修改）
var ev = new SomeEvent();
RaiseLocalEvent(entityUid, ref ev);
```

### 靜態輔助方法
```csharp
// 取得其他系統的參考
var otherSystem = EntitySystem.Get<OtherSystem>();

// 嘗試取得（可能不存在）
if (EntitySystem.TryGet<OtherSystem>(out var sys))
{
    // ...
}

// 注入依賴
EntitySystem.InjectDependencies(someObject);
```

## 3.6 EntityEventBus — 事件匯流排

事件匯流排是系統間通訊的核心機制，分為三個部分：

### Broadcast（廣播事件）
```
EntityEventBus.Broadcast.cs
```
用於不針對特定實體的全局事件：

```csharp
// 介面
public interface IBroadcastEventBus
{
    void SubscribeEvent<T>(EventSource source, IEntityEventSubscriber subscriber, 
                           EntityEventHandler<T> eventHandler);
    void RaiseEvent(EventSource source, object toRaise);
    void RaiseEvent<T>(EventSource source, T toRaise) where T : notnull;
    void RaiseEvent<T>(EventSource source, ref T toRaise) where T : notnull;
}

// EventSource 枚舉
[Flags]
public enum EventSource : byte
{
    None    = 0b00,
    Local   = 0b01,  // 本地事件
    Network = 0b10,  // 網路事件（目前未使用）
    All     = Local | Network
}
```

### Directed（定向事件）
```
EntityEventBus.Directed.cs
```
針對特定實體的事件，只有有對應組件的實體才會收到：

```csharp
// 發送到特定實體（只有訂閱了 SomeComponent 的系統會收到）
void RaiseLocalEvent(EntityUid uid, SomeEvent args);

// ref 版本（允許修改事件資料）
void RaiseLocalEvent(EntityUid uid, ref SomeEvent args);
```

### Ordering（事件排序）
```
EntityEventBus.Ordering.cs
```
允許指定事件處理器的執行順序：

```csharp
// 使用 SubId 標識符指定排序
SubscribeEvent<T>(
    EventSource.Local,
    subscriber: this,
    eventHandler: handler,
    orderIdent: new SubId(typeof(MySystem), "HandleEvent"),
    before: new[] { new SubId(typeof(OtherSystem), "HandleEvent") },
    after: null
);
```

## 3.7 組件存取模式

### 取得組件
```csharp
// 取得（若不存在則拋出例外）
var skills = _entityManager.GetComponent<SkillsComponent>(entityUid);

// 嘗試取得
if (_entityManager.TryGetComponent<SkillsComponent>(entityUid, out var skills))
{
    // ...
}

// 確保存在（若不存在則新增）
var skills = _entityManager.EnsureComponent<SkillsComponent>(entityUid);
```

### 從系統內查詢所有實體
```csharp
// 查詢所有有 CharaComponent 的實體
foreach (var chara in EntityManager.EntityQuery<CharaComponent>())
{
    // chara 是 CharaComponent 實例
}

// 查詢多個組件（取交集）
foreach (var (chara, skills) in EntityManager.EntityQuery<CharaComponent, SkillsComponent>())
{
    // 同時有 CharaComponent 和 SkillsComponent 的實體
}
```

### 使用 Resolve 模式（在系統方法中）
```csharp
// 在系統方法內，使用 Resolve 確保組件存在
public TurnResult RunVanillaAI(EntityUid entity, VanillaAIComponent? ai = null, SpatialComponent? spatial = null)
{
    if (!Resolve(entity, ref ai, ref spatial))
        return TurnResult.Failed;
    
    // 此後 ai 和 spatial 不為 null
}
```

## 3.8 內建必要組件

每個實體在建立時都會**自動**添加以下組件：

### MetaDataComponent
```csharp
// 每個實體都有，儲存基本元資料
public class MetaDataComponent : Component
{
    public EntityPrototype? EntityPrototype { get; set; }  // 來源原型
    public EntityLifeStage EntityLifeStage { get; set; }   // 實體生命週期
    public EntityGameLiveness Liveness { get; set; }        // 遊戲中的存活狀態
    public bool EntityDeleted => EntityLifeStage >= EntityLifeStage.Deleted;
}
```

### SpatialComponent（空間組件）
```csharp
// 每個實體都有，儲存位置和父子關係
public class SpatialComponent : Component
{
    public EntityCoordinates Coordinates { get; set; }      // 相對於父實體的座標
    public MapCoordinates MapPosition { get; }              // 地圖絕對座標
    public EntityUid ParentUid { get; }                     // 父實體
    public IEnumerable<EntityUid> Children { get; }         // 子實體
    
    // 座標系統轉換
    public void AttachParent(SpatialComponent newParent);
    public void DetachParentToNull();
}
```

## 3.9 EntitySystemManager — 系統管理器

`EntitySystemManager` 負責管理所有 `EntitySystem` 實例：

```csharp
// 初始化：掃描所有 EntitySystem 子類別並實例化
void Initialize()
{
    // 透過反射找到所有 EntitySystem 子類別
    foreach (var type in _reflection.GetAllChildren<IEntitySystem>())
    {
        // 建立實例並注入依賴
        var system = _typeFactory.CreateInstance(type);
        IoCManager.InjectDependencies(system);
        system.Initialize();
    }
}

// 更新所有系統
void Update(float frameTime)
{
    foreach (var system in _systems)
        system.Update(frameTime);
}
```

## 3.10 座標系統

OpenNefia 使用三層座標系統：

```
Vector2i                    ← 純整數網格座標（無語意）
    ↓
EntityCoordinates           ← 相對座標（相對於父實體）
    EntityUid Parent        ← 父實體（通常是地圖實體）
    Vector2 Position        ← 在父座標系中的位置
    ↓
MapCoordinates              ← 地圖絕對座標
    MapId MapId             ← 地圖 ID
    Vector2i Position       ← 在地圖格子中的位置
    ↓
ScreenCoordinates           ← 螢幕座標（相機 / 視口空間）
    Vector2 Position        ← 螢幕像素位置
```

### 座標轉換
```csharp
// EntityCoordinates → MapCoordinates
var mapCoords = entityCoords.ToMap(entityManager);

// 檢查座標有效性
bool valid = entityCoords.IsValid(entityManager);

// 取得地圖 ID
MapId mapId = entityCoords.GetMapId(entityManager);
```
