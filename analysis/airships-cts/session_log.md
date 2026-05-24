# Airships: Conquer the Skies — Session Log

- 2026-05-23 定位專案：Steam 安裝版 `Airships Conquer the Skies`（Java，主類 `com.zarkonnen.airships.Main`，1.4G）。
- 2026-05-23 Level 1-2 探索：技術棧（Java+LWJGL+Slick2D+自製 CatEngine）、629 頂層 class、雙層 Combat/Strategic、Loadable 資料系統、確定性鎖步。
- 2026-05-23 用 CFR 0.152 反編譯 `game.jar`+`CatEngine.jar`+`CatSlick.jar` → `projects/airships-cts/src/`（691 .java，11M，零錯誤）；第三方 OSS 庫略過。
- 2026-05-23 撰寫 `architecture/01_overview_and_architecture.md`（總覽，含真實行號與 GuardedRandom no-op 校正）。
- 2026-05-23 派 5 個平行 agent 深掘子系統（面向 C++ 重寫），產出：
  - `details/combat_simulation.md`（戰鬥模擬/確定性/鎖步）
  - `details/ship_module_crew_model.md`（船艦/模組/船員/加成系統）
  - `architecture/data_loadable_system.md`（71 型別/JSON 載入/modding/校驗碼）
  - `architecture/strategic_and_ai.md`（戰略層/評分式 AI/autoresolve）
  - `architecture/engine_rendering.md`（引擎/Screen/繪圖/資產/shader）
- 2026-05-23 撰寫統整文件 `architecture/00_cpp_rewrite_roadmap.md`（模組分解、分階段里程碑 M0-M6、確定性契約、風險登記）。
