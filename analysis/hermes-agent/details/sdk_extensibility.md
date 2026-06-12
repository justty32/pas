# hermes-agent 擴充架構深度剖析：SDK 設計者視角

> 核對於 2026-06-12。所有引用均指向 `projects/hermes-agent/` 下的相對路徑。

---

## 1. Hook 系統的核心設計

### 1.1 儲存結構

所有 hook callback 儲存在 `PluginManager._hooks` 這個 `Dict[str, List[Callable]]` 裡（`hermes_cli/plugins.py:1034`）。鍵是 hook 名稱字串，值是 callback 列表。插件呼叫 `ctx.register_hook(hook_name, callback)` 時，最終執行的是：

```python
# hermes_cli/plugins.py:953
self._manager._hooks.setdefault(hook_name, []).append(callback)
```

這個設計極為樸素——就是個 Python dict of lists，沒有任何優先序數字、沒有依賴圖，先註冊先呼叫。

### 1.2 執行順序（多 plugin 掛同一個 hook）

`invoke_hook` 的執行邏輯（`hermes_cli/plugins.py:1574-1609`）：

1. 取出 `self._hooks.get(hook_name, [])` 的整個 callback 列表。
2. 以 `for cb in callbacks:` 依序呼叫，**依照 `append` 的先後順序**。
3. 每個 callback 各自獨立的 `try/except` 包裹。
4. 收集所有非 `None` 的回傳值組成 `results` 列表後回傳給呼叫端。

**關鍵結論**：執行順序完全由 plugin 的載入順序決定，而載入順序由來源優先序決定（bundled → user → project → entrypoint），同層內由目錄的 `sorted()` 字母序決定（`hermes_cli/plugins.py:1270`）。

### 1.3 hook 失敗時是否中止主流程

**不會中止**。每個 callback 都被包裹在：

```python
# hermes_cli/plugins.py:1597-1608
try:
    ret = cb(**kwargs)
    if ret is not None:
        results.append(ret)
except Exception as exc:
    logger.warning(
        "Hook '%s' callback %s raised: %s", hook_name, getattr(cb, "__name__", repr(cb)), exc,
    )
```

這意味著即使某個 plugin 拋出未處理的例外，主 agent 迴圈照常執行，只在 log 留下 WARNING。這是「觀察者不能讓主流程崩潰」的安全設計原則。

### 1.4 特例：`pre_tool_call` 的阻擋語義

這個 hook 有特殊處理，不只是觀察：`get_pre_tool_call_block_message()` 函式（`hermes_cli/plugins.py:1760-1807`）會遍歷 `invoke_hook` 的結果，找第一個 `{"action": "block", "message": "..."}` dict 就回傳封鎖訊息，中止工具執行。「第一個有效 block 指令勝出」（first valid block wins），後續 callback 的意見被忽略。

同樣地，`transform_llm_output`、`pre_gateway_dispatch` 也有各自的回傳值協議，由呼叫端的框架代碼解讀；`invoke_hook` 本身只負責「收集非 None 回傳值」，語義由呼叫端負責。

### 1.5 Hooks 與 Middleware 的設計分工

hermes-agent 明確區分了兩個概念（`hermes_cli/middleware.py:1-9`）：

- **Hooks（觀察者）**：被動觀察事件，也可以回傳特定結構影響流程，但設計重心是 *報告*。
- **Middleware（攔截器）**：主動重寫請求 payload 或包裹執行邏輯（chain of responsibility 模式）。

Middleware 有 4 種類型（`hermes_cli/middleware.py:29-34`）：
- `tool_request`：在工具執行前重寫引數。
- `tool_execution`：包裹工具執行邏輯。
- `llm_request`：在 LLM 呼叫前重寫請求 payload（model、messages、temperature 等）。
- `llm_execution`：包裹整個 LLM 呼叫。

Middleware 的結果是「鏈式」的，每個 callback 的輸出可以成為下一個的輸入（`hermes_cli/middleware.py:108-117`），而 hook 的結果是「平行收集」的。

### 1.6 設計優缺點分析

