# ai_core 已獨立成單獨的 git repo（2026-05-26）

原本放在這裡的 `others/ai_core/`（ai_core 的規範／框架版：八／九軸 metadata、
`register` library、`core_nature/` 規範、`roadmap.md` 北極星、`try_implement/` 遊樂場）
已**獨立成單獨的 git repo**，不再寄居於 pas 工作區。

- **新位置**：`~/repo/ai_core`（主線 `main` 持有此份框架／規範版內容；該 repo 原本的
  process-based 極簡實作保留在 `master` / `try` / `try_2`）
- **遠端**：`git@github.com:justty32/ai_core.git`（GitHub：`justty32/ai_core`）
- **歷史備份**：原內容仍在 pas git 歷史中（`dev` branch，commit `3046815` 及之前）可找回。

> 搬出原因：ai_core 已從 pas 的「分析／思考對象」長成需要獨立開發與 git 管理的專案，
> 不再適合放在 `others/` 雜項區。
