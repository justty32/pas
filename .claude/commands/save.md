---
description: 會話保存 — 在當前工作模式的 session_log.md 追加進度快照（準則 5）
argument-hint: "[補充說明，可留空]"
---
使用者準備退出。依 `CLAUDE.md` 準則 5，在**當前工作模式對應的** `session_log.md` 末尾追加一筆進度快照。

## 寫到哪
- Analysis → `analysis/<project>/session_log.md`
- Create → `derived/<project>/session_log.md`
- Patch → `patches/<patch>/session_log.md`

若不確定當前是哪個工作單位，先確認再寫。

## 快照內容
$ARGUMENTS

彙整以下四項（上面有補充說明就一併納入）：
1. **當前理解**（一句話摘要）
2. **已完成項目**
3. **剩餘待辦事項**
4. **核心上下文摘要**（讓下一個 agent 冷啟動能接手）

## 約束
- `session_log.md` **上限 50 行**：超過時刪舊紀錄、只保留最新數筆（最舊的可直接放棄）。日誌僅供「接上進度」，非歷史檔案。
- 全程繁體中文。
