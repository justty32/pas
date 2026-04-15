# 01 - 專案整體結構與設計哲學

## 1.1 專案背景

OpenNefia 是 **Elona**（一款日本 roguelike RPG）的開源重製版引擎。原版 Elona 以 HSP（Hot Soup Processor）語言撰寫，架構龐雜且難以維護。OpenNefia 的目標是：

- 以現代化 C# 重新實作引擎底層
- 提供完整的 Mod 擴充系統
- 保留原版遊戲的核心玩法與世界觀
- 透過 ECS 架構使遊戲邏輯更加模組化

## 1.2 技術棧

| 技術 | 用途 |
|------|------|
| **C# / .NET 6.0** | 主要開發語言與執行環境 |
| **LÖVE 2D (via Love2dCS)** | 圖形渲染後端（2D 遊戲框架） |
| **NLua** | Lua 腳本整合（用於本地化文字） |
| **YamlDotNet** | 解析 YAML 格式的原型資料檔案 |
| **CSharpRepl** | 遊戲內 C# REPL 開發者主控台 |
| **xUnit** | 單元測試框架 |
| **MSBuild** | 建構系統 |

## 1.3 解決方案（Solution）組成

```
OpenNefia.sln
├── OpenNefia.Core/           ← 引擎核心（~400 個 C# 檔案）
├── OpenNefia.Content/        ← 遊戲內容（~650 個 C# 檔案）
├── OpenNefia.EntryPoint/     ← 進入點（Main 方法）
├── OpenNefia.LecchoTorte/    ← 額外內容擴充模塊
├── OpenNefia.Analyzers/      ← 自訂 Roslyn 程式碼分析器
├── OpenNefia.Benchmarks/     ← 效能基準測試
├── OpenNefia.Tests/          ← 核心引擎單元測試
├── OpenNefia.Content.Tests/  ← 遊戲內容單元測試
├── OpenNefia.Packaging/      ← 遊戲打包與發行工具
└── Thirdparty/
    ├── CSharpRepl/           ← C# REPL（Git Submodule）
    └── Love2dCS/             ← LÖVE 2D 的 C# 綁定（Git Submodule）
```

## 1.4 OpenNefia.Core 子系統清單（35 個）

核心引擎負責所有與具體遊戲內容無關的底層功能：

| 子系統目錄 | 說明 |
|-----------|------|
| `IoC/` | 依賴注入容器 |
| `GameController/` | 主控制器（遊戲循環的指揮官） |
| `GameObjects/` | ECS 核心（Entity、Component、System、EventBus） |
| `Maps/` | 地圖與磁磚管理 |
| `Areas/` | 區域（地城樓層）管理 |
| `Graphics/` | 圖形後端抽象層（Love2D 或 Headless） |
| `Rendering/` | 地圖渲染、精靈圖集、字型管理 |
| `Input/` | 輸入處理（按鍵綁定） |
| `UserInterface/` | UI 層管理器 |
| `UI/` | UI 元素基底類別 |
| `Audio/` | 音效與音樂管理 |
| `Serialization/` | YAML / 型別序列化系統（100+ 個檔案） |
| `Prototypes/` | 原型資料系統（YAML 載入、繼承、熱重載） |
| `ResourceManagement/` | 資源快取與虛擬檔案系統 |
| `ContentPack/` | Mod / 內容包載入系統 |
| `SaveGames/` | 存讀檔系統 |
| `Configuration/` | 組態檔管理（CVars 系統） |
| `Reflection/` | 型別掃描（Assembly 掃描、屬性發現） |
| `Locale/` | 本地化（多語言）支援 |
| `Log/` | 日誌系統 |
| `Console/` | 開發者主控台 |
| `Timing/` | 計時器管理 |
| `Asynchronous/` | 非同步任務管理 |
| `Random/` | 隨機數產生器 |
| `Maths/` | 數學工具（Vector、Matrix、Color 等） |
| `Containers/` | 容器系統（物品欄位） |
| `Directions/` | 方向工具 |
| `Logic/` | 遊戲邏輯基礎（Verb 動作系統） |
| `Stats/` | 屬性值包裝器（含修正值） |
| `Profiles/` | 使用者設定檔管理 |
| `Game/` | 遊戲會話管理 |
| `Exceptions/` | 自訂例外類別 |
| `Utility/` | 通用工具函式 |
| `Properties/` | 組件相依性管理 |
| `CVars.cs` | 全域組態變數定義 |

## 1.5 OpenNefia.Content 子系統清單（57 個）

遊戲內容層負責所有與 Elona 遊戲玩法直接相關的邏輯：

