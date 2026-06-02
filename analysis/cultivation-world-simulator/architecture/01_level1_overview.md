# Level 1：初始探索 — cultivation-world-simulator

> 核對於 2026-06-01，對應 commit 最新版 (v3.4.0)

---

## 一、專案定位

**修仙世界模擬器 (Cultivation World Simulator)**：玩家扮演「天道」，觀察由規則系統與 LLM 共同驅動的修仙世界自行演化。每個 NPC 都是獨立的 LLM Agent，有性格、記憶、人際關係與目標，無預設劇本，所有事件由世界邏輯自主推演。

- **版本**: `3.4.0`（`static/config.yml:2`）
- **授權**: CC BY-NC-SA 4.0

---

## 二、技術棧

| 層級 | 技術 |
|---|---|
| 後端語言 | Python 3.10+ |
| Web 框架 | FastAPI + Uvicorn |
| 即時通訊 | WebSocket（fastapi + websockets） |
| LLM 接入 | urllib 直呼 OpenAI 相容接口 / Anthropic 原生接口（無 SDK） |
| 設定管理 | PyYAML + OmegaConf（`static/config.yml`） |
| 前端框架 | Vue.js 3.x + TypeScript + Vite |
| 前端渲染 | PixiJS（2D 地圖動畫） |
| 打包 | PyInstaller（frozen exe）+ Electron（桌面） |
| 容器化 | Docker + Nginx |
| 測試 | pytest + pytest-asyncio + httpx（後端）、Vitest（前端） |

---

## 三、目錄頂層結構

```
cultivation-world-simulator/
├── src/           後端核心（Python）
│   ├── classes/   領域模型（Avatar、Sect、World、Action、Item…）
│   ├── server/    FastAPI 應用層（路由、生命週期、指令處理）
│   ├── sim/       模擬引擎（Simulator、Manager、Save/Load）
│   ├── systems/   全局系統（戰鬥、修為、時間、宗門、事件）
│   ├── utils/     工具（LLM 客戶端、設定、文字、ID）
│   ├── config/    設定服務（settings.json / secrets.json / RunConfig）
│   ├── i18n/      國際化（locale registry、模板解析）
│   └── run/       啟動輔助（地圖載入、靜態資料、日誌）
├── web/           前端（Vue3 + Vite + PixiJS）
├── static/        靜態資源（config.yml、locales、game_configs）
├── assets/        截圖、素材、頭像
├── docs/          規格文件（specs/）
├── tests/         pytest 測試套件
├── tools/         打包、i18n 工具、wiki 生成
├── deploy/        Docker 配置（Nginx、Dockerfile）
├── .cursor/       Cursor 規則 / 技能 / 指令
├── AGENTS.md      多 Agent 工作說明（Codex/Cursor）
└── docker-compose.yml
```

---

## 四、入口點

| 情境 | 指令 |
|---|---|
| 開發模式啟動 | `python src/server/main.py --dev` |
| 正式模式 | `python src/server/main.py` |
| Docker | `docker-compose up -d --build` |
| 凍結打包 | `tools/package/pack_desktop.ps1` |

`src/server/main.py` 是唯一入口，負責：
1. 修正跨平台編碼（`encode_runtime.configure_process_encoding()`）
2. 組裝全局遊戲狀態 `game_instance`（dict）與 `GameSessionRuntime`
3. 裝配 `public_query_builders`（查詢層）與 `command_handlers`（寫入層）
4. 建立 FastAPI lifespan（啟動遊戲迴圈 `game_loop()`）
5. 呼叫 `configure_routes_and_mounts()` 掛載所有路由
6. 呼叫 `start_server()` 啟動 Uvicorn

---

## 五、設定系統

三層設定分離：

| 設定層 | 位置 | 說明 |
|---|---|---|
| 只讀版本設定 | `static/config.yml` | 世界規則、LLM 模式、宗門經濟（不得用戶覆蓋） |
| 應用設定 | `$DATA_DIR/settings.json` + `secrets.json` | LLM base_url/key、語言、預設值 |
| 本局快照 | `RunConfig`（隨存檔保存） | 每局參數（NPC 數量、語言、角色設定） |

> LLM API Key 不回傳前端；`secrets.json` 與 `settings.json` 合併由 `src/config/settings_service.py` 管理。

---

## 六、API 設計

外部控制以 `/api/v1/` 命名空間為穩定接口，分為：

| 類型 | 路由前綴 | 說明 |
|---|---|---|
| 查詢（只讀） | `/api/v1/query/*` | world/state、events、detail、rankings、sect_relations… |
| 指令（寫入） | `/api/v1/command/*` | game/start、avatar/*、world/* |
| 設定 | `/api/settings*` + `/api/settings/llm*` | LLM 設定與連線測試 |
| WebSocket | `/ws` | 遊戲循環即時推送（tick 狀態更新） |

所有寫入指令需透過統一 mutation 入口序列化，避免與 `Simulator.step()` 並發（`AGENTS.md:26`）。

---

## 七、構建與測試

```bash
# 後端依賴
pip install -r requirements.txt

# 前端依賴
cd web && npm install

# 後端測試
pytest
pytest -n 8          # 快速並發

# 前端測試
cd web && npm run test
cd web && npm run type-check

# i18n locale 對齊
pytest tests/test_frontend_locales.py
pytest tests/test_backend_locales.py

# 打包桌面版（Windows PowerShell）
powershell ./tools/package/pack_desktop.ps1
```

---

## 八、國際化

- 語言清單唯一真源：`static/locales/registry.json`
- 源文件目錄：`static/locales/<lang>/modules/*.po`（日常維護）
- 合併產物：`static/locales/<lang>/LC_MESSAGES/messages.po`（由 `tools/i18n/build_mo.py` 生成）
- 前端支援語言：zh-CN（預設）、zh-TW、en-US、vi-VN、ja-JP

---

## 九、專案類型判斷

主要對應模板 **A（遊戲原始碼分析）**，兼具：
- **C**（Web 後端 / API 服務）：FastAPI REST + WebSocket
- **F**（AI/LLM 集成）：全 NPC LLM Agent 驅動

Level 3+ 依遊戲模板 A 展開，重點：
- L3：AI 決策鏈（NPC Agent）、世界生成、宗門系統、事件系統
- L4：戰鬥系統、修為境界、物品背包、裝備
- L5：存檔格式、LLM 接口協議、外部控制 API、資源定義
- L6：前端渲染（PixiJS 地圖）、WebSocket 推送協議
