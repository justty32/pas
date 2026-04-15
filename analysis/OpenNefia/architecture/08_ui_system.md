# 08 - 使用者介面系統

## 8.1 概述

OpenNefia 的 UI 系統基於**層（Layer）堆疊**的概念。每個遊戲畫面（標題畫面、遊戲主畫面、背包、對話等）都是一個 UI 層，層之間可以堆疊，輸入事件只傳遞給頂部的層。

相關檔案：
- `OpenNefia.Core/UserInterface/UserInterfaceManager.cs` — UI 管理器
- `OpenNefia.Core/UserInterface/Layers.cs` — 層管理邏輯
- `OpenNefia.Core/UI/Layer/UiLayer.cs` — UI 層基底類別
- `OpenNefia.Core/UI/Element/UiElement.cs` — UI 元素基底類別

## 8.2 IUserInterfaceManager — UI 管理器

```csharp
public interface IUserInterfaceManager
{
    // 焦點管理
    UiElement? KeyboardFocused { get; }
    UiElement? ControlFocused { get; set; }
    UiElement? CurrentlyHovered { get; }
    
    // 鍵盤焦點
    void GrabKeyboardFocus(UiElement control);
    void ReleaseKeyboardFocus();
    void ReleaseKeyboardFocus(UiElement ifControl);
    
    // 滑鼠位置
    ScreenCoordinates MousePositionScaled { get; }
    
    // 查詢滑鼠下的控制項
    UiElement? MouseGetControl(ScreenCoordinates coordinates);
    
    // 格式化按鍵提示文字
    string FormatKeyHints(IEnumerable<UiKeyHint> keyHints);
    
    // 執行一個 UI 層並等待結果
    UiResult<T> Query<T>(IUiLayerWithResult<T> layer);
}
```

### 焦點管理

```csharp
// 取得鍵盤焦點
public void GrabKeyboardFocus(UiElement control)
{
    // 只有 CanKeyboardFocus = true 的控制項可以取得焦點
    if (!control.CanKeyboardFocus)
        throw new ArgumentException("Control cannot get keyboard focus.");
    
    ReleaseKeyboardFocus();   // 先釋放舊焦點
    KeyboardFocused = control;
    KeyboardFocused.KeyboardFocusEntered();
}
```

### 鍵位提示格式化

```csharp
// 格式化按鍵提示（如「A [攻擊] B [防禦]」）
public string FormatKeyHints(IEnumerable<UiKeyHint> keyHints)
{
    var result = new StringBuilder();
    foreach (var keyHint in keyHints)
    {
        var keyNames = keyHint.KeyFunctions
            .Select(func => _inputManager.GetKeyFunctionButtonString(func));
        var keyNamesStr = String.Join(',', keyNames);
        result.Append($"{keyNamesStr} [{keyHint.ActionText}] ");
    }
    return result.ToString().TrimEnd();
}
```

## 8.3 Layer 系統

### IUiLayer — 層介面

```csharp
public interface IUiLayer : IDrawable
{
    // 更新層
    void Update(float dt);
    
    // 是否要求獨占輸入（阻擋下方層的輸入）
    bool IsModal { get; }
    
    // 層的結果類型（若需要返回值）
    Type? ResultType { get; }
}

// 帶返回值的層
public interface IUiLayerWithResult<T> : IUiLayer
{
    // 執行層並等待結果
    UiResult<T> GetResult();
}
```

### UiLayer — 層基底類別

```csharp
public abstract class UiLayer : BaseDrawable, IUiLayer
{
    [Dependency] protected readonly IInputManager InputManager = default!;
    [Dependency] protected readonly IUserInterfaceManager UiManager = default!;
    
    // 是否是模態層（阻擋下方輸入）
    public virtual bool IsModal => true;
    
    public abstract override void Update(float dt);
    public abstract override void Draw();
    
    // 訂閱按鍵動作
    protected void SubscribeKey(BoundKeyFunction function, Action<KeyEventArgs> handler);
    
    // 取消訂閱
    protected void UnsubscribeKey(BoundKeyFunction function);
}

// 帶泛型返回值的層
public abstract class UiLayerWithResult<T> : UiLayer, IUiLayerWithResult<T>
{
    // 結果容器
    private UiResult<T>? _result;
    
    // 子類別調用此方法結束層並返回結果
    protected void Finish(T result)
    {
        _result = new UiResult<T>.Value(result);
    }
    
    // 取消
    protected void Cancel()
    {
        _result = new UiResult<T>.Cancelled();
    }
    
    // 發生錯誤
    protected void Error(Exception ex)
    {
        _result = new UiResult<T>.Error(ex);
    }
}
```

