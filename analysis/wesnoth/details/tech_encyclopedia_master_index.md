# Wesnoth 技術全典：地圖與 AI 全源碼解析 (終極版主索引)

本索引導引讀者查閱對 Wesnoth 核心系統的「全檔案、全函數、全跨層」零死角解剖報告。從底層 C++ 演算法到頂層 Lua 腳本，共涵蓋 11 卷完整工程手冊。

---

## 🗺️ 第一部分：地圖生成與空間表現層 (Map & Rendering)

| 卷數 | 文件名稱 | 涵蓋檔案/目錄 | 核心解析內容 |
| :--- | :--- | :--- | :--- |
| **Vol.1** | `complete_manual_vol1_map.md` | `src/map/` | 六角格幾何算術、坐標旋轉、WML 地圖編譯、座標雜湊與標籤可視性管理。 |
| **Vol.2** | `complete_manual_vol2_terrain.md` | `src/terrain/` | 地形代碼二進位編譯、規則模式匹配、多層次渲染合成與延遲加載。 |
| **Vol.3** | `complete_manual_vol3_pathfinding.md` | `src/pathfind/` | A* 歐幾里得偏置優化、ZOC 非線性代價跳變、傳送門路徑擴展與視線干擾。 |
| **Vol.4** | `complete_manual_vol4_generators.md` | `src/generators/` | 標量場丘陵疊加、島嶼形態學、洞穴房間-通道演算法、水文遞歸擴散。 |

---

## 🧠 第二部分：人工智慧與 C++ 決策引擎 (AI System - C++ Core)

| 卷數 | 文件名稱 | 涵蓋檔案/目錄 | 核心解析內容 |
| :--- | :--- | :--- | :--- |
| **Vol.5** | `complete_manual_vol5_ai_framework.md` | `src/ai/composite/` | RCA 任務競爭框架、AI 屬性 (Aspect) 工廠、階段調度與有限狀態機轉移。 |
| **Vol.6** | `complete_manual_vol6_ai_default_ca.md` | `src/ai/default/` | 馬可夫鏈戰鬥模擬、風險敞口公式、經濟預測模型、戰場特徵採樣。 |
| **Vol.7** | `complete_manual_vol7_ai_lua.md` | `src/ai/lua/` | C++/Lua 狀態同步、行為授權機制、腳本層對象包裝與安全隔離。 |
| **Vol.8** | `complete_manual_vol8_ai_management.md` | `src/ai/manager.cpp` | AI 生命週期管理、觀察者模式監控、組件反射註冊與熱插拔。 |
| **Vol.9** | `complete_manual_vol9_ai_actions.md` | `src/ai/actions.cpp` | 行動執行合法性驗證、虛擬沙盤預演、遊戲狀態快照與命令執行。 |

---

## ⚙️ 第三部分：行動結算、實體與資料驅動層 (Execution, Entities & Scripts)

| 卷數 | 文件名稱 | 涵蓋檔案/目錄 | 核心解析內容 |
| :--- | :--- | :--- | :--- |
| **Vol.10** | `complete_manual_vol10_actions.md` | `src/actions/` | 戰鬥傷害結算矩陣、移動伏擊中斷、光線投射迷霧清除、Undo (撤銷) 歷史堆疊。 |
| **Vol.11** | `complete_manual_vol11_data_ai.md` | `data/ai/` | Micro AI 實作：刺客打帶跑、護衛編隊、動物群集邏輯，以及 RCA 框架的腳本實體化。 |
| **Vol.12** | `complete_manual_vol12_game_board.md` | `src/game_board.cpp` | 世界容器狀態機、回合生命週期、RAII 暫時性實體管理器、全域空間視圖。 |
| **Vol.13** | `complete_manual_vol13_units.md` | `src/units/` | 單位能力空間過濾、特技條件狀態編譯、無限遞歸防護鎖、戰鬥武器特效動態覆寫。 |
| **Vol.14** | `complete_manual_vol14_whiteboard.md` | `src/whiteboard/` | 未來時間線架構、虛擬地圖平行宇宙、動作有向無環圖 (DAG) 依賴性分析。 |

---

## 🖥️ 第四部分：引擎事件、直譯器與表現層 (Events, Scripts & Display)

| 卷數 | 文件名稱 | 涵蓋檔案/目錄 | 核心解析內容 |
| :--- | :--- | :--- | :--- |
| **Vol.15** | `complete_manual_vol15_events.md` | `src/game_events/` | 事件泵佇列、WML 動態條件直譯器、短路求值優化、自定義選單。 |
| **Vol.16** | `complete_manual_vol16_scripting.md` | `src/scripting/` | Lua 多核心虛擬機架構、API Hook C++ 函數映射、沙盒安全性與變數持久化。 |
| **Vol.17** | `complete_manual_vol17_display.md` | `src/display.cpp` | 六角格螢幕像素映射數學、髒矩形 (Dirty Rectangles) 局部重繪優化、畫家演算法 Z-Index。 |

---

## ⚡ 第五部分：極限底層、同步與效能剖析 (Network, Parser & Profiling)

| 卷數 | 文件名稱 | 涵蓋檔案/目錄 | 核心解析內容 |
| :--- | :--- | :--- | :--- |
| **Vol.18** | `complete_manual_vol18_network_sync.md` | `src/synced_checkup.cpp` | 確定性亂數 (Deterministic RNG)、OOS 同步檢查點、網路對戰 AI 狀態鎖。 |
| **Vol.19** | `complete_manual_vol19_serialization.md` | `src/serialization/` | WML 詞法掃描器 (Tokenizer)、巨集展開引擎、二進位快取映射 (Memory Mapping)。 |
| **Vol.20** | `complete_manual_vol20_memory_profiling.md` | 全域引擎 | L1/L2 快取命中率優化、一維陣列降維、AI 戰鬥雜湊快取、智慧指標生命週期防護。 |
| **Vol.21** | `complete_manual_vol21_grand_unified_architecture.md` | 架構總覽 | Wesnoth 引擎大一統架構：從 `wesnoth_main` 啟動、VFS 掛載、RCA 決策到 SDL 繪製的完整生命週期。 |

---

## 📊 第六部分：動態交互視圖 (Call Graphs)

| 卷數 | 文件名稱 | 解析內容 |
| :--- | :--- | :--- |
| **圖集** | `tech_encyclopedia_vol7_call_graphs.md` | 地圖生成管線圖、AI 決策遞歸圖、地形拼接渲染圖。 |

---

## 🛠️ 工程標準聲明
本《技術全典》已完全捨棄所有生活化比喻，全面採用「計算機科學」與「數學」之正規學術術語進行撰寫。我們窮舉了包含 C++ 引擎層與 Lua 資料層的所有關鍵函數與演算法，為 The Battle for Wesnoth 留下了一份最極致、最零死角的「反向工程手冊」。

*最後更新日期：2026-05-17*
