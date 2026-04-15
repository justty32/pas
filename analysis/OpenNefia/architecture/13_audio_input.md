# 13 - 音訊與輸入系統

## 13.1 音訊系統概述

音訊系統分為兩個獨立管理器：
- `IAudioManager` — 音效（Sound Effects，一次性播放）
- `IMusicManager` — 音樂（Background Music，循環播放）

相關檔案：
- `OpenNefia.Core/Audio/LoveAudioManager.cs` — Love2D 音效管理器
- `OpenNefia.Core/Audio/LoveMusicManager.cs` — Love2D 音樂管理器
- `OpenNefia.Core/Audio/HeadlessAudioManager.cs` — 無頭音效管理器（測試用）
- `OpenNefia.Core/Audio/HeadlessMusicManager.cs` — 無頭音樂管理器（測試用）

## 13.2 IAudioManager — 音效管理器

```csharp
public interface IAudioManager
{
    void Initialize();
    void Shutdown();
    
    // 播放音效（根據原型 ID）
    void Play(PrototypeId<SoundPrototype> id);
    
    // 播放音效（帶音量和音調）
    void Play(PrototypeId<SoundPrototype> id, float volume, float pitch = 1.0f);
    
    // 設定主音量（0.0 ~ 1.0）
    void SetMasterVolume(float volume);
    
    // 停止所有音效
    void StopAll();
}
```

### SoundPrototype — 音效原型

```yaml
- type: sound
  id: Elona.AttackMelee
  path: "/Elona/Sound/attack_melee.ogg"

- type: sound
  id: Elona.Explosion
  path: "/Elona/Sound/explosion.ogg"
  
- type: sound
  id: Elona.Footstep
  path: "/Elona/Sound/footstep.ogg"
```

### LoveAudioManager — Love2D 實作

```csharp
public sealed class LoveAudioManager : IAudioManager
{
    // 已預載的音效快取
    private readonly Dictionary<string, Love.SoundData> _soundCache = new();
    
    public void Play(PrototypeId<SoundPrototype> id)
    {
        var proto = _prototypeManager.Index(id);
        
        // 從快取取得或載入音效資料
        if (!_soundCache.TryGetValue(proto.Path.ToString(), out var soundData))
        {
            soundData = Love.Sound.NewSoundData(proto.Path.ToString());
            _soundCache[proto.Path.ToString()] = soundData;
        }
        
        // 建立一個 Love2D Source 並播放
        var source = Love.Audio.NewSource(soundData, Love.SourceType.Static);
        source.Play();
    }
    
    public void SetMasterVolume(float volume)
    {
        Love.Audio.SetVolume(volume);
    }
}
```

## 13.3 IMusicManager — 音樂管理器

```csharp
public interface IMusicManager
{
    void Initialize();
    void Shutdown();
    
    // 播放音樂（自動循環）
    void Play(PrototypeId<MusicPrototype> id);
    
    // 淡出並停止
    void Stop(float fadeOutTime = 0);
    
    // 暫停
    void Pause();
    
    // 繼續
    void Resume();
    
    // 當前播放的音樂
    PrototypeId<MusicPrototype>? CurrentMusic { get; }
    
    // 設定音量
    void SetVolume(float volume);
}
```

### MusicPrototype — 音樂原型

```yaml
- type: music
  id: Elona.Town1
  path: "/Elona/Music/gm_town1.ogg"

- type: music
  id: Elona.Battle
  path: "/Elona/Music/gm_battle.ogg"

- type: music
  id: Elona.Boss
  path: "/Elona/Music/gm_boss.ogg"
```

### LoveMusicManager — Love2D 實作

```csharp
public sealed class LoveMusicManager : IMusicManager
{
    private Love.Source? _currentSource;
    
    public void Play(PrototypeId<MusicPrototype> id)
    {
        // 若正在播放同一首音樂，不重置
        if (CurrentMusic == id) return;
        
        // 停止當前音樂
        Stop();
        
        var proto = _prototypeManager.Index(id);
        
        // 使用串流模式載入（Stream，不完整載入到記憶體）
        var stream = Love.Audio.NewStream(proto.Path.ToString());
        _currentSource = Love.Audio.NewSource(stream, Love.SourceType.Stream);
        _currentSource.SetLooping(true);    // 設定循環
        _currentSource.Play();
        
        CurrentMusic = id;
    }
}
```

## 13.4 輸入系統

### 系統架構