### UiResult<T> — 層執行結果

```csharp
// 代數型別，表示 UI 層的三種結果
public abstract record UiResult<T>
{
    // 成功並返回值
    public record Value(T Data) : UiResult<T>;
    
    // 使用者取消
    public record Cancelled : UiResult<T>;
    
    // 發生錯誤
    public record Error(Exception Exception) : UiResult<T>;
    
    // 便利屬性
    public bool HasValue => this is Value;
    public T? TryGetValue() => this is Value v ? v.Data : default;
}

// 無返回值版本（UINone）
public record UiResult<UINone> : UiResult<UINone>;
```

## 8.4 Layers.cs — 層管理邏輯

```csharp
// 內部實作 - 層堆疊管理
public sealed partial class UserInterfaceManager
{
    // 層堆疊（最後一個是頂部活動層）
    private readonly List<IUiLayer> _layers = new();
    
    // 取得頂部層
    public IUiLayer? CurrentLayer => _layers.Count > 0 ? _layers[^1] : null;
    
    // 推入層（顯示新畫面）
    public void PushLayer(IUiLayer layer)
    {
        _layers.Add(layer);
        layer.GetPreferredSize(out var size);
        layer.SetPosition(0, 0);
        layer.SetSize(size.X, size.Y);
    }
    
    // 彈出層（關閉當前畫面）
    public void PopLayer(IUiLayer layer)
    {
        _layers.Remove(layer);
    }
    
    // 更新所有層
    public void UpdateLayers(FrameEventArgs frame)
    {
        // 只更新頂部層（或允許穿透的非模態層）
        for (int i = _layers.Count - 1; i >= 0; i--)
        {
            _layers[i].Update(frame.DeltaSeconds);
            if (_layers[i].IsModal) break;    // 遇到模態層就停止
        }
    }
    
    // 繪製所有層（由底到頂）
    public void DrawLayers()
    {
        foreach (var layer in _layers)
            layer.Draw();
    }
    
    // 執行一個層並等待結果（阻塞式）
    public UiResult<T> Query<T>(IUiLayerWithResult<T> layer)
    {
        PushLayer(layer);
        
        // 等待層完成（通過 Love2D 的事件循環）
        while (layer.GetResult() == null)
        {
            SystemStep();    // 處理 Love2D 事件（包括 Update 和 Draw）
        }
        
        PopLayer(layer);
        return layer.GetResult()!;
    }
}
```

## 8.5 UiElement — UI 元素基底

`UiElement` 是所有 UI 控制項的基底類別：

```csharp
public abstract class UiElement : IDrawable
{
    // 位置和大小
    public Vector2 Position { get; set; }
    public Vector2i PixelPosition { get; }
    public UIBox2i PixelRect { get; }
    
    // 可見性
    public bool Visible { get; set; } = true;
    
    // 焦點
    public bool CanKeyboardFocus { get; set; } = false;
    
    // 滑鼠事件處理
    public UIEventFilterMode EventFilter { get; set; } = UIEventFilterMode.Ignore;
    
    // UI 縮放
    public float UIScale { get; }
    
    // 子元素
    public int ChildCount { get; }
    public UiElement GetChild(int index);
    
    // 位置包含測試
    public virtual bool ContainsPoint(Vector2 point);
    
    // 焦點事件
    public virtual void KeyboardFocusEntered() { }
    public virtual void KeyboardFocusExited() { }
    
    // 滑鼠事件
    public virtual void MouseEntered() { }
    public virtual void MouseExited() { }
    
    // 繪製與更新
    public abstract void Draw();
    public abstract void Update(float dt);
    public abstract void GetPreferredSize(out Vector2 size);
}
```

