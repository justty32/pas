# SDK 設計視角：hermes-agent 記憶與脈絡管理系統深度剖析

> 核對於 2026-06-12，源碼版本：hermes-agent main branch

本文以「**從零打造 AI agent SDK**」的視角，深度剖析 hermes-agent 的記憶與脈絡管理實作。所有引用均附原始碼位置。

---

## 1. 短期脈絡管理策略

### 1.1 Token 數追蹤機制

hermes-agent **不直接計算精確 token 數**，而是使用粗估（rough estimate）搭配真實 API 回傳值的雙重機制：

- **粗估函式**：`estimate_request_tokens_rough()` 以 `len(text) / 4` 為基礎換算（`agent/context_compressor.py:95`：`_CHARS_PER_TOKEN = 4`），並對圖片部分加上固定 1600 token 常數（`:101`：`_IMAGE_TOKEN_ESTIMATE = 1600`）。
- **真實 token 更新**：每次 API 回應都攜帶 `usage.prompt_tokens`，由 `ContextCompressor.update_from_response()` 更新（`agent/context_compressor.py:700-712`）。
- **雙軌切換**：粗估會故意高估（因為工具 schema 的 overhead），但若上一輪真實 token 證明請求在閾值內，`should_defer_preflight_to_real_usage()` 會讓當輪跳過壓縮（`agent/context_compressor.py:714-742`）。這避免了「schema 開銷讓估算虛高導致無謂壓縮」的問題。

**SDK 意涵**：第一版可以只用 `len(text) // 4` 粗估，但一定要在 API 回傳後更新真實值，否則會陷入不必要的壓縮迴圈。

### 1.2 壓縮觸發條件

觸發邏輯在 `ContextCompressor.should_compress()` (`agent/context_compressor.py:744-764`)：

```python
def should_compress(self, prompt_tokens: int = None) -> bool:
    tokens = prompt_tokens if prompt_tokens is not None else self.last_prompt_tokens
    if tokens < self.threshold_tokens:
        return False
    if self._ineffective_compression_count >= 2:
        return False  # 防抖保護
    return True
```

**閾值設定**：預設為 `context_length × 50%`，但有 64K token 的絕對地板（`agent/context_compressor.py:641-643`）。例如 200K 模型的閾值是 100K，但 128K 模型的閾值是 64K（不是 64K 以下）。

**防抖保護（Anti-thrashing）**：若連續兩次壓縮各自節省不到 10%，就停止壓縮並警告使用者（`agent/context_compressor.py:749-763`）。這是防止「每次壓縮只清一兩條訊息，但 token 仍超閾，再壓再超，無窮迴圈」的關鍵。

### 1.3 `StreamingContextScrubber` 的作用

**問題**：記憶片段是以 `<memory-context>...</memory-context>` XML 包裹後注入到 prompt 中（`agent/memory_manager.py:235-249`）。這些標籤不應該出現在串流回應裡，但 LLM 可能在回應中回引這些脈絡塊。

**更嚴重的問題**：正規表達式 `sanitize_context()` 是一次性（one-shot）清洗，無法跨串流 chunk 運作——開標籤 `<memory-context>` 可能在第一個 delta，關標籤 `</memory-context>` 在第五個 delta（`agent/memory_manager.py:71-79`）。

`StreamingContextScrubber` 是一個**有限狀態機**（`agent/memory_manager.py:70-233`）：

- 狀態：`_in_span`（是否在標籤內）、`_buf`（暫存可能是標籤前綴的尾端）、`_at_block_boundary`（是否在行首）。
- `feed(delta)` → 傳回可見文字，可能為空。
- `flush()` → 串流結束時排出暫存；若仍在 span 內則捨棄（`agent/memory_manager.py:155-169`）：

```python
def flush(self) -> str:
    if self._in_span:
        self._buf = ""
        self._in_span = False
        return ""  # 未閉合的 span 直接丟棄
    tail = self._buf
    self._buf = ""
    return tail
```

**設計意涵**：「寧可截斷，不可洩漏」——若 span 在串流結束前仍未閉合，整個 buffer 直接丟棄，因為把記憶脈絡塊顯示給使用者比截斷內容更糟。

**SDK 必要性**：只要你在串流輸出時注入了任何你不想給使用者看到的系統片段（記憶、工具狀態等），就需要類似的串流狀態機清洗器。

---

## 2. 壓縮（Compression）機制深度剖析