**優點**：
- **容錯性強**：每個 callback 獨立隔離，一個壞掉不影響其他。
- **實作極簡**：dict of lists + for loop，任何開發者都能立刻理解整個系統。
- **向前相容**：未知 hook 名稱只 warning 不報錯（`hermes_cli/plugins.py:945-953`），舊 plugin 在新版本不會炸。

**缺點**：
- **無優先序機制**：無法宣告「我的 hook 要在 X plugin 之前執行」。
- **result 語義不統一**：`pre_tool_call` 用 `{"action": "block"}`、`transform_llm_output` 用 `str`、`pre_llm_call` 用 `{"context": "..."}` 或 `str`——每個特殊 hook 的回傳語義散落在框架的各個呼叫點，沒有統一的型別系統。
- **同步執行**：hook 是同步呼叫，無法並行。耗時的 hook（如遠端審計）會阻塞主迴圈。
- **無移除機制**：`PluginManager` 沒有 `unregister_hook()` API（除非完整 `force` 重掃）。

---

## 2. Plugin 生命週期

### 2.1 `plugin.yaml` manifest 格式

`PluginManifest` dataclass 的欄位（`hermes_cli/plugins.py:236-269`）完整對應了 YAML 格式：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `name` | `str` | Plugin 的顯示名稱（若缺省，使用目錄名） |
| `version` | `str` | 版本號，純展示用 |
| `description` | `str` | 一行描述 |
| `author` | `str` | 作者 |
| `requires_env` | `list` | 需要的環境變數列表（可包含 dict 指定選填/必填） |
| `provides_tools` | `list[str]` | 宣告提供的工具名（文件用，非強制） |
| `provides_hooks` | `list[str]` | 宣告掛的 hook（文件用，非強制） |
| `kind` | `str` | `standalone`/`backend`/`exclusive`/`platform`/`model-provider` |
| `key` | `str` | 路徑衍生的唯一 key，用於 enabled/disabled 查找 |

實際範例（`plugins/disk-cleanup/plugin.yaml:1-7`）：

```yaml
name: disk-cleanup
version: 2.0.0
description: "Auto-track and clean up ephemeral files..."
author: "@LVT382009 (original), NousResearch (plugin port)"
hooks:
  - post_tool_call
  - on_session_end
```

注意：`hooks:` 欄位是純文件宣告，框架**不會**根據它自動掛載 hook，真正的掛載在 `register(ctx)` 的程式碼裡。

### 2.2 `register(ctx)` 的呼叫時機

`_load_plugin()` 函式（`hermes_cli/plugins.py:1432-1512`）負責：

1. 匯入 `__init__.py` 模組（`importlib.util.spec_from_file_location`）。
2. 取得 `module.register`。
3. 建立 `PluginContext(manifest, self)`。
4. 呼叫 `register_fn(ctx)`。

這個過程發生在 `discover_and_load()` 期間（`hermes_cli/plugins.py:1053`），而 `discover_and_load()` 是惰性的：第一次呼叫 `discover_plugins()` 或 `_ensure_plugins_discovered()` 時才執行，且有 `_discovered` 旗標確保只跑一次（除非 `force=True`）。

### 2.3 `PluginContext` 提供的 API 完整清單

`PluginContext` 是插件能觸碰的整個「框架表面」（`hermes_cli/plugins.py:290-1023`）：

| 方法 | 功能 |
|------|------|
| `register_hook(hook_name, callback)` | 掛載生命週期 hook |
| `register_middleware(kind, callback)` | 掛載請求/執行中間件 |
| `register_tool(name, toolset, schema, handler, ...)` | 向全域工具登錄表登記工具 |
| `register_command(name, handler, ...)` | 登記會話內 slash 指令（如 `/disk-cleanup`） |
| `register_cli_command(name, help, setup_fn, ...)` | 登記 CLI 子指令（如 `hermes meet`） |
| `register_skill(name, path, ...)` | 登記 plugin 提供的 skill（SKILL.md） |
| `register_auxiliary_task(key, ...)` | 登記 plugin 自訂的 auxiliary LLM 任務 |
| `register_context_engine(engine)` | 替換內建的 context 壓縮引擎（全域唯一） |
| `register_image_gen_provider(provider)` | 登記圖像生成後端 |
| `register_video_gen_provider(provider)` | 登記影片生成後端 |
| `register_web_search_provider(provider)` | 登記 web 搜尋/擷取後端 |
| `register_browser_provider(provider)` | 登記 cloud browser 後端 |
| `register_tts_provider(provider)` | 登記 TTS 後端 |
| `register_transcription_provider(provider)` | 登記 STT 後端 |
| `register_platform(name, label, ...)` | 登記 gateway 平台適配器 |
| `register_dashboard_auth_provider(provider)` | 登記 dashboard 認證後端 |
| `inject_message(content, role)` | 向活躍對話注入訊息 |
| `dispatch_tool(tool_name, args, ...)` | 透過框架分派工具呼叫 |
| `ctx.llm` (property) | 存取 host-owned LLM facade（`PluginLlm`） |

