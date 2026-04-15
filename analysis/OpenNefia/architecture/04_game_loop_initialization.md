# 04 - 遊戲啟動流程與主循環

## 4.1 概述

OpenNefia 的啟動流程分為三個大階段：
1. **進入點初始化** — 設定 IoC，載入組件
2. **GameController.Startup()** — 依序初始化所有子系統
3. **GameController.Run()** — 執行主循環

相關檔案：
- `OpenNefia.EntryPoint/Program.cs` — `Main()` 進入點
- `OpenNefia.Core/GameController/GameController.cs` — 主控制器
- `OpenNefia.Core/ProgramShared.cs` — 共用初始化工具

## 4.2 進入點（Program.cs）

```csharp
// OpenNefia.EntryPoint/Program.cs
static void Main(string[] args)
{
    if (args.Length > 0)
        CommandLineStart(args);      // 命令列模式
    else
        GameStart();                 // 正常遊戲模式
}

static void GameStart()
{
    InitIoC(DisplayMode.Love);       // 初始化 IoC，使用 Love2D 圖形
    
    // 設定遊戲啟動選項
    var options = new GameControllerOptions
    {
        // 各種路徑設定...
    };
    
    var controller = IoCManager.Resolve<IGameController>();
    
    if (!controller.Startup(options))
        return;                      // 初始化失敗
    
    controller.Run();                // 進入主循環
}

static void InitIoC(DisplayMode mode)
{
    IoCManager.InitThread();          // 初始化執行緒的 IoC 容器
    IoCSetup.Register(mode);          // 注冊所有服務
    IoCManager.BuildGraph();          // 建構依賴圖
    
    RegisterReflection();             // 載入組件掃描用的 Assembly
}
```

## 4.3 GameController.Startup() — 完整初始化流程

```csharp
public bool Startup(GameControllerOptions options)
{
    // ===== 第一階段：基礎設施 =====
    
    // 1. 設定 UTF-8 輸出編碼
    System.Console.OutputEncoding = EncodingHelpers.UTF8;
    
    // 2. 初始化資源快取（建立虛擬檔案系統）
    _resourceCache.Initialize(Options.UserDataDirectoryName);
    
    // 3. 初始化使用者設定檔管理器
    _profileManager.Initialize();
    
    // 4. 初始化組態系統（載入 CVars）
    InitializeConfig();
    
    // 5. 設定日誌系統
    SetupLogging(() => new ConsoleLogHandler());
    
    // 6. 初始化非同步任務管理器
    _taskManager.Initialize();
    
    // ===== 第二階段：資源與圖形 =====
    
    // 7. 設定 Mod 載入器（啟用組件載入上下文）
    _modLoader.SetUseLoadContext(true);
    ProgramShared.DoMounts(_resourceCache);   // 掛載資源目錄
    
    // 8. 初始化字型管理器
    _fontManager.Initialize();
    
    // 9. 綁定視窗事件（文字輸入、滑鼠、鍵盤）
    BindWindowEvents();
    
    // 10. 初始化圖形後端（Love2D）
    _graphics.Initialize();
    
    // 11. 顯示啟動畫面（在其他資源載入前）
    ShowSplashScreen();
    
    // 12. 初始化音訊
    _audio.Initialize();
    _music.Initialize();
    
    // ===== 第三階段：Mod 載入 =====
    
    // 13. 從組件目錄載入 Mod
    if (!_modLoader.TryLoadModulesFrom(Options.AssemblyDirectory, string.Empty))
    {
        Logger.Fatal("Errors while loading content assemblies.");
        return false;
    }
    
    // 14. 從已載入的 Mod 載入 CVars 定義
    foreach (var loadedModule in _modLoader.LoadedModules)
        _config.LoadCVarsFromAssembly(loadedModule);
    
    // ===== 第四階段：序列化與 UI =====
    
    // 15. 初始化序列化系統（型別掃描、序列化器注冊）
    _serialization.Initialize();
    
    // 16. 初始化 UI 管理器
    _uiManager.Initialize();
    
    // ===== 第五階段：Mod 初始化廣播 =====
    
    // 17. 廣播 PreInit（Mod 可以在此進行最早期的初始化）
    _modLoader.BroadcastRunLevel(ModRunLevel.PreInit);
    
    // 18. 廣播 Init（主要的 Mod 初始化）
    _modLoader.BroadcastRunLevel(ModRunLevel.Init);
    
    // ===== 第六階段：輸入與實體系統 =====
    
    // 19. 初始化輸入管理器（鍵位綁定）
    _inputManager.Initialize();
    
    // 20. 初始化實體管理器（建立 EventBus，掃描組件）
    _entityManager.Initialize();
    
    // 21. 下載原版資源（若不存在）
    if (!TryDownloadVanillaAssets())
        return false;
    
    // ===== 第七階段：組件與原型 =====
    
    // 22. 注冊組件工廠（DoDefaultRegistrations + DoAutoRegistrations）
    _components.DoDefaultRegistrations();
    _components.DoAutoRegistrations();
    _components.FinishRegistration();
    
    // 23. 預載紋理資源
    _resourceCache.PreloadTextures();
    
    // 24. 初始化主題管理器並載入主題
    _themeManager.Initialize();
    _themeManager.LoadDirectory(Options.ThemeDirectory);
    
    // 25. 初始化原型管理器並載入所有 YAML 原型
    _prototypeManager.Initialize();
    _prototypeManager.LoadDirectory(Options.PrototypeDirectory);
    _prototypeManager.Resync();
    
    // 26. 預載所有資源（圖片等）
    _assetManager.PreloadAssets();
    
    // ===== 第八階段：磁磚與地圖渲染 =====
    
    // 27. 初始化磁磚定義管理器
    _tileDefinitionManager.Initialize();
    _tileDefinitionManager.RegisterAll();
    
    // 28. 初始化本地化系統
    _localizationManager.Initialize();
    
    // 29. 初始化存檔管理器
    _saveGameManager.Initialize();
    
    // 30. 初始化圖集管理器（精靈圖集打包）
    _atlasManager.Initialize();
    _atlasManager.LoadAtlases();
    
    // 31. 啟動實體管理器（初始化所有 EntitySystem）
    _entityManager.Startup();
    
    // 32. 初始化存讀檔序列化器
    _saveGameSerializer.Initialize();
    
    // 33. 初始化地圖渲染器（注冊 TileLayer）
    _mapRenderer.Initialize();
    _mapRenderer.RegisterTileLayers();
    
    // ===== 最終階段：PostInit 廣播 =====
    
    // 34. 廣播 PostInit（Mod 可以在此進行最終初始化）
    _modLoader.BroadcastRunLevel(ModRunLevel.PostInit);
    
    // 35. 強制進行一次 GC 壓縮（大型物件堆）
    GCSettings.LargeObjectHeapCompactionMode = GCLargeObjectHeapCompactionMode.CompactOnce;
    GC.Collect();
    
    return true;
}
```

