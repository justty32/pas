# Freedom-Hunter 分析總結

## 專案定位

一款以 **Godot 4.3 + GDScript** 開發、仿 Monster Hunter 風格的 3D 動作 RPG 開源遊戲。支援合作/PvP 線上多人、Android 觸控操作，目前處於早期開發階段，核心框架完整但許多進階功能仍是 TODO。

---

## 整體架構一覽

```
Autoload（全域單例）
├── global.gd        → 場景生命週期、玩家/怪物實例管理
└── networking.gd    → ENet 多人、RPC 協議、玩家同步

實體系統（CharacterBody3D 繼承鏈）
├── Entity           → HP/耐力/AnimationTree/傷害/復活（多人RPC）
├── Player           → 輸入/裝備/互動/物品欄
└── Monster          → AI（巡邏↔狩獵）/導航/視野/火焰攻擊

道具系統（純 GDScript 物件，非 Node）
├── Item             → 基底（名稱/圖示/數量/稀有度）
├── Consumable       → Template Method（use → effect）
│   ├── Potion       → 回血 + drink 動畫
│   ├── Whetstone    → 回復武器銳利度 + whetstone 動畫
│   ├── Meat         → 永久增加最大耐力上限
│   ├── Barrel       → 生成爆炸桶（連鎖爆炸機制）
│   ├── CannonBall   → 裝填大砲發射 / 丟到地上
│   └── Firework     → 生成煙火節點自動升空
└── Collectible      → 採集材料

介面系統
├── Inventory        → Panel + 拖放 Slot，堆疊管理
├── ItemsBar         → 快捷物品列（5格，觸控滑動切換）
├── Shop             → ShopItem signal buy → Player.buy_item()
└── HUD              → status / interact浮標 / notification佇列 / respawn

多人系統（ENet）
├── 伺服器/客戶端架構，無 relay
├── register_player @rpc：加入時雙向廣播所有玩家資訊
├── HP/耐力：Signal → lambda → @rpc("call_remote")
└── 怪物AI只在 authority 端（伺服器）執行
```

---

## 五大設計亮點

### 1. 動畫驅動的遊戲邏輯
狀態機（AnimationTree）不只是播動畫，它**同時驅動移動速度**：`move_entity()` 讀取當前動畫狀態節點來決定速度倍率（walk=5, run=7.5, dodge=8），動畫狀態即是遊戲狀態。

### 2. 雙層 AnimationPlayer 音畫同步
玩家的 `AnimationsWithSounds` 把骨骼動畫 track 與 audio track 打包在同一個 AnimationPlayer 中，音效時機（如喝藥水 t=0.35s 才響）精確到幀，且可純用編輯器調整，不需改程式碼。

### 3. 動態腳本替換（Monster 死後變採集點）
```gdscript
call_deferred("set_script", preload("res://src/interact/monster drop.gd"))
```
怪物死後不從場景移除，而是直接替換腳本，使節點搖身成為採集互動物件，既省效能又保留屍體位置。

### 4. MultiMesh 草地（1000 株一次 Draw Call）
Planter + GrassFactory + Shader 三層分工：Planter 在編輯器中以 @tool 即時預覽，每株草的寬高、搖擺幅度存在 INSTANCE_CUSTOM.rgba 傳入 Shader；Worley 噪聲模擬陣風流過，根部固定頂部搖擺，強風時 ROUGHNESS 下降產生閃光感。

### 5. 空白鍵語境感知操作
跑步中按空白 = 跳躍；靜止/走路時按空白 = 閃避，完全符合 Monster Hunter 原作設計，一鍵兩用靠 `movement/conditions/running` 狀態分流。

---

## 系統完成度評估

| 系統 | 完成度 | 備註 |
|------|--------|------|
| Entity 基底（HP/耐力/狀態機/傷害） | ★★★★★ | 完整 |
| 玩家移動/閃避/跳躍 | ★★★★☆ | 右攻擊動畫缺失 |
| 怪物 AI（巡邏/狩獵/視野） | ★★★★☆ | 移動 RPC 未實作 |
| 道具/消耗品系統 | ★★★★★ | 完整且可擴充 |
| 物品欄（拖放/堆疊） | ★★★★★ | 完整 |
| 武器銳利度系統 | ★★★☆☆ | 銳利度未影響傷害（TODO） |
| 防具/技能/寶石系統 | ★☆☆☆☆ | 資料結構宣告，完全未實作 |
| 多人同步 | ★★★☆☆ | 怪物移動未同步（TODO） |
| 商店/NPC | ★★★★☆ | 完整，NPC 有隨機轉頭行為 |
| 相機系統 | ★★★★★ | 含陀螺儀/觸控/手把 |
| 草地 Shader | ★★★★★ | 完整的 Worley 風場效果 |
| 元素弱點/傷害計算 | ★★☆☆☆ | 資料結構在，計算未套用 |
| 大砲/爆炸桶/煙火 | ★★★★☆ | 完整，連鎖爆炸機制完善 |

---

## 已知問題彙整

| 問題 | 位置 |
|------|------|
| 右攻擊動畫不存在，按右鍵實際播左攻擊 | `player.gd:101`, `entity.gd:342` |
| 怪物移動 transform RPC 被注解掉 | `entity.gd:218` |
| 銳利度未影響武器傷害 | `weapon.gd:93` `get_weapon_damage()` |
| 怪物元素弱點未套用到傷害計算 | `monster.gd:41-48` |
| 防具 skills/gems 完全未實作 | `armour.gd:7-8` |
| NavigationAgent debug_enabled=true（正式版應關） | `dragon.tscn:715` |
| 大廳伺服器 register 邏輯被注解 | `networking.gd:31-34` |
| Weapon.player 依賴固定路徑 `$"../../../.."` | `weapon.gd:41` |

---

## 對開發者的參考價值

| 想學什麼 | 對應系統 |
|---------|---------|
| Godot 多人 ENet 架構 | `networking.gd` + `global.gd` |
| AnimationTree 雙層狀態機 | `dragon.tscn` + `male.tscn` |
| 動畫內嵌音效同步 | `AnimationsWithSounds` in `male.tscn` |
| MultiMesh + Shader 草地 | `planter.gd` + `grass.gdshader` |
| 道具 Template Method 設計 | `consumable.gd` → 各 consumables/ |
| 物品欄拖放 UI | `inventory.gd` Slot/ItemStack |
| 世界空間→螢幕空間 UI | `interact.gd` `unproject_position()` |
| 動態腳本替換技巧 | `monster.gd:76` `set_script()` |
| Worley 噪聲實作 | `grass.gdshader:44-56` |