`ctx.llm` 值得特別注意：它讓 plugin 能用使用者已設定的 provider 與金鑰發起 LLM 呼叫，而不需要 plugin 自帶 API key（`hermes_cli/plugins.py:307-316`）。這個設計讓 plugin 成為 host 的「可信客戶端」，而非獨立服務。

### 2.4 4 種 Plugin 來源的發現機制

`discover_and_load()` 的掃描順序（`hermes_cli/plugins.py:1074-1128`）：

1. **Bundled** — `<repo>/plugins/`（或 `HERMES_BUNDLED_PLUGINS` env var 指定的路徑）。`memory/`、`context_engine/`、`platforms/`、`model-providers/` 在頂層被 `skip_names` 排除，各有自己的發現系統。`platforms/` 則在第二個 `_scan_directory` 呼叫中額外掃描。

2. **User** — `~/.hermes/plugins/`（由 `get_hermes_home()` 決定）。

3. **Project** — `./.hermes/plugins/`（當前工作目錄）。**預設停用**，必須設 `HERMES_ENABLE_PROJECT_PLUGINS=1` 才啟動。這個 opt-in 設計是出於安全考量：避免克隆任意 repo 就自動執行裡面的 plugin。

4. **Entry-points (pip)** — 透過 `importlib.metadata.entry_points()` 掃描 `hermes_agent.plugins` group（`hermes_cli/plugins.py:1402-1426`）。pip 安裝的 package 在 `setup.cfg`/`pyproject.toml` 宣告 entry point 即可被發現，無需放置在任何目錄。

**名稱衝突處理**：後掃描的來源覆蓋前面的同名 plugin（`hermes_cli/plugins.py:1138-1139`）：

```python
for manifest in manifests:
    winners[manifest.key or manifest.name] = manifest
```

所以 user plugin 可以完全替換 bundled plugin，project plugin 又可以覆蓋 user plugin。

---

## 3. Hook 完整清單與呼叫語境

以下是 `VALID_HOOKS` 的完整列表（`hermes_cli/plugins.py:128-170`），共 20 個 hook。

### 3.1 工具呼叫相關

| Hook 名稱 | 觸發時機 | 關鍵引數 | 回傳值語義 |
|-----------|----------|----------|------------|
| `pre_tool_call` | 工具執行**前**，在 middleware 和審批之後 | `tool_name: str`, `args: dict`, `task_id: str`, `session_id: str`, `tool_call_id: str`, `turn_id: str`, `api_request_id: str`, `middleware_trace: list` | 回傳 `{"action": "block", "message": "..."}` 可阻止工具執行；其他值或 `None` 則繼續 |
| `post_tool_call` | 工具執行**後** | `tool_name: str`, `args: dict`, `result: Any`, `task_id: str`, `session_id: str`, `tool_call_id: str` | 純觀察，回傳值被忽略 |
| `transform_tool_result` | 工具執行後，result 回傳給 LLM 前 | 需查框架呼叫點 | 回傳字串替換 result；回傳 None 保持原值 |
| `transform_terminal_output` | 終端指令執行後，輸出回傳前 | 需查框架呼叫點 | 回傳字串替換輸出；回傳 None 保持原值 |

### 3.2 LLM 呼叫相關

