# PROJECT — opennefia-cpp

> 衍生小專案：用 **C++20** 重寫 OpenNefia 的**引擎核心**，架構藍本取自使用者自有的 `medps`。
> 建立於 2026-06-01（Create 模式，依 `create_workflow.md`）。

---

## 1. 源專案

- **重寫對象**：OpenNefia（C# / .NET 8.0 的 Elona 開源重製引擎）。分析產物：`analysis/OpenNefia/`（architecture 14 篇 + C++ 重寫初探 `details/plan_cpp/`）。
- **架構藍本**：medps（使用者自有 C++20 4X 模擬核心，EnTT + cereal）。分析產物：`analysis/medps/`。

## 2. 衍生目標

把 OpenNefia 的 **C# 引擎核心**（ECS、原型、序列化、系統、地圖邏輯、設定 / 日誌 / 在地化）以 **godot-free 的純 C++20 函式庫**重新實作，**完全基於 medps 已驗證的做法**：

- 用 **EnTT** 取代自製 EntityManager。
- 用 **`entt::type_list` + fold expression + cereal** 取代 C# `[DataField]` 反射序列化。
- 用 **自由函式系統 + 明確註冊** 取代 C# Assembly 掃描自動發現。
- 用 **編譯目標邊界**（核心目標不連任何前端庫）取代 IoC 注入式解耦。

> 核心命題：OpenNefia 的 C# 架構大量依賴**反射**（DI 注入、系統自動發現、欄位序列化）。C++ 沒有反射。medps 證明——順著 C++ 的紋理（type_list、自由函式、編譯期展開）能用**更少抽象**表達同樣意圖。本專案就是把這個證明套用到 OpenNefia 的內容規模上。

## 3. 範圍（重要：目前只做核心）

**本階段聚焦純 C++ 核心，不碰 Godot 整合與前端。**

### ✅ 範圍內（godot-free 核心）
- ECS（EnTT registry / component / 自由函式系統 / 事件）
- 原型系統（YAML 載入、`PrototypeId<T>`、繼承合併）
- 序列化 / 存讀檔（EnTT snapshot + cereal）
- 地圖**邏輯**（tile 稠密網格 component、實體佈局；不含渲染）
- 設定（CVar）、日誌、在地化資料、亂數、計時、虛擬檔案系統（讀 YAML / data）

### ⏸ 暫緩（前端，之後另開階段）
- 圖形 / 渲染、UI（Wisp / Control）、輸入裝置、音效、視窗 / OS
- Godot GDExtension 綁定層（`gbind/` 對應物）

> 暫緩不代表忽略：核心的所有對外介面都會設計成「前端可掛接」——例如系統產出的事件 / 狀態以 POD 形式暴露，未來薄殼 facade（仿 medps `gbind/`）即可橋接 Godot。但本階段不寫任何前端碼。

## 4. 技術棧

| 功能 | 函式庫 | 對應 medps |
|---|---|---|
| 語言 | C++20 | 同 |
| ECS | EnTT | `gcore/` 全面採用 |
| 序列化 | cereal（PortableBinary） | `serialize/` |
| YAML | yaml-cpp | （medps 用 cereal binary；本專案另需 YAML 讀原型） |
| 日誌 | spdlog | （medps 尚未引入） |
| 設定 | tomlplusplus 或自製 CVar | 對應 OpenNefia Configuration |
| 構建 | CMake ≥3.14 | 同 medps 雙目標式 |
| 測試 | doctest v2.4.11 | medp_test |

> 與 OpenNefia 不同：本專案**不採 raylib**（已棄）。前端方向（未來）為 Godot 4 GDExtension，與 medps 一致——但本階段不實作。

## 5. 完成定義（本階段＝核心）

核心階段「做完了」的判準：

1. `opennefia_core` 靜態庫可獨立編譯，**不連任何前端庫**（編譯邊界可驗證）。
2. 能從 YAML 載入一批原型（如角色 / 物品定義），`SpawnEntity(protoId)` 組出帶 component 的實體。
3. ECS 事件匯流排可跑：系統訂閱 / 發送定向與廣播事件。
4. 一張地圖（tile 網格 component + 若干實體）能 **snapshot 存檔 → 還原**，round-trip 正確。
5. 有最小測試套件涵蓋上述（仿 `medp_test` 的綠燈保證）。

## 6. 參照素材

- `analysis/medps/architecture/02_core_patterns.md` —— 六條核心藍本（多 registry / type_list 序列化 / 自由函式系統 / ...）。
- `analysis/OpenNefia/architecture/03_ecs_system.md`、`06_prototype_serialization.md`、`11_save_load_system.md` —— 要重現的目標語意。
- `analysis/OpenNefia/details/plan_cpp/05_lessons_from_medps.md` —— 三大反射難題的 medps 對照。
- medps 源碼：`C:/code/mine/medps/src/gcore/`（直接當實作參考）。

## 7. 設計文件索引

- `docs/01_core_architecture.md` —— 核心分層與目標結構（godot-free）。
- `docs/02_subsystem_mapping.md` —— OpenNefia 子系統 → C++ 核心對照（範圍內 / 暫緩）。
- `docs/03_roadmap.md` —— 核心階段路線圖（Phase 0–4）。
- `docs/decisions/` —— 重要設計決策的追溯連結（借鑒自哪份分析）。

## 8. 外部連結

GitHub Repo：（尚無；如日後推送由使用者手動建立並於此記錄）

## 9. 進度

- 2026-06-01：專案初始化，完成 PROJECT.md 與設計文件 01–03。尚未開始實作（src/ 空）。
- 2026-06-01：**Phase 0 完成**。CMakeLists.txt（FetchContent：EnTT v3.16.0 / cereal v1.3.2 / spdlog v1.14.1 / doctest v2.4.11），`opennefia_core` STATIC 靜態庫編譯通過，`version()` smoke test 綠燈（1/1）。**下一步**：Phase 1 ECS 地基。
</content>
