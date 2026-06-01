# medps — Level 1：專案總覽

> 分析於 2026-06-01，對象 `C:/code/mine/medps`。本篇為初始探索（定位、技術棧、目錄、構建、入口）。核心設計模式見 `02_core_patterns.md`。

## 1. 定位

medps 是使用者親手撰寫的**奇幻 4X 策略遊戲模擬核心**——定位為「太閣立志傳 × 騎馬與砍殺 × 上古卷軸 × 三國志」的結合體（`medps/work/design/zone_layers.md:11`）。

它**不是完整遊戲**，而是一個**純 C++ 後端函式庫**（`medp`）：負責世界模擬、ECS、存讀檔；圖形 / UI / 音效 / 視窗等交給未來的 Godot 4 前端。這個「純核心 + 薄前端」的切分是 medps 最重要的架構決策，也是 `derived/opennefia-cpp/` 採用它當藍本的主因。

> 與 OpenNefia 的關係：兩者底層技術高度重疊（都用 EnTT + cereal），但 medps 是**已驗證可編譯、有測試**（`medp_test` 25/25 綠燈，`work/design/zone_layers.md:146`）的真實核心。OpenNefia 的 C# 反射機制在 C++ 沒有對應物，medps 示範了「不靠反射」如何把同樣的 ECS / 序列化 / 系統需求做出來。

## 2. 技術棧

| 功能 | 函式庫 | 用途 |
|---|---|---|
| ECS | **EnTT** (v3.16.0) | `entt::registry` 作實體儲存；`view` 作查詢；`snapshot` 作存檔 |
| 序列化 | **cereal** (v1.3.2) | `PortableBinaryArchive`，可攜二進位；接 EnTT snapshot |
| 前端綁定（暫不深入） | **godot-cpp** (Godot 4.6+) | GDExtension，只在 `gbind/` 出現 |
| 構建 | **CMake** (≥3.14) | `medp` SHARED + `medp_static` STATIC 兩目標 |
| 語言 | **C++20** | fold expression、`if constexpr`、concept |

技術棧版本標於 `gbind/medp_core.cpp:10`（`"medp core 0.1 (entt v3.16.0 + cereal v1.3.2)"`）。

## 3. 目錄結構

```
medps/
├── src/
│   ├── gcore/                  ← 純 C++ 核心（禁止 include godot）
│   │   ├── zone_key.h          ZoneKey 定址 + 三層世界結構常數
│   │   ├── chunk_key.h         chunk（儲存分組）推導
│   │   ├── global_manager.h/.cpp   多 registry 生命週期 + tick + streaming
│   │   ├── components/         POD 組件（Position/Velocity/ZoneMeta/...）
│   │   ├── systems/            自由函式系統（movement.h ...）
│   │   ├── serialize/          all_components / zone_io / cereal adapter / store
│   │   └── util/               mydef.h（宏）、tdarray.hpp（稠密 2D 陣列）
│   └── gbind/                  ← 唯一允許 include godot-cpp 之處（薄殼 facade）
│       ├── medp_core.cpp/.h    smoke-test RefCounted facade
│       ├── register_types.cpp  GDExtension 進入點 medp_library_init
│       └── medp.gdextension    Godot 載入描述檔
├── work/                       分析 / 設計工作區（design/zone_layers.md 等）
├── data/                       資料（構建時複製到 build）
└── CMakeLists.txt
```

## 4. 構建與目標分離（核心觀念）

`CMakeLists.txt` 用 `GLOB_RECURSE` 蒐集 `src/`，但**明確排除 `/gbind/`**，產出兩個與 godot 完全無關的核心目標：

- `medp`（SHARED）與 `medp_static`（STATIC）——純 C++，不連 godot。
- 選用旗標 `MEDP_BUILD_GDEXTENSION`（預設 OFF）才會編 `gbind/`，連 godot-cpp（位於 `C:/code/mine/pas/projects/godot-cpp`）。

構建：`cmake -S . -B build && cmake --build build` → `build/bin/medp.windows.debug.64.dll`。

> **為什麼重要**：核心 godot-free 不是靠「介面注入」的執行期約定，而是靠**編譯目標邊界 + 目錄約定**強制達成——核心目標的編譯單元裡根本沒有 godot 標頭，想違反都很難。這比 OpenNefia C# 用 IoC 注入 `HeadlessGraphics` 來解耦更硬。

## 5. 入口點

- **核心**沒有 `main()`——它是函式庫，由呼叫者（測試 / 前端）驅動。`GlobalManager` 是核心的根物件。
- **前端綁定**入口為 `medp_library_init`（`gbind/register_types.cpp:22`），Godot 載入 `.gdextension` 時呼叫，於 `SCENE` 初始化階段註冊 GDClass。
- **測試**（`medp_test`）是核心的真正驅動者與正確性保證。

## 6. 一句話總結

medps = 用 **EnTT（多 registry，一 zone 一 registry）+ cereal（snapshot 序列化）** 寫的純 C++ 世界模擬核心；**不靠反射**（系統是自由函式、序列化靠 type_list）、**不碰 godot**（編譯邊界強制），把巨大世界（最多約 900 萬個 Area）用「絕不全載 + 滾動視窗 streaming」撐起來。
</content>
