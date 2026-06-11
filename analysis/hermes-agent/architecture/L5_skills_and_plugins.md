# hermes-agent 架構分析 - Level 5: 技能系統與外掛架構

## 1. 雙層擴充體系
`hermes-agent` 區分了兩種類型的擴充：輕量級的 **Skills** 與系統級的 **Plugins**。

### 1.1 技能 (Skills)
- **目錄**: `skills/`
- **核心檔案**: `SKILL.md`（定義 Metadata、環境要求、安裝說明）與各類腳本。
- **特點**: 
    - 以腳本為核心（Python, Bash 等）。
    - 透過 `tools/registry.py` 封裝成 LLM 可用的工具。
    - 支援「Agent 自我維護」，Agent 可以透過 `create_skill` 工具產出新的技能。

### 1.2 外掛 (Plugins)
- **目錄**: `plugins/`
- **核心檔案**: `plugin.yaml` 與 `__init__.py`（需實作 `register(ctx)`）。
- **來源機制**: 支援內建（Bundled）、使用者目錄（User）、專案目錄（Project）以及透過 Pip 安裝的 Entry-points。
- **特點**: 
    - 擁有完整的生命週期鉤子（Hooks）。
    - 可以介入系統底層邏輯，如修改 LLM 的輸出、攔截 API 請求、或改變通訊閘道的行為。

## 2. 插件生命週期鉤子 (Hooks)
外掛系統提供了極其豐富的介入點，讓開發者能深度自訂 Agent 行為：

| 類別 | 關鍵鉤子 | 用途 |
|---|---|---|
| **工具介入** | `pre_tool_call`, `post_tool_call`, `transform_tool_result` | 攔截危險操作、修改工具回傳結果。 |
| **LLM 介入** | `pre_llm_call`, `post_llm_call`, `transform_llm_output` | 在發送前調整提示詞、或在顯示前過濾模型回應。 |
| **會話管理** | `on_session_start`, `on_session_reset`, `on_session_end` | 初始化外部資源、清理快取或產出會話報告。 |
| **基礎設施** | `pre_api_request`, `pre_gateway_dispatch` | 處理跨域認證、閘道層級的訊息過濾與重寫。 |
| **使用者互動** | `pre_approval_request`, `post_approval_response` | 觀察使用者的核准行為，用於審計或學習。 |

## 3. 工具分派與註冊流程
1. **發現 (Discovery)**: `hermes_cli/plugins.py` 掃描各來源目錄，讀取 `plugin.yaml`。
2. **註冊 (Registration)**: 呼叫插件的 `register(ctx)`，插件透過 `ctx.register_tool()` 將其功能注入到 `tools.registry` 中。
3. **調用 (Invocation)**: 當 LLM 產出工具調用時，`tool_executor.py` 透過註冊表找到對應的 Handler 並執行，執行前後會觸發該插件（及其他監聽者）的 Hooks。

## 4. 安全與隔離
- **中間件 (Middleware)**: 插件可以註冊為中間件，參與資料的清洗與脫敏。
- **權限控制**: 透過設定檔中的 `enabled` / `disabled` 清單，使用者可以精確控制啟用的擴充功能。
