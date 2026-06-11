# Level 5: OpenClaw 擴充體系 (Plugins, Skills & MCP)

## 1. 插件架構 (Plugin System)

OpenClaw 的插件系統是其「Multi-channel」特性的根基。

### 1.1 插件註冊表 (`registry.ts`)
所有插件都必須通過 `PluginRegistry` 進行生命週期管理：
-   **發現 (Discovery)**: 從 `package.json` 的 `openclaw-plugins` 或本地目錄掃描插件。
-   **載入 (Loading)**: 支援非同步載入，並處理插件間的依賴關係。
-   **隔離**: 插件運行在受限的 `PluginContext` 中，防止插件損毀主進程。

### 1.2 鉤子機制 (Wired Hooks)
系統在關鍵執行路徑上佈置了「有線鉤子」：
-   `wired-hooks-inbound-claim`: 允許插件「認領」入站訊息（例如 Telegram 插件認領 Telegram 訊息）。
-   `wired-hooks-llm`: 允許插件攔截 LLM 的輸入輸出（例如進行即時翻譯或安全過濾）。
-   `wired-hooks-reply-payload-sending`: 在訊息真正發送給使用者前進行最後的格式化。

## 2. 技能系統 (Skills)
-   **原子化工具**: Skills 是 Agent 可以呼叫的最小功能單元。
-   **MCP 整合**: OpenClaw 深度支援 **Model Context Protocol (MCP)**，這使得它能無縫接軌現代 AI 生態中的外部工具伺服器。

## 3. 多平台適配 (Channels)
-   **抽象化介面**: 所有的通訊平台（Telegram, Discord, Slack 等）都被抽象為 `ChannelPlugin`。
-   **雙向轉譯**: 
    -   **Inbound**: 將平台特定的訊息格式轉為 OpenClaw 的 `MsgContext`。
    -   **Outbound**: 將 Agent 的 `ReplyPayload` 轉回平台特定的格式（支援多媒體、按鈕等）。

---

# Level 6: 穩定性與診斷 (Infrastructure)

## 1. 事件循環監控 (Health Monitor)
-   `server/event-loop-health.ts`: 即時監控 Node.js 事件循環的延遲。如果延遲過高，系統會自動標記為 `UNHEALTHY` 並通知負載均衡器或自動重啟。

## 2. 診斷追蹤 (Diagnostic Trace)
-   內建了詳細的 **Timeline Span** 機制，能記錄每個請求在每個階段（Auth, LLM, Skills）消耗的精確時間，這對調優 Agent 的反應速度至關重要。