### 2.1 壓縮具體流程

`ContextCompressor.compress()` 的完整五階段（`agent/context_compressor.py:1909-2182`）：

```
Phase 1: 廉價預處理（無 LLM）
  └─ 替換舊工具結果為一行摘要
  └─ 去重重複的工具輸出
  └─ 截斷大型 tool_call 參數 JSON（保持 JSON 有效性）

Phase 2: 決定壓縮邊界
  └─ head：系統提示 + protect_first_n（預設 3）條訊息
  └─ tail：向後走累積 token，直到超過 tail_token_budget（≈ threshold × 20%）

Phase 3: LLM 總結
  └─ 呼叫 auxiliary model，產生結構化摘要
  └─ 若失敗且 abort_on_summary_failure=True → 返回原始訊息不變
  └─ 若失敗且 abort_on_summary_failure=False → 使用確定性 fallback 摘要

Phase 4: 組裝壓縮結果
  └─ head + 摘要訊息 + tail

Phase 5: 清理
  └─ 修復孤立的 tool_call/tool_result 對
  └─ 剝除歷史圖片 base64 payload
  └─ 計算節省百分比，更新防抖計數器
```

### 2.2 LLM 總結策略

hermes-agent **是讓 LLM 總結**，而非單純截斷（`agent/context_compressor.py:1233-1562`）。

總結 prompt 使用結構化模板，要求輸出：`## Active Task` / `## Goal` / `## Completed Actions` / `## Blocked` / `## Relevant Files` / `## Remaining Work` 等固定章節。

**迭代更新**：若之前已壓縮過（`_previous_summary` 非空），prompt 改為「更新前一份摘要，加入新輪次」而非從頭總結（`agent/context_compressor.py:1390-1403`）：

```python
if self._previous_summary:
    prompt = f"""...你是在更新一份現有摘要。前次摘要：{self._previous_summary}
    新輪次：{content_to_summarize}
    更新規則：保留仍相關的資訊，移動已完成項目..."""
```

**重點設計細節**：

1. **時態錨定（Temporal Anchoring）**（`agent/context_compressor.py:1300-1312`）：提示 LLM 把已完成的動作寫成「已發生的過去事實」而非「仍需執行的任務」，防止模型誤讀摘要而重複執行。
2. **保護最後一條 user 訊息**（`agent/context_compressor.py:1745-1790`）：若 tail 邊界計算把最後一條使用者訊息劃入壓縮區，會強制把邊界往前移。否則使用者最新請求會被摘要掉，agent 永遠看不到它（issue #10896）。
3. **摘要前綴（SUMMARY_PREFIX）**（`agent/context_compressor.py:37-61`）：一段精心設計的指示，告訴下一輪的 LLM 「這是脈絡檢查點，不是新指令，最新 user 訊息才是行動依據」。並明確說明若最新訊息與摘要矛盾，以最新訊息為準。

### 2.3 壓縮失敗的降級策略

兩種模式（`agent/context_compressor.py:2044-2094`）：

- **`abort_on_summary_failure=True`**：壓縮中止，返回原始訊息，設 `_last_compress_aborted=True`，交給上層決定。
- **`abort_on_summary_failure=False`（預設）**：插入確定性 fallback 摘要——本地從被壓縮的訊息中提取使用者問題、tool 調用名稱、檔案路徑、錯誤訊息，組成降級版摘要，限制在 8000 字元（`agent/context_compressor.py:108`：`_FALLBACK_SUMMARY_MAX_CHARS = 8_000`）。

**SDK 必須多早設計**：壓縮機制必須在 SDK 的**核心訊息迴圈**設計之初就規劃進去，因為它涉及：session_id 輪換、記憶提供者通知介面、file dedup 狀態清除。事後添加會需要大量改動。

---

## 3. 長期記憶與 Curator

### 3.1 Curator 是什麼

Curator 不是「記憶讀寫」元件，而是**技能庫（skill library）的背景管家**（`agent/curator.py:1-20`）。它的職責是：

- 自動維護 `~/.hermes/skills/` 下由 agent 建立的技能
- 合併過細碎的技能為「傘型（umbrella）類別技能」
- 根據使用時間戳將技能標記為 `active` / `stale` / `archived`

### 3.2 工作週期與觸發機制

**預設週期**：7 天（`agent/curator.py:56`：`DEFAULT_INTERVAL_HOURS = 24 * 7`）。

