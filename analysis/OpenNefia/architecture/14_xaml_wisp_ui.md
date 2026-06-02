# 14 - XAML 編譯期注入與 Wisp UI 框架

> 核對於 2026-06-01 (Claude Code Sonnet 4.6)

## 14.1 概述

OpenNefia 包含兩套並存的 UI 子系統：

| 子系統 | 定義位置 | 特性 |
|--------|---------|------|
| **UiElement / UiLayer** | `OpenNefia.Core/UI/Element/` | 舊版 UI，直接繼承 Love2D 繪製，手動定位 |
| **Wisp** | `OpenNefia.Core/UI/Wisp/` | 新版 UI，自動版面配置、XAML 定義、ImGui 風格浮動視窗 |

Wisp 是 OpenNefia 的「未來 UI」，設計目標是最終取代舊版 UiElement 系統。名稱源自其預期使用情境——浮動的除錯/工具視窗。

---

## 14.2 XAML 編譯期注入系統（XamlInjectors）

OpenNefia 使用與 **Avalonia UI** 相同的 XamlX 技術，在**編譯期**將 `.xaml` 標記語言轉換為 IL 指令，直接嵌入目標 assembly。

### 技術棧

```
.xaml 檔案（標記語言）
    ↓  MSBuild Task (OpenNefia.XamlInjectors.csproj)
XamlX（解析器 + AST）
    ↓
Mono.Cecil（IL 讀寫）
    ↓  編譯期生成 InitializeComponent() 方法
*.dll（內嵌控件初始化 IL）
```

相關檔案：
- `OpenNefia.XamlInjectors/XamlCompiler.cs` — 主編譯器，基於 Avalonia 的 `XamlCompilerTaskExecutor.cs`
- `OpenNefia.XamlInjectors/CompileOpenNefiaXamlTask.cs` — MSBuild Task 入口
- `OpenNefia.Core/UserInterface/XAML/OpenNefiaXamlLoader.cs` — 執行期載入器
- `MSBuild/XamlIL.targets` — MSBuild 整合目標

### XAML 檔案格式

```xml
<!-- OpenNefia.Content/DebugView/Controls/AllInOneWindow.xaml -->
<DefaultWindow xmlns="https://opennefia.io"
               Class="OpenNefia.Content.DebugView.AllInOneWindow"
               Title="All In One"
               MinSize="300 300">
    <ScrollContainer VerticalExpand="False">
        <BoxContainer Orientation="Vertical">
            <Button Text="Button" HorizontalAlignment="Left" Margin="0 4" />
            <Label Text="Label" HorizontalAlignment="Left" Margin="0 4" />
            <CheckBox Text="CheckBox" HorizontalAlignment="Left" Margin="0 4" />
        </BoxContainer>
    </ScrollContainer>
</DefaultWindow>
```

### Code-Behind 模式

每個 XAML 檔案對應一個 `.xaml.cs` code-behind：

```csharp
// OpenNefia.Content/DebugView/Controls/AllInOneWindow.xaml.cs
public partial class AllInOneWindow : DefaultWindow
{
    public AllInOneWindow()
    {
        OpenNefiaXamlLoader.Load(this);   // 執行期呼叫編譯期注入的 InitializeComponent
    }
}
```

### IDE 支援的技巧

Rider 的 XAML 工具高度依賴對 Avalonia SDK 的識別。OpenNefia 為此採取了一個值得注意的做法：

1. 定義假的 `Avalonia.Metadata.XmlnsDefinitionAttribute` 型別（`OpenNefia.Core/UserInterface/XAML/XmlnsDefinitionAttribute.cs`）讓 Rider 偵測到「這是 Avalonia 專案」
2. 定義假的 `Avalonia.Data.Binding`（實際呼叫時拋出例外，因為資料綁定尚未支援）
3. 在 csproj 中引用一個名為 `Avalonia.Base` 的假專案以通過 Rider 的 SDK 偵測

> `RiderNotes.md`（`OpenNefia.Core/UserInterface/XAML/RiderNotes.md`）詳細記錄了這些 hack 的緣由。

---

## 14.3 WispControl — 自動版面配置控件基底

`WispControl`（`OpenNefia.Core/UI/Wisp/WispControl.cs`）繼承自 `UiElement`，增加了自動版面配置能力。

### 版面配置模型（Measure / Arrange 兩階段）

與 WPF/Avalonia 相同的兩階段版面：

```
第一階段：Measure（量測）
    控件回報需要多大空間（DesiredSize）
    ↓
第二階段：Arrange（排列）
    父容器決定子控件的實際位置與大小
```

### 主要屬性

