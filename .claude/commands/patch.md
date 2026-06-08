---
description: Patch 模式 — 製作可被 agent 套用到原專案的獨立 Patch 小專案
argument-hint: "[patch 名稱，可留空]"
---
你現在進入 **Patch 模式**。根目錄 `CLAUDE.md` 的核心行為準則最高優先；本模式的完整 SOP 以 `patch_workflow.md` 為**權威來源**，下面是濃縮版。

## 對象
$ARGUMENTS

留空則先與使用者敲定：patch 名稱、目標專案、要改什麼。
**前置條件**：`analysis/<source_project>/` 下已有 Level 1-2 以上的分析產物。
**核心原則**：Patch 與原專案**無 git 直接聯繫**；原專案不假設有版控，一律以**檔案操作**描述套用步驟。

## 此模式要做的事
1. **定義 Patch 目標**：在 `patches/<patch_name>/PATCH.md` 回答——目標專案、修改類型（功能增強／Bug 修正／重構／實驗）、影響範圍（對照 Level 2 職責劃分）、預期結果、分析依據。
2. **環境初始化**：建 `patches/<patch_name>/`，含 `PATCH.md APPLY.md src/ tests/ session_log.md` 與 agent 指導檔。
3. **實作 Patch 代碼**：`src/` 下放**最終要套用的完整檔案**（非 diff），目錄結構**模擬原專案相對路徑**以便一對一對照。
4. **撰寫 `APPLY.md`（核心交付物）**：讓**冷啟動 agent 不依賴對話上下文**就能獨立套用——摘要、前置條件、套用步驟（備份→複製檔案對照表→需手動修改處→構建驗證→功能驗證）、回退方式、已知限制。
5. **連結管理**：在 `analysis/<source>/session_log.md` 反向附記；另建 GitHub 由使用者操作，只在 `PATCH.md` 記文字連結。

## 此模式的鐵則（出自 `CLAUDE.md` 核心準則）
- 全程**繁體中文**。
- 引用原專案／Patch 自身的程式碼**必附 `path/to/file:line`**。
- 每次操作 append 一句話到 `session_log.md`（**上限 50 行**）。
- 圖表禁用 ASCII art 框線，改 Mermaid／列點／表格。

完整細節（`src/` 策略表、`APPLY.md` 標準結構）回查 `patch_workflow.md`。