```
使用者輸入（鍵盤/滑鼠）
    ↓
IGraphics 事件（OnKeyPressed、OnMouseMoved 等）
    ↓
InputManager 處理
    ↓
BoundKeyFunction（語意化的按鍵動作）
    ↓
UIManager（UI 焦點元素） 或 Game Logic（遊戲邏輯）
```

### IInputManager — 輸入管理器

```csharp
public interface IInputManager
{
    void Initialize();
    
    // 取得滑鼠在螢幕上的位置
    ScreenCoordinates MouseScreenPosition { get; }
    
    // 更新按鍵重複（長按）
    void UpdateKeyRepeats(FrameEventArgs frame);
    
    // 取得按鍵功能對應的按鍵名稱字串（用於 UI 顯示）
    string GetKeyFunctionButtonString(BoundKeyFunction function);
    
    // 設定按鍵綁定
    void SetKeyBinding(BoundKeyFunction function, Keyboard.Key key);
    
    // UI 按鍵狀態變更事件
    event Func<BoundKeyEventArgs, bool>? UIKeyBindStateChanged;
}
```

### BoundKeyFunction — 按鍵功能

`BoundKeyFunction` 是語意化的按鍵動作，不直接耦合到具體的按鍵：

```csharp
// 引擎內建按鍵功能
public static class EngineKeyFunctions
{
    public static readonly BoundKeyFunction UIClick = "UIClick";
    public static readonly BoundKeyFunction UIRightClick = "UIRightClick";
    public static readonly BoundKeyFunction UIAccept = "UIAccept";
    public static readonly BoundKeyFunction UISelect = "UISelect";
    public static readonly BoundKeyFunction UICancel = "UICancel";
    public static readonly BoundKeyFunction UINextTab = "UINextTab";
    public static readonly BoundKeyFunction UIPrevTab = "UIPrevTab";
    public static readonly BoundKeyFunction UIUp = "UIUp";
    public static readonly BoundKeyFunction UIDown = "UIDown";
    public static readonly BoundKeyFunction UILeft = "UILeft";
    public static readonly BoundKeyFunction UIRight = "UIRight";
}

// 遊戲特定按鍵功能
public static class ContentKeyFunctions
{
    public static readonly BoundKeyFunction MoveNorth = "MoveNorth";
    public static readonly BoundKeyFunction MoveSouth = "MoveSouth";
    public static readonly BoundKeyFunction MoveEast = "MoveEast";
    public static readonly BoundKeyFunction MoveWest = "MoveWest";
    
    public static readonly BoundKeyFunction OpenInventory = "OpenInventory";
    public static readonly BoundKeyFunction OpenCharaSheet = "OpenCharaSheet";
    public static readonly BoundKeyFunction Wait = "Wait";
    public static readonly BoundKeyFunction PickUp = "PickUp";
    
    public static readonly BoundKeyFunction OpenConsole = "OpenConsole";
}
```

### BoundKeyMap — 按鍵綁定表

```csharp
// 按鍵功能 → 實際按鍵的映射
public class BoundKeyMap
{
    // 功能 → 按鍵列表（支援多鍵綁定）
    private readonly Dictionary<BoundKeyFunction, List<Keyboard.Key>> _bindings = new();
    
    // 取得某功能對應的所有按鍵
    public IReadOnlyList<Keyboard.Key> GetBoundKeys(BoundKeyFunction function);
    
    // 取得某按鍵對應的功能
    public BoundKeyFunction? GetFunctionFromKey(Keyboard.Key key);
    
    // 設定綁定
    public void SetBinding(BoundKeyFunction function, Keyboard.Key key);
}
```

### InputCmdMessage — 輸入命令訊息

```csharp
// 按鍵事件資料
public class BoundKeyEventArgs
{
    public BoundKeyFunction Function { get; }      // 按鍵功能
    public BoundKeyState State { get; }             // 按下或放開
    public Keyboard.Key Key { get; }               // 實際按鍵
    public bool CanFocus { get; }                  // 是否可以有焦點
    public bool Repeat { get; }                    // 是否是重複事件（長按）
}

public enum BoundKeyState
{
    Up,     // 按鍵放開
    Down,   // 按鍵按下
}
```

### InputContextContainer — 輸入上下文

不同的遊戲狀態（標題畫面、遊戲中、UI 開啟）需要不同的按鍵響應。輸入上下文系統允許切換：

```csharp
public interface IInputContextContainer
{
    // 當前活動的輸入上下文
    IInputContext? ActiveContext { get; }
    
    // 切換輸入上下文
    void SetContext(string contextName);
    
    // 新增上下文
    void AddContext(string contextName, IInputContext context);
}

// 上下文定義
public interface IInputContext
{
    // 此上下文中哪些按鍵功能是啟用的
    bool HasFunction(BoundKeyFunction function);
}
```

