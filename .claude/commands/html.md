---
description: 生成／更新 HTML 導覽層（降低 .md 瀏覽認知負擔，準則 6）
argument-hint: "[工作單位，如 analysis/<project> 或 derived/<name>，可留空]"
---
你現在進入 **HTML 導覽層模式**（`CLAUDE.md` 準則 6）。根目錄 `CLAUDE.md` 最高優先。

## 對象
$ARGUMENTS

留空則先確認要為哪個工作單位生成／更新導覽層。

## 定位（鐵則）
- HTML **不取代 .md**。`.md` 是內容的**唯一真實來源**；內容更新**一律先改 .md，再重生 HTML**。
- HTML 只負責**索引與呈現**。

## 位置（放在該工作單位下的 `html/`，與來源 .md 同層）
- Analysis → `analysis/<project>/html/`
- Create → `derived/<project>/html/`
- Patch → `patches/<patch>/html/`

## 結構
- `index.html`：入口頁，提供總覽與導覽（頂部導覽列 + 卡片連結）。
- 各主題 `*.html`。
- `_shared.css`：同一單位共用一份樣式。
- 連結以**相對路徑**連回同層或上層的 .md，讓使用者能在導覽頁與原始文件間往返。

## 圖表（準則 7）
- **禁止 ASCII art 框線圖**。
- 視覺化分層用 **CSS 分層卡片**，沿用 `analysis/c-mera/html/_shared.css` 既有類別：`.card` + `.card-accent-{blue,green,orange,purple,red,cyan}`、格線 `.g2`/`.g3`/`.g4`、`.section` + `.section-title`；需要流程連線時內嵌 Mermaid 或用箭頭元素串接卡片。

## 參考範例
`analysis/c-mera/html/`（`index.html` + 主題頁 + `_shared.css` 的完整實作）。

全程繁體中文。
