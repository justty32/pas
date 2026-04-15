# 11 - 存讀檔系統

## 11.1 概述

OpenNefia 的存讀檔系統負責將整個遊戲狀態（所有地圖、實體、組件、全域資料）序列化到磁碟並在之後還原。

相關檔案：
- `OpenNefia.Core/SaveGames/SaveGameSerializer.cs` — 存讀檔序列化邏輯
- `OpenNefia.Core/SaveGames/SaveGameManager.cs` — 存檔檔案管理
- `OpenNefia.Core/SaveGames/SaveGameHandle.cs` — 存檔處理物件

## 11.2 SaveGameManager — 存檔管理器

管理存檔的檔案系統操作（建立、列表、刪除存檔目錄）：

```csharp
public interface ISaveGameManager
{
    // 所有存檔的列表
    IEnumerable<ISaveGameHandle> SaveGames { get; }
    
    // 當前活動的存檔
    ISaveGameHandle? CurrentSave { get; }
    
    // 設定當前存檔
    void SetCurrentSave(ISaveGameHandle save);
    
    // 初始化（掃描存檔目錄）
    void Initialize();
}

public interface ISaveGameManagerInternal : ISaveGameManager
{
    // 建立新存檔
    ISaveGameHandle CreateSave(string saveName);
    
    // 刪除存檔
    void DeleteSave(ISaveGameHandle save);
}
```

## 11.3 ISaveGameHandle — 存檔處理物件

代表一個存檔目錄的抽象：

```csharp
public interface ISaveGameHandle
{
    // 存檔名稱
    string Name { get; }
    
    // 存檔目錄路徑
    ResourcePath BasePath { get; }
    
    // 讀取存檔中的檔案
    Stream OpenRead(ResourcePath path);
    
    // 寫入存檔中的檔案
    Stream OpenWrite(ResourcePath path);
    
    // 檢查檔案是否存在
    bool Exists(ResourcePath path);
    
    // 刪除存檔中的檔案
    void Delete(ResourcePath path);
}
```

## 11.4 SaveGameSerializer — 序列化器

`ISaveGameSerializer` 是存讀檔的核心邏輯，處理完整的遊戲狀態序列化：

```csharp
public interface ISaveGameSerializer
{
    // 事件
    event GameSavedDelegate OnGameSaved;
    event GameLoadedDelegate OnGameLoaded;
    event SaveDataInitializeDelegate OnSaveDataInitialize;
    
    // 初始化新存檔
    ISaveGameHandle InitializeSaveGame(string name);
    
    // 存檔
    void SaveGame(ISaveGameHandle save);
    
    // 讀檔
    void LoadGame(ISaveGameHandle save);
    
    // 重置遊戲狀態（在讀取新存檔前清除當前狀態）
    void ResetGameState();
}
```

## 11.5 存檔資料結構

### SessionData — 工作階段資料

```csharp
// 全域、引擎內部的資料（不屬於地圖或實體系統）
[DataDefinition]
internal class SessionData
{
    // 儲存時的玩家實體 UID
    [DataField(required: true)]
    public int PlayerUid { get; set; }
    
    // 地圖管理器的下一個 ID
    [DataField(required: true)]
    public int NextMapId { get; set; }
    
    // 區域管理器的下一個 ID
    [DataField(required: true)]
    public int NextAreaId { get; set; }
    
    // 實體管理器的下一個 UID
    [DataField(required: true)]
    public int NextEntityUid { get; set; }
}
```

### 存檔目錄結構

```
save/
└── MySave/                      ← 存檔根目錄
    ├── meta.yml                 ← 存檔元資料（名稱、版本、日期）
    ├── session.yml              ← SessionData（玩家 UID、下一個 ID 等）
    ├── global.yml               ← 全域資料（時間、聲望等）
    ├── areas/
    │   ├── area_1.yml          ← 區域資料
    │   ├── area_2.yml
    │   └── ...
    └── maps/
        ├── map_2.yml           ← 地圖資料（磁磚 + 所有實體）
        ├── map_3.yml
        └── ...
```

## 11.6 存檔流程詳解

```csharp
public void SaveGame(ISaveGameHandle save)
{
    // 1. 發送 OnGameSaved 事件（讓子系統有機會準備存檔資料）
    OnGameSaved?.Invoke(save);
    
    // 2. 儲存全域工作階段資料
    SaveGlobalData(save);
    
    // 3. 儲存每個已載入的區域
    foreach (var (areaId, area) in _areaManager.LoadedAreas)
    {
        SaveArea(save, areaId, area);
    }
    
    // 4. 儲存每個已載入的地圖（包含所有實體和組件）
    foreach (var (mapId, map) in _mapManager.LoadedMaps)
    {
        SaveMap(save, mapId, map);
    }
}

private void SaveGlobalData(ISaveGameHandle save)
{
    // 儲存 SessionData
    var sessionData = new SessionData
    {
        PlayerUid = (int)_gameSession.Player.Uid,
        NextMapId = _mapManager.NextMapId,
        NextAreaId = _areaManager.NextAreaId,
        NextEntityUid = _entityManager.NextEntityUid,
    };
    
    var yaml = _serialization.WriteValueAs<SessionData>(sessionData);
    using var stream = save.OpenWrite(SessionDataPath);
    WriteYaml(stream, yaml);
    
    // 通知子系統儲存各自的全域資料
    OnSaveDataInitialize?.Invoke();
}

private void SaveMap(ISaveGameHandle save, MapId mapId, IMap map)
{
    // 序列化地圖磁磚資料
    var mapData = SerializeMapTiles(map);
    
    // 序列化所有在此地圖上的實體（包含其組件）
    var entities = GetEntitiesOnMap(mapId);
    var entityData = SerializeEntities(entities);
    
    // 寫入存檔
    using var stream = save.OpenWrite($"maps/map_{mapId.Value}.yml");
    WriteYaml(stream, new { map = mapData, entities = entityData });
}
```

