# 多人網路系統 深入分析

## 架構概覽

```
[Autoload: networking]  NetworkingAutoload (networking.gd)
    ├── ENetMultiplayerPeer            ← Godot 4 內建 UDP 多人框架
    ├── Lobby (lobby.gd)               ← HTTP 大廳伺服器（可選）
    └── players: {peer_id: Player}     ← 玩家節點字典

[Autoload: global]  GlobalAutoload (global.gd)
    ├── 場景生命週期管理
    └── 玩家/怪物實例化
```

---

## ENet 連線流程

### 伺服器端（server_start）

```gdscript
# networking.gd:25-40
func server_start(port: int, username=null, host=null) -> void:
    peer = ENetMultiplayerPeer.new()
    peer.create_server(port)
    multiplayer.multiplayer_peer = peer
    unique_id = peer.get_unique_id()            # 伺服器 ID 通常為 1
    set_process_mode(PROCESS_MODE_ALWAYS)        # 確保暫停時仍處理網路
    global.start_game(username)                 # 先啟動遊戲場景
    players[unique_id] = global.local_player   # 登記自己
    multiplayer.peer_disconnected.connect(...)
    multiplayer.peer_connected.connect(...)
```

### 客戶端（client_start）

```gdscript
# networking.gd:44-54
func client_start(ip: String, port: int, username: String) -> void:
    peer = ENetMultiplayerPeer.new()
    peer.create_client(ip, port)
    multiplayer.multiplayer_peer = peer
    unique_id = peer.get_unique_id()            # 客戶端 ID 由伺服器分配
    multiplayer.connected_to_server.connect(_connected_to_server.bind(username))
    multiplayer.connection_failed.connect(_connection_failed.bind(ip, port))
    multiplayer.server_disconnected.connect(_server_disconnected)
```

```gdscript
# 連線成功後
func _connected_to_server(username: String):
    global.start_game(username)                 # 建立本地場景
    players[unique_id] = global.local_player
    rpc("register_player", unique_id, username, null)  # 向伺服器報到
```

---

## 玩家同步協議（register_player）

這是整個多人同步的核心 RPC：

```gdscript
# networking.gd:85-102
@rpc("any_peer") func register_player(id, username, transform) -> void:
    if multiplayer.is_server():
        # 1. 驗證使用者名稱不重複
        if game.find_child("player_spawn").has_node(username):
            rpc_id(id, "_register_error", "Username is in use")
            peer.disconnect_peer(id)
            return
        
        # 2. 向新玩家廣播所有現有玩家資訊
        for peer_id in players:
            var player = players[peer_id]
            rpc_id(id, "register_player", peer_id, player.name, player.transform)
        
        # 3. 向所有現有玩家廣播新玩家
        for peer_id in players:
            rpc_id(peer_id, "register_player", id, username, transform)
        
        # 4. 在伺服器自己的場景建立新玩家節點
        players[id] = global.add_player(username, id, transform)
    else:
        # 客戶端：直接建立收到的玩家
        players[id] = global.add_player(username, id, transform)
```

**同步順序說明**：
```
新客戶端 C 連線到伺服器 S（已有玩家 A、B）

C → S: register_player(C_id, "C", null)

S → C: register_player(A_id, "A", A.transform)   ← 告知 C 關於 A
S → C: register_player(B_id, "B", B.transform)   ← 告知 C 關於 B
S → A: register_player(C_id, "C", null)           ← 告知 A 關於 C
S → B: register_player(C_id, "C", null)           ← 告知 B 關於 C
S 自己：global.add_player("C", C_id)              ← 伺服器建立 C 的節點
```

---

## RPC 裝飾器語義

| 函數 | 裝飾器 | 含義 |
|------|--------|------|
| `register_player` | `@rpc("any_peer")` | 任何 peer 都可以呼叫（客戶端→伺服器） |
| `_register_error` | `@rpc("any_peer")` | 伺服器→客戶端錯誤通知 |
| `died` | `@rpc("any_peer", "call_local")` | 任何人呼叫，且呼叫者自己也執行 |
| `respawn` | `@rpc` | 預設：authority 呼叫，所有 peer 執行 |
| `_update_hp` | `@rpc("call_remote")` | 只在遠端執行（不在呼叫者本地重複執行） |
| `_update_stamina` | `@rpc("call_remote")` | 同上 |

