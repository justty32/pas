# Session Log — godot-demo-projects 分析

- 起始時間：2026-05-25
- 作業系統：Windows 11（PowerShell / bash）
- Agent：Claude Code (Opus 4.7, 1M context)
- 專案根路徑：`C:\code\mine\pas\projects\godot-demo-projects`
- 工作模式：Analysis

---

- 閱讀工作區規範（CLAUDE.md、analysis_workflow.md）與既有範例（Cogito level1）。
- 探索 repo 頂層結構，確認為 13 個分類的 Godot 官方範例集合（每個含 project.godot 的子資料夾為獨立 demo）。
- 以 `find` 列出全部 132 個 demo 路徑；以 grep 統計 Godot 版本（主流 4.6，少數 4.5/4.7）。
- 批量擷取每個 demo README 首段描述，建立「一句話用途」素材。
- 深入閱讀代表性 demo：2d/platformer、2d/finite_state_machine、compute/texture、networking/websocket_chat 的關鍵腳本。
- 建立 analysis 目錄結構與 session_log。
- 撰寫 architecture/level1_overview.md（repo 定位、版本、分類結構、執行方式）。
- 撰寫 architecture/level2_catalog.md（13 分類全部 demo 的分類目錄表）。
- 撰寫 details/ 四篇代表性 demo 深入剖析。
- 撰寫 tutorial/learn_by_topic.md（依主題查 demo 的學習導引）。
- 以 find 精確覆核 demo 數量，修正計數：總計 137 個 project.godot（136 獨立 demo + plugins 1 彙整專案）；3d 為 32、gui 為 14；同步更新 level1/level2。
- 在 others/external_links.md 以純文字記錄上游 GitHub、線上預覽與版本對應連結。
- 生成 html/ 導覽層四頁（index/catalog/details/tutorial）並沿用 Cogito 的 _shared.css（原封複製）：index 為總覽（13 分類卡片 + 版本統計 + 執行方式），catalog 為核心頁（13 分類全 demo 表格 + 主題速查 + 錨點跳轉），details 為 4 個代表 demo 摘要，tutorial 為 7 條學習路徑 + 外部連結。
