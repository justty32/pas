# 07 - 渲染管線與圖形系統

## 7.1 概述

OpenNefia 的渲染系統採用**分層抽象**設計：
1. `IGraphics` — 最底層的圖形後端抽象
2. `MapRenderer` — 地圖渲染器（使用 TileLayer 系統）
3. `IUserInterfaceManager` — UI 層渲染

相關檔案：
- `OpenNefia.Core/Graphics/LoveGraphics.cs` — Love2D 圖形後端（19.5KB）
- `OpenNefia.Core/Graphics/HeadlessGraphics.cs` — 無頭模式（測試用）
- `OpenNefia.Core/Rendering/MapRenderer.cs` — 地圖渲染器
- `OpenNefia.Core/Rendering/AssetManager.cs` — 資源實例管理
- `OpenNefia.Core/Rendering/TileAtlasManager.cs` — 精靈圖集管理

## 7.2 IGraphics — 圖形後端介面

最底層的圖形抽象，封裝了所有與底層圖形庫的互動：

```csharp
public interface IGraphics
{
    // 視窗屬性
    Vector2i WindowSize { get; }
    float WindowScale { get; }
    
    // 視窗事件
    event Action<TextEditingEventArgs>? OnTextEditing;
    event Action<TextInputEventArgs>? OnTextInput;
    event Action<MouseMovedEventArgs>? OnMouseMoved;
    event Action<MouseButtonEventArgs>? OnMousePressed;
    event Action<MouseButtonEventArgs>? OnMouseReleased;
    event Action<KeyEventArgs>? OnKeyPressed;
    event Action<KeyEventArgs>? OnKeyReleased;
    event Action<MouseWheelEventArgs>? OnMouseWheel;
    event Action<WindowResizedEventArgs>? OnWindowResized;
    event Func<QuitEventArgs, bool>? OnQuit;
    
    // 初始化與關閉
    void Initialize();
    void Shutdown();
    
    // 渲染控制
    void BeginDraw();
    void EndDraw();
    
    // 啟動畫面
    void ShowSplashScreen();
}
```

### LoveGraphics — Love2D 後端
```csharp
// OpenNefia.Core/Graphics/LoveGraphics.cs
public sealed class LoveGraphics : Love.Scene, IGraphics
{
    // 繼承 Love.Scene（Love2D 的場景基底類別）
    // 覆寫 Love2D 的事件方法並轉發到 OpenNefia 的事件系統
    
    public override void Load()
    {
        // Love2D 初始化
        Love.Graphics.SetDefaultFilter(Love.FilterMode.Nearest, Love.FilterMode.Nearest);
        // 設定視窗...
    }
    
    public override void Draw()
    {
        // 每幀渲染（由 Love2D 呼叫）
        _gameController.Draw();
    }
    
    public override void Update(float dt)
    {
        // 每幀更新（由 Love2D 呼叫）
        var frame = new FrameEventArgs(dt);
        _gameController.Update(frame);
    }
    
    // 鍵盤事件轉換
    public override void KeyPressed(Love.KeyConstant key, Love.Scancode scancode, bool isRepeat)
    {
        // 轉換 Love.KeyConstant → Keyboard.Key
        OnKeyPressed?.Invoke(new KeyEventArgs(convertedKey, isRepeat));
    }
}
```

### HeadlessGraphics — 無頭後端
```csharp
// 用於單元測試和無顯示器的環境
public sealed class HeadlessGraphics : IGraphics
{
    // 所有方法都是空操作（No-op）
    public void Initialize() { }
    public void BeginDraw() { }
    public void EndDraw() { }
    // ...
}
```

## 7.3 MapRenderer — 地圖渲染器

地圖渲染器使用**責任鏈（Chain of Responsibility）**模式，由多個 `ITileLayer` 按序疊加渲染：

```csharp
public sealed class MapRenderer : BaseDrawable, IMapRenderer
{
    [Dependency] private readonly IMapDrawables _mapDrawables = default!;
    [Dependency] private readonly IReflectionManager _reflectionManager = default!;
    [Dependency] private readonly ITileAtlasManager _tileAtlasManager = default!;
    [Dependency] private readonly IEntitySystemManager _entitySystemManager = default!;
    
    // 所有已注冊的 TileLayer
    private readonly List<ITileLayer> _allTileLayers = new();
    
    // 已啟用的 TileLayer（按順序渲染）
    private List<ITileLayer> _enabledTileLayers = new();
    
    // 目前渲染的地圖
    private IMap? _map;
}
```

