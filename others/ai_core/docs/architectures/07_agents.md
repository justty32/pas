# AI Core — Agent 整合與文檔策略

## §15. Agent 整合與文檔策略

ai_core 初期使用方式是「人類 + 現成 AI agent（Claude Code / Cline / Cursor / Aider / ...）+ ai_core function」三方協作。**長期目標是 function 集合成熟到能替代 agent 的部分功能** — 這條演進路徑要求文檔系統從一開始就把 agent 當一級讀者。

### 15.1 文檔分層

```
ai_core/
├── README.md              # 人類入口；快速上手 + 用例
├── CLAUDE.md              # Claude Code 專用入口（已存在）
├── AGENTS.md              # 通用 agent 入口；任何 agent 進專案先讀這個
├── docs/
│   ├── ARCHITECTURE.md    # 設計導覽入口（指向 architectures/）
│   └── architectures/     # 詳細設計（本目錄）
└── auto/                  # 由 ai-core-hub 產生 / 更新，不手寫
    ├── FUNCTIONS.md       # 所有 function 清單與用法（人類 + agent 兩用）
    ├── CHAINS.md          # 常見 calling chain pattern
    ├── tools.openai.json  # OpenAI tools schema export
    ├── tools.anthropic.json
    ├── server.mcp.json    # MCP server descriptor
    └── skills/            # Claude Code skills 格式
        └── <func_name>/
            └── SKILL.md
```

**手寫 vs 自動產生**：手寫文件描述「設計與哲學」（少變動）；自動產生文件描述「目前能力」（隨 function 集合變動）— 兩者分開避免手動同步。

### 15.2 AGENTS.md 結構

新增專案根目錄的 `AGENTS.md` 作為通用 agent 入口（不只給 Claude Code，所有 agent 都看這個）。建議模板：

```markdown
# AI Core — Agent Guide

## 你能用 ai_core 做什麼
- 呼叫 LLM             → ai-core-call --entry <model> --input X --output Y
- 列出可用 function    → ai-core-hub --build-list   或   GET hub-server /funcs
- 製作新 function      → ai-core-author --spec spec.json

## 進入專案後的建議流程
1. 跑 `ai-core-hub --build-list` 拿到當前 function 清單
2. 對任一 function 不確定用法時：`<func> --metadata`
3. 需要 LLM 推理：呼 `ai-core-call`
4. 需要新能力且確定要寫 function：呼 `ai-core-author`，**不要直接手寫到 funcs/**

## 行為規範
- 每個 function 都應遵守 --metadata 協議；不確定先看 metadata
- 錯誤訊息走 stderr；機器可解析錯誤加 `--json-errors` 旗標

## Tool calling schema（給支援 native tool calling 的 agent）
- OpenAI format    → auto/tools.openai.json
- Anthropic format → auto/tools.anthropic.json
- MCP server       → auto/server.mcp.json
```

`AGENTS.md` 由 `ai-core-hub --gen-agent-md > AGENTS.md` 產生，並在 function 集合變動時可重新跑。

### 15.3 Hub `--export` 支援的 agent 格式

| 格式 | 用途 | 對應 agent |
|---|---|---|
| `openai-tools` | OpenAI tools schema | GPT、Cursor、Aider 等 |
| `anthropic-tools` | Anthropic tools schema | Claude API |
| `mcp` | MCP server descriptor | Claude Desktop、MCP-aware client |
| `claude-skill` | Claude Code skills（`SKILL.md` + frontmatter） | Claude Code |
| `agent-md` | 通用 markdown agent guide（產生 AGENTS.md） | 任何 agent |
| `functions-md` | 函式清單 markdown（產生 auto/FUNCTIONS.md） | 任何 agent / 人類 |

```bash
ai-core-hub --export openai-tools ./funcs/* > auto/tools.openai.json
ai-core-hub --export claude-skill ./funcs/* --out auto/skills/
ai-core-hub --gen-agent-md > AGENTS.md
ai-core-hub --gen-functions-md > auto/FUNCTIONS.md
```

Server 版（`ai-core-hub-server`）對應端點：`GET /export?format=...`、`GET /agents-md`、`GET /functions-md`。

### 15.4 自動文檔更新時機

設計三個觸發點：

1. **手動**：使用者 / agent 跑 `ai-core-hub --gen-*`
2. **註冊時觸發**：`ai-core-author` 註冊新 function 後自動跑 `--gen-functions-md` 與 `--gen-agent-md`，讓 auto/ 永遠最新
3. **CI / pre-commit**（可選）：把 `auto/` 視為產出物，`pre-commit` hook 驗證它與當前 funcs/ 一致

### 15.5 Self-Sufficiency 演進路徑

詳細路線圖待後續展開（規劃寫成 `docs/EVOLUTION.md`，目前尚未建立）。本節先給概念輪廓：

| 階段 | 狀態 | agent 角色 | ai_core 重點 |
|---|---|---|---|
| 1. Agent-assisted | function 集合稀少 | 主導；人類提需求、agent 直接做 | 提供 LLM 入口、author 工具 |
| 2. Function-rich | function 豐富、多數任務有對應 function | orchestrator；決定組哪些 function | calling chain template、語意搜尋 |
| 3. Self-sufficient | 常用任務有 chain template | 輕薄 router 或不需要 | chain 自動萃取、ai-core-author 自動發現重複模式 |

第一版（M0–M6）專注階段 1。階段 2 / 3 等真實使用模式累積後再設計，不預先過度工程。

### 15.6 與現成 agent 的整合 hint

ai_core 不深度耦合任何特定 agent，但提供慣例配置降低接入摩擦：

| Agent | 整合方式 |
|---|---|
| Claude Code | 已有 `CLAUDE.md`；可選 `auto/skills/` 載入為 skills |
| Cursor | `.cursorrules` 指向 `AGENTS.md` |
| Aider | `.aider.conf.yml` 把 `AGENTS.md` 加進 context |
| Cline | 同 Cursor，讀 `AGENTS.md` |
| MCP client | 啟動 `ai-core-hub-server` 並用 `auto/server.mcp.json` |

這些是文件層的接入；底層 function 不變。