---

## 玩家節點的 Authority 設計

```gdscript
# global.gd:24-29
static func add_entity(entity_name, scene, spawn, id=1):
    var entity = scene.instantiate()
    entity.set_multiplayer_authority(id)   ← 設定誰是這個節點的 authority
    entity.set_name(entity_name)
    spawn.add_child(entity)
    return entity
```

**規則**：
- 每個 Player 節點的 authority = 那個玩家的 peer_id
- `is_multiplayer_authority()` → 只有本地玩家對自己的節點回傳 true
- 怪物 authority = 1（伺服器），單人模式 authority 也是 1

**基於 Authority 的行為分歧**：
```gdscript
# player.gd:171-175
func resume_player():
    var has_peer := multiplayer.has_multiplayer_peer()
    var enable := not has_peer or is_multiplayer_authority()
    set_process_input(enable)       # 只有自己的角色接收輸入
    set_physics_process(enable)     # 只有自己的角色做物理運算

# monster.gd:58-65
func setup_monster():
    var singleplayer_or_server := not multiplayer.has_multiplayer_peer() or is_multiplayer_authority()
    await NavigationServer3D.map_changed
    set_physics_process(singleplayer_or_server)   # 怪物 AI 只在伺服器跑
```

---

## 大廳（Lobby）系統

### HTTP 大廳伺服器（lobby.gd）

```gdscript
const BASE_URL = "https://elinvention.ovh"

# 玩家可在此瀏覽公開伺服器列表
func servers_list(object, method):
    http.request(BASE_URL + "/fh/cmd.php?cmd=list_servers")
    http.connect("request_completed", Callable(object, method))

# 伺服器可選擇向大廳註冊（讓其他人看到）
func register_server(host, port):
    http.request(BASE_URL + "/fh/cmd.php?cmd=register_server&hostname=%s&port=%s&max_players=10" % [host, port])
```

### 大廳 UI（lobby-ui.gd）

```gdscript
# 設定儲存至 user://multiplayer.conf（ConfigFile）
func save_config():
    config.set_value("global", "username", ...)
    config.set_value("client", "host", ...)
    config.set_value("client", "port", ...)
    config.set_value("server", "host", ...)
    config.save(CONF_FILE)

# 每 10 秒自動刷新伺服器列表
$lobby/refresh.start()   # Timer，10 秒間隔
```

大廳 UI 提供兩種連線方式：
1. **直連**：手動輸入 IP:Port
2. **大廳瀏覽**：從 HTTP 伺服器取得公開伺服器清單，點擊連線

---

## 斷線處理

```gdscript
# networking.gd:73-82
func _on_network_peer_disconnected(id) -> void:
    if id in players:
        global.remove_player(players[id].name)   # 從場景移除玩家節點
        players.erase(id)
    else:
        print("Peer ID %d disconnected" % id)    # 可能是連線中的匿名 peer

# global.gd:49-51
func remove_player(player_name):
    players_spawn.get_node(player_name).queue_free()
    player_disconnected.emit(player_name)

# 伺服器斷線
func _server_disconnected() -> void:
    stop_and_report_error("Server disconnected.")
```

`stop_and_report_error` 流程：
```gdscript
func stop_and_report_error(message) -> void:
    global.stop_game()                    # 清除遊戲場景
    await get_tree().tree_changed         # 等待場景切換完成（change_scene 是異步的）
    $"/root/main_menu/multiplayer".show()
    $"/root/main_menu/multiplayer".report_error(message)  # 顯示錯誤對話框
```

---

## 已知限制與 TODO

| 問題 | 位置 | 說明 |
|------|------|------|
| 怪物移動不同步 | entity.gd:210-219 | transform RPC 被注解掉（`#rpc("transform", tf)`） |
| 大廳註冊被注解 | networking.gd:31-34 | register_server/register_player 邏輯有 yield 殘留（Godot 3 語法） |
| 客戶端輸入無驗證 | networking.gd | 任何 peer 都可以呼叫 register_player，沒有伺服器端驗證輸入合法性 |
| 怪物 authority 固定 = 1 | global.gd:33 | 若伺服器斷線，怪物 AI 會停止（沒有 authority 轉移機制） |