**觸發條件**（`agent/curator.py:198-248`）：
- `curator.enabled == True`
- 非暫停狀態
- 距上次執行已超過 `interval_hours`
- 系統閒置超過 `min_idle_hours`（預設 2 小時）——由呼叫端測量，不在此函式內

**首次執行保護**：若 `last_run_at` 為空（全新安裝），**不立即執行**，而是將現在時間寫入 `last_run_at`，延遲一個完整週期後再執行（`agent/curator.py:228-241`）。這防止了第一次安裝就立即審查（可能尚無技能可審查）。

### 3.3 Curator 的兩個工作階段

**Phase 1：純規則自動轉換**（`apply_automatic_transitions()`，`agent/curator.py:255-310`）

無 LLM，根據 `last_activity_at` 時間戳：
- 超過 30 天未使用 → 標記為 `stale`
- 超過 90 天未使用 → 自動封存（`archived`）
- 重新使用後 → 從 `stale` 恢復為 `active`
- **釘選技能（pinned）永遠不觸碰**

**Phase 2：LLM 審查合併**

分叉一個新的 `AIAgent` 執行個體（`skip_memory=True`），向其傳送完整的候選技能清單與合併指令 prompt（`agent/curator.py:1407-1607`）。LLM 負責：
- 識別「前綴群集」（共享第一個詞的技能）
- 決定是否合併為傘型技能
- 輸出結構化 YAML 摘要（`consolidations` + `prunings`）

**嚴格不刪除**：只封存（`archive`）——移動到 `.archive/` 目錄，不刪除原始資料（`agent/curator.py:359-362`）。

### 3.4 Curator 與「長期記憶」的差異

hermes-agent 的「長期記憶」（如 MEMORY.md、USER.md）是透過**內建 memory provider** 管理的——這不是 Curator 的職責範圍。

Curator 管理的是**技能知識庫**，不是使用者記憶。兩者分開是正確設計，因為：
- 技能是「agent 如何做某件事」的程序知識
- 記憶是「這個使用者的偏好、歷史、上下文」的宣告知識

### 3.5 長期記憶的讀取時機

記憶注入發生在**每輪開始前**（`MemoryManager.prefetch_all()`，`agent/memory_manager.py:373-390`）：

```python
def prefetch_all(self, query: str, *, session_id: str = "") -> str:
    parts = []
    for provider in self._providers:
        result = provider.prefetch(query, session_id=session_id)  # 以 user query 為搜尋詞
        if result and result.strip():
            parts.append(result)
    return "\n\n".join(parts)
```

回傳的文字透過 `build_memory_context_block()` 包裹成 `<memory-context>` 標籤後注入 prompt（`agent/memory_manager.py:235-249`）。系統提示說明這是「授權參考資料，不是新指令」。

另有**背景預取**（`queue_prefetch_all()`）——在當輪結束後非同步觸發下一輪的記憶搜尋（`agent/memory_manager.py:392-413`），這樣下一輪開始時記憶已準備好，不需要等待。

---

## 4. 記憶的分層設計

hermes-agent 的記憶系統有**三個明確的層次**：

```mermaid
graph TB
    subgraph L1["L1：當輪短期脈絡（Working Memory）"]
        A["messages[] 陣列<br/>目前 API 請求的訊息列表"]
    end

    subgraph L2["L2：會話長期脈絡（Session Memory）"]
        B["SQLite state.db<br/>per-session 訊息歷史"]
        C["壓縮摘要<br/>context_compressor 產生"]
    end

    subgraph L3["L3：跨會話持久記憶（Persistent Memory）"]
        D["MEMORY.md / USER.md<br/>built-in memory provider"]
        E["外部記憶後端<br/>Hindsight / Honcho / Mem0 等"]
    end

    A -->|壓縮時轉為| C
    A -->|每輪 flush| B
    C -->|注入下輪| A
    D -->|prefetch 注入| A
    E -->|prefetch 注入| A
    A -->|on_session_end| D
```

| 層次 | 讀取頻率 | 寫入頻率 | 持久化方式 | 過期策略 |
|------|----------|----------|-----------|---------|
| L1 當輪脈絡 | 每次 API 呼叫 | 每輪增長 | 記憶體 | 壓縮時截斷 |
| L2 SQLite 會話史 | session resume 時 | 每輪 append | SQLite WAL | 壓縮輪換（parent/child session） |
| L3 持久記憶 | 每輪 prefetch | 每輪 sync / session end | 檔案系統 / 外部 API | 永久，由 provider 自訂 |