### 注冊 TileLayer

TileLayer 透過**反射自動注冊**，不需要手動添加：

```csharp
// 任何標記了 [RegisterTileLayer] 的類別都會被自動注冊
[RegisterTileLayer(enabledAtStartup: true)]
public class TileAndShadowTileLayer : ITileLayer
{
    // 渲染磁磚和陰影
}

[RegisterTileLayer(enabledAtStartup: true)]
public class EntityTileLayer : ITileLayer
{
    // 渲染實體精靈圖
}
```

注冊流程：
```csharp
public void RegisterTileLayers()
{
    // 建立 TileLayer 專用的依賴集合
    _layerDependencyCollection = new(_entitySystemManager.DependencyCollection);
    
    // 透過反射找到所有 [RegisterTileLayer] 類別
    foreach (var type in _reflectionManager.FindTypesWithAttribute<RegisterTileLayerAttribute>())
    {
        RegisterTileLayer(type);
    }
    
    // 建構依賴圖（解析 TileLayer 的依賴）
    _layerDependencyCollection.BuildGraph();
    
    // 按排序建立 TileLayer 實例
    foreach (var type in GetSortedLayers())
    {
        var layer = (ITileLayer) _layerDependencyCollection.ResolveType(type);
        layer.Initialize();
        _allTileLayers.Add(layer);
    }
}
```

### ITileLayer — 磁磚渲染層介面

```csharp
public interface ITileLayer
{
    void Initialize();
    
    // 設定渲染目標地圖
    void SetMap(IMap map, MapCoordinates viewportCenter);
    
    // 更新渲染資料（每幀）
    void Update(float dt);
    
    // 執行渲染
    void Draw();
    
    // 視窗大小改變時
    void OnThemeSwitched();
}
```

### 渲染排序

TileLayer 支援使用 `Before`/`After` 屬性指定渲染順序：

```csharp
[RegisterTileLayer(enabledAtStartup: true)]
[RegisterBefore(typeof(EntityTileLayer))]    // 在 EntityTileLayer 之前渲染
public class FloorTileLayer : ITileLayer { }

[RegisterTileLayer(enabledAtStartup: true)]
[RegisterAfter(typeof(FloorTileLayer))]       // 在 FloorTileLayer 之後渲染
public class EntityTileLayer : ITileLayer { }
```

## 7.4 AssetManager — 資源管理器

管理遊戲中的精靈圖資源：

```csharp
// 資源原型（YAML 定義）
[Prototype("asset")]
public class AssetPrototype : IPrototype
{
    public string ID { get; private set; } = default!;
    public ResourcePath Path { get; private set; } = default!;  // 圖片路徑
    public List<AssetRegion>? Regions { get; private set; }     // 子區域定義
}

// 資源實例（執行時）
public class AssetInstance
{
    public AssetPrototype Prototype { get; }
    
    // 取得整個圖片
    public Love.Image Image { get; }
    
    // 取得命名子區域
    public Love.Quad GetRegion(string regionName);
    
    // 繪製到螢幕
    public void Draw(float x, float y, float angle = 0, float sx = 1, float sy = 1);
    public void DrawRegion(string regionName, float x, float y);
}
```

### 預載資源

```csharp
public void PreloadAssets()
{
    // 枚舉所有 AssetPrototype 並預載
    foreach (var proto in _prototypeManager.EnumeratePrototypes<AssetPrototype>())
    {
        var image = Love.Graphics.NewImage(proto.Path.ToString());
        _assets[proto.ID] = new AssetInstance(proto, image);
    }
}
```

## 7.5 TileAtlasManager — 磁磚圖集管理器

將多個小圖片打包成一個大圖集（Atlas），提升渲染效率：

```csharp
public interface ITileAtlasManager
{
    // 初始化並載入所有圖集
    void Initialize();
    void LoadAtlases();
    
    // 取得磁磚的圖集區域
    AtlasRegion GetTileRegion(int tileIndex);
    
    // 主題切換
    event Action? ThemeSwitched;
}
```

### TileAtlasFactory — 圖集生成器