| Hook 名稱 | 觸發時機 | 關鍵引數 | 回傳值語義 |
|-----------|----------|----------|------------|
| `pre_llm_call` | 每次 LLM API 呼叫前 | 至少含 `turn_id`、`session_id`、`messages` 相關欄位 | 回傳 `{"context": "文字"}` 或純字串，注入到本輪使用者訊息（**不**注入 system prompt，以保留 prompt cache）|
| `post_llm_call` | LLM API 呼叫後，回應解析後 | 含回應相關欄位 | 純觀察 |
| `transform_llm_output` | LLM 輸出顯示給使用者前 | 含輸出文字 | 第一個非 None 非空字串勝出，替換顯示文字；適合語彙/個性轉換 |

### 3.3 API 請求相關

| Hook 名稱 | 觸發時機 | 回傳值語義 |
|-----------|----------|------------|
| `pre_api_request` | 向 LLM provider 發送請求前 | 純觀察（注意：實際請求修改走 `llm_request` middleware，不走這個 hook） |
| `post_api_request` | provider 回應後 | 純觀察 |
| `api_request_error` | provider 請求失敗時 | 純觀察 |

### 3.4 會話生命週期

| Hook 名稱 | 觸發時機 | 關鍵引數 | 回傳值語義 |
|-----------|----------|----------|------------|
| `on_session_start` | 對話 session 開始時 | `session_id: str` 等 | 純觀察；用於初始化外部資源 |
| `on_session_end` | session 結束時（agent 完成一輪） | `session_id: str`, `completed: bool`, `interrupted: bool` | 純觀察；用於清理資源、產出摘要 |
| `on_session_finalize` | `on_session_end` **之後**觸發 | 同上 | 純觀察；最終清理 |
| `on_session_reset` | 使用者要求重置 session 時 | `session_id: str` | 純觀察；清除 plugin 內部狀態 |

### 3.5 子 Agent 生命週期

| Hook 名稱 | 觸發時機 | 回傳值語義 |
|-----------|----------|------------|
| `subagent_start` | 一個子 agent 任務啟動時 | 純觀察 |
| `subagent_stop` | 子 agent 任務結束時 | 純觀察 |

### 3.6 Gateway 與審批

| Hook 名稱 | 觸發時機 | 關鍵引數 | 回傳值語義 |
|-----------|----------|----------|------------|
| `pre_gateway_dispatch` | Gateway 收到訊息後、auth/pairing 和 agent dispatch 之前 | `event: MessageEvent`, `gateway: GatewayRunner`, `session_store` | 回傳 `{"action": "skip", "reason": "..."}` 丟棄訊息；`{"action": "rewrite", "text": "..."}` 替換文字後繼續；`{"action": "allow"}` 或 `None` 正常分派 |
| `pre_approval_request` | 危險指令需要使用者審批前（CLI 和 gateway 均觸發） | `command: str`, `description: str`, `pattern_key: str`, `pattern_keys: list[str]`, `session_key: str`, `surface: "cli" \| "gateway"` | **純觀察**，回傳值被忽略。無法通過此 hook 預批或否決審批請求（要阻擋工具執行，用 `pre_tool_call`） |
| `post_approval_response` | 使用者對審批作出回應後 | 同 `pre_approval_request` 加 `choice: "once" \| "session" \| "always" \| "deny" \| "timeout"` | 純觀察 |

---

## 4. SDK 擴充點設計建議

### 4.1 從 hermes-agent 學到的教訓

**值得採用的設計**：

1. **容錯隔離是必需品**：每個 callback 都用 try/except 包裹，寫一個壞 plugin 不能讓整個 agent 崩潰。這在多 plugin 環境裡是最基本的防護。

2. **Context facade 比直接存取 manager 更安全**：`PluginContext` 把 plugin 能做的事集中在一個 API 介面，而非讓 plugin 直接操作 `PluginManager` 的內部 dict。未來要加權限控制，只需在 `PluginContext` 方法上加檢查。

3. **Hooks 與 Middleware 分工清晰**：觀察事件 → hooks；主動改變行為 → middleware。不要把這兩個混在一個機制裡。

4. **manifest 是文件，程式碼是真相**：`plugin.yaml` 的 `hooks:` 欄位只是給人讀的，不影響實際掛載。真正的掛載由 `register(ctx)` 完成。這樣的設計讓 manifest 永遠不會和程式碼不同步（因為它根本不影響行為）。