**關鍵設計點**：
- L1 → L2 透過**壓縮輪換**（session_id rotation）實作「輪換而非截斷」。壓縮後不是替換舊訊息，而是結束舊 session、建立子 session，保持完整歷史可查（`agent/conversation_compression.py:507-553`）。
- L3 的讀取通過 `<memory-context>` fence 保持語義隔離，LLM 清楚知道哪些是長期記憶、哪些是即時對話。

---

## 5. SDK 最小記憶系統建議

### 5.1 第一版可以多簡單？

**非加不可（Tier 1）**：

1. **Token 計數（粗估）**：`len(text) // 4`，必要時從 API 回傳校正。
2. **上下文截斷**：最簡版只需在超過閾值時從頭部截斷最舊訊息，保留 N 條最新訊息。
3. **串流清洗器**：若你會在串流輸出中夾帶系統資料，就需要狀態機清洗。

**有了更好（Tier 2）**：

4. **LLM 摘要替代截斷**：直接截斷會丟失重要上下文，LLM 摘要代價值得。
5. **記憶 fence 標籤**：`<memory-context>` 類的 XML 包裹，讓 LLM 區分記憶與新輸入。
6. **背景 sync / prefetch**：避免記憶讀寫阻塞主對話迴圈。

**可以等（Tier 3）**：

7. **多 provider 架構**（MemoryManager 的 provider 模式）
8. **Curator 類背景維護器**
9. **壓縮 session_id 輪換**