| 子系統目錄 | 說明 |
|-----------|------|
| `Charas/` | 角色系統（種族、職業、性別） |
| `Skills/` | 技能與屬性系統（HP/MP/體力） |
| `Equipment/` | 裝備系統 |
| `EquipSlots/` | 裝備欄位定義 |
| `Inventory/` | 背包系統 |
| `Cargo/` | 重量 / 攜帶量系統 |
| `Levels/` | 角色等級系統 |
| `CharaMake/` | 角色創建介面與邏輯 |
| `CharaAppearance/` | 角色外觀（精靈圖） |
| `PCCs/` | PCC（像素角色創建器）圖形 |
| `StatusEffects/` | 狀態異常（中毒、祝福等） |
| `Feats/` | 特技 / 成就系統 |
| `Roles/` | 職業角色系統 |
| `Factions/` | 陣營聲望系統 |
| `Fame/` | 聲望 / 榮耀追蹤 |
| `Karma/` | 業力 / 道德陣營 |
| `Sanity/` | 精神狀態系統 |
| `God/` | 神明系統 |
| `Guild/` | 公會系統 |
| `Parties/` | 隊伍 / 夥伴系統 |
| `TurnOrder/` | 戰鬥回合順序 |
| `VanillaAI/` | NPC AI 系統 |
| `FieldMap/` | 主要探索地圖 |
| `Maps/` | 地圖載入 / 生成 |
| `Areas/` | 區域原型與管理 |
| `Dungeons/` | 地城生成與管理 |
| `RandomAreas/` | 隨機區域生成 |
| `Nefia/` | Nefia（特殊地城）系統 |
| `MapVisibility/` | 視野 / FOV 系統 |
| `World/` | 世界時間與日期 |
| `EntityGen/` | 程序化實體生成 |
| `DisplayName/` | 實體命名（含本地化） |
| `CustomName/` | 自訂實體名稱 |
| `DrawDepth/` | 視覺層次深度排序 |
| `HealthBar/` | 視覺生命值指示器 |
| `Qualities/` | 物品品質 / 附魔等級 |
| `Properties/` | 物品屬性與屬性值 |
| `Currency/` | 金幣 / 貨幣系統 |
| `Shopkeeper/` | NPC 商店系統 |
| `Journal/` | 任務 / 日誌系統 |
| `Effects/` | 視覺特效 |
| `GameObjects/` | 遊戲特定實體組件 |
| `Input/` | 遊戲控制鍵位綁定 |
| `UI/` | 多個 UI 層（HUD、背包、角色資訊等） |
| `TitleScreen/` | 標題畫面與存檔載入 UI |
| `ConfigMenu/` | 設定 / 組態 UI |
| `Repl/` | 互動式 C# REPL 主控台層 |
| `Audio/` | 音訊 / 音樂內容 |
| `Rendering/` | 遊戲特定渲染 |
| `Locale/` | 本地化內容 |
| `Logic/` | 遊戲邏輯輔助 |
| `Prototypes/` | 內容原型載入器 |
| `Resources/` | 資源清單 |
| `ConsoleCommands/` | 除錯 / 管理員命令 |
| `RandomText/` | 隨機名稱 / 別名生成 |
| `EntryPoint.cs` | Mod 進入點初始化 |
| `ContentIoC.cs` | 內容特定的 IoC 注冊 |
| `CCVars.cs` | 內容層組態變數 |

## 1.6 目錄結構完整圖

```
OpenNefia-0.1.0/
├── OpenNefia.Core/
│   ├── CVars.cs                  ← 核心 CVars 定義（顯示、音訊、日誌、動畫）
│   ├── Engine.cs                 ← 版本資訊（"OpenNefia.NET"）
│   ├── IoCSetup.cs               ← 注冊 70+ 個服務的靜態設定類別
│   ├── ProgramShared.cs          ← 共用初始化工具（資源掛載等）
│   └── [各子系統目錄]/
│
├── OpenNefia.Content/
│   ├── CCVars.cs                 ← 內容層 CVars（遊戲特定設定）
│   ├── ContentIoC.cs             ← 內容層 IoC 注冊
│   ├── EntryPoint.cs             ← 內容 Mod 進入點
│   └── [各子系統目錄]/
│
├── OpenNefia.EntryPoint/
│   └── Program.cs                ← Main() 入口
│
├── Support/                      ← 原版遊戲資源（圖片、音樂等）
├── Resources/                    ← 引擎內建資源
├── docs/                         ← DocFX 文件設定
├── build.sh / build.ps1          ← 建構腳本
├── stylua.toml                   ← Lua 程式碼格式設定
└── OpenNefia.sln                 ← Visual Studio 解決方案檔
```

## 1.7 重要設計決策

### 為何使用 ECS？
Elona 原版的程式碼是一個巨大的過程式程式，各功能緊密耦合。ECS 將遊戲物件分解為純資料（Component）和純邏輯（System），使得：
- 新增功能不需修改現有類別
- 元件可以任意組合
- 測試單一系統不需要整個遊戲環境

### 為何使用 IoC？
- 允許在測試時替換 `HeadlessGraphics` 取代 `LoveGraphics`
- 系統間透過介面通訊，不依賴具體實作
- 支援在同一程序中執行多個遊戲實例（Thread-local 容器）

### 為何資料使用 YAML 原型？
- Mod 作者不需要撰寫 C# 程式碼即可添加新的實體、種族、物品
- 原型系統支援繼承，可以基於現有原型進行修改
- 支援熱重載，開發時可即時看到修改效果
