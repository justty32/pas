# Freedom-Hunter 架構概覽

## 專案基本資訊

| 項目 | 內容 |
|------|------|
| 引擎 | Godot 4.3 |
| 語言 | GDScript |
| 類型 | 3D 動作 RPG（仿 Monster Hunter 風格） |
| 授權 | GPL-3.0-or-later |
| 特色 | 合作 & PvP 線上多人遊戲、Android 觸控/陀螺儀支援 |

---

## 目錄結構

```
Freedom-Hunter/
├── project.godot          # 引擎設定：主場景、Autoload、Input Map
├── src/                   # 所有 GDScript 原始碼
│   ├── global.gd          # [Autoload] 全域狀態、場景切換、玩家管理
│   ├── multiplayer/
│   │   ├── networking.gd  # [Autoload] ENet 多人網路、RPC 玩家同步
│   │   └── lobby.gd       # 大廳 UI 邏輯
│   ├── entities/
│   │   ├── entity.gd      # 基底類別：HP/耐力/狀態機/傷害/復活
│   │   ├── player.gd      # 玩家控制、輸入、互動、裝備
│   │   └── monster.gd     # 怪物 AI：巡邏/狩獵/視野/導航
│   ├── equipment/
│   │   ├── equipment.gd   # 裝備基底
│   │   ├── weapon.gd      # 武器：銳利度系統、傷害碰撞
│   │   └── armour.gd      # 防具：防禦值
│   ├── items/
│   │   ├── item.gd        # 道具基底（name/icon/quantity/rarity）
│   │   ├── consumable.gd  # 消耗品基底
│   │   ├── collectibles.gd# 收集品
│   │   └── consumables/   # Potion, Whetstone, Meat, Barrel, CannonBall, Firework
│   ├── interact/
│   │   ├── cannon.gd      # 互動：大砲
│   │   ├── chest.gd       # 互動：寶箱
│   │   ├── gathering.gd   # 互動：採集點
│   │   ├── monster drop.gd# 互動：怪物死亡後掉落物
│   │   ├── mushroom.gd    # 互動：蘑菇
│   │   └── NPC.gd         # 互動：NPC
│   ├── interface/
│   │   ├── hud/           # debug/interact/inventory/names/notification/players_list/respawn
│   │   ├── items_bar.gd   # 快捷物品列
│   │   ├── shop.gd        # 商店介面
│   │   └── status.gd      # 狀態列（HP/耐力/銳利度）
│   ├── inventory.gd       # 物品欄（Panel，拖放 UI）
│   ├── camera.gd          # 第三人稱相機（Yaw/Pitch/縮放/陀螺儀）
│   └── ...
└── data/
    ├── scenes/            # .tscn 場景檔（main_menu, game, player, monsters, hud...）
    └── images/items/      # 道具圖示
```

---

## 系統架構圖

