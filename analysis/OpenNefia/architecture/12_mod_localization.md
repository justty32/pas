# 12 - Mod 載入與本地化系統

## 12.1 概述

OpenNefia 提供完整的 Mod 系統（以 .NET Assembly 為單位）和本地化系統（以 Lua 腳本為基礎）。

相關檔案：
- `OpenNefia.Core/ContentPack/ModLoader.cs` — Mod 載入器
- `OpenNefia.Core/ResourceManagement/ResourceCache.cs` — 虛擬檔案系統
- `OpenNefia.Core/Locale/LocalizationManager.cs` — 本地化管理器

## 12.2 虛擬檔案系統（VFS）

OpenNefia 使用虛擬檔案系統（Virtual File System）統一管理所有資源。所有資源都通過 `ResourcePath` 存取，實際的檔案可以來自不同的掛載點：

```csharp
public interface IResourceManager
{
    // 讀取虛擬路徑的檔案
    Stream ContentFileRead(ResourcePath path);
    
    // 判斷虛擬路徑是否存在
    bool ContentFileExists(ResourcePath path);
    
    // 列舉虛擬路徑下的所有相對路徑
    IEnumerable<ResourcePath> ContentFindRelativeFiles(ResourcePath dir);
}

public interface IResourceCacheInternal : IResourceManager
{
    // 初始化（設定使用者資料目錄）
    void Initialize(string userDataDirectoryName);
    
    // 掛載一個實際目錄到虛擬路徑
    void MountContentDirectory(string path, ResourcePath? prefix = null);
    
    // 掛載一個 ZIP 檔案到虛擬路徑
    void MountContentPack(string path, ResourcePath? prefix = null);
    
    // 預載所有紋理（Textures）
    void PreloadTextures();
}
```

### 資源掛載

```csharp
// ProgramShared.cs
public static void DoMounts(IResourceCacheInternal resourceCache)
{
    // 掛載引擎核心資源目錄
    resourceCache.MountContentDirectory("Resources/", ResourcePath.Root);
    
    // 掛載遊戲內容資源目錄
    resourceCache.MountContentDirectory("Content/", ResourcePath.Root);
    
    // 掛載 Elona 原版資源（圖片、音樂）
    if (Directory.Exists("Support/"))
        resourceCache.MountContentDirectory("Support/", new ResourcePath("/Elona"));
}
```

掛載後，所有資源都可以通過虛擬路徑存取：
```csharp
// 實際位置：Support/chara.png
// 虛擬路徑：/Elona/chara.png
var image = _resourceCache.GetResource<TextureResource>("/Elona/chara.png");
```

## 12.3 ModLoader — Mod 載入器

Mod 以 .NET Assembly（DLL 檔案）的形式存在：

```csharp
internal sealed class ModLoader : BaseModLoader, IModLoaderInternal, IDisposable
{
    [Dependency] private readonly IResourceManagerInternal _res = default!;
    [Dependency] private readonly ILogManager _logManager = default!;
    
    // 使用獨立的 AssemblyLoadContext 載入 Mod（支援卸載）
    private readonly AssemblyLoadContext _loadContext;
    
    // 已載入的 Mod 清單
    public IReadOnlyList<Assembly> LoadedModules { get; }
}
```

### 載入流程

```csharp
public bool TryLoadModulesFrom(ResourcePath mountPath, string filterPrefix)
{
    // 1. 掃描指定目錄下的所有 .dll 檔案
    foreach (var filePath in _res.ContentFindRelativeFiles(mountPath)
        .Where(p => p.Extension == "dll" && p.Filename.StartsWith(filterPrefix)))
    {
        // 2. 讀取 Assembly 的依賴資訊
        var (asmRefs, asmName) = GetAssemblyReferenceData(asmFile);
        files[asmName] = (fullPath, asmRefs);
    }
    
    // 3. 按依賴順序排序（先載入被依賴的 Assembly）
    var sortedFiles = TopologicalSort(files);
    
    // 4. 依序載入每個 Assembly
    foreach (var file in sortedFiles)
    {
        LoadAssembly(file);
    }
    
    return true;
}
```

### 廣播運行等級

```csharp
public void BroadcastRunLevel(ModRunLevel level)
{
    foreach (var module in LoadedModules)
    {
        // 在每個 Assembly 中尋找 GameShared 子類別
        var entryPoints = module.GetTypes()
            .Where(t => t.IsSubclassOf(typeof(GameShared)) && !t.IsAbstract);
        
        foreach (var entryPoint in entryPoints)
        {
            var instance = (GameShared)Activator.CreateInstance(entryPoint)!;
            
            // 根據 level 呼叫對應方法
            switch (level)
            {
                case ModRunLevel.PreInit: instance.PreInit(); break;
                case ModRunLevel.Init:    instance.Init();    break;
                case ModRunLevel.PostInit: instance.PostInit(); break;
            }
        }
    }
}
```

### GameShared — Mod 進入點

```csharp
// Mod 的進入點基底類別
public abstract class GameShared
{
    public virtual void PreInit()  { }
    public virtual void Init()     { }
    public virtual void PostInit() { }
    public virtual void Shutdown() { }
}

// OpenNefia.Content 的實作
public sealed class EntryPoint : GameShared
{
    public override void PreInit()
    {
        // 注冊 Content 特定的 IoC 服務
        IoCManager.Register<IMapGenerator, VanillaMapGenerator>();
    }
    
    public override void Init()
    {
        // 主要初始化
    }
    
    public override void PostInit()
    {
        // 最終初始化（所有系統已就緒）
    }
}
```

## 12.4 本地化系統（Localization）

