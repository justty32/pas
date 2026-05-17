# Wesnoth 原始碼全解析百科全書：地圖與 AI 零死角計畫

本計畫旨在以「高中生能懂的白話文 + 論文級的底層數學與程式碼細節」風格，將 Wesnoth 的地圖生成與 AI 決策系統，進行毫無遺漏的逐函數、逐邏輯拆解。

計畫將產出以下五大卷（分為多個 `.md` 檔案存放於 `details/` 目錄）：

## 卷一：創世的泥巴球（地貌生成核心）
- **目標檔案**: `default_map_generator_job.cpp`
- **解析內容**: `generate_height_map` 的每一行邏輯。為何要用 Bounding Box？邊緣山谷（Island Mode）的數學公式是什麼？地圖數值如何從隨機變成 0-1000 的標準高度？

## 卷二：大自然的刻刀（水文與戰略設施）
- **目標檔案**: `default_map_generator_job.cpp`
- **解析內容**: `generate_lake` 的幾何衰減機率、`generate_river_internal` 的逆坡爬行（Uphill）與 DFS 尋路、`rank_castle_location` 的空間密度矩陣評分。

## 卷三：死神的算盤（AI 戰鬥與風險評估）
- **目標檔案**: `ai/default/attack.cpp`
- **解析內容**: `attack_analysis::analyze` 如何建立馬可夫矩陣？經驗值如何換算成黃金價值？`rating()` 函數中的 `Exposure`（風險敞口）公式每一項變數的物理意義與邊界條件。

## 卷四：螞蟻的導航儀（路徑搜尋與空間幾何）
- **目標檔案**: `pathfind/astarsearch.cpp`, `pathfind.cpp`
- **解析內容**: A* 演算法中九億分之一的微小偏置（Heuristic Tie-breaker）如何運作？ZOC（控制區）如何在演算法底層變成一堵無形的牆？

## 卷五：將軍的帳本（AI 招募與反制引擎）
- **目標檔案**: `ai/default/recruitment.cpp`
- **解析內容**: 未來五回合經濟預測模型 (`get_estimated_income`)、兵種相剋權重矩陣 (`do_combat_analysis`) 如何掃描全圖並即時修改招募清單的評分。

---
*計畫啟動日期：2026-05-17*
