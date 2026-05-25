# 深入剖析：`networking/websocket_chat`（WebSocket 聊天室）

## 為何選它
這是 repo 中把 **WebSocket 低階 API** 講得最完整的 demo：同時示範「在 Godot 內自架 WS server」與「連到 server 的 client」，並手動處理握手、輪詢（poll）、收發訊息與廣播。相較於 `websocket_minimal`（最小連線）與 `websocket_multiplayer`（接 Multiplayer API），本 demo 直接操作 `TCPServer` / `WebSocketPeer`，最能看懂底層運作。

## 檔案組成

| 檔案 | 角色 |
|---|---|
| `networking/websocket_chat/websocket/WebSocketServer.gd` | **可重用** server 包裝類（核心） |
| `networking/websocket_chat/websocket/WebSocketClient.gd` | 可重用 client 包裝類 |
| `networking/websocket_chat/server.gd` | server UI / 業務（呼叫 WebSocketServer） |
| `networking/websocket_chat/client.gd` | client UI / 業務（呼叫 WebSocketClient） |
| `*.tscn`（chat / client / server / combo） | 四種運行場景，`combo.tscn` 同畫面開 server+client 方便測試 |

## Server 核心剖析 `websocket/WebSocketServer.gd`
`WebSocketServer.gd:1` 用 `class_name WebSocketServer` 註冊為可重用節點，對外只暴露三個訊號：`message_received` / `client_connected` / `client_disconnected`（`WebSocketServer.gd:4-6`），把底層細節封裝起來。

### 連線握手的狀態推進
WebSocket 連線要先 TCP 連上、（可選）TLS 握手、再做 WS 握手。demo 用一個 `PendingPeer` 內部類追蹤每個尚未完成握手的連線（`WebSocketServer.gd:20-29`），其 `_connect_pending`（`WebSocketServer.gd:133-169`）是一個逐幀推進的狀態機：
- TCP 還沒連上 → 繼續等（`WebSocketServer.gd:146-147`）。
- 非 TLS：TCP 就緒就建 `WebSocketPeer` 並 `accept_stream(tcp)`（`WebSocketServer.gd:148-152`）。
- TLS：先用 `StreamPeerTLS.accept_stream` 包一層，握手完成再 `accept_stream(tls)`（`WebSocketServer.gd:154-169`）。
- WS 進入 `STATE_OPEN` → 配發隨機 peer id、emit `client_connected`（`WebSocketServer.gd:138-142`）。

逾時保護：`connect_time + handshake_timout < now` 就丟棄（`WebSocketServer.gd:104-106`）。

### 主迴圈 `poll()`（手動輪詢，無自動回呼）
`WebSocketServer.gd:91-130`，每幀由 `_process` 呼叫（`WebSocketServer.gd:172-173`）：
1. 接受新 TCP 連線、加入 pending（`WebSocketServer.gd:95-98`）。
2. 推進所有 pending 握手，逾時的移除（`WebSocketServer.gd:102-114`）。
3. 對每個已連線 peer 呼叫 `poll()`；若狀態不再 OPEN 就 emit `client_disconnected` 並移除（`WebSocketServer.gd:116-123`）。
4. 把收到的每個封包 emit `message_received`（`WebSocketServer.gd:125-126`）。

> 關鍵心智模型：**WebSocketPeer 不會主動推事件，必須每幀 `poll()`**，否則收不到資料、也偵測不到斷線。

### 收發與廣播 `send()` / `get_message()`
`send()`（`WebSocketServer.gd:48-65`）用 peer_id 的正負號做路由語意：
- `peer_id == 0`：廣播給所有人。
- `peer_id < 0`：廣播但排除 `-peer_id` 那位（例：不回傳給發訊者）。
- `peer_id > 0`：點對點。

並依型別自動選 `send_text`（字串）或 `var_to_bytes` 後 `send`（其他變數，`WebSocketServer.gd:55-65`）。`get_message`（`WebSocketServer.gd:68-76`）用 `was_string_packet()` 判斷是字串還是二進位，二進位用 `bytes_to_var` 還原。

## Client 業務層 `client.gd`
`client.gd:1` 繼承 `Control`，把 WebSocketClient 的訊號接到 UI：連上/斷線/收訊息分別寫進 RichTextLabel（`client.gd:13-25`）；送出與連線按鈕呼叫 `_client.send()` / `_client.connect_to_url()`（`client.gd:28-50`）。這示範了「把可重用網路類包裝層」與「畫面業務層」分離的乾淨分工。

## 可遷移的設計重點
1. **WebSocketPeer 是 poll 驅動**：每幀 `poll()` 是收訊、偵測斷線的前提。
2. **握手是多階段狀態機**：TCP → (TLS) → WS，用 PendingPeer 逐幀推進並設逾時。
3. **peer_id 正負號當廣播語意**（0=全體、負=排除一人）是簡潔的路由技巧。
4. **字串 vs 二進位**用 `was_string_packet()` / `var_to_bytes` 對稱處理。
5. **把 server/client 封裝成 `class_name` 節點**，對外只露訊號與少數方法，業務層不碰底層。

## 對照學習
- 最小連線：`networking/websocket_minimal`。
- 接高階 Multiplayer API：`networking/websocket_multiplayer`。
- RPC + MultiplayerSpawner 的高階多人：`networking/multiplayer_bomber`。
