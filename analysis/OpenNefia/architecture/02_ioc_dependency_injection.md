# 02 - IoC 容器與依賴注入系統

## 2.1 概述

IoC（Inversion of Control，控制反轉）是 OpenNefia 所有子系統連接在一起的黏合劑。
每個子系統透過**介面**聲明自己需要哪些服務，而不是直接建立具體實作的實例。

相關檔案：
- `OpenNefia.Core/IoC/IoCManager.cs` — 靜態公開 API
- `OpenNefia.Core/IoC/DependencyCollection.cs` — 容器實際實作
- `OpenNefia.Core/IoCSetup.cs` — 所有服務的注冊表
- `OpenNefia.Core/IoC/DynamicTypeFactory.cs` — 動態型別工廠

## 2.2 Thread-Local 容器設計

`IoCManager` 是一個靜態包裝類別，其底層是一個 `ThreadLocal<IDependencyCollection>`：

```csharp
// IoCManager.cs
private static readonly ThreadLocal<IDependencyCollection> _container = new();
```

這意味著：
- 每個執行緒有**自己獨立的** IoC 容器實例
- 伺服器端與客戶端可以在同一個程序中共存（各自有獨立容器）
- 在 Task.Run() 這類執行緒池中**不應**初始化 IoC（執行緒池的執行緒可能被不同實例共用）

## 2.3 完整 API 說明

### 初始化執行緒
```csharp
// 建立一個新的空容器給當前執行緒
IoCManager.InitThread();

// 或者使用現有的 DependencyCollection
IoCManager.InitThread(existingCollection, replaceExisting: false);
```

### 注冊服務
```csharp
// 介面 → 實作
IoCManager.Register<IEntityManager, EntityManager>();

// 自身就是實作（不需要介面）
IoCManager.Register<SomeConcreteService>();

// 使用工廠函式
IoCManager.Register<IFoo, FooImpl>((deps) => new FooImpl(...));

// 注冊現有實例
IoCManager.RegisterInstance<IFoo>(existingFooInstance);
```

### 建構依賴圖
```csharp
// 解析所有相依關係，建構實例
IoCManager.BuildGraph();
```

### 解析服務
```csharp
// 手動解析
var entityManager = IoCManager.Resolve<IEntityManager>();

// 解析到 ref 變數（更快，避免裝箱）
IEntityManager em = default!;
IoCManager.Resolve(ref em);
```

### 依賴注入
```csharp
// 注入 [Dependency] 標記的欄位
IoCManager.InjectDependencies(someObject);
```

### 清除
```csharp
// 清除所有服務（測試間使用）
IoCManager.Clear();
```

## 2.4 [Dependency] 屬性注入

這是最常用的使用方式。在任何需要使用服務的類別中，標記欄位：

```csharp
public class SomeSystem
{
    [Dependency] private readonly IEntityManager _entityManager = default!;
    [Dependency] private readonly IMapManager _mapManager = default!;
    [Dependency] private readonly IRandom _random = default!;
    
    // 呼叫 IoCManager.InjectDependencies(this) 後，上述欄位會被自動填入
}
```

**注意：** `default!` 是 C# 8+ 的 null 強制忽略寫法，實際執行時這些欄位一定會被注入。

## 2.5 IoCSetup.cs — 服務注冊表

這是整個系統的注冊清單，根據 `DisplayMode`（顯示模式）選擇不同實作：

