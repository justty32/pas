# AI Core — 變更紀錄

## §16. 變更紀錄

- 2026-04-28：初版定稿。涵蓋四個元件、queue 流程、stderr 錯誤慣例、跨平台選型。
- 2026-04-28：新增 `io` 慣例 key 描述函式 I/O 風格。
- 2026-04-28：將「常駐 server + queue」抽象為 **Singleton Resource Manager Pattern**（§1）；Entry Manager 補上 `--entry-metadata` 與 `/entries/*` HTTP 端點。
- 2026-04-28：明確定位為 **AI 80% / 人類 20%**，新增 §7 Calling Chain Observability（ledger + ai-core-trace）；Function Hub 拆為 **server + one-shot 雙形態**；新增 ai-core-author（含 dry-run）；§4.6 補 metadata **容錯與降級**規則；§5.1 補 `--json-errors` 旗標；補 Singleton Resource Manager 必須**配套 shell wrapper CLI**。
- 2026-04-28：新增 Agent 整合與文檔策略（AGENTS.md / auto-generated docs / claude-skill 與 agent-md export 格式 / Self-Sufficiency 演進階段）。
- 2026-04-28：依 `thinking.md` 補完四個缺口：①補 Singleton Pattern 兩種亞型；②新增 **entrydata 介面宣告**；③補 **佇列等待逾時**機制；④補 M4.5 milestone。
- 2026-04-28：釐清三個設計決策：①server 未啟動的錯誤行為；②移除 `--preview-chain`；③新增 **Hub Scanner 掃描策略**。
- 2026-04-28：新增 **Small Function Center (SFC) 設計**。
- 2026-04-28：A 類修正（內部一致性）；新增 `docs/OPEN_QUESTIONS.md`。
- 2026-04-28：處理 B1（Streaming output）→ §6.9。
- 2026-04-28：處理 B2（Messages / chat history 介面）→ §6.10。
- 2026-04-28：處理 B3（Server 生命週期）→ §4.8 + §5.2。
- 2026-04-28：處理 B4（雲端 model 並行呼叫）→ §6.6。
- 2026-05-12：處理 B6（Server 自身 Log）→ §6.11。預設 stderr；`--log-file` 可選寫檔；`--log-level` 控制層級；不內建 log rotation。處理 B7（Server 重啟行為）→ §6.12。第一版不 persist task；sync wrapper 偵測連線斷開直接報錯 exit 1；async task id 重啟後失效（404）；無自動恢復。處理 B8（本機 Token 認證細節）→ §6.13。首次啟動自動生成寫入 `user_config_dir/ai_core/token`（0600）；wrapper 讀 `AI_CORE_TOKEN` env 或 token 檔；`Authorization: Bearer` header；第一版不做 rotation。B5（Ledger rotation）因 ledger 架構整體移除而自動作廢。
- 2026-05-12：**移除 Calling Chain Observability（ledger / ai-core-trace / AI_CORE_PARENT_CALL_ID）**，視為很後期才需要的功能；`ai-core-trace` 從 CLI 入口移除；`trace/` 從目錄結構移除；`ledger_path` 從 config 移除；M2（Ledger）里程碑整體移除，M3–M7 重編為 M2–M6。解決 C 類設計缺口 C1–C6：C1（author 寫獨立 function vs SFC 由 `--target sfc` 明確指定）→ §8.3；C2（`funcs/` 預設路徑為 `user_data_dir/ai_core/funcs/`，`AI_CORE_FUNCS_DIR` env 可 override）→ §8.3；C3（語言中立性說明：Python 為 ai_core 自身實作語言，function 語言不限）→ §3；C4（HTTP 路徑統一：`GET /entries/<name>` 移除 `/metadata` 後綴）→ §4.7 / §6.4；C5（calling pack 就是普通獨立 function，放 funcs/）→ §8；C6（`io` 各型態補例）→ §4.2。§8–§17 整體降編為 §7–§16。
- 2026-05-12：刪除 `docs/OPEN_QUESTIONS.md`（所有問題已解決）。建立程式碼骨架（`src/ai_core/` 各模組、`funcs/echo.sh`、`pyproject.toml`）。`docs/ARCHITECTURE.md` 改為導覽入口，詳細設計切分至 `docs/architectures/`。
- 2026-05-18：消化 `thinking.md` 第 4–5 行剩餘設計點 —— 在 §10.1 明確宣告 `src/ai_core/protocol/` 是 function 作者與 manager 作者的共用 helper 出口，列出當前已存在子模組（`metadata.py` / `env.py`）與未來規劃但 YAGNI 暫不抽出的三項（`server.py` / `queue.py` / `ratelimit.py`，等第二個 singleton manager 出現時才從 `entry_manager/` 抽離）。§1 Singleton Resource Manager Pattern 結尾加一行指向 §10.1。
