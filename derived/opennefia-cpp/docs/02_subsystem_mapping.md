# 02 — OpenNefia 子系統 → C++ 核心對照

> 把 OpenNefia.Core 的子系統逐一標記：**範圍內（本階段做）／ 暫緩（前端階段）**，並對照在 C++ 用什麼取代 C# 的反射機制。來源：`analysis/OpenNefia/architecture/` 與 `details/implements/`（既有的 .hpp 骨架）。

---

## 1. 範圍總表

| OpenNefia.Core 子系統 | 本階段 | C# 原機制 | C++ 取代方案（基於 medps） |
|---|---|---|---|
| **IoC** (`DependencyCollection`) | ✅ 縮減 | `Reflection.Emit` 注入 `[Dependency]` | `ServiceContext` 強型別 + 系統顯式 `SystemCtx`；系統無狀態即免 DI |
| **GameObjects / ECS** | ✅ | 自製 EntityManager + Component 狀態機 | EnTT `registry`；薄 `EntityManager`；生命週期用 EnTT signal |
| **EntityEventBus** | ✅（本專案重點） | 反射式泛型訂閱 | `entt::dispatcher`（廣播）+ 自製定向 `EventBus`；明確訂閱 |
| **Prototypes** | ✅ | YAML + 反射建型別 | yaml-cpp + `PrototypeId<T>` + 繼承合併 |
| **Serialization** | ✅ | `[DataField]` 反射讀寫 | `entt::type_list` + fold + cereal（移植 medps 三件套） |
| **Maps / Area** | ✅ 邏輯部分 | MapManager + Tile | tile 稠密網格 component（`tdarray<Tile>`）；實體佈局；**不含渲染** |
| **Configuration** (CVar) | ✅ | Nett(TOML) + 反射 CVarDef | tomlplusplus 或自製；CVar 強型別 + 觀察者 |
| **Log** | ✅ | Serilog | spdlog |
| **Locale** | ✅ 資料層 | NLua 驅動本地化 | 載入 locale 鍵值；**文字渲染屬前端** |
| **Random** | ✅ | IRandom / SysRandom | 同介面，C++ `<random>` |
| **Timing** | ✅ | FrameEventArgs | 純資料；tick 計時（驅動由外部） |
| **Asynchronous** (TaskManager) | ◐ 視需要 | ITaskManager | `std::async` / 自製；初版可省 |
| **ResourceManagement / VFS** | ✅ 唯讀部分 | 虛擬檔案系統 | 讀 YAML / data 的路徑抽象；寫檔走 ZoneStore 式後端 |
| **Graphics** (`Love2dCS`) | ⏸ 暫緩 | Love2D 後端 | （前端：Godot 渲染） |
| **UserInterface** (UiElement) | ⏸ 暫緩 | 手動繪製 UI 層 | （前端：Godot Control） |
| **XAML / Wisp UI** | ⏸ 暫緩 | XamlX 編譯期 IL 注入 | （前端：Godot Control / .tscn，**Wisp 不移植**） |
| **Input** (BoundKeyFunction) | ⏸ 暫緩 | 直讀後端按鍵 | （前端：Godot InputMap action） |
| **Audio / Music** | ⏸ 暫緩 | raylib/Love 音訊 | （前端：Godot AudioStreamPlayer） |

> 圖例：✅ 本階段做；◐ 視需要 / 可延後；⏸ 暫緩到前端階段。

---

## 2. 為什麼這樣切

切割線就是 medps 的核心 / 前端線：**凡是「世界怎麼運作」屬核心，凡是「玩家怎麼看到 / 操作」屬前端。**

- 核心吃指令、推進世界、產出狀態與事件——全部可在無視窗、無圖形的測試環境跑（仿 `medp_test`）。
- 前端把指令送進來、把狀態畫出去——未來由薄殼 facade（仿 medps `gbind/`）橋接 Godot。

這條線讓本階段能**完全不依賴任何前端庫**就把核心做到「可存檔、可模擬、可測試」。

---

## 3. 三個關鍵取代的細節

### 3.1 IoC 反射 → 顯式服務傳遞

OpenNefia `OpenNefia.Core/IoC/DependencyCollection.cs` 用 `Reflection.Emit` 動態產生注入器掃 `[Dependency]` 欄位。C++ 無此能力，且 medps 證明系統無狀態時根本不需要。做法：

- 真．全域單例（Log / CVar / Locale / Random / VFS）→ `ServiceContext`，啟動時建好、強型別存取。
- 系統依賴 → `SystemCtx` 顯式傳參（見 `01_core_architecture.md` §4）。
- **好處**：依賴在簽名上可見、可在測試中替換假物件、零執行期反射開銷。

### 3.2 系統自動發現 → 明確註冊

OpenNefia `EntitySystemManager.cs:133` 用 `GetAllChildren<IEntitySystem>()` 掃 Assembly。C++ 改**明確註冊 vector**（medps `add_zone_system` 形態）。系統依賴排序在註冊端手排或啟動期建圖，不靠反射。

### 3.3 `[DataField]` 反射 → type_list

逐欄位反射讀寫 → `AllComponents` type_list 單一來源 + fold 展開。新增 component 補一行清單。詳見 `01_core_architecture.md` §6 與 `analysis/medps/architecture/02_core_patterns.md` 模式三。

---

## 4. 既有骨架的去留

`analysis/OpenNefia/details/implements/` 裡已有一批 .hpp 骨架（先前 raylib 方向產出）。對本階段：

| 骨架 | 去留 |
|---|---|
| `ioc/ServiceLocator.hpp` | **改造**：縮為 ServiceContext，只服務全域單例 |
| `GameObjects/*`（EntityUid / Component / lifecycle） | **參考語意**：實作改以 EnTT 為底，別照搬 C# 狀態機 |
| `Graphics/RaylibGraphics.*`、`UI/*`、`Input/*`、`Audio/*` | **本階段忽略**（前端、且 raylib 已棄） |
| `Maths/*`、`Random/*`、`Log/*`、`Configuration/*`、`Locale/*` | **可沿用 / 翻新**：屬核心服務 |

> 這些骨架在 `analysis/OpenNefia/` 下是 OpenNefia 分析的一部分，**不**搬進本衍生專案；本專案 `src/core/` 重新撰寫，需要時參考其介面語意並標註來源路徑。
</content>