## 13.5 按鍵重複處理

長按按鍵時，會產生重複事件（用於在 UI 列表中滾動等）：

```csharp
public void UpdateKeyRepeats(FrameEventArgs frame)
{
    // 對每個正在按住的按鍵
    foreach (var (key, data) in _heldKeys)
    {
        data.HeldTime += frame.DeltaSeconds;
        
        // 超過重複延遲後，開始重複
        if (data.HeldTime > RepeatDelay)
        {
            data.RepeatTime += frame.DeltaSeconds;
            
            while (data.RepeatTime > RepeatInterval)
            {
                data.RepeatTime -= RepeatInterval;
                // 發送重複事件
                FireKeyBindDown(key, isRepeat: true);
            }
        }
    }
}
```

## 13.6 LoveInputManager — Love2D 輸入管理器

```csharp
public sealed class LoveInputManager : IInputManager
{
    // Love2D 的按鍵常數 → OpenNefia 的 Keyboard.Key
    private static readonly Dictionary<Love.KeyConstant, Keyboard.Key> KeyMap = new()
    {
        { Love.KeyConstant.A, Keyboard.Key.A },
        { Love.KeyConstant.B, Keyboard.Key.B },
        // ...
        { Love.KeyConstant.Up, Keyboard.Key.Up },
        { Love.KeyConstant.Down, Keyboard.Key.Down },
        { Love.KeyConstant.Return, Keyboard.Key.Return },
        { Love.KeyConstant.Escape, Keyboard.Key.Escape },
        // ...
    };
    
    // 當 Love2D 的 KeyPressed 事件觸發時
    public void KeyPressed(Love.KeyConstant key, bool isRepeat)
    {
        if (!KeyMap.TryGetValue(key, out var mappedKey))
            return;
        
        // 找到對應的 BoundKeyFunction
        var function = _boundKeyMap.GetFunctionFromKey(mappedKey);
        if (function == null) return;
        
        // 發送到 UI 或遊戲邏輯
        var args = new BoundKeyEventArgs(function, BoundKeyState.Down, mappedKey, isRepeat: isRepeat);
        UIKeyBindStateChanged?.Invoke(args);
    }
}
```

## 13.7 TimerManager — 計時器系統

不同於每幀 Update，計時器允許在特定時間後觸發回呼：

```csharp
public interface ITimerManager
{
    // 在指定時間後執行回呼（一次性）
    Timer AddTimer(TimeSpan delay, Action callback);
    
    // 定期執行回呼（重複）
    Timer AddRepeatingTimer(TimeSpan interval, Action callback);
    
    // 取消計時器
    void RemoveTimer(Timer timer);
    
    // 更新計時器（每幀呼叫）
    void UpdateTimers(FrameEventArgs frame);
}

// Timer 物件
public class Timer
{
    public TimeSpan Delay { get; }
    public bool Repeating { get; }
    public Action Callback { get; }
    
    public void Cancel();
}
```

使用範例：
```csharp
// 3 秒後顯示訊息
_timerManager.AddTimer(TimeSpan.FromSeconds(3), () =>
{
    ShowMessage("Time's up!");
});

// 每 1 秒更新一次狀態效果
_timerManager.AddRepeatingTimer(TimeSpan.FromSeconds(1), () =>
{
    UpdateStatusEffects();
});
```

## 13.8 TaskManager — 非同步任務管理

允許在遊戲主執行緒上安全地執行非同步操作：

```csharp
public interface ITaskManager
{
    void Initialize();
    
    // 處理所有待執行的任務
    void ProcessPendingTasks();
    
    // 在主執行緒上排程一個任務
    void RunOnMainThread(Action action);
}
```

```csharp
// 使用範例（在 async 方法中）
public async Task LoadSomethingAsync()
{
    // 在非同步操作後切換回主執行緒
    await Task.Run(() => DoHeavyComputation());
    
    // 此後的代碼在主執行緒上執行
    _entityManager.SpawnEntity(...);
}
```

### RobustTaskScheduler

自訂的 `TaskScheduler`，確保 `Task.Run()` 外的 `await` 都在主執行緒上恢復：

```csharp
// 使用範例（適合遊戲邏輯）
public async Task ShowMenuAsync()
{
    // 顯示 UI 並等待結果（在主執行緒上）
    var result = await _uiManager.QueryAsync(new MenuLayer());
    
    // 處理結果（同樣在主執行緒上）
    HandleMenuResult(result);
}
```