```csharp
// OpenNefia.Core/IoCSetup.cs
public class IoCSetup
{
    internal static void Register(DisplayMode mode)
    {
        // 依顯示模式選擇圖形/輸入/任務/音訊的具體實作
        switch (mode)
        {
            case DisplayMode.Headless:
                // 無頭模式（用於測試、伺服器）
                IoCManager.Register<IGraphics, HeadlessGraphics>();
                IoCManager.Register<IInputManager, InputManager>();
                IoCManager.Register<ITaskRunner, HeadlessTaskRunner>();
                IoCManager.Register<IAudioManager, HeadlessAudioManager>();
                IoCManager.Register<IMusicManager, HeadlessMusicManager>();
                break;
                
            case DisplayMode.Love:
                // LÖVE 2D 顯示模式（正常遊戲執行）
                IoCManager.Register<IGraphics, LoveGraphics>();
                IoCManager.Register<IInputManager, LoveInputManager>();
                IoCManager.Register<ITaskRunner, LoveTaskRunner>();
                IoCManager.Register<IAudioManager, LoveAudioManager>();
                IoCManager.Register<IMusicManager, LoveMusicManager>();
                break;
        }
        
        // 其餘服務不依賴顯示模式：
        IoCManager.Register<ILogManager, LogManager>();
        IoCManager.Register<IConfigurationManager, ConfigurationManager>();
        IoCManager.Register<IEntitySystemManager, EntitySystemManager>();
        IoCManager.Register<IEntityManager, EntityManagerInternal>();
        IoCManager.Register<IMapManager, MapManager>();
        IoCManager.Register<IAreaManager, AreaManager>();
        IoCManager.Register<IPrototypeManager, PrototypeManager>();
        IoCManager.Register<ISerializationManager, SerializationManager>();
        IoCManager.Register<IAssetManager, AssetManager>();
        IoCManager.Register<IUserInterfaceManager, UserInterfaceManager>();
        IoCManager.Register<ILocalizationManager, LocalizationManager>();
        IoCManager.Register<ISaveGameManager, SaveGameManager>();
        IoCManager.Register<ISaveGameSerializer, SaveGameSerializer>();
        // ... 共 70+ 個服務
    }
}
```

## 2.6 內部 vs 公開介面模式

OpenNefia 使用一個常見模式：同一個類別注冊兩個介面，一個公開、一個內部：

```csharp
// 公開介面（供外部使用）
IoCManager.Register<IMapManager, MapManager>();

// 內部介面（供引擎內部使用，有額外方法）
IoCManager.Register<IMapManagerInternal, MapManager>();
```

實作類別（`MapManager`）同時實作兩個介面：
- `IMapManager` — 公開 API（查詢地圖、設定活動地圖等）
- `IMapManagerInternal` — 內部 API（`RegisterMap()`、`FlushMaps()`、`NextMapId` 等，僅供存讀檔時使用）

這樣做的好處是：外部代碼只能看到安全的公開介面，不會誤用危險的內部方法。

## 2.7 DependencyCollection — 容器實作細節

`DependencyCollection` 是實際的容器實作，主要職責：

1. **型別映射：** 維護 `TInterface → TImplementation` 的對映
2. **實例管理：** 以單例模式（Singleton）管理所有服務實例
3. **依賴圖建構：** `BuildGraph()` 會反射掃描所有 `[Dependency]` 欄位並注入
4. **`IPostInjectInit` 支援：** 若服務實作 `IPostInjectInit`，在注入後會自動呼叫 `PostInject()`

## 2.8 DynamicTypeFactory — 動態型別工廠

`DynamicTypeFactory`（`IDynamicTypeFactory`）允許在執行時動態建立型別實例，同時自動注入依賴：

```csharp
// 建立一個型別的新實例，並自動注入其 [Dependency] 欄位
var instance = _typeFactory.CreateInstance<SomeComponent>();
```

這主要用於：
- 建立 `Component` 實例（組件工廠）
- 建立 `EntitySystem` 實例（系統管理器）
- 建立 UI 層（Layer）實例

## 2.9 容器生命週期圖

```
程式啟動
    ↓
IoCManager.InitThread()          ← 初始化當前執行緒的容器
    ↓
IoCSetup.Register(mode)          ← 注冊所有介面-實作對映
    ↓
IoCManager.BuildGraph()          ← 建構所有實例，解析所有依賴
    ↓
[各服務可以被 Resolve 了]
    ↓
GameController.Startup()         ← 各服務依序初始化
    ↓
GameController.Run()             ← 遊戲主循環
    ↓
GameController.DoShutdown()      ← 各服務依序關閉
    ↓
IoCManager.Clear()               ← 清除容器（測試時使用）
```