## 11.7 讀檔流程詳解

```csharp
public void LoadGame(ISaveGameHandle save)
{
    // 1. 重置當前遊戲狀態
    ResetGameState();
    
    // 2. 載入全域工作階段資料
    LoadGlobalData(save);
    
    // 3. 載入所有區域
    LoadAreas(save);
    
    // 4. 載入所有地圖（包含所有實體）
    LoadMaps(save);
    
    // 5. 恢復玩家實體參考
    RestorePlayerReference();
    
    // 6. 發送 OnGameLoaded 事件
    OnGameLoaded?.Invoke(save);
}

public void ResetGameState()
{
    // 刪除所有實體（重置 NextEntityUid）
    _entityManager.FlushEntities();
    
    // 清除所有地圖
    _mapManager.FlushMaps();
    
    // 清除所有區域
    _areaManager.FlushAreas();
}

private void LoadGlobalData(ISaveGameHandle save)
{
    // 讀取並反序列化 SessionData
    using var stream = save.OpenRead(SessionDataPath);
    var sessionData = ReadYaml<SessionData>(stream);
    
    // 恢復計數器
    _mapManager.NextMapId = sessionData.NextMapId;
    _areaManager.NextAreaId = sessionData.NextAreaId;
    _entityManager.NextEntityUid = sessionData.NextEntityUid;
    
    // 記錄玩家 UID（在所有實體載入後才能設定）
    _pendingPlayerUid = new EntityUid(sessionData.PlayerUid);
}
```

## 11.8 實體序列化

實體的序列化通過 YAML 和序列化系統完成：

```yaml
# 一個序列化後的實體範例
- uid: 42
  prototype: Elona.Goblin
  components:
    - type: Chara
      race: Elona.Goblin
      class: Elona.Fighter
      gender: Male
      liveness: Alive
    - type: Skills
      HP: 25
      MaxHP: 30
      MP: 5
      MaxMP: 10
      Skills:
        Elona.MartialArts:
          Level: 3
          Potential: 120
          Experience: 450
    - type: Spatial
      parent: 1          # 父實體 UID（地圖實體）
      position: [10, 15] # 在地圖上的位置
```

## 11.9 存讀檔事件鉤子

各子系統可以訂閱存讀檔事件來儲存自己的自訂資料：

```csharp
public class WorldSystem : EntitySystem
{
    [Dependency] private readonly ISaveGameSerializer _saveGameSerializer = default!;
    
    public override void Initialize()
    {
        // 訂閱存讀檔事件
        _saveGameSerializer.OnSaveDataInitialize += OnSaveDataInitialize;
        _saveGameSerializer.OnGameSaved += OnGameSaved;
        _saveGameSerializer.OnGameLoaded += OnGameLoaded;
    }
    
    private void OnGameSaved(ISaveGameHandle save)
    {
        // 儲存世界時間到存檔
        var worldData = new WorldSaveData
        {
            CurrentTime = _worldTime.CurrentTime,
        };
        
        var yaml = _serialization.WriteValueAs<WorldSaveData>(worldData);
        using var stream = save.OpenWrite("global/world.yml");
        WriteYaml(stream, yaml);
    }
    
    private void OnGameLoaded(ISaveGameHandle save)
    {
        // 從存檔讀取世界時間
        using var stream = save.OpenRead("global/world.yml");
        var worldData = ReadYaml<WorldSaveData>(stream);
        _worldTime.CurrentTime = worldData.CurrentTime;
    }
}
```

## 11.10 ProfileManager — 使用者設定檔

存檔和設定都儲存在使用者設定檔目錄中：

```csharp
public interface IProfileManager
{
    // 當前使用者設定檔
    IUserProfile CurrentProfile { get; }
    
    void Initialize();
}

public interface IUserProfile
{
    // 設定檔根目錄
    ResourcePath Root { get; }
    
    // 讀取設定檔中的檔案
    Stream? OpenFileRead(ResourcePath path);
    
    // 寫入設定檔中的檔案
    Stream OpenFileWrite(ResourcePath path);
    
    // 檢查檔案是否存在
    bool Exists(ResourcePath path);
}
```

預設路徑（Windows）：
```
%APPDATA%\OpenNefia\
    config.toml          ← 遊戲設定
    saves\               ← 所有存檔目錄
        MySave\
        MySave2\
    logs\                ← 日誌檔案
```