## 4.4 GameController.Run() — 主循環

```csharp
public void Run()
{
    _running = true;
    
    // MainCallback 在 EntryPoint 中被設定為 IMainTitleLogic.RunTitleScreen()
    // 這個回呼會執行標題畫面，然後進入遊戲主循環
    MainCallback?.Invoke();
    
    // MainCallback 返回代表遊戲結束
    DoShutdown();
}
```

**注意：** `MainCallback` 本身是一個阻塞呼叫，它包含標題畫面的邏輯，以及之後的遊戲主循環。整個遊戲在 `MainCallback?.Invoke()` 返回前都不會結束。

## 4.5 Update() 與 Draw() — 每幀執行

```csharp
// 每幀更新（由 Love2D 的事件循環呼叫）
public void Update(FrameEventArgs frame)
{
    if (!_running)
        DoShutdown();
    
    // 1. 處理非同步任務（TaskManager 的 pending 任務）
    _taskManager.ProcessPendingTasks();
    
    // 2. 更新計時器（觸發到期的 Timer）
    _timerManager.UpdateTimers(frame);
    
    // 3. 更新按鍵重複（處理長按按鍵的重複事件）
    _inputManager.UpdateKeyRepeats(frame);
    
    // 4. 更新所有 UI 層（主要的遊戲邏輯在這裡）
    _uiManager.UpdateLayers(frame);
    
    // 5. 再次處理非同步任務（UI 更新可能產生新的 async 任務）
    _taskManager.ProcessPendingTasks();
}

// 每幀渲染（由 Love2D 的事件循環呼叫）
public void Draw()
{
    if (Love.Graphics.IsActive())
    {
        // 清除背景
        Love.Graphics.Clear(backgroundColor);
        Love.Graphics.SetScissor();
        Love.Graphics.Origin();
        
        DoDraw();
        
        // 呈現到螢幕
        Love.Graphics.Present();
    }
    
    // 控制幀率
    Love.Timer.Sleep(0.001f);
}

private void DoDraw()
{
    _graphics.BeginDraw();
    _uiManager.DrawLayers();   // 繪製所有 UI 層
    _graphics.EndDraw();
}
```

## 4.6 Shutdown 流程