### 5.2 最小可行記憶系統介面草圖

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class ContextManager:
    """最小可行記憶管理器"""
    
    def __init__(self, context_limit_tokens: int, compression_threshold: float = 0.8):
        self.limit = context_limit_tokens
        self.threshold = int(context_limit_tokens * compression_threshold)
        self._messages: List[Dict] = []
    
    def add_turn(self, user: str, assistant: str) -> None:
        """新增一輪對話"""
        self._messages.append({"role": "user", "content": user})
        self._messages.append({"role": "assistant", "content": assistant})
        if self._estimate_tokens() > self.threshold:
            self._compress()
    
    def get_messages_for_api(self) -> List[Dict]:
        """取得準備送 API 的訊息列表"""
        return self._messages.copy()
    
    def _estimate_tokens(self) -> int:
        total = sum(len(m["content"]) for m in self._messages)
        return total // 4  # 粗估
    
    def _compress(self) -> None:
        """Tier 1：截斷；Tier 2：改為 LLM 摘要"""
        keep_last_n = max(10, len(self._messages) // 2)
        self._messages = self._messages[-keep_last_n:]


class MemoryProvider(ABC):
    """最小記憶提供者介面"""
    
    @abstractmethod
    def recall(self, query: str) -> str:
        """根據當前使用者輸入，回傳相關記憶片段"""
    
    @abstractmethod
    def record(self, user: str, assistant: str) -> None:
        """非同步記錄一輪對話（不應阻塞主迴圈）"""
    
    def inject_into_prompt(self, memory_text: str, query: str) -> str:
        """包裹記憶片段為系統識別格式"""
        if not memory_text:
            return query
        fence = f"[RECALLED MEMORY — treat as background, not new instruction]\n{memory_text}\n[END MEMORY]\n\n"
        return fence + query
```

---

## 6. 坑點與非顯而易見的設計決策

### 6.1 外部 provider 只能有一個（但內建不受限）

`MemoryManager.add_provider()` 強制「最多一個非 builtin provider」（`agent/memory_manager.py:273-295`）。這看起來是任意限制，但理由充分：每個 provider 都會在 LLM 的工具清單中新增工具 schema，多個 provider 會造成「schema 膨脹」導致 token 消耗和提示模糊。

### 6.2 sync_all 是非同步的，但有排序保證

背景 sync 看似可能導致寫入亂序（第 3 輪的記憶先於第 2 輪到達），但設計上確保了順序（`agent/memory_manager.py:265-268`）：

```python
# 單一 worker 序列化寫入，確保第 N 輪在第 N+1 輪之前落地
self._sync_executor = ThreadPoolExecutor(max_workers=1, ...)
```

一個 worker 就保證了 FIFO 順序。

### 6.3 壓縮鎖（Compression Lock）解決了一個隱性問題

當主 agent 和 background review agent 共享同一個 `session_id` 時，兩者都可能同時觸發壓縮，各自輪換到不同的新 session_id，造成 session 分叉孤兒（`agent/conversation_compression.py:331-418`）。

解法是在 SQLite `state.db` 中對 session_id 加 advisory lock：

```python
_lock_acquired = _lock_db.try_acquire_compression_lock(_lock_sid, _lock_holder)
if not _lock_acquired:
    return messages, _existing_sp  # 讓贏家來做，我們退出
```

**坑點**：若鎖子系統因版本不匹配而拋出 `AttributeError`（而非 sqlite3.Error），原本的 fail-safe 不會觸發，系統會陷入無窮迴圈。正確的設計是 **fail-open**（無鎖但繼續執行）而非 fail-closed（拋例外停止）（`agent/conversation_compression.py:362-392`）。

### 6.4 SUMMARY_PREFIX 有完整的歷史版本管理

每次修改壓縮摘要的前綴文字（`SUMMARY_PREFIX`），舊版本必須加入 `_HISTORICAL_SUMMARY_PREFIXES` 元組（`agent/context_compressor.py:63-82`）。這是因為：

- 老的摘要可能透過 `/resume` 載入到新會話中
- 如果不剝除舊前綴就追加新前綴，舊指示（如「resume exactly from Active Task」這種會強迫 agent 繼續舊任務的文字）會嵌入摘要正文永遠存在

**SDK 必做**：任何你向 LLM 注入的控制文字，都需要版本管理和清除機制。

### 6.5 tool_call/tool_result 對的完整性修復

壓縮後的訊息列表可能有孤立的 tool 呼叫（call 在中間被壓縮了，但 result 在 tail 留著）。hermes-agent 在每次壓縮後都會執行修復（`agent/context_compressor.py:1618-1676`）：

- 孤立的 tool result → 刪除
- 孤立的 tool call（result 被刪了）→ 插入 stub result `"[Result from earlier conversation — see context summary above]"`

這是 API 的硬性要求（Anthropic/OpenAI 都要求 call/result 配對），不做修復會導致 400 錯誤。

### 6.6 壓縮時的 session_id 輪換時序

session_id 更新有兩個獨立的傳播路徑（`agent/conversation_compression.py:513-530`）：

1. `gateway.session_context.set_current_session_id()`：路由層，決定後續請求路由到哪個 session
2. `hermes_logging.set_session_context()`：日誌層，決定日誌標籤顯示哪個 session_id

兩者分開是因為日誌失敗不應影響路由更新。但若兩者的時序不同步（例如在同一輪次的後半段），同一輪次的前半日誌和後半日誌會顯示不同 session_id，造成調試混亂（issue #34089）。

**SDK 教訓**：session_id 是一個「橫切關注點（cross-cutting concern）」，凡是涉及 session 識別的地方（路由、日誌、記憶寫入、工具狀態）都必須同步更新，且應該有一個統一的「session_id 更新事件」而非分散通知。

### 6.7 確定性 fallback 摘要的長度上限

LLM 摘要失敗時的 fallback 有嚴格的字元上限（`agent/context_compressor.py:108`：`_FALLBACK_SUMMARY_MAX_CHARS = 8_000`，每條訊息 `_FALLBACK_TURN_MAX_CHARS = 700`）。這乍看是隨意數字，但背後邏輯是：

- fallback 摘要本身也會佔用 token，若不限制，大型 fallback 可能讓壓縮後的脈絡仍然超過閾值
- 8K 字元 ≈ 2K token，足夠提供基本連續性錨點而不會過度消耗空間

---

## 小結

hermes-agent 的記憶與脈絡管理是一個**高度防禦性設計**的系統，幾乎每個決策都有明確的失敗模式背景。最值得 SDK 建造者借鑑的核心原則是：

1. **永遠 fail-open**：任何記憶子系統的失敗都不應阻塞主對話迴圈
2. **語義隔離勝於混合注入**：用 fence 標籤把記憶和新輸入分開，讓 LLM 知道各塊的語義
3. **壓縮是核心設計而非事後補丁**：必須在 SDK 架構早期就規劃好 session 輪換、provider 通知介面
4. **任何注入的控制文字都需要版本管理**：`SUMMARY_PREFIX` 的歷史版本陣列就是明證
