# Wesnoth 技術全典：動態交互與函數呼叫流程圖 (第七卷)

本卷透過 Mermaid 流程圖展示 Wesnoth 核心系統的動態呼叫鏈結 (Call Graphs)，旨在協助工程師理解函數間的執行序向與資料流向。

---

## 1. 程序化地圖生成管線 (Map Generation Pipeline)

此流程圖解構了 `default_map_generator_job` 啟動後的執行路徑，展示了地形從標量場合成到實體化為地圖字串的過程。

```mermaid
graph TD
    A[default_generate_map] --> B[generate_height_map]
    B --> B1[幾何實體疊加 Iterations]
    B1 --> B2{Island Mode?}
    B2 -- Yes --> B3[極性反轉 - 邊界侵蝕]
    B2 -- No --> B4[直接高度累加]
    B3 --> B5[Linear Normalization 0-1000]
    B4 --> B5
    
    A --> C[地形碼轉換]
    C --> C1[高度/溫度雙維度映射]
    
    A --> D[水文模擬]
    D --> D1[generate_lake 遞歸擴散]
    D --> D2[generate_river_internal DFS尋路]
    
    A --> E[戰略設施配置]
    E --> E1[rank_castle_location 密度評分]
    E --> E2[place_village 快取偏好檢索]
    
    A --> F[路徑網構建]
    F --> F1[road_path_calculator 噪聲注入]
    F1 --> F2[A* 搜尋實體化道路]
    
    A --> G[output_map 裁剪與偏移修正]
```

---

## 2. AI RCA 決策與戰鬥模擬管線 (AI Decision Pipeline)

此流程圖展示了 AI 如何透過遞歸任務競爭框架，從底層機率模擬推導至高層戰略執行。

```mermaid
graph TD
    Start[ai_composite::play_turn] --> Stage[Stage 任務分發]
    Stage --> RCA[RCA 決策循環]
    
    subgraph Evaluate 階段
        RCA --> Eval[candidate_action::evaluate]
        Eval --> Combat[combat_phase::evaluate]
        Eval --> Recruit[recruitment::evaluate]
        
        Combat --> Analyze[attack_analysis::analyze]
        Analyze --> Markov[馬可夫鏈戰鬥模擬]
        Markov --> Rating[attack_analysis::rating 期望值計算]
        Rating --> Penalty[Exposure Risk 懲罰修正]
        
        Recruit --> Economy[get_estimated_income 經濟預測]
        Recruit --> Counter[do_combat_analysis 兵種相剋矩陣]
    end
    
    subgraph Execute 階段
        RCA --> Winner[選取得分最高者]
        Winner --> Exec[candidate_action::execute]
        Exec --> Action[執行移動/攻擊/招募原語]
    end
    
    Action --> Loop[狀態改變 - 遞歸觸發下一輪 RCA]
    Loop --> RCA
```

---

## 3. 地形渲染拼接流程 (Terrain Rendering Transition)

此圖展示了 `terrain_builder` 如何根據鄰接規則決定圖層。

```mermaid
graph LR
    Map[gamemap 變更] --> Builder[terrain_builder::rebuild_all]
    Builder --> Rule[building_rule 匹配]
    Rule --> Constraint[鄰接座標地形代碼檢查]
    Constraint -- Match --> Overlay[多層次圖像疊加]
    Overlay --> Cache[tile::rebuild_cache]
    Cache --> Final[渲染輸出]
```

---
*第七卷解析完畢。此卷提供的流程圖為前六卷的靜態函數解析提供了動態的時間軸與交互視圖。*
*最後更新: 2026-05-17*