5. **來源優先序覆蓋**：bundled < user < project，讓使用者能無痛替換任何內建 plugin，不需要修改原始碼。

**應該改進的設計**：

1. **hook 回傳語義應有統一的型別定義**。目前每個特殊 hook 的回傳格式散落在框架各處，plugin 作者必須讀文件字串才知道。

2. **應支援 async hook**。目前 hooks 是同步呼叫，阻塞主迴圈。

3. **應有 hook 移除機制**，至少要能支援測試場景的清理。

### 4.2 最小可擴充 SDK 的 Hook 介面草圖

以下是第一版就必要的 hook 集合，以 Python 型別定義表達：

```python
from typing import Any, Callable, Dict, List, Optional, Protocol

# ── 第一版必要 hooks ──────────────────────────────────────────

class HookCallbacks(Protocol):
    """第一版 agent SDK 的最小 hook 介面。"""

    def on_session_start(self, session_id: str, **kwargs: Any) -> None:
        """初始化外部資源（DB 連線、認證 token 等）。"""

    def on_session_end(
        self, session_id: str, completed: bool, **kwargs: Any
    ) -> None:
        """清理資源、產出報告、持久化狀態。"""

    def pre_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        """工具執行前呼叫。
        回傳 {"action": "block", "message": "..."} 可阻擋工具。
        回傳 None 或其他值則繼續。
        """

    def post_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: Any,
        **kwargs: Any,
    ) -> None:
        """工具執行後呼叫（純觀察）。"""

    def pre_llm_call(
        self,
        messages: List[Dict],
        **kwargs: Any,
    ) -> Optional[str]:
        """LLM 呼叫前觸發。回傳字串會注入到本輪使用者訊息。"""

    def post_llm_call(
        self,
        response_text: str,
        **kwargs: Any,
    ) -> None:
        """LLM 回應後觸發（純觀察）。"""

    def transform_llm_output(
        self,
        text: str,
        **kwargs: Any,
    ) -> Optional[str]:
        """顯示給使用者前呼叫。回傳字串替換輸出，None 保持原值。
        多 plugin 時，第一個非 None 勝出（first wins）。
        """


# ── 可以之後再加的 hooks ──────────────────────────────────────

class ExtendedHookCallbacks(HookCallbacks, Protocol):
    """第二版可追加的 hook。"""

    def on_session_reset(self, session_id: str, **kwargs: Any) -> None: ...

    def subagent_start(self, agent_id: str, task: str, **kwargs: Any) -> None: ...
    def subagent_stop(self, agent_id: str, result: Any, **kwargs: Any) -> None: ...

    def pre_api_request(self, request: Dict, **kwargs: Any) -> None: ...
    def post_api_request(self, response: Any, **kwargs: Any) -> None: ...
    def api_request_error(self, error: Exception, **kwargs: Any) -> None: ...

    def pre_gateway_dispatch(
        self,
        event: Any,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        """Gateway 分派前。回傳 {"action": "skip"|"rewrite", ...} 影響流程。"""


# ── 最小 SDK PluginContext 草圖 ───────────────────────────────

class MinimalPluginContext:
    """最小可擴充 SDK 給 plugin 的介面。"""

    def register_hook(self, hook_name: str, callback: Callable) -> None: ...
    def register_tool(
        self,
        name: str,
        schema: Dict,
        handler: Callable,
        *,
        toolset: str = "plugin",
        override: bool = False,
    ) -> None: ...
    def register_command(self, name: str, handler: Callable, description: str = "") -> None: ...


def register(ctx: MinimalPluginContext) -> None:
    """所有 plugin 的進入點，由 SDK 在 discover_and_load() 時呼叫。"""
    ...
```

**第一版必要理由**：
- `on_session_start/end`：plugin 最基本的資源管理需求。
- `pre_tool_call`（含 block 能力）：安全性最低需求——沒有這個，plugin 無法做任何策略控制。
- `post_tool_call`：觀測與審計，幾乎所有實用 plugin 都需要。
- `pre_llm_call`（context injection）：RAG、記憶體插件的核心需求。
- `transform_llm_output`：persona、語言轉換插件的核心需求。