```
[project.godot]
    ├── Autoload: global   → GlobalAutoload (global.gd)
    └── Autoload: networking → NetworkingAutoload (networking.gd)

GlobalAutoload
    ├── start_game()       → 載入 game.tscn + hud.tscn，生成 Dragon，創建本地玩家
    ├── add_player()       → 實例化 PlayerScene，設定 multiplayer_authority
    ├── add_monster()      → 實例化怪物 Scene
    └── stop_game()        → 清除遊戲，回到主選單

NetworkingAutoload (ENet)
    ├── server_start()     → 建立伺服器，呼叫 global.start_game()
    ├── client_start()     → 建立客戶端連線
    ├── register_player()  [@rpc] → 雙向同步新玩家資訊給所有 peer
    └── players {}         → {peer_id: Player 節點} 字典

Entity (CharacterBody3D)        ← 基底
    ├── HP 系統（hp / hp_max / hp_regenerable / hp_regeneration）
    ├── 耐力系統（stamina / stamina_max，getter/setter 自動 emit signal）
    ├── 狀態機（AnimationTree + AnimationNodeStateMachinePlayback）
    │     └── 主狀態：idle-loop / movement / attack / rest / death
    │         └── 移動子狀態：walk-loop / run-loop / dodge / jump / falling
    ├── 異常狀態（ailments: {element: timestamp}）
    ├── damage() → 計算防禦後扣血，死亡觸發 die() RPC
    ├── move_entity() → 依狀態機速度移動，含重力與撞牆邏輯
    └── RPC 同步：_update_hp / _update_stamina / died / respawn

Player (extends Entity)
    ├── _physics_process()  → 讀取鍵盤/觸控輸入，計算相機相對移動方向
    ├── _input()            → 攻擊/閃避/跳躍/奔跑/互動/物品欄
    ├── equipment {}        → {"weapon": Weapon, "armour": {slot: Armour}}
    ├── inventory: Inventory → 消耗品物品欄
    ├── get_defence()       → 累加所有防具 strength
    ├── interact_with_nearest() → 取最近 Area3D("interact" group) 互動
    └── set_equipment()     → 掛載模型到 Skeleton3D BoneAttachment3D

Monster (extends Entity)
    ├── _physics_process()  → AI 狀態機：target==null→find→scout, target!=null→hunt
    ├── field_of_view       → 120° FOV，line_of_sight() 用 Raycast 確認視線
    ├── NavigationAgent3D   → 路徑導航（NavMesh）
    ├── scout()             → 隨機目標巡邏
    ├── hunt_target()       → 距離分級：>10=跑、>5=走、≤5=攻擊
    ├── check_fire_collision() → RayCast3D 確認火焰是否打到玩家
    └── died()              → 切換腳本為 monster drop.gd（可採集）

Weapon (extends Equipment)
    ├── sharpness []        → [Sharp{type,value,max_val}] 從 purple 到 red 7 級
    ├── blunt(amount)       → 消耗銳利度（從最高級往下扣）
    ├── sharpen(amount)     → 回復銳利度（Whetstone 使用）
    └── _on_body_entered()  → 碰撞體偵測傷害觸發點

Inventory (extends Panel)
    ├── items []            → Item 陣列
    ├── add_item()          → 堆疊同名物品或放入空槽
    ├── use_item()          → 呼叫 item.use(player)，數量歸零則移除
    ├── Slot (inner class)  → 拖放容器，_get_drag_data / _can_drop_data / _drop_data
    └── ItemStack (inner class) → TextureRect 顯示圖示與數量

Camera (extends Camera3D)
    ├── Yaw/Pitch 節點分離  → 水平旋轉(yaw_node) + 垂直旋轉(pitch_node)
    ├── 輸入來源            → 滑鼠移動 / 觸控拖曳 / 手把搖桿 / 陀螺儀
    ├── lerp 平滑            → yaw: delta*10, pitch: delta*5
    └── camera_zoom()       → 沿相機方向插值縮放距離
```

---

## 多人同步機制

| 機制 | 實作方式 |
|------|----------|
| 傳輸層 | `ENetMultiplayerPeer` |
| 玩家加入 | `register_player` @rpc("any_peer") - 伺服器廣播，客戶端接收 |
| HP 同步 | `_update_hp` @rpc("call_remote") - authority 端在 hp_changed signal 觸發 |
| 耐力同步 | `_update_stamina` @rpc("call_remote") |
| 死亡同步 | `died()` @rpc("any_peer", "call_local") |
| 復活同步 | `respawn()` @rpc |
| 怪物 AI | 只在伺服器/單人端執行（`is_multiplayer_authority()` 控制） |
| 怪物移動 | 目前有 TODO 標記，transform 同步尚未完整實作 |

---

## 異常狀態（Ailment）系統

```
Entity.ailments = {element_name: timestamp_msec}

觸發：damage(dmg, reg, element) → ailments[element] = Time.get_ticks_msec()
效果：各實體自行 connect ailment_added signal

Player._on_ailment_added("fire"):
    → 播放火焰粒子 ($Flames)
    → effect_over_time(1秒間隔, 3次, damage(10, 0.5), 清除ailment + 停粒子)
```

Monster 的 weakness 字典定義對各元素的易傷倍率（目前 damage 計算 TODO）。

---

## 互動（Interact）系統

```
Area3D (group="interact") ← 放置於各互動物件子節點

Player.get_nearest_interact()
    → $interact.get_overlapping_areas()  ← 玩家互動範圍 Area3D
    → 過濾 group="interact"
    → 按距離排序取最近
    → interact.get_parent().interact(player, interact_area)

死亡怪物：monster.died() 後 call_deferred("set_script", "monster drop.gd")
    → 動態替換腳本，使怪物屍體成為可採集的互動點
```

---

## 銳利度系統（Sharpness）

```
7 個銳利度等級（從高到低）：
purple → white → blue → green → yellow → orange → red

blunt(amount): 從最高等級往下消耗
sharpen(amount): 從最低缺少處往上補滿（Whetstone 道具效果）
HUD 顯示：sharpness/fading AnimationPlayer 播放對應顏色動畫
```

---

## Level 1 分析完成狀態

- [x] README 與技術棧確認（Godot 4.3 / GDScript / ENet）
- [x] 目錄結構完整掌握
- [x] 核心模組職責分析：Entity / Player / Monster / Weapon / Inventory / Camera
- [x] 多人同步機制理解
- [x] 異常狀態系統
- [x] 互動系統
- [x] 銳利度系統