```csharp
// 將多個磁磚圖片打包成一個大圖集
public class TileAtlasFactory
{
    public Love.Image PackAtlas(IEnumerable<TileSource> tiles)
    {
        // 1. 計算最佳圖集大小
        // 2. 將每個磁磚圖片複製到對應位置
        // 3. 記錄每個磁磚的 UV 座標（AtlasRegion）
        // 4. 返回打包好的圖集
    }
}
```

## 7.6 FontManager — 字型管理器

```csharp
public interface IFontManager
{
    void Initialize();
    
    // 取得字型（依據大小和樣式）
    Love.Font GetFont(FontSpec spec);
    
    // Love2D 字型
    Love.Font DefaultFont { get; }
}

public readonly struct FontSpec
{
    public int Size { get; }
    public FontStyle Style { get; }  // Normal, Bold, Italic
}
```

## 7.7 ThemeManager — 主題管理器

主題系統允許更換遊戲的視覺風格：

```csharp
public interface IThemeManager
{
    void Initialize();
    void Shutdown();
    
    // 載入主題目錄
    void LoadDirectory(ResourcePath path);
    
    // 切換活動主題
    void SetActiveTheme(string themeId);
}
```

主題可以覆寫磁磚圖集、UI 顏色等視覺元素。

## 7.8 ICoords — 座標系統

座標系統抽象了地圖格子座標到螢幕像素的轉換：

```csharp
public interface ICoords
{
    // 磁磚大小（像素）
    Vector2i TileSize { get; }
    
    // 地圖格子座標 → 螢幕像素座標
    Vector2 TileToScreen(Vector2i tilePos);
    
    // 螢幕像素座標 → 地圖格子座標
    Vector2i ScreenToTile(Vector2 screenPos);
}

// 正交座標系（預設實作）
public class OrthographicCoords : ICoords
{
    public Vector2i TileSize => new(48, 48);    // Elona 的磁磚大小
    
    public Vector2 TileToScreen(Vector2i tilePos)
        => new Vector2(tilePos.X * TileSize.X, tilePos.Y * TileSize.Y);
}
```

## 7.9 MapDrawables — 地圖繪製物件

短暫出現的視覺效果（如攻擊動畫、特效）：

```csharp
public interface IMapDrawables
{
    // 添加一個繪製物件（指定位置和持續時間）
    void Add(IMapDrawable drawable, MapCoordinates coords, float duration);
    
    // 更新（每幀）
    void Update(float dt);
    
    // 渲染
    void Draw();
}
```

## 7.10 BaseDrawable — 可繪製元素基底

所有可以被繪製的 UI 元素都繼承自 `BaseDrawable`：

```csharp
public abstract class BaseDrawable : IDrawable
{
    public Vector2 Position { get; set; }
    public Vector2 Size { get; protected set; }
    
    public abstract void Update(float dt);
    public abstract void Draw();
    
    // 計算繪製所需大小
    public abstract void GetPreferredSize(out Vector2 size);
    
    // 設定位置和大小
    public virtual void SetPosition(float x, float y);
    public virtual void SetSize(float width, float height);
}
```

## 7.11 渲染流程圖

```
GameController.Draw()
    ↓
DoDraw()
    ↓
_graphics.BeginDraw()          ← 開始 Love2D 渲染
    ↓
_uiManager.DrawLayers()        ← 繪製所有 UI 層
    ↓
    每個 UI 層（由頂到底）：
    ↓
    FieldLayer.Draw()           ← 主遊戲層
        ↓
        MapRenderer.Draw()      ← 地圖渲染器
            ↓
            對每個啟用的 ITileLayer（按順序）：
            ↓
            1. FloorTileLayer.Draw()        ← 地板磁磚 + 陰影
            2. WallTileLayer.Draw()         ← 牆壁磁磚
            3. EntityTileLayer.Draw()       ← 實體精靈圖
            4. EffectTileLayer.Draw()       ← 特效
            5. UITileLayer.Draw()           ← 地圖上的 UI 元素
        ↓
        MapDrawables.Draw()     ← 臨時動畫效果
        ↓
        HUDLayer.Draw()         ← 血量、MP 等 HUD
    ↓
_graphics.EndDraw()
    ↓
Love.Graphics.Present()        ← 呈現到螢幕
```