**可以之後再加的理由**：
- gateway hooks 在沒有 gateway 的 SDK 裡沒有意義。
- 多 agent/subagent hooks 在單 agent SDK 裡也沒有意義。
- API 錯誤 hooks 在第一版可以讓主流程自己處理。

---

## 5. Plugin 隔離與安全性

### 5.1 hermes-agent 的現狀

hermes-agent **沒有任何 sandbox 或 OS 級別的隔離**。Plugin 的 `__init__.py` 是直接透過 `importlib.util.exec_module()` 在主行程執行（`hermes_cli/plugins.py:1549`），享有完整的 Python 行程能力：

- 可以讀寫任意檔案系統路徑。
- 可以開網路連線。
- 可以呼叫 `os.system()`、`subprocess` 等。
- 可以存取主行程的所有 Python 物件（包括 API key、session DB 等）。

hermes-agent 的安全邊界是**信任邊界**（trust boundary），不是執行邊界：

1. **opt-in 啟用**：使用者必須明確在 `plugins.enabled` 列表中加入 plugin 名稱才會載入（`hermes_cli/plugins.py:1198-1213`）。bundled 和 platform plugin 例外（自動載入）。

2. **project plugins 預設停用**：必須設環境變數 `HERMES_ENABLE_PROJECT_PLUGINS=1`（`hermes_cli/plugins.py:1112`），防止克隆 repo 就自動執行惡意 plugin。

3. **disabled 清單**（deny list）：`plugins.disabled` 可以強制排除特定 plugin，優先於 `enabled`（`hermes_cli/plugins.py:1144-1149`）。

4. **type checking 在 `register_*` 方法**：所有 provider 的 `register_*` 方法都做 `isinstance()` 檢查（例如 `hermes_cli/plugins.py:519-526`），但這只防止型別錯誤，不防止惡意行為。

5. **thread-local tool whitelist**：`set_thread_tool_whitelist()` 函式（`hermes_cli/plugins.py:1748`）可以限制特定執行緒（如 subagent）可用的工具集，這是 plugin 的間接沙箱——不是隔離 plugin 本身，而是限制 plugin 透過框架能發起的工具呼叫範圍。

### 5.2 SDK 設計上需要補充的安全機制

若要設計生產級的可信 plugin SDK，hermes-agent 的現有設計需補充：

1. **執行隔離**：至少提供 subprocess 模式（每個 plugin 跑在獨立行程，透過 IPC 通訊）作為高信任等級 plugin 的可選模式。完整隔離可考慮 WebAssembly（WASM）sandbox（如 Extism 框架的做法）。

2. **API 能力宣告**：在 `plugin.yaml` 加入明確的能力宣告（`capabilities: [network, filesystem:read, tool_block]`），由框架在載入前向使用者展示，讓使用者知道授予了什麼。

3. **PluginContext 的存取控制**：依 plugin 的信任等級，動態決定 `PluginContext` 提供哪些 API。例如，低信任 plugin 的 `ctx` 不應有 `inject_message()`（可造成惡意訊息注入）。

4. **Hook callback 的 read-only 參數**：傳入 hook callback 的引數應是深複製或 frozen 物件，防止 plugin 直接修改主行程的 mutable 物件。

---

## 6. 坑點與非顯而易見的設計決策

### 6.1 `kind` 的隱式推斷（反直覺）

`_parse_manifest()` 會讀取 `__init__.py` 的前 8192 字元，用字串搜尋判斷 kind（`hermes_cli/plugins.py:1344-1373`）：

```python
if "register_memory_provider" in source_text or "MemoryProvider" in source_text:
    kind = "exclusive"
elif "register_provider" in source_text and "ProviderProfile" in source_text:
    kind = "model-provider"
```

這個「讀程式碼推斷行為」的設計是為了向後相容——讓已存在的 plugin（在 `kind:` 欄位加入之前寫的）也能被正確分類。但副作用是：如果你的 plugin 的 `__init__.py` 裡有包含這些字串的**字面值字串**（例如文件字串裡寫了 `register_memory_provider`），它可能被誤判為 exclusive plugin 而跳過載入。

