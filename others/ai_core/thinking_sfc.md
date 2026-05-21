# thinking_sfc.md

Small Function Center 設計（2026-05-21）

---

## Small Function 定義

Small function 是符合以下條件的函式：
- **只允許 one-shot**（multi-shot 或 persistent 無論多簡單，不算 small function——非硬性規定，但建議遵守）
- 對 input/output 做簡單處理，或執行非常簡單的邏輯、運算
- 可以套用「inline」概念——邏輯夠薄，不值得獨立成一個檔案

典型例子：`code_senior.sh` 最簡單的實作只是在 input 前面插一串 prompt 宣告「你是資深軟體工程師」，寫成程式不到兩行。

---

## 分層架構

SFC 的完整設計是一個由簡到繁的分層架構，不同層次各自獨立可用：

### Layer 0：純資料（無程式）

把小函式的定義存入一個 JSON 檔（array 或 object），另一個 key 或另一個檔案存 index。  
不需要任何額外程式——這是最簡單的集中管理形式。

```
functions.json     ← 函式定義的 array/object
index.json         ← name → 函式在 functions.json 中的位置
```

### Layer 1a：`intake`（one-shot）

把散落的腳本片段納入 Layer 0 的 JSON 檔，並更新 index。  
生產端工具：將新函式「收進來」。

### Layer 1b：Router（one-shot）

從 index 查找目標函式，mapping 到實際內容（檔案路徑或 JSON 中的腳本片段），執行之。  
消費端工具：使用 Layer 0 的資料。詳見 `thinking_routing.md`。

### Layer 2：`forge`（persistent server，基礎版）

**存在理由**：Layer 1 每次呼叫都要讀檔、解析 JSON、查 index——I/O 與解析開銷在頻繁呼叫時不可忽視。`forge` 的解法：啟動時付一次讀取與編譯的代價，之後每次呼叫都是純記憶體查表與執行。

行為極簡：**啟動 → 讀取指定資料夾/檔案 → 將 tiny function 定義編譯成可呼叫函式物件 → 存入記憶體 dict → 等待 API 呼叫**。

### Layer 3：`forge` + 管理 API

在 Layer 2 之上加入對 tiny function 的操作介面：
- 查詢：列出目前載入的函式
- 新增：動態載入並編譯新函式，加入 dict
- 刪除：從 dict 移除
- 保存：將目前記憶體中的函式定義寫回 Layer 0 的 JSON 檔

### Layer 4：SFC Server（頂層）

在 Layer 3 之上加入：
- **資源管理**：記憶體用量、執行時間限制
- **錯誤處理**：呼叫失敗的標準化回應、retry 機制

並加上 git-style subcommand CLI 介面，讓 shell 可以直接呼叫：

```bash
sfc greet --name Alice        # 呼叫 greet
sfc word-count --input foo.txt

sfc --metadata                # SFC 自身的 metadata
sfc greet --metadata          # greet 的 subcommand-scoped metadata（§4.0）
```

---

## Dispatcher 機制（Layer 2）

SFC 內部維護 global dict：

```
{ "function_name": <function_object>, ... }
```

subcommand 名稱作為字串 key 查表，直接呼叫對應的 function object。

---

## Tiny Function 定義格式

格式應非常靈活，常見形式：
- **Shell pipe**（最常見）：一串 shell 指令，支援 pipe 串接
- **Python**：小段 Python 邏輯
- **Lua**：小段 Lua 邏輯

具體格式（設定檔結構）待設計。

### In-process 的程度（Layer 2）

| 函式類型 | 執行方式 |
|---|---|
| Python / Lua | 真正 in-process，SFC 直接在自身 runtime 執行，無 subprocess |
| Shell pipe | SFC 內部開 shell subprocess——subprocess 存在，但由 SFC 管理，dispatch 決策在 SFC 內完成 |

---

## 動態 API（待設計）

SFC server 計劃提供以下 API：
- **新增**：執行期間動態添加新的 tiny function
- **持久化**：將目前記憶體中的函式定義存回 Layer 0 的 JSON 檔

---

## Hub / SFC / Indexer / Router 的關係

| 工具 | Layer | 本質 |
|---|---|---|
| Indexer | — | 掃描可執行檔，產出靜態索引 |
| `intake` | 1a | 把腳本片段納入 JSON store，更新 index |
| Router | 1b | 從 JSON store 的 index 查找，mapping 後執行 |
| SFC server | 2 | Router 的 persistent 升級版，in-process 執行 |

---

## 待設計

- Tiny function 設定檔（Layer 0）的具體格式
- 呼叫介面細節（參數傳遞方式）
- 動態 API 的具體介面
- SFC 與 hub 的協作：hub 如何得知 SFC 旗下有哪些 subcommand
