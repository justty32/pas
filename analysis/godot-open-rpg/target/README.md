# Target：GDExtension 後端 RPG 前端規劃包

> 這個目錄是整個專案的**規劃與委派中心**。
> 你（專案主）負責規劃與驗收，執行模型（Haiku 等）負責實作。
> 所有交付內容皆依本目錄的文件推進。

---

## 文件地圖

### 📘 給你（規劃者）自己看的

| 文件 | 用途 | 何時看 |
| :--- | :--- | :--- |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | 架構總覽、設計哲學、非目標 | 每次展開新工作前先看一遍 |
| [`TASKS.md`](TASKS.md) | 所有實作任務的拆解清單，可直接指派 | 要派新工作給執行模型時查 |
| [`PROMPT_TEMPLATES.md`](PROMPT_TEMPLATES.md) | 給執行模型下 prompt 的範本與原則 | 要派工作時，搭配 TASKS.md 使用 |

### 📕 給執行模型當參考的規格文件

| 文件 | 用途 | 誰會用到 |
| :--- | :--- | :--- |
| [`00_master_guide.md`](00_master_guide.md) | 施工指南總表（Milestone、接口清單） | 任何執行模型都要讀 |
| [`01_extraction_and_modification_guide.md`](01_extraction_and_modification_guide.md) | 從 godot-open-rpg 提取/改造的詳細步驟 | 做 M1-M7 的執行模型 |
| [`02_frontend_design.md`](02_frontend_design.md) | 前端元件與事件的完整程式碼規格 | 寫元件的執行模型 |
| [`gdextension_backend_architecture.md`](gdextension_backend_architecture.md) | GDExtension 後端注意事項 | 做後端的執行模型 |
| [`project_idea_gdextension_rpg.md`](project_idea_gdextension_rpg.md) | 最初的構想記錄 | 參考背景 |

---

## 工作流程

```
你（規劃者）                           執行模型（Haiku/Sonnet/etc.）
───────────                           ──────────────────────────
  1. 從 TASKS.md 挑下一個任務
  2. 查 PROMPT_TEMPLATES.md 找對應模板
  3. 組裝 prompt（任務 + 參考文件路徑）───→ 4. 讀文件、實作
                                        ←─── 5. 回報完成
  6. 依任務的驗收標準檢查
     ├─ 通過 → 標記完成，指派下一個
     └─ 未通過 → 用 debug 模板繼續

當架構有新想法時：
  先更新 ARCHITECTURE.md + 規格文件（00/01/02）
  再拆成新任務加入 TASKS.md
```

---

## 目前進度

實作尚未啟動。請依 `TASKS.md` 的順序從 M0（專案骨架）開始。