### 6.2 `provides_hooks` 欄位完全不影響實際行為

`plugin.yaml` 裡的 `hooks:` / `provides_hooks:` 欄位（以及 `provides_tools:`）由 `_parse_manifest()` 讀取後存入 manifest，但 `discover_and_load()` **完全不用這些欄位決定是否載入或如何載入**（`hermes_cli/plugins.py:1379-1391`）。這些欄位純粹是給 `hermes plugins list` 指令的展示資料，以及給 `plugin.yaml` 的讀者理解 plugin 意圖。新手很容易誤以為「在 YAML 裡聲明 hook 就會自動掛載」。

### 6.3 `discover_and_load()` 的 winners dict 會丟失多個同名 plugin 的詳細狀態

```python
# hermes_cli/plugins.py:1137-1139
winners: Dict[str, PluginManifest] = {}
for manifest in manifests:
    winners[manifest.key or manifest.name] = manifest
```

如果 user 和 bundled 各有一個 `disk-cleanup`，最後 winners dict 只保留 user 版本的 manifest，bundled 版本的 manifest **完全消失**。`hermes plugins list` 指令無法告訴你「有個被覆蓋的 bundled plugin」。

### 6.4 `pre_llm_call` 的 context injection 機制保護了 prompt cache

```python
# hermes_cli/plugins.py:1586-1592（invoke_hook 的文件字串）
# Context is ALWAYS injected into the user message, never the
# system prompt. This preserves the prompt cache prefix — the
# system prompt stays identical across turns so cached tokens
# are reused. All injected context is ephemeral — never
# persisted to session DB.
```

這個設計決策（注入使用者訊息而非系統提示詞）是為了保持 system prompt 不變，讓 LLM provider 的 prompt cache 可以跨 turn 命中。如果 memory plugin 把記憶資料注入 system prompt，每次都會破壞快取，造成 token 浪費。這個決策在 plugin API 文件字串裡說明了，但不在 `plugin.yaml` 格式文件裡，容易被 plugin 作者忽略。

### 6.5 `transform_llm_output` 的 first-wins 語義

```python
# hermes_cli/plugins.py:133-136（VALID_HOOKS 的行內文件）
# First non-None string wins. Useful for vocabulary/personality transformation.
"transform_llm_output",
```

多個 plugin 都掛 `transform_llm_output` 時，第一個回傳非空字串的 plugin 的輸出被採用，後面的 plugin **看不到**前一個 plugin 轉換後的文字——它們全部拿到的都是原始 LLM 輸出。這與 `pre_llm_call` 的 context injection 行為（全部疊加）完全不同。這個語義差異容易讓 plugin 作者犯錯：若兩個 plugin 都想改輸出（如語言轉換 + 個性轉換），第二個永遠不會生效。

### 6.6 async plugin command handler 的同步橋接

`resolve_plugin_command_result()`（`hermes_cli/plugins.py:1834-1877`）用了一個 `threading.Event` + daemon thread 橋接 async handler 到同步呼叫點。當已經在一個 event loop 內時，它在新的 daemon thread 裡跑 `asyncio.run()`。這意味著：

- 30 秒 timeout 之後 hung 的 handler 不會被 cancel（只是 `done.wait()` 超時），daemon thread 繼續跑到行程結束。
- 在 daemon thread 裡的 `asyncio.run()` 和主行程的 loop 是完全隔離的——plugin command 無法 `await` 主行程的任何 coroutine。

這個設計對「plugin command 只需要做一次性的同步-like 工作」的場景完全夠用，但對「plugin command 需要長期串流或與主 loop 互動」的場景就很不適合。

---

## 總結

hermes-agent 的 plugin 系統是一個設計成熟、考量周全的 **observer-first + selective interceptor** 架構。其核心哲學是：plugin 能觀察一切，但要主動改變行為，需要明確的 hook/middleware 協議支援，而不是直接操作內部物件。對於想設計可擴充 agent SDK 的人，最值得借鑑的三個設計決策是：(1) PluginContext facade 控制 plugin 能觸碰的表面、(2) hooks 容錯隔離讓壞 plugin 不影響主流程、(3) 來源優先序覆蓋讓使用者能無縫替換任何內建行為。
