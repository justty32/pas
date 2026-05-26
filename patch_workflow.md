# Patch 小專案標準作業流程 (Patch SOP)

本文件定義了在完成分析後，如何建立一個可被 agent 套用到原專案的獨立 Patch 小專案。

適用情境：你已對某個專案完成分析，現在要實作一批**針對原專案的修改**，並將其打包為一個獨立的小專案，附上讓 agent 能夠自行套用的操作指南。

核心原則：
- Patch 小專案與原專案**沒有 git 上的直接聯繫**，兩者完全獨立存在
- 原專案不一定是 git repository，一律以**檔案操作**方式描述套用步驟
- `pas` 中僅存放文字形式的連結（如 GitHub URL），不使用 git submodule

前置條件：`analysis/<source_project>/` 下已存在 Level 1-2 以上的分析產物。

---

## 階段一：定義 Patch 目標

在開始前，先明確回答以下問題，並記錄於 `patches/<patch_name>/PATCH.md`：

1. **目標專案**：要修改的是哪個專案？（名稱、路徑或 URL）
2. **修改類型**：功能增強 / Bug 修正 / 重構 / 實驗性改動？
3. **影響範圍**：哪些模組或檔案？（參照 `analysis/<source>/architecture/` Level 2 的職責劃分）
4. **預期結果**：套用後應有什麼可量測或可觀察的變化？
5. **分析依據**：主要參考哪些分析文件？

---

## 階段二：環境初始化

### 1. 建立 Patch 專案目錄

所有 Patch 小專案統一置於 `patches/<patch_name>/`：

```powershell
mkdir patches/<patch_name>
```

### 2. 建立目錄結構

```
patches/<patch_name>/
├── PATCH.md            # Patch 目標、修改類型、影響範圍、分析依據
├── APPLY.md            # Agent 套用操作手冊（核心交付物）
├── session_log.md      # 操作日誌
├── session_temp/       # 進度快照
├── src/                # Patch 的實際代碼（新增或修改的檔案）
├── tests/              # 驗證 Patch 效果的測試腳本或說明
├── html/               # HTML 導覽層（選用，.md 過多時生成；見階段三第 6 點）
└── CLAUDE.md           # 當前 agent 的指導文件
```

### 3. 初始化 session_log.md

在開頭記錄：
- 起始時間
- Agent 名稱與版本
- 目標專案名稱與路徑
- Patch 目標（一句話）

---

## 階段三：規則設定

1. **輸出語言**：所有輸出與留檔一律使用**繁體中文**
2. **程式碼標註**：引用原專案的程式碼必附完整路徑 `path/to/file:line`；Patch 自身的程式碼同樣標註
3. **自動留檔**：技術細節自動寫入 `patches/<patch_name>/` 下對應位置
4. **會話日誌**：每次操作後 append 一句話至 `session_log.md`
5. **會話保存**：收到「我準備要退出了」時，在 `session_temp/session_resume.md` 建立進度保存檔
6. **HTML 導覽層（選用）**：當 Patch 說明文件（`PATCH.md`、`APPLY.md` 等）增多、難以綜覽時，於 `patches/<patch_name>/html/` 生成導覽層（`index.html` + 主題頁 + 共用 `_shared.css`），以相對路徑連回 .md。HTML 不取代 .md，內容更新一律先改 .md。參考範例：`analysis/c-mera/html/`

---

## 階段四：實作 Patch 代碼

### 1. src/ 目錄規範

`src/` 下存放**最終要套用至原專案的檔案**，目錄結構應**模擬原專案中的相對路徑**，以便 agent 能一對一對照：

```
patches/<patch_name>/src/
└── <原專案中的相對路徑>/
    ├── modified_file.c     # 修改過的完整版本
    └── new_file.h          # 新增的檔案
```

### 2. 修改類型對應的 src/ 策略

| 修改類型 | src/ 放什麼 |
|---|---|
| 新增檔案 | 完整的新檔案 |
| 修改現有檔案 | 修改後的完整檔案（不用 diff 格式） |
| 刪除檔案 | 在 APPLY.md 中標註，src/ 可留空或放說明 |
| 配置變更 | 修改後的完整配置檔 |

完整檔案（而非 diff）優先，讓 agent 能直接複製覆蓋，降低套用出錯的機率。

---

## 階段五：撰寫 APPLY.md（核心交付物）

`APPLY.md` 是這份 Patch 最重要的文件，讓**任何 agent 能夠在冷啟動狀態下，獨立完成套用操作**。

### 標準結構

```markdown
# APPLY.md — <Patch 名稱>

## 摘要
<一句話說明這個 Patch 做了什麼，以及為什麼>

## 前置條件
- 目標專案路徑：`<path>` 或 GitHub URL：`<url>`
- 依賴的分析文件：`analysis/<source>/architecture/level2_xxx.md`
- 套用前需確認：<例如：目標專案能正常構建>

## 套用步驟

### Step 1：備份（若原專案無版本控制）
<說明如何備份，或確認 git 狀態>

### Step 2：複製新增/修改的檔案
將以下檔案從 `patches/<patch_name>/src/` 複製到原專案對應路徑：

| Patch 中的位置 | 套用至原專案的路徑 | 操作 |
|---|---|---|
| `src/module/foo.c` | `<原專案>/module/foo.c` | 覆蓋 |
| `src/include/bar.h` | `<原專案>/include/bar.h` | 新增 |

### Step 3：需手動修改的部分
以下修改無法直接覆蓋，需要 agent 手動操作：

**檔案**：`<原專案>/CMakeLists.txt`
**操作**：在第 XX 行後插入：
```
<插入的內容>
```
**原因**：<說明為何不能直接覆蓋>

### Step 4：構建驗證
<套用後的構建指令，以及預期輸出>

### Step 5：功能驗證
<如何確認 Patch 已生效的具體步驟>

## 回退方式
<若套用失敗或結果不符預期，如何還原>

## 已知限制
<若有，例如：僅在特定版本或平台上測試過>
```

---

## 階段六：Patch 完成後的連結管理

### 在 analysis 中建立反向連結

在 `analysis/<source_project>/session_log.md` 附記：

```
針對 <描述> 建立 Patch 小專案：patches/<patch_name>/
```

### 若 Patch 小專案另建 GitHub Repo（使用者自行操作）

使用者可自行在 GitHub 建立獨立 Repo 並推送。在 `patches/<patch_name>/PATCH.md` 中記錄：

```markdown
## 外部連結
GitHub Repo：<url>（由使用者手動建立與維護）
```

`pas` 中僅存放此文字連結，不使用 git submodule 或任何 git 嵌入方式。

---

## 快速啟動提示詞

> 請依照 `patch_workflow.md` 建立此 Patch 小專案：
> - 目標專案：`<source_name>`，分析產物位於 `analysis/<source_name>/`
> - Patch 目標：`<一句話描述要修改什麼>`
> - 修改類型：`<功能增強 / Bug 修正 / 重構 / 實驗>`
>
> 步驟：
> 1. 在 `patches/<patch_name>/` 建立目錄結構，初始化 `session_log.md` 與 `PATCH.md`。
> 2. 所有輸出使用繁體中文；程式碼必附 `檔案:行號`；分析依據記錄至 PATCH.md。
> 3. 實作 `src/` 下的 Patch 代碼，最後撰寫完整的 `APPLY.md`，確保 agent 能在冷啟動下獨立套用。
