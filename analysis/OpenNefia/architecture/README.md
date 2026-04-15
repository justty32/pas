# OpenNefia 0.1.0 架構文件總覽

本目錄包含 OpenNefia 開源遊戲引擎的完整架構分析文件，涵蓋每個模塊、每個子系統與設計思想的詳細說明。

## 文件索引

| 文件 | 內容 |
|------|------|
| [01_project_overview.md](01_project_overview.md) | 專案整體結構、技術棧、設計哲學 |
| [02_ioc_dependency_injection.md](02_ioc_dependency_injection.md) | IoC 容器與依賴注入系統 |
| [03_ecs_system.md](03_ecs_system.md) | Entity-Component-System 核心架構 |
| [04_game_loop_initialization.md](04_game_loop_initialization.md) | 遊戲啟動流程與主循環 |
| [05_map_area_system.md](05_map_area_system.md) | 地圖與區域管理系統 |
| [06_prototype_serialization.md](06_prototype_serialization.md) | 原型系統與資料序列化 |
| [07_rendering_pipeline.md](07_rendering_pipeline.md) | 渲染管線與圖形系統 |
| [08_ui_system.md](08_ui_system.md) | 使用者介面系統 |
| [09_content_modules.md](09_content_modules.md) | 遊戲內容子系統（角色、技能、物品等） |
| [10_ai_turn_order.md](10_ai_turn_order.md) | NPC AI 與回合順序系統 |
| [11_save_load_system.md](11_save_load_system.md) | 存讀檔系統 |
| [12_mod_localization.md](12_mod_localization.md) | Mod 載入與本地化（多語言）系統 |
| [13_audio_input.md](13_audio_input.md) | 音訊與輸入系統 |

## 快速理解：核心設計概念

OpenNefia 是一個以 **Elona** roguelike 遊戲為基礎的開源重製引擎，使用 C# (.NET 6.0) 撰寫。

### 三大核心設計模式

```
1. Entity-Component-System (ECS)
   → 遊戲物件由純資料的 Component 組成
   → EntitySystem 負責邏輯處理
   → EntityEventBus 提供系統間的解耦通訊

2. Inversion of Control (IoC)
   → 以介面解耦所有子系統
   → Thread-local 容器支援多實例
   → [Dependency] 屬性標記自動注入

3. Data-Driven Prototypes
   → YAML 定義所有遊戲資料
   → PrototypeId<T> 型別安全的資料參考
   → 支援繼承與熱重載
```

### 專案層次結構

```
OpenNefia.EntryPoint      ← 進入點（Main()）
       ↓
OpenNefia.Core            ← 引擎核心（35 個子系統）
       ↓
OpenNefia.Content         ← 遊戲內容（57 個子系統）
       ↓
OpenNefia.LecchoTorte     ← 額外內容模塊
```