OpenNefia 使用 **Lua 腳本**作為本地化資料的格式，支援複雜的語言規則（如日文的複數、性別等）。

### ILocalizationManager

```csharp
public interface ILocalizationManager
{
    // 當前語言
    PrototypeId<LanguagePrototype> Language { get; }
    
    // 初始化
    void Initialize();
    
    // 是否是全寬文字語言（如日文）
    bool IsFullwidth();
    
    // 切換語言
    void SwitchLanguage(PrototypeId<LanguagePrototype> language);
    
    // 讓物件執行本地化（DoLocalize 模式）
    void DoLocalize(object o, LocaleKey key);
    
    // 載入 Lua 本地化檔案
    void LoadContentFile(ResourcePath luaFile);
    void LoadString(string luaScript);
    
    // 重新同步
    void Resync();
    
    // 文字取得
    bool TryGetString(LocaleKey key, out string? str, params LocaleArg[] args);
    string GetString(LocaleKey key, params LocaleArg[] args);
    string GetPrototypeString<T>(PrototypeId<T> protoId, LocaleKey key, params LocaleArg[] args);
    
    // 實體本地化資料
    bool TryGetLocalizationData(EntityUid uid, out LuaTable? table);
    EntityLocData GetEntityData(string prototypeId);
}
```

### Lua 本地化格式

本地化文字以 Lua 表格的形式定義：

```lua
-- /Locale/ja_JP/Charas.lua
OpenNefia.Locale.setLocale("Elona", {
    -- 種族名稱
    Race = {
        Human = {
            Name = "人間",
            Description = "もっとも繁栄した種族。",
        },
        Elf = {
            Name = "エルフ",
        },
    },
    
    -- 訊息（可以是函式，接受引數）
    Messages = {
        -- 固定文字
        LevelUp = "レベルが上がった！",
        
        -- 帶引數的函式
        AttackHit = function(attacker, target, damage)
            return string.format("%sは%sに%dのダメージを与えた。", 
                attacker.name, target.name, damage)
        end,
    },
})
```

### LocaleKey — 本地化鍵

```csharp
// 本地化鍵（dot notation）
var key = new LocaleKey("Elona.Race.Human.Name");

// 取得翻譯文字
string name = _loc.GetString(key);
// 結果：「人間」（日文）

// 帶引數
string msg = _loc.GetString(
    new LocaleKey("Elona.Messages.AttackHit"),
    new LocaleArg("attacker", attacker),
    new LocaleArg("target", target),
    new LocaleArg("damage", 25)
);
```

### LocaleArg — 本地化引數

```csharp
public struct LocaleArg
{
    public string Name { get; set; }     // Lua 中的引數名稱
    public object? Value { get; set; }   // 引數值
    
    public LocaleArg(string name, object? value)
    {
        Name = name;
        Value = value;
    }
}
```

### 靜態 Loc 類別

提供簡便的靜態存取方式：

```csharp
// Loc.cs — 靜態包裝器
public static class Loc
{
    // 取得翻譯
    public static string GetString(LocaleKey key, params LocaleArg[] args)
        => IoCManager.Resolve<ILocalizationManager>().GetString(key, args);
    
    // 嘗試取得翻譯
    public static bool TryGetString(LocaleKey key, out string? str, params LocaleArg[] args)
        => IoCManager.Resolve<ILocalizationManager>().TryGetString(key, out str, args);
}
```

### LanguagePrototype — 語言原型

```yaml
# 日文
- type: language
  id: JaJP
  isFullwidth: true      # 全寬文字（影響 UI 對齊）

# 英文
- type: language
  id: EnUS
  isFullwidth: false
```

### EntityLocData — 實體本地化資料

特殊的本地化系統，讓每個實體原型可以有專屬的本地化資料（如對話、描述）：

```lua
-- 實體的本地化資料（可以是函式以支援複雜邏輯）
OpenNefia.Locale.setEntityLocale("Elona.Goblin", {
    -- 實體名稱
    Name = function(entity)
        -- 根據性別返回不同名稱（日文有此需求）
        if entity.gender == "Male" then
            return "ゴブリン"
        else
            return "ゴブリン（女）"
        end
    end,
    
    -- 描述
    Description = "小さな緑色の生き物。",
    
    -- NPC 對話
    Dialogue = {
        Greeting = "うがー！",
        Hostile = "ぶっ殺す！",
    },
})
```

## 12.5 ReflectionManager — 反射管理器

```csharp
public interface IReflectionManager
{
    // 取得所有已載入 Assembly
    IReadOnlyList<Assembly> Assemblies { get; }
    
    // 尋找所有帶有特定屬性的型別
    IEnumerable<Type> FindTypesWithAttribute<T>() where T : Attribute;
    
    // 尋找所有指定型別的子類別
    IEnumerable<Type> GetAllChildren<T>();
    
    // 動態呼叫（反射呼叫）
    bool TryParseEnumReference(string value, out object? @enum);
}
```

反射管理器在初始化時掃描所有已載入的 Assembly，建立型別索引，供序列化系統、ECS 系統等使用。

## 12.6 自訂 Roslyn 分析器

`OpenNefia.Analyzers` 提供編譯時期的程式碼檢查：

```csharp
// 檢查 [DataField] 的使用是否正確
// 例如：DataField 只能用於有 [DataDefinition] 的類別中的屬性
[DiagnosticAnalyzer(LanguageNames.CSharp)]
public class DataFieldAnalyzer : DiagnosticAnalyzer
{
    // ...
}
```

這些分析器在 IDE 中即時顯示警告，幫助開發者避免常見錯誤。