```csharp
public partial class WispControl : UiElement
{
    // 期望尺寸（Measure 後設定）
    public Vector2 DesiredSize { get; private set; }
    public Vector2i DesiredPixelSize => (Vector2i)(DesiredSize * UIScale);

    // 伸展比例（用於 BoxContainer 的 Fill 分配）
    private float _sizeFlagsStretchRatio = 1f;

    // 對齊方式
    public HAlignment HorizontalAlignment { get; set; }  // Left / Center / Right / Stretch
    public VAlignment VerticalAlignment { get; set; }    // Top / Center / Bottom / Stretch

    // 是否在對應方向上擴張以佔用剩餘空間
    public bool HorizontalExpand { get; set; }
    public bool VerticalExpand { get; set; }

    // 邊距（同 WPF 的 Margin）
    public Thickness Margin { get; set; }

    // CSS-like 樣式類別
    public StyleClassCollection StyleClasses { get; }
}
```

### 與舊版 UiElement 的關係

```
UiElement                    ← 舊版手動定位基底，Love2D 繪製
    └── WispControl          ← 新版自動版面，擴充 Measure/Arrange
            └── 各控件類別
```

未來計畫：將 `WispControl` 與 `UiElement` 合併為單一 `Control` 類別，並將所有現有 `UiElement` UI 遷移到 Wisp。

---

## 14.4 Wisp 控件目錄

`OpenNefia.Core/UI/Wisp/Controls/` 提供以下標準控件（共 25 個）：

| 控件 | 說明 |
|------|------|
| `Label` | 靜態文字標籤 |
| `Button` | 按鈕 |
| `CheckBox` | 核取方塊 |
| `LineEdit` | 單行文字輸入 |
| `OptionButton` | 下拉選單 |
| `BoxContainer` | 線性排列容器（水平 / 垂直） |
| `GridContainer` | 格線排列容器 |
| `LayoutContainer` | 手動定位容器 |
| `PanelContainer` | 帶背景面板的容器 |
| `ScrollContainer` | 可捲動容器 |
| `TabContainer` | 分頁容器 |
| `PopupContainer / Popup` | 浮動彈出視窗 |
| `ItemList` | 清單元件 |
| `TextureRect` | 紋理顯示 |
| `TextureButton` | 圖片按鈕 |
| `ChipView` | 精靈圖（tile chip）顯示 |
| `TileView` | 遊戲地圖 Tile 顯示 |
| `HScrollBar / VScrollBar / ScrollBar / Range` | 捲軸控件族群 |
| `BaseButton / ContainerButton` | 按鈕基底類別 |
| `Container` | 容器基底類別 |

### CustomControls（自訂複合控件）

`OpenNefia.Core/UI/Wisp/CustomControls/` 包含組合型控件：

| 控件 | 說明 |
|------|------|
| `DefaultWindow` | 標準視窗（含標題列、關閉按鈕、最小尺寸）— XAML 根節點常用 |

---

## 14.5 XAML 中存在的控件（DebugView 範例）

`OpenNefia.Content/DebugView/Controls/` 包含 7 個 XAML 視窗，均為除錯用途：

| XAML 檔案 | 用途 |
|-----------|------|
| `AllInOneWindow.xaml` | 綜合控件展示 |
| `ControlDebugWindow.xaml` | 控件樹除錯視窗 |
| `ControlTestMainWindow.xaml` | 控件測試主視窗 |
| `EntityPickerWindow.xaml` | 實體選取器（開發工具） |
| `NewMapDialog.xaml` | 新增地圖對話框 |
| `TextureRectWindow.xaml` | 紋理顯示測試 |
| `TilePickerWindow.xaml` | Tile 選取器 |

---

## 14.6 Wisp 樣式系統

`OpenNefia.Core/UI/Wisp/Styling/` 提供類 CSS 的樣式機制。

控件可透過 `StyleClasses` 屬性標記：

```csharp
myButton.StyleClasses.Add("danger");
```

樣式系統尚在開發中，目前主要用於按鈕與容器的視覺狀態（hover、pressed、disabled）。

---

## 14.7 XamlNameGenerator — 名稱屬性生成器

`OpenNefia.XamlNameGenerator` 專案在編譯期掃描 XAML 中有 `Name` 屬性的控件，為 code-behind 類別自動生成對應的欄位存取屬性（類似 Avalonia 的 `x:Name` 機制）。

---

## 14.8 Wisp 與遊戲 UI 的邊界

| 特性 | 舊版 UiElement 遊戲 UI | Wisp UI |
|------|----------------------|---------|
| 使用情境 | 遊戲主畫面（HUD、背包、角色頁） | 除錯工具、浮動視窗 |
| 定義方式 | C# 程式碼（`GetPreferredSize()`、`Draw()`） | XAML + code-behind |
| 版面配置 | 手動（setPosition、setSize） | 自動（Measure / Arrange） |
| Love2D 整合 | 直接調用 `Love.Graphics.*` | 透過 WispControl 抽象層 |
| 完成度 | 成熟（主遊戲已使用） | 開發中（僅除錯用） |

---

## 14.9 OpenNefia.YAMLValidator

`OpenNefia.YAMLValidator` 是獨立的命令列工具，用於驗證 `Resources/Prototypes/` 下的 YAML 原型定義是否符合 schema。不屬於遊戲執行路徑，僅用於開發期 CI 驗證。
