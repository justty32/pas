# AI Core — 目錄結構、CLI、配置、里程碑與跨平台注意事項

## §10. 目錄結構

```
ai_core/
├── pyproject.toml
├── README.md
├── CLAUDE.md / thinking.md（已存在）
├── docs/
│   ├── ARCHITECTURE.md（導覽入口）
│   └── architectures/（本目錄，詳細設計）
├── src/ai_core/
│   ├── entry_manager/      # ai-core-server
│   │   ├── server.py
│   │   ├── queue.py
│   │   ├── ratelimit.py
│   │   ├── backends.py
│   │   └── cli.py
│   ├── client/             # ai-core-call (entry manager wrapper)
│   │   └── cli.py
│   ├── hub/
│   │   ├── scanner.py      # 共用函式掃描 / metadata fetch 邏輯
│   │   ├── exports.py      # mcp / openai-tools / anthropic-tools 格式轉換
│   │   ├── server.py       # ai-core-hub-server
│   │   └── cli.py          # ai-core-hub (one-shot)
│   ├── small_funcs/
│   │   ├── registry.py
│   │   ├── funcs/
│   │   └── cli.py          # ai-core-sfc
│   ├── author/             # ai-core-author
│   │   ├── generator.py    # 透過 ai-core-call 產 function 骨架
│   │   ├── dryrun.py
│   │   └── cli.py
│   └── protocol/
│       ├── metadata.py     # fetch_metadata、--json-errors helper
│       └── env.py          # AI_CORE_TOKEN 等環境變數
├── funcs/                  # 範例外部函式
│   └── echo.sh
└── tests/
```

---

## §11. CLI 入口（`pyproject.toml`）

```toml
[project.scripts]
ai-core-server      = "ai_core.entry_manager.cli:main"
ai-core-call        = "ai_core.client.cli:main"
ai-core-hub         = "ai_core.hub.cli:main"             # one-shot
ai-core-hub-server  = "ai_core.hub.server:main"          # 常駐
ai-core-sfc         = "ai_core.small_funcs.cli:main"
ai-core-author      = "ai_core.author.cli:main"
```

跨平台都能用，不依賴 shebang。

---

## §12. 配置範例

位置：`platformdirs.user_config_dir("ai_core")/config.json`

- Linux：`~/.config/ai_core/config.json`
- Windows：`%APPDATA%\ai_core\config.json`

```json
{
  "server": {"host": "127.0.0.1", "port": 5577},
  "hub_server": {"host": "127.0.0.1", "port": 5578},
  "models": {
    "ollama-llama3": {
      "backend": "ollama",
      "model": "llama3",
      "base_url": "http://localhost:11434"
    },
    "lmstudio-local": {
      "backend": "openai",
      "model": "local-model",
      "base_url": "http://localhost:1234/v1",
      "api_key": "not-needed"
    },
    "gemini-flash": {
      "backend": "gemini",
      "model": "gemini-2.0-flash",
      "api_key_env": "GEMINI_API_KEY",
      "limits": {"rpm": 15, "tokens_per_day": 1000000, "cost_per_day": 5.0},
      "concurrency": 5
    }
  }
}
```

---

## §13. 開發里程碑

### M0 — 骨架與協議（半天 ~ 一天）
- [ ] `pyproject.toml` + `uv` lockfile
- [ ] 6 個 CLI entrypoint 空殼
- [ ] `protocol/metadata.py`：`fetch_metadata`（含容錯）、`--json-errors` helper
- [ ] 範例 `funcs/echo.sh` 支援 `--input/--output/--metadata`
- [ ] 測試：`--metadata` 容錯（缺欄位 / 不合法 JSON / 函式根本不支援，都 graceful）

### M1 — Entry Manager MVP
- [ ] FastAPI server + `/call`、`/tasks/<id>`、`/status`、`/entries`、`/entries/<name>`
- [ ] litellm 接通三個 backend（ollama / lm studio / gemini）
- [ ] per-model asyncio queue + worker
- [ ] `ai-core-call` wrapper（同步 + `--async` 模式）
- [ ] **Dogfood**：`ai-core-call` 自身實作 `--metadata` 與 `--entry-metadata`

### M2 — Rate limit + 真實 backend 測試
- [ ] rpm / tokens / cost 限制與超限 stderr
- [ ] `--json-errors` 旗標
- [ ] 對 ollama / lm studio / gemini 各跑通一次
- [ ] 失敗重試與排隊降級

### M3 — Function Hub（雙形態）
- [ ] `hub/scanner.py`：掃描 + 容錯抓 metadata
- [ ] `ai-core-hub`（one-shot）：`--build-list`
- [ ] `hub/exports.py`：mcp / openai-tools / anthropic-tools 三種 export
- [ ] `ai-core-hub-server`：runtime discovery API（含 `/funcs`、`/search`、`/graph`、`/export`）
- [ ] 用 `ai-core-call` 自己對 list.txt 做摘要 — 自舉

### M3.5 — Agent Docs 自動化
- [ ] `ai-core-hub --gen-agent-md > AGENTS.md`（產生通用 agent 入口文件）
- [ ] `ai-core-hub --gen-functions-md > auto/FUNCTIONS.md`（產生函式清單）
- [ ] `ai-core-hub --export claude-skill` 產生 `auto/skills/<name>/SKILL.md`
- [ ] `ai-core-author` 成功註冊後自動觸發 `--gen-functions-md` + `--gen-agent-md`，讓 `auto/` 永遠最新
- [ ] `auto/` 目錄內容納入 CI / pre-commit 驗證（與 `funcs/` 一致性）

### M4 — Small Function Center（參考實作 `ai-core-sfc`）
- [ ] 子函式機制（Python 模組動態 import / 掛載；新增子函式不需改核心）
- [ ] dispatch CLI：`ai-core-sfc <dispatch-flag> <name> --input X --output Y`（旗標名稱由實作者決定）
- [ ] SFC 自身的 `--metadata`
- [ ] `--list` 列出子函式名稱
- [ ] 子函式 metadata 查詢（pass-through 或 SFC 自管，二擇一）
- [ ] hub scanner 整合測試：能正確展開 SFC 內所有子函式

### M5 — ai-core-author（自舉）
- [ ] `--spec` 介面 + dry-run + 註冊流程
- [ ] 多語言骨架產出（先支援 bash / python）
- [ ] 失敗回饋 LLM 重試機制
- [ ] author 自身遵守 `--metadata`，可被其他 AI 透過 hub 發現

### M6 — calling pack 範例集 + README
- [ ] `llm_call_coding_question` 等典型 calling pack 範例
- [ ] README 教學（人類視角 + AI agent 視角）

---

## §14. 跨平台注意事項

1. 路徑全用 `pathlib.Path`，不寫死 `/` 或 `\`
2. Subprocess 一律 `shell=False` + list args（避開 Windows quote 地獄）
3. 檔案 I/O 強制 `encoding="utf-8"`
4. CLI 透過 `[project.scripts]`，不依賴 shebang
5. Server port 衝突：第一版只做 TCP（unix socket / named pipe 留待未來）
6. config / data dir 一律走 `platformdirs`
7. 檔案寫入 lock：用 `fcntl`（Linux）+ `msvcrt`（Windows）寫薄 wrapper，或乾脆用單行原子 append（POSIX `O_APPEND` + Windows 對應）
