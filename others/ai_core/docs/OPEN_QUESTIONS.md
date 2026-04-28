# AI Core — 開放問題與待補設計

> 本檔追蹤 `ARCHITECTURE.md` 尚未涵蓋、但已識別到值得處理的設計缺口。
> 每項應在被處理時搬入 `ARCHITECTURE.md` 並從本檔移除（或標 `[已處理 → §X.Y]`）。

最後更新：2026-04-28

---

## D 類：已從架構移出、留待未來實作

### D1. Calling Chain Observability（ledger + ai-core-trace + parent_call_id）
**狀態**：原 §7，2026-04-28 整體刪除，視為很後期才會考慮的功能。

**原構想摘要**（保留作為未來重啟時的設計種子）：
- `calls.jsonl` append-only ledger，每筆呼叫一個 JSON record
- 透過環境變數 `AI_CORE_PARENT_CALL_ID` 傳遞 parent / child 關係，自然形成樹狀
- `ai-core-trace` CLI 提供 `--recent` / `--tree` / `--func` / `--errors` 查詢
- ledger rotation / vacuum 工具
- 自動萃取 calling chain pattern 到 `auto/CHAINS.md`

**刪除影響**：
- `parent_call_id` 從 `POST /call` body 移除
- `ai-core-trace` 從 CLI 入口移除
- `trace/` 從目錄結構移除
- `ledger_path` 從 config 移除
- M2 milestone 整個移除
- AGENTS.md 模板移除相關提示

**未來重啟條件**：當系統累積足夠多 function、calling chain 複雜到人類無法靠 stdout 追蹤時，再回頭設計。

---

## B 類：設計缺口（值得認真考慮）

### B1. Streaming output ✅ [已處理 → ARCHITECTURE.md §6.9]
結論：新增 `--stream` 旗標，stdout 即時吐 token；`--output` 在 stream 模式下可選；`--stream --async` 不允許；HTTP 用 chunked transfer encoding；`time_to_wait_ms` 只計算 queue 等待時間，streaming 過程不受限制；ledger 仍寫單筆完整 record。

### B2. Messages / chat history 傳遞介面 ✅ [已處理 → ARCHITECTURE.md §6.10]
結論：協議層**只強制 `--input <file>`**（內容包成單一 user message）。多輪對話、system prompt、history 都由 caller 自己管理（呼應 §1 stateless 原則）。`--system` / `--messages` / `--append` 等是 wrapper 實作層的可選 sugar，不在協議裡強制。caller 需要超出 sugar 能力時可直接走 HTTP。`ai-core-call` 第一版實作哪些 sugar 留待 M1 視情境決定。

### B3. Server 生命週期管理 ✅ [已處理 → ARCHITECTURE.md §4.8 + §5.2]
結論：架構**不規範** server 啟動方式（daemon、systemd、`nohup` 等都是使用者選擇）。`ai-core-server` 為前景執行程式，需常駐請用系統工具。server 沒啟動 → wrapper 直接 stderr + exit 1（§5.2 已有）。新增 §4.8 metadata 註解 (`server.activation` / `server.activation_hint`) 讓 hub 對 caller 顯示「這個 server 默認啟用狀態」與「啟動方式提示」，純註解、不影響 wrapper 行為。

### B4. 雲端 model 的並行呼叫 ✅ [已處理 → ARCHITECTURE.md §6.6]
結論：entry config 新增 `concurrency` 欄位（預設 1），queue 改為「N 個 worker 共享消費同一條 queue」。`concurrency: 1` 退化為原本的 FIFO 串行（適合本地 GPU 受限模型）；`concurrency > 1` 讓雲端 stateless API 可並行，受 rate limit 約束。`concurrency` 為靜態配置（改值需重啟 server，KISS）。`--entry-metadata` 暴露 `concurrency` 與 `active_workers`。

### B5. Ledger rotation / 增長控制
`calls.jsonl` 永遠 append，無 rotation 機制。

**待決定**：
- size cap + 滾動（如 100MB rotate）？
- 時間 cap（如保留 30 天）？
- 由誰執行 rotation：server / 獨立 cron / `ai-core-trace --rotate`？

### B6. Server 自身 log（不是 ledger）
server startup、worker 例外、queue 狀態 → 寫到哪？

**待決定**：
- stderr 直接吐？適合前景，daemon 不行
- 寫到 `user_data_dir/server.log`？
- log level 控制（`--verbose` / `--quiet`）？

### B7. Server 重啟時的進行中工作
worker 處理到一半 server 被 kill，wrapper 還在 sync 等待。

**待決定**：
- task 是否 persist 到磁碟？server 重啟能恢復？
- 還是 sync wrapper 偵測連線斷掉就視為失敗？
- async task id 在 server 重啟後是否還有效？

### B8. Authentication 細節
§6.4「本機 token 認證」一句話帶過。

**待決定**：
- token 何時產生（首次 server 啟動）？
- 檔案權限（0600）？
- wrapper 怎麼讀（環境變數 / 檔案路徑）？
- rotation 機制？

---

## C 類：模糊處，需要澄清

### C1. ai-core-author 與 SFC 的關係
§9.1 寫「寫入 `funcs/<name>.<ext>` 或 small_funcs registry」，但 §10 說 SFC 內部管理自由、沒有固定 registry。

**待釐清**：author 怎麼決定該寫成獨立 function 還是塞進 SFC？由 spec 指定？

### C2. `funcs/` 路徑語意
ai-core-author 的 `--target funcs/` 預設位置在哪？cwd？固定 user data dir？跨專案使用呢？

### C3. 語言中立性的強調位置
§3 寫「主語言 Python 3.11+」容易被誤讀為 function 也得用 Python。實際上 ai_core 自己用 Python 實作，function 不限語言。

**待處理**：在 §1 設計原則或 §3 加一條明確聲明。

### C4. Hub `/funcs/<name>` 與 Entry `/entries/<name>/metadata` 路徑風格不統一
一個直接回 metadata，一個要加 `/metadata` 後綴。

**待決定**：是否統一風格？

### C5. Calling pack 怎麼實作
M7 提到 `llm_call_coding_question` 這種 calling pack，但實作形式未定。

**待決定**：是獨立 function、SFC 子函式、還是更上層的 prompt template 機制？

### C6. 空 input、no-output、args-input 缺範例
§4.2 列了 `io.input = "args" / "none"`、`io.output = "none"`，但沒範例。

**待補**：各加一個簡短範例，讓實作者明白 metadata 該怎麼描述。

---

## 處理慣例

當其中一項被討論並決定後：
1. 把結論寫進 `ARCHITECTURE.md` 對應章節
2. 在本檔該項標 `[已處理 → §X.Y]`，或直接刪除
3. 在 `ARCHITECTURE.md` 變更紀錄附註