```csharp
private void DoShutdown()
{
    _entityManager.Shutdown();   // 刪除所有實體，關閉所有系統
    _uiManager.Shutdown();       // 關閉 UI 管理器
    _graphics.Shutdown();        // 關閉圖形後端
    _audio.Shutdown();           // 關閉音效
    _music.Shutdown();           // 關閉音樂
    _themeManager.Shutdown();    // 關閉主題管理器
    
    // 關閉日誌處理器
    if (_logHandler != null)
    {
        _log.RootSawmill.RemoveHandler(_logHandler);
        (_logHandler as IDisposable)?.Dispose();
    }
    
    Logger.Log(LogLevel.Info, "Quitting game.");
    Environment.Exit(0);
}
```

## 4.7 Mod 初始化三階段（RunLevel）

Mod 的初始化被分成三個運行等級（RunLevel）：

```csharp
public enum ModRunLevel
{
    PreInit,   // 最早期初始化（在 UI 和輸入初始化後）
    Init,      // 主要初始化（在 EntityManager 初始化前）
    PostInit,  // 最終初始化（所有系統都已初始化後）
}
```

### Mod 進入點（EntryPoint.cs）
```csharp
// OpenNefia.Content/EntryPoint.cs
public sealed class EntryPoint : GameShared
{
    public override void PreInit()
    {
        // 在此注冊 Content 特定的 IoC 服務
        IoCManager.Register<IContentManager, ContentManager>();
    }
    
    public override void Init()
    {
        // 在此進行主要初始化
        // 例如：注冊本地化、設定預設值等
    }
    
    public override void PostInit()
    {
        // 在此進行需要其他系統已初始化才能執行的邏輯
    }
}
```

## 4.8 視窗事件綁定

```csharp
private void BindWindowEvents()
{
    // 文字輸入（IME 支援）
    _graphics.OnTextEditing += TextEditing;
    _graphics.OnTextInput += TextInput;
    
    // 滑鼠事件
    _graphics.OnMouseMoved += MouseMoved;
    _graphics.OnMousePressed += MousePressed;
    _graphics.OnMouseReleased += MouseReleased;
    _graphics.OnMouseWheel += MouseWheel;
    
    // 鍵盤事件
    _graphics.OnKeyReleased += KeyUp;
    _graphics.OnKeyPressed += KeyDown;
    
    // 關閉視窗事件
    _graphics.OnQuit += (_) =>
    {
        DoShutdown();
        return false;
    };
}
```

## 4.9 GameControllerOptions — 啟動選項

```csharp
public class GameControllerOptions
{
    // 遊戲主視窗標題
    public string WindowTitle { get; set; } = "OpenNefia";
    
    // 使用者資料目錄名稱（儲存設定、存檔）
    public string UserDataDirectoryName { get; set; } = "OpenNefia";
    
    // 組態檔名稱
    public string ConfigFileName { get; set; } = "config.toml";
    
    // 原型 YAML 的載入目錄
    public ResourcePath PrototypeDirectory { get; set; } = new ResourcePath("/Prototypes");
    
    // 主題目錄
    public ResourcePath ThemeDirectory { get; set; } = new ResourcePath("/Themes");
    
    // Mod 組件（DLL）目錄
    public ResourcePath AssemblyDirectory { get; set; } = new ResourcePath("/Assemblies");
    
    // 是否載入組態檔與使用者資料
    public bool LoadConfigAndUserData { get; set; } = true;
}
```

## 4.10 CVars — 全局組態變數

CVars 是遊戲的全域設定系統，在 `CVars.cs` 中定義：

```csharp
// OpenNefia.Core/CVars.cs
public static class CVars
{
    // 顯示設定
    public static readonly CVarDef<int> DisplayWidth = CVarDef.Create("display.width", 1280);
    public static readonly CVarDef<int> DisplayHeight = CVarDef.Create("display.height", 720);
    public static readonly CVarDef<bool> DisplayFullscreen = CVarDef.Create("display.fullscreen", false);
    
    // 音訊設定
    public static readonly CVarDef<float> AudioMasterVolume = CVarDef.Create("audio.mastervolume", 1.0f);
    
    // 日誌設定
    public static readonly CVarDef<bool> LogEnabled = CVarDef.Create("log.enabled", true);
    public static readonly CVarDef<string> LogPath = CVarDef.Create("log.path", "logs");
    public static readonly CVarDef<LogLevel> LogLevel = CVarDef.Create("log.level", LogLevel.Info);
    
    // 除錯設定
    public static readonly CVarDef<int> DebugTargetFps = CVarDef.Create("debug.targetfps", 60);
}
```

### 讀取與設定 CVar
```csharp
// 讀取
int width = _config.GetCVar(CVars.DisplayWidth);

// 設定
_config.SetCVar(CVars.DisplayWidth, 1920);

// 監聽變更
_config.OnValueChanged(CVars.DisplayWidth, (newVal) => {
    // 寬度改變時的處理
});
```
