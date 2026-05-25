# 衍生小專案標準作業流程 (Create SOP)

本文件定義了在完成分析後，如何基於分析產物建立一個獨立的衍生小專案。

適用情境：你已對某個專案完成分析，現在要實作一個從分析中衍生的小型獨立專案（PoC、工具、擴充套件、學習實作等）。此類專案以**獨立存在**為目標，不預設需要被套用回原專案。

前置條件：`analysis/<source_project>/` 下已存在 Level 1-2 以上的分析產物。

---

## 階段一：定義衍生目標

在開始建立前，先明確回答以下問題，並記錄於 `derived/<project_name>/PROJECT.md`：

1. **源專案**：分析的是哪個專案？（路徑或名稱）
2. **衍生目標**：這個小專案要解決什麼問題，或驗證什麼概念？
3. **參照素材**：主要參考 `analysis/<source>/` 中的哪些文件？
4. **技術棧**：要用什麼語言或框架實作？（不必和源專案相同）
5. **完成定義**：什麼狀態算「做完了」？

---

## 階段二：環境初始化

### 1. 建立專案目錄

所有衍生專案統一置於 `derived/<project_name>/`：

```powershell
mkdir derived/<project_name>
```

### 2. 建立目錄結構

```
derived/<project_name>/
├── PROJECT.md          # 衍生目標、參照素材、技術棧、完成定義
├── session_log.md      # 操作日誌
├── session_temp/       # 進度快照
├── src/                # 源碼（依技術棧慣例調整）
├── tests/              # 測試
├── docs/               # 設計決策、實作說明
└── CLAUDE.md           # 當前 agent 的指導文件
```

### 3. 初始化 session_log.md

在 `session_log.md` 開頭記錄：
- 起始時間
- Agent 名稱與版本
- 源專案名稱
- 衍生目標（一句話）

---

## 階段三：規則設定

1. **輸出語言**：所有輸出與留檔一律使用**繁體中文**
2. **程式碼標註**：所有提到的程式碼必附原始碼位置 `path/to/file:line`；若引用自源專案則附源專案路徑
3. **自動留檔**：技術細節自動寫入 `derived/<project_name>/docs/` 或對應子目錄
4. **會話日誌**：每次操作後 append 一句話至 `session_log.md`
5. **會話保存**：收到「我準備要退出了」時，在 `session_temp/session_resume.md` 建立進度保存檔，彙整當前理解、已完成項目、剩餘待辦

---

## 階段四：骨架建置

### 1. 依技術棧初始化

根據選定技術棧執行標準初始化，並記錄於 `session_log.md`：

| 技術棧 | 初始化指令 |
|---|---|
| Rust | `cargo init` |
| Node.js | `npm init -y` |
| Go | `go mod init <module>` |
| Python | `uv init` 或 `python -m venv .venv` |
| C/C++ | 建立 `CMakeLists.txt` 或 `Makefile` |

### 2. 生成 Agent 指導文件

在 `derived/<project_name>/` 下建立對應 agent 的指導文件，內容包含：
- 衍生目標與源專案背景
- 技術棧與構建指令
- 與分析產物的連結方式（路徑參照）

---

## 階段五：實作與追溯連結

### 追溯連結規範

每當有重要設計決策或借鑒自分析的概念，在 `docs/decisions/` 中以 Markdown 記錄：

```markdown
## 設計決策：<標題>

**參照來源**：`analysis/<source>/architecture/level3_xxx.md`
**借鑒概念**：<說明從分析中學到了什麼>
**實作方式**：<在衍生專案中如何應用>
```

每個功能點完成後更新 `session_log.md`；重大里程碑時更新 `PROJECT.md` 的進度區塊。

---

## 階段六：外部 Repo 連結管理（選用）

若使用者決定將衍生專案另行推送至 GitHub，由**使用者自行操作**，agent 僅提供建議。`pas` 中不使用 git submodule；在 `derived/<project_name>/PROJECT.md` 記錄文字連結即可：

```markdown
## 外部連結
GitHub Repo：<url>（由使用者手動建立與維護）
```

同時在 `analysis/<source_project>/session_log.md` 附記：

```
基於分析建立衍生小專案：derived/<project_name>/，外部 Repo：<url>
```

---

## 快速啟動提示詞

> 請依照 `create_workflow.md` 初始化此衍生專案：
> - 源專案：`<source_name>`，分析產物位於 `analysis/<source_name>/`
> - 衍生目標：`<一句話描述目標>`
> - 技術棧：`<語言/框架>`
>
> 步驟：
> 1. 在 `derived/<project_name>/` 建立目錄結構，初始化 `session_log.md` 與 `PROJECT.md`。
> 2. 所有輸出使用繁體中文；程式碼必附 `檔案:行號`；設計決策記錄追溯連結至分析文件。
> 3. 依技術棧完成骨架建置，然後開始實作，每個功能點完成後更新日誌。
