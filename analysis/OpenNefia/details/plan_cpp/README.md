# OpenNefia C++ 重寫計畫 (Raylib 版)

本計畫旨在將 C# 版 OpenNefia 引擎以 C++ 重新實作，並使用 raylib 作為圖形後端。重寫過程將嚴格遵循原始碼的架構，將 C# 的子系統逐一遷移至 C++。

## 核心技術棧選擇

| 功能 | C++ 函式庫 | 說明 |
|------|------------|------|
| **圖形/音訊/輸入** | **raylib** | 代替原本的 Love2D (Love2dCS) |
| **ECS 核心** | **EnTT** | 高效能且成熟的 C++ ECS 框架，對應 `OpenNefia.Core.GameObjects` |
| **YAML 解析** | **yaml-cpp** | 用於原型系統與資料序列化，對應 `OpenNefia.Core.Serialization` |
| **日誌系統** | **spdlog** | 高效能非同步日誌，對應 `OpenNefia.Core.Log` |
| **配置 (Config)** | **tomlplusplus** | 處理 TOML 設定檔，對應 `OpenNefia.Core.Configuration` |
| **依賴注入** | **自定義 (Service Locator)** | 由於 C++ 缺乏反射，將改用強型別的 Service Locator 或 Context 模式 |

## 重寫階段與優先順序

### 第一階段：基礎建設 (Foundation)
- [ ] 專案結構與 CMake 設定
- [ ] 基礎工具類 (Maths, Utility, Log)
- [ ] IoC/服務定位器 (Service Locator)
- [ ] 虛擬檔案系統 (ResourceManagement)

### 第二階段：ECS 與 事件系統 (ECS Core)
- [ ] 實體管理器 (EntityManager) 封裝 EnTT
- [ ] 基礎組件 (MetaData, Spatial)
- [ ] 事件匯流排 (EntityEventBus) - 廣播與定向事件

### 第三階段：資料驅動 (Prototypes & Serialization)
- [ ] YAML 序列化系統 (SerializationManager)
- [ ] 原型管理系統 (PrototypeManager)
- [ ] 資源快取 (AssetManager)

### 第四階段：渲染與輸入 (Rendering & Input)
- [ ] raylib 抽象層 (Graphics)
- [ ] 磁磚渲染 (MapRenderer)
- [ ] 輸入綁定 (InputManager)

### 第五階段：遊戲循環與 UI (Game Loop & UI)
- [ ] 主控制器 (GameController)
- [ ] UI 系統基底 (UserInterface)
- [ ] 本地化系統 (LocalizationManager)

---

## 檔案對照表 (Core)

| C# Namespace / Directory | C++ 目錄 (src/) | 關鍵類別 |
|-------------------------|----------------|----------|
| `OpenNefia.Core.IoC` | `core/ioc/` | `ServiceLocator` |
| `OpenNefia.Core.GameObjects` | `core/ecs/` | `EntityManager`, `EntitySystem` |
| `OpenNefia.Core.Prototypes` | `core/prototypes/` | `PrototypeManager` |
| `OpenNefia.Core.Serialization` | `core/serialization/` | `SerializationManager` |
| `OpenNefia.Core.Graphics` | `core/graphics/` | `RaylibGraphics` |
| `OpenNefia.Core.UserInterface` | `core/ui/` | `UIManager` |