## 8.6 Input.cs — 輸入路由

```csharp
// UI 輸入路由邏輯
public sealed partial class UserInterfaceManager
{
    // 鍵盤輸入處理
    private bool OnUIKeyBindStateChanged(BoundKeyEventArgs args)
    {
        if (args.State == BoundKeyState.Down)
            KeyBindDown(args);
        else
            KeyBindUp(args);
        
        // 若有焦點元素，消費此事件（不傳遞到遊戲邏輯）
        if (!args.CanFocus && KeyboardFocused != null)
            return true;
        
        return false;
    }
    
    private void KeyBindDown(BoundKeyEventArgs args)
    {
        // 先嘗試傳遞給焦點元素
        if (KeyboardFocused != null)
        {
            KeyboardFocused.KeyBindDown(args);
            return;
        }
        
        // 再傳遞給頂部層
        CurrentLayer?.KeyBindDown(args);
    }
}
```

## 8.7 主要 UI 層清單

### 核心遊戲 UI 層

| 層類別 | 位置 | 說明 |
|--------|------|------|
| `TitleScreenLayer` | Content/TitleScreen | 標題畫面（開始遊戲、讀取存檔） |
| `FieldLayer` | Content/FieldMap | 主要遊戲探索層（地圖、HUD） |
| `InventoryLayer` | Content/Inventory | 背包管理介面 |
| `CharaSheetLayer` | Content/UI | 角色資訊介面 |
| `EquipmentLayer` | Content/Equipment | 裝備管理介面 |
| `ReplLayer` | Content/Repl | C# REPL 主控台（除錯用）|
| `ConfigMenuLayer` | Content/ConfigMenu | 遊戲設定介面 |
| `MessageBoxLayer` | Content/UI | 訊息對話框 |
| `CharaMakeLayer` | Content/CharaMake | 角色創建介面 |

### UI 層查詢模式（典型用法）

```csharp
// 開啟背包並等待使用者選擇
var result = _uiManager.Query(new InventoryLayer(entity));

switch (result)
{
    case UiResult<InventoryResult>.Value v:
        HandleInventorySelection(v.Data);
        break;
    case UiResult<InventoryResult>.Cancelled:
        // 使用者取消
        break;
}
```

## 8.8 UIEventFilterMode — 事件過濾模式

```csharp
public enum UIEventFilterMode
{
    // 忽略事件（不接收滑鼠事件）
    Ignore,
    
    // 通過事件（接收但向下傳遞）
    Pass,
    
    // 停止事件（接收並阻止向下傳遞）
    Stop
}
```

## 8.9 UiKeyHint — 按鍵提示

```csharp
public class UiKeyHint
{
    // 對應的按鍵功能（可多個）
    public IEnumerable<BoundKeyFunction> KeyFunctions { get; }
    
    // 顯示的動作文字
    public string ActionText { get; }
    
    // 直接指定按鍵名稱文字（可選，覆蓋自動生成）
    public string? KeybindNamesText { get; }
}
```

在 UI 層底部顯示按鍵提示的典型用法：

```csharp
public class InventoryLayer : UiLayerWithResult<InventoryResult>
{
    private IEnumerable<UiKeyHint> GetKeyHints()
    {
        return new[]
        {
            new UiKeyHint(new[] { EngineKeyFunctions.UISelect }, "Select"),
            new UiKeyHint(new[] { EngineKeyFunctions.UICancel }, "Cancel"),
        };
    }
    
    public override void Draw()
    {
        // 繪製 UI...
        
        // 在底部繪製按鍵提示
        var keyHintsStr = UiManager.FormatKeyHints(GetKeyHints());
        DrawText(keyHintsStr, x: 0, y: Height - 20);
    }
}
```

## 8.10 ScreenCoordinates — 螢幕座標

```csharp
public readonly struct ScreenCoordinates
{
    public Vector2 Position { get; }     // 螢幕像素位置
    
    // 考慮 UI 縮放後的位置
    public Vector2 ScaledPosition { get; }
}
```
