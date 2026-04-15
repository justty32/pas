# T-Engine 4 — game/ 目錄原始碼詳細分析

> 本文件涵蓋 `game/` 目錄下所有子系統，包含引擎啟動、模組（boot/example/ToME）、Addon 與第三方函式庫。

---

## 目錄

1. [game/loader/ — 引擎啟動器](#1-gameloader--引擎啟動器)
2. [game/profile-thread/ — 在線 Profile 執行緒](#2-gameprofile-thread--在線-profile-執行緒)
3. [game/thirdparty/ — 第三方函式庫](#3-gamethirdparty--第三方函式庫)
4. [game/engines/te4-1.7.6/data/ — 引擎靜態資產](#4-gameengineste4-176data--引擎靜態資產)
5. [game/modules/boot — 啟動/主選單模組](#5-gamemodulesboot--啟動主選單模組)
6. [game/modules/example — 回合制範例模組](#6-gamemodulesexample--回合制範例模組)
7. [game/modules/example_realtime — 即時制範例模組](#7-gamemodulesexample_realtime--即時制範例模組)
8. [game/modules/tome-1.7.6 — Tales of Maj'Eyal](#8-gamemodustome-176--tales-of-majeyal)
   - 8.1 [模組入口（init.lua / load.lua / settings.lua）](#81-模組入口)
   - 8.2 [核心類別（mod/class/）](#82-核心類別-modclass)
   - 8.3 [介面混入（mod/class/interface/）](#83-介面混入-modclassinterface)
   - 8.4 [AI 系統（mod/ai/）](#84-ai-系統-modai)
   - 8.5 [資料層（data/）](#85-資料層-data)
   - 8.6 [地區（data/zones/）](#86-地區-datazones)
9. [game/addons/ — Addon 系統](#9-gameaddons--addon-系統)

---

## 1. game/loader/ — 引擎啟動器

`game/loader/` 是整個引擎的第一段 Lua 代碼，在任何模組載入前執行。

### pre-init.lua

- **LuaJIT 初始化**：嘗試啟用 JIT（`jit.on()`，最佳化等級 2），失敗則降級到標準 Lua
- **RNG 工具函數**：注入全局 `rng.*` 函數（`mbonus`、`avg`、`table*`）
- **Table 序列化**：`table.serialize()` / `table.unserialize()` 用於遊戲狀態持久化
- **安全強化**：停用危險 OS 函數（`os.execute`、`os.getenv`、`os.remove`、`os.rename`）

### init.lua

**引擎發現與載入**：
- 掃描 `/engines/` 目錄尋找可用引擎版本（支援目錄型或 `.teae` 壓縮包）
- 解析版本字串（`engine/version.lua` 或 `name-X.Y.Z.teae` 檔名格式）
- 選取指定版本（預設 "LATEST"），掛載到虛擬根目錄

**模組 Loader 鏈**（自訂 `package.loaders`）：
- `te4_loader()`：實作 Addon **Superload** 能力
  - 載入原始模組後，依 `__addons_superload_order` 順序在 `/mod/addons/<addon>/superload/` 找覆蓋
  - `loadPrevious()` 讓 superload 取得原始模組
- Stub DLC：`.lua.stub` 映射到預編譯 DLCD 內容

**設計模式**：
- **三層初始化**：pre-init（VM 設定）→ init（引擎選取）→ engine/init（遊戲設定）
- **Plugin 架構**：Addon superloading 讓模組在不修改基礎代碼的情況下擴充任何模組

---

## 2. game/profile-thread/ — 在線 Profile 執行緒

獨立執行緒，負責維持與 te4.org 伺服器的連線，避免阻塞主遊戲迴圈。

### init.lua

執行緒初始化與生命週期管理。

### Client.lua

**雙 TCP Socket 架構**：
- 主 Socket（port 2257/2260）：請求/回應（認證、角色存檔、設定）
- Push Socket（port 2258/2260）：伺服器主動推送事件
- 元伺服器查詢：`profiles.te4.org:2240` 動態路由

**主要功能**：

| 功能 | 方法 |
|------|------|
| 認證 | Steam token（`STM_`）或帳號密碼（`AUTH`/`PASH`）|
| 角色管理 | `orderRegisterNewCharacter()`、chardump 兩段上傳 |
| 設定同步 | `orderSetConfigsBatch()` — 批次設定 + zlib 壓縮 |
| 雜湊驗證 | 模組/Addon MD5 批次校驗 |
| Addon 管理 | 版本上傳、Steam Workshop 整合、更新檢查 |
| 微交易 | Steam/TE4 購物車建立與完成 |
| 心跳 | 60 秒 keep-alive |

**設計模式**：Producer-Consumer（主執行緒推送命令，profile-thread 推回事件）、Non-blocking I/O（`socket.select()`）

### UserChat.lua

- 事件路由：talk、whisper、成就廣播、序列化資料
- 頻道管理：join/part 追蹤
- 好友列表：`FriendJoin`/`FriendPart` 事件

---

## 3. game/thirdparty/ — 第三方函式庫

| 函式庫 | 用途 |
|--------|------|
| `socket/` | TCP/UDP 網路（http, ftp, smtp, url 協議層） |
| `moonscript/` | MoonScript 編譯器（CoffeeScript 語法 → Lua 轉譯）|
| `jit/` | LuaJIT 位元碼生成與反組譯（bc, v, dis_* 多架構）|
| `lpeg/` | Lua PEG 解析表達式語法庫 |
| `lxp/` | Lua XML 解析器 |
| `remdebug/` | 遠端偵錯框架 |
| `algorithms/` | `binarysearch`、`unionfind`、`shuffling`、排序、Trie |
| `Json2.lua` | JSON ↔ Lua table 互轉 |
| `ltn12.lua` | LuaSocket 過濾器/泵浦（stream 資料管線）|
| `md5.lua` | MD5 雜湊（包裝 native md5.core）|
| `sha1.lua` | SHA1 雜湊 |
| `tween.lua` | 動畫 tween（緩動函數值插值）|
| `binpack.lua` | 2D 矩形打包（MAXRECTS，圖集生成）|
| `mime.lua` | MIME 編碼（Base64、Quoted-Printable）|
| `slt2.lua` | 簡易 Lua 模板引擎 |
| `vector.lua` | 2D 向量數學 |

---

## 4. game/engines/te4-1.7.6/data/ — 引擎靜態資產

| 目錄 | 內容 |
|------|------|
| `gfx/` | 材質圖集、粒子效果、UI 主題（dark/metal/parchment/stone/tombstone 等）|
| `gfx/shaders/` | GLSL 著色器（distortion/volumetric/advanced 等品質等級）|
| `gfx/ui/` | 按鈕、邊框、進度條、圖示 |
| `gfx/particles/` | 粒子特效精靈圖 |
| `font/` | TrueType + 位元圖字型，含 CJK 字集（ja_JP/ko_KR/zh_hans/zh_hant）|
| `locales/engine/` | 引擎 UI 翻譯（zh_hans、zh_hant、ja_JP、ko_KR）|
| `sound/ui/` | UI 互動音效（點擊、懸停、確認）|
| `keybinds/` | 預設按鍵設定 |

---

## 5. game/modules/boot — 啟動/主選單模組

**用途**：遊戲啟動時顯示的主選單模組（`is_boot=true`）。

**繼承**：`engine.GameEnergyBased + GameMusic + GameSound`（完整音訊/即時引擎）

**初始化流程**：`init.lua` → `load.lua` → `class/Game` → 顯示 MainMenu 對話框

**特色**：
- 即時模式（8 tick/s）
- 載入背景材質、Web tooltip、Discord Presence、shader 支援
- Player 繼承自 NPC（非獨立），使用 demo AI（`ai="player_demo"`）
- FOV 距離預計算用不同係數（除以 17 vs 14）
- 約 117 個 Lua 檔（21 mod + 96 data）

---

## 6. game/modules/example — 回合制範例模組

**用途**：最小化 RPG 模板，展示回合制地城探索 + 玩家 vs NPC 戰鬥。

**繼承**：`engine.GameTurnBased + engine.interface.GameTargeting`

**核心流程**：

```
tick() → engine.GameTurnBased.tick()
Player.act(): cooldowns → regen → timedEffects → 消耗 energy
  → game.paused = true（等待輸入）
```

**類別結構**：

```
Game (439行) ← GameTurnBased + GameTargeting
  Player ← Actor + PlayerRest/Run/Hotkeys/Mouse
  NPC    ← Actor + ActorAI
  Actor  ← Entity + ActorStats/Talents/Life/FOV/Resource...
  Grid
  interface/Combat.lua
```

**資料層**：30+ Lua 檔（talents、damage_types、birth、zones、grids、NPCs）

**顯示**：32×32 ASCII 圖磚，底部 80% 為 log，右側 20% 為快捷鍵/NPC 列表

**Birth 流程**：選擇 "base" + "role" 描述符，合併屬性、技能、裝備到角色

---

## 7. game/modules/example_realtime — 即時制範例模組

**用途**：與 `example/` 內容完全相同，但改為即時制（energy-based）。

**關鍵差異**：

| 項目 | example（回合制）| example_realtime（即時制）|
|------|-----------------|--------------------------|
| 繼承 | `GameTurnBased` | `GameEnergyBased` |
| tick 回傳 | `true`（有暫停邏輯）| `false`（永不暫停）|
| 即時設定 | 無 | `core.game.setRealtime(20)` |
| 玩家行動 | useEnergy → paused=false | 無暫停邏輯 |

---

## 8. game/modules/tome-1.7.6 — Tales of Maj'Eyal

ToME 是引擎上最完整的遊戲實現，作者 Nicolas Casalini（DarkGod），GPL v3 授權。

### 8.1 模組入口

#### init.lua

- 模組元資料：名稱 "Tales of Maj'Eyal"、版本 {1,7,6}、引擎 {1,7,6,"te4"}
- 145+ 載入提示（lore 與玩法提示）
- 40+ 載入背景圖
- 字型套件選擇系統
- Profile 統計欄位：artifacts、characters、deaths、uniques、scores、lore、escorts

#### load.lua

- 載入 `/mod/settings.lua` 設定
- ASCII 模式支援（低端渲染）
- 地圖設定（平滑捲動、陣營危險等級）
- **揹包系統定義**（16 個 slot）：
  - MAINHAND、OFFHAND、PSIONIC_FOCUS
  - BODY、CLOAK、HEAD、HANDS、FEET
  - FINGER（×2）、NECK、LITE、BELT、TOOL、QUIVER
  - GEM、QS_MAINHAND、QS_OFFHAND（快速換組）
- 裝備娃娃定義（視覺裝備預覽）
- 鍵位、Resolver、存檔 MD5 設定

#### settings.lua

| 設定 | 說明 |
|------|------|
| `autosave` | 自動存檔開關 |
| `smooth_move` | 平滑移動等級（0-3）|
| `twitch_move` | 瞬間移動模式 |
| `tile_size` | 圖磚尺寸（48/64 像素）|
| `weather_effects` | 天氣效果 |
| `day_night` | 日夜循環 |
| `smooth_fov` | FOV 平滑 |
| `log_lines` | 訊息列數（5）|

#### resolvers.lua

- `resolveObject(e, filter, do_wear, tries)` — 進階物品生成：
  - 支援預生成物品（`_use_object`）、指定唯一品（`defined`）、自訂清單（`base_list`）
  - 反魔法相容性檢查
  - 最多 5 次重試
  - `autoreq`：強制升級/學技能以符合需求
  - `alter`：生成後修改函數

---

### 8.2 核心類別 (mod/class/)

#### Game.lua — 主遊戲控制器

**繼承**：`engine.GameTurnBased + GameMusic + GameSound + GameTargeting`

| 欄位 | 說明 |
|------|------|
| `visited_zones` | 已探索地區 |
| `calendar` | 遊戲內日曆（122 天/年、167 天/月）|
| `tooltip`, `tooltip2` | 提示框管理 |
| `flyers` | 飄字傷害顯示 |
| `bignews` | 成就/事件通知 |
| `nicer_tiles` | 增強圖磚渲染 |

ToME 特有：Hook 系統（`"ToME:run"`, `"ToME:runDone"`）、動態視窗標題、Shader gamma 校正

#### GameState.lua — 遊戲會話狀態

**繼承**：`engine.Entity + mod.class.interface.WorldAchievements`

跨關卡/地區的持久狀態管理：

| 欄位 | 說明 |
|------|------|
| `world_artifacts_pool` | 尚未生成的任務神器 |
| `unique_death` | 已擊殺的唯一怪 |
| `boss_killed` | Boss 擊殺計數 |
| `stores_restock` | 商店補貨計數器 |
| `birth` | 角色出生描述符資料 |

關鍵方法：`generateRandart(data)`（隨機神器生成）、`createRandomBossNew(base, data)`（隨機精英 Boss 生成）、`entityFilter()`/`entityFilterPost()`（戰利品過濾）、`dayNightCycle()`（日夜循環）

#### Actor.lua — 所有活體實體基底（318KB）

**繼承**（15+ 介面混入）：
```
engine.Actor
engine.interface.ActorInventory
engine.interface.ActorTemporaryEffects
mod.class.interface.ActorLife
engine.interface.ActorProject
engine.interface.ActorLevel
engine.interface.ActorStats
engine.interface.ActorTalents
engine.interface.ActorResource
engine.interface.BloodyDeath
engine.interface.ActorFOV
mod.class.interface.ActorAI
mod.class.interface.ActorPartyQuest
mod.class.interface.ActorInscriptions
mod.class.interface.ActorObjectUse
mod.class.interface.Combat
mod.class.interface.Archery
```

**11 種資源池**（部分）：

| 資源 | 說明 |
|------|------|
| mana | 魔法施法 |
| stamina | 體力（物理技能）|
| vim | 惡魔/Reaver |
| equilibrium | 自然平衡（反轉值）|
| paradox | 時間悖論（反轉值）|
| positive/negative | 善/惡能量 |
| hate | 狂暴者怒氣 |
| psi | 心靈能量 |
| soul | 靈魂（上限 10，不自動回復）|
| air | 呼吸空氣 |

**三層戰鬥系統**：

| 層級 | 屬性 |
|------|------|
| 物理 | `combat_atk`, `combat_dam`, `combat_physcrit`, `combat_physspeed` |
| 法術 | `combat_spellcrit`, `combat_spellspeed` |
| 心靈 | `combat_mindcrit`, `combat_mindspeed` |

#### Player.lua — 玩家角色

**繼承**：`mod.class.Actor + PlayerRest/Run/Hotkeys/Mouse/Slide + PlayerStats/DumpJSON/Explore/QuestPopup + PartyDeath`

| 欄位 | 說明 |
|------|------|
| `descriptor` | 出生描述符（種族/職業/世界）|
| `died_times` | 各死因死亡次數 |
| `puuid` | 角色 UUID（在線同步）|
| `damage_log`, `damage_intake_log` | 戰鬥統計 |

特有功能：
- 出生後 callback 系統（`registerOnBirth`）
- UUID 跨存檔追蹤
- JSON 角色卡匯出
- 新學技能自動分配快捷鍵
- 三頁快捷鍵列 + 教學系統

#### NPC.lua — AI 控制實體

**繼承**：`mod.class.Actor`

**關鍵特性**：

| 機制 | 說明 |
|------|------|
| `seen_by(who)` | 目標傳遞：含 FOV/距離/時間驗證，防止 chain aggro 濫用 |
| `checkAngered(src, set, value)` | 陣營反應修改（-200 到 200 範圍）|
| `reaction_actor` | 每個 Actor 的個別關係追蹤 |
| `summon_time` | 召喚物倒計時（歸零則消失）|
| `shove_pressure` | 推擠動量計數器 |
| `automaticTalents()` | 戰鬥狀態感知的自動技能系統 |
| `rank` | NPC 等級（2=普通、3=稀有、3.5+=Boss）|

NPC 死亡：rank 4+ 掉落 Rod of Recall；觸發成就；陣營反應降低

#### World.lua — 世界管理器

**繼承**：`engine.World + mod.class.interface.WorldAchievements`

- `unlocked_shimmers`：外觀解鎖（Shimmer 裝甲/武器顏色）
- `gainAchievement(id, src)`：依難度前綴（`EXPLORATION_`、`NORMAL_ROGUELIKE_`、`NIGHTMARE_`…）

#### Zone.lua — 地區生成器

**繼承**：`engine.Zone`

- `_object_special_ego_rules`：可堆疊 ego 屬性（`special_on_hit` 等）
- `onLoadZoneFile(basedir)`：載入地區特有事件（events.lua）
- `doQuake(rad, x, y, check)`：地震地形重排
- `adjustComputeRaritiesLevel()`：高等級物品生成機率縮放

#### Object.lua — 物品/裝備

**繼承**：`engine.Object + ObjectActivable + ObjectIdentify + ActorTalents`

- `moddable_tile` 系列欄位：外觀自訂（神器自動生成 tile 名）
- `getRequirementDesc()`：含反魔法相容性的需求描述
- 特殊 ego 觸發：`special_on_hit`、`talent_on_*`、`on_block` 等清單追加

#### Grid.lua — 地形

**繼承**：`engine.Grid`

| 欄位 | 說明 |
|------|------|
| `door_opened` | 開門後替換的 Grid |
| `door_player_check` | 開門前顯示的對話框 |
| `change_zone` | 傳送目標地區（樓梯）|
| `air_level`, `air_condition` | 呼吸需求 |

`block_move()` 處理：門的開啟對話框、穿透能力、空氣需求檢查、地形變更事件觸發

#### Party.lua — 隊伍管理

**繼承**：`engine.Entity + PartyIngredients + PartyLore`

- `members`：Actor → 成員定義映射
- `addMember(actor, def)`：通知所有成員（`callbackOnPartyAdd`）、轉換為 PartyMember 類別、建立 leash AI 狀態
- `switchParty(new_party)`：特殊地區的多隊伍切換

#### PartyMember.lua — 隨從

**繼承**：`mod.class.NPC + PartyDeath + PlayerHotkeys + PlayerQuestPopup`

- AI 切換為 `"party_member"`，備份原始 AI 型別
- `tactic_leash`/`tactic_leash_anchor`：限制隨從活動範圍

#### Store.lua — 商店

**繼承**：`engine.Store`

- 按補貨計數器（非玩家等級）提升基礎等級
- 材料等級每 10 玩家等級縮放一次（1-5 階）
- 寶石 40% 收購價，其他 5%
- `allowStockObject(e)`：過濾任務物品與 cost=0 物品

#### WildernessGrid.lua — 未探索地區入口指示器

**繼承**：`mod.class.Grid`

- `defineDisplayCallback()`：在未訪問地區入口附加 `entrance_glow` 粒子效果

---

### 8.3 介面混入 (mod/class/interface/)

#### Combat.lua（2844 行）— 核心戰鬥系統

**主要方法**：

| 方法 | 說明 |
|------|------|
| `bumpInto(target, x, y)` | 碰撞分派（對話/攻擊/位移）|
| `attackTarget(target, damtype, mult, ...)` | 攻擊入口 |
| `attackTargetWith(target, weapon, ...)` | 單武器攻擊邏輯 |
| `attackTargetHitProcs(...)` | 命中後特效處理（特效/爆擊/閃避）|
| `combatAttack()` / `combatDefense()` | 命中/閃避計算 |
| `combatDamage()` / `combatArmor()` / `combatAPR()` | 傷害/護甲/穿透 |
| `combatPhysicalpower()` / `combatSpellpower()` / `combatMindpower()` | 三層施法力 |
| `physicalCrit()` / `spellCrit()` / `mindCrit()` | 爆擊計算 |
| `combatTalentScale(t, min, max)` | 線性技能縮放 |
| `combatTalentLimit(t, limit, min, max)` | 有上限技能縮放 |
| `grappleSizeCheck()` / `startGrapple()` | 擒抱機制 |
| `buildCombo()` / `getCombo()` | 連擊系統 |

**設計特點**：
- 階層命中 vs 防禦系統（`getTierDiff()`、`checkHit()`）
- 護甲硬韌度系統（減少護甲穿透影響）
- 武器類型訓練路徑
- 隊友受攻擊時的救援機制

#### ActorLife.lua — 生命/死亡

- `oktodie()`：檢查存活機制（T_CAUTERIZE 技能、callback）
- 殺手記功系統（`on_kill`）
- NPC 雙重死亡條件

#### ActorAI.lua（1825 行）— AI 決策

**戰術系統**（ToME 核心 AI）：

```
三步戰術評分：
1. 計算每個技能的 TACTIC WEIGHT（via aiTalentTactics()）
2. 計算各戰術的 WANT VALUE（AI 特定）
3. FINAL TACTICAL SCORE = sum(WEIGHT × WANT)，依技能等級/速度調整
```

**戰術分類**（`AI_TACTICS` 係數表）：

| 有害 | 有益 |
|------|------|
| attackarea, attack, closein | cure, heal, buff |
| escape, surrounded, disable | defend, protect, feedback |
| attackall | special, ammo |

**額外功能**：
- `aiResourceAction()`：資源補充決策
- `aiHealingAction()`：治療目標選擇
- `aiGridDamage()` / `aiGridHazard()`：環境評估
- `aiFindSafeGrid()`：安全位置尋路
- Lite/夜視/增強感知支援的視野判斷

#### ActorInscriptions.lua — 銘文系統

- 插槽式銘文（Rune/Infusion/Talon）管理
- `max_inscriptions`：插槽數（預設 3）
- 同類型最多 2 個銘文限制
- 屬性縮放（`use_stat_mod`、`use_any_stat`）
- 替換時保留快捷鍵

#### Archery.lua（878 行）— 弓箭遠程戰鬥

| 方法 | 說明 |
|------|------|
| `archeryAcquireTargets(tg, params)` | 目標+資源檢查 |
| `archeryShoot(targets, talent, tg, params)` | 投射物建立 |
| `hasArcheryWeapon(type, quickset)` | 弓箭裝備檢查 |
| `hasAmmo(type, quickset)` | 彈藥驗證 |
| `reloadRate()` / `reload()` | 換彈速度/手動換彈 |

支援：主手+副手+Psionic Focus 射手、無限彈藥屬性、多重射擊、彈藥耗盡追蹤

#### ActorObjectUse.lua — 物品使用AI整合

將物品能力包裝為技能，讓 NPC AI 能評估並使用物品：
- 支援三種物品能力類型：`use_power`、`use_simple`、`use_talent`
- `no_npc_use` / `allow_npc_use` 旗標控制 AI 使用權
- 戰術權重系統整合

#### ActorPartyQuest.lua — 隊伍任務管理

所有任務事件委派給主玩家：
- `grantQuest(quest, args)` / `setQuestStatus()` / `hasQuest()` / `isQuestStatus()`

#### PartyDeath.lua — 隊伍死亡處理

- 非主要成員死亡時切換目前玩家
- 遊戲結束判定（無合適玩家）
- Easy 模式多命、在線 profile 提交

#### PartyIngredients.lua — 食材/材料系統

- 食材定義與收集追蹤（含 INFINITY 常數支援）
- `collectIngredient(id, nb)` / `useIngredient(id, nb)` / `hasIngredient(id, nb)`

#### PartyLore.lua — 史料系統

- 史料條目發現與顯示（富文本：`[i]`、`[b]`、`[u]`）
- 模板支援（slt2 渲染）
- 發現時打斷玩家休息/奔跑
- 史料貢獻角色統計

#### PlayerStats.lua — 角色統計追蹤

- 唯一角色識別符（世界/種族/職業/難度/永久死亡）
- Profile 持久化：死亡、唯一怪擊殺、神器收集、護送任務

#### TooltipsData.lua — 提示框資料

537 行靜態常數，定義所有 UI 幫助文字：
- 資源（黃金、生命、耐力、魔力、Vim 等）
- 技能（銘文、偉業、物品技能、主動/持續/被動）
- 速度（全局/移動/施法/攻擊/心靈）
- 屬性（力量/敏捷/體質/魔法/意志/狡詐）
- 戰鬥（命中/攻擊力/傷害/護甲/穿透/爆擊）
- 防禦（疲勞/護甲硬韌度/爆擊減免/防禦/抗性）

---

### 8.4 AI 系統 (mod/ai/)

ToME 的 AI 比引擎基礎 AI 複雜得多，以下是所有 AI 腳本：

| 檔案 | AI 名稱 | 說明 |
|------|---------|------|
| `target.lua` | `target_simple`, `target_player_radius`, `target_closest` | 含 Lite/夜視的目標選取 |
| `improved_tactical.lua` | `improved_tactical` | 三步戰術評分系統（最先進 AI）|
| `improved_talented.lua` | `improved_talented_simple` | 技能使用 + 維護 + 移動 |
| `tactical.lua` | `use_tactical` | 傳統戰術決策系統 |
| `escort.lua` | `escort_quest`, `move_escort` | 護送任務 NPC（隨機停頓、逃跑）|
| `heal.lua` | `target_heal`, `dumb_heal`, `dumb_heal_simple` | 支援/治療 NPC |
| `maintenance.lua` | `maintenance` | 非戰鬥資源維護 |
| `party.lua` | `party_member`, `move_anchor` | 隊伍成員（含 leash 距離）|
| `quests.lua` | `move_quest_limmir` | 任務特定 NPC 行為 |
| `summon.lua` | `summoned`, `mirror_image` | 召喚物和鏡像複製體 |
| `shadow.lua` | `shadow` | 影子隨從（相位門、盲襲、防牆）|
| `sandworm_tunneler.lua` | `sandworm_tunneler`, `sandworm_tunneler_huge` | 沙蟲挖掘地形機制 |
| `worldnpcs.lua` | `world_patrol`, `world_hostile` | 世界地圖 NPC 巡邏/追擊 |
| `special_movements.lua` | `move_safe_grid`, `flee_dmap_keep_los` | 危險迴避移動 |

**戰術 AI 配置**（`improved_tactical`）：
- Actor 透過 `ai_tactic` table 設定各戰術的乘數
- `self_compassion`（預設 5）：自傷技能懲罰係數
- `ally_compassion`（預設 1）：友傷技能懲罰係數
- `AI_TACTICAL_RANDOM_RANGE`（預設 0.5）：隨機化範圍
- 技能需宣告 `tactical` table 指定涵蓋的戰術及其效果量

---

### 8.5 資料層 (data/)

#### 角色創建（birth/）

**選擇流程**：Campaign（世界）→ Difficulty → Permadeath → Race → Subrace → Sex → Class → Subclass

**描述符類型**：`world`、`difficulty`、`permadeath`、`race`、`subrace`、`sex`、`class`、`subclass`

**難度等級**：

| 難度 | 怪物等級 | 技能倍率 | 樓梯延遲 | 特殊 |
|------|---------|---------|---------|------|
| Easy | ×1 | ×1 | 0 | 無敵免疫、傷害-30%、治療+30% |
| Normal | ×1 | ×1 | 2 回合 | 無敵免疫 |
| Nightmare | ×1.25 | ×1.3 | 3 回合 | — |
| Insane | ×1.5+1 | ×1.7 | 5 回合 | — |
| Madness | ×2.5+2 | ×2.7 | 9 回合 | 生命×3、獵殺機制 |

**永久死亡模式**：Exploration（無限復活）、Adventure（多條命）、Roguelike（1 條命）

**職業分類**（12 大類，各含子職業）：

| 職業類 | 子職業 |
|--------|--------|
| 戰士 | Berserker、Bulwark、Archer、Brawler、Arcane Blade |
| 法師 | Alchemist、Archmage、Necromancer |
| 盜賊 | Rogue、Shadowblade、Marauder、Skirmisher |
| 天界 | Sun Paladin、Anorithil |
| 野性 | Summoner、Wyrmic、Oozemancer、Stone Warden |
| 心靈 | Mindslayer、Solipsist |
| 時空 | Chronomancer 系列 |
| 腐化 | Corruptor 系列 |
| 受詛 | Cursed 系列 |
| 冒險家 | Adventurer（全職業混合）|
| 無 / 教學 | 特殊用途 |

**種族**（8 種）：Human（Cornac/Higher）、Elf（Shalore/Thalore）、Dwarf、Halfling、Yeek、Giant、Undead（Ghoul/Skeleton）、Construct

**世界/戰役**：
- Maj'Eyal（主線）、Infinite Dungeon（無限下降）、The Arena（競技場）

#### 資源（resources.lua）

11 種資源池，各有獨立顏色、回復設定、AI 管理：

| 資源 | 特色 |
|------|------|
| Air | 窒息機制 |
| Stamina | 物理技能耗費 |
| Mana | 魔法施法（mana_pool 技能）|
| Equilibrium | `invert_values=true`（越高越不穩）|
| Vim | 惡魔能量，`restore_factor=0.8` |
| Positive/Negative | 善/惡能量，`restore_factor=0.4` |
| Hate | 狂暴者 |
| Paradox | 時空悖論，`invert_values=true` |
| Psi | 心靈能量 |
| Souls | 上限 10，不自動回復 |

#### 傷害類型（damage_types.lua）

含物理、火、冷、閃電、酸、毒、光、暗、時間等 40+ 傷害類型，各有獨立投射器與視覺顏色。

#### 陣營（factions.lua）

25+ 個陣營：Allied Kingdoms、Angolwen、Shalore、Thalore、Iron Throne、Orc Pride 系列、Sorcerers、Sher'Tul、Undead 等。

- 初始反應值由 CSV 矩陣定義（-100 到 100）
- `hostile_on_attack`：受攻擊後轉敵對

#### 技能分類（data/talents/）

13 個大類，200+ 個技能檔案：

| 類別 | 數量 | 說明 |
|------|------|------|
| `techniques/` | 40 | 物理戰鬥（combat-training、2h、dual、archery、shield 等）|
| `spells/` | 48 | 秘術魔法（fire、ice、air、stone、arcane、necromancy、temporal 等）|
| `celestial/` | 19 | 神聖力量（sun、light、chants、circles、guardian 等）|
| `psionic/` | 30 | 心靈能力（absorption、telekinetic、dreaming、solipsism 等）|
| `corruptions/` | — | 黑暗/腐化 |
| `chronomancy/` | — | 時間操縱 |
| `gifts/` | — | 野性恩賜/自然 |
| `cunning/` | — | 盜賊/潛行 |
| `cursed/` | — | 受詛/受苦 |
| `misc/` | — | 雜項 |
| `undeads/` | — | 不死生物特有 |
| `uber/` | — | 偉業技能（高階）|

**技能定義模式**：
```lua
newTalent{
    name="Fireball", type={"spells/fire",1}, mode="activated",
    points=5, cooldown=10, mana=20, range=8,
    target=function(self,t) ... end,
    action=function(self,t) ... end,
    tactical={attackarea=2, escape=1},  -- AI 戰術評分
    getDamage=function(self,t) ... end, -- 縮放函數
    info=function(self,t) ... end,      -- 提示文字
}
```

技能縮放函數：`combatTalentScale`、`combatTalentLimit`、`combatTalentSpellDamage`

---

### 8.6 地區 (data/zones/)

共 89 個地區，依用途分組：

**新手地區（Tier 1，等級 1-7）**
- Abashed Expanse（太空蟲洞）、Deep Bellow、Blighted Ruins、Heart of the Gloom、Murgol Lair（水下）、Norgos Lair、Tutorial

**前期地城（等級 7-25）**
- Daikara（火山/一般）、Old Forest（晶質/一般）、The Maze、Paradox Plane（零重力）、Lake of Nur、Last Hope Graveyard、Ruined Halfling Complex

**中期地城（等級 25-45）**
- Ardhungol、Dark Crypt（任務關鍵）、Illusory Castle（TileSet）、Briagh's Lair、Ancient Elven Ruins

**後期地城（等級 35-80）**
- Gorbat/Grushnak/Rak'shor Pride（沙漠/地下/骨頭美術風格）、Orc Breeding Pits、High Peak（10 層）

**特殊/劇情地區**
- Charred Scar（550 回合計時任務）、Eidolon Plane（零重力死亡復活）、Demon Plane（熔岩惡魔）、Dreams/Dreamscape

**城鎮/樞紐**
- Derth、Last Hope（196×80 靜態地圖）、Angolwen、Zigur、Iron Council、Gates of Morning

**特殊玩法**
- The Arena（波次戰鬥/排行榜）、Infinite Dungeon（max_level=1,000,000,000）

**使用的地圖生成器**：Roomer（最常用）、Cavern、Forest、Static、TileSet、Maze、Octopus、MapScript、GOL、Empty

**特殊地區設定**：
- 替代佈局（多次遊玩變體）：火山/一般、崩塌/一般、晶質/一般
- `tier1=true`：控制初始任務進程
- `underwater=true`：水下環境
- `zero_gravity=true`：零重力移動

---

## 9. game/addons/ — Addon 系統

### 系統架構

每個 addon 使用三種整合機制：

| 機制 | 路徑 | 說明 |
|------|------|------|
| `hooks/` | `hooks/*.lua` | 在特定遊戲事件執行代碼（非侵入式）|
| `superload/` | `superload/mod/class/*.lua` | 覆蓋基礎模組類別（深度修改）|
| `overload/` | `overload/engine/*.lua` | 替換引擎代碼 |
| `data/` | `data/` | 新增內容檔案 |

**常用 Hook 點**：`ToME:run`、`ToME:load`、`ToME:runDone`、`Entity:loadList`、`MapGenerator*:subgenRegister`、`DonationDialog:features`、`DebugMain:*`

---

### tome-addon-dev（開發工具）

**版本**：1.7.4｜**類型**：開發工具

- FSHelper：檔案系統操作輔助
- Luafish 整合：偵錯/IDE 支援
- Hook：`ToME:run` 初始化 FSHelper

---

### tome-items-vault（道具保管庫）

**版本**：1.7.6｜**類型**：跨角色物品交易（贊助功能）

- Hook：`MapGeneratorStatic:subgenRegister`（地圖中加入保管庫房間）
- Hook：`DonationDialog:features`（在贊助對話框顯示功能）
- Hook：`ToME:PlayerDumpJSON`（JSON 匯出含保管庫資料）
- 核心類別：`mod.class.ItemsVaultDLC`

---

### tome-possessors（附身者 DLC 職業）

**版本**：1.7.4｜**類型**：付費 DLC（`dlc=5`）

- 新增「Possessor」職業：可附身敵人身體，繼承其能力/屬性同時保留玩家技能
- Hook：`ToME:load` → `PossessorsDLC.hookLoad`
- 核心類別：`mod.class.PossessorsDLC`
- 包含技能、物品、地圖覆蓋資料

---

### tome-remote-designer（遠端設計器）

**版本**：1.0.0｜**類型**：開發工具（`cheat_only=true`）

- 遊戲執行中透過網頁瀏覽器即時設計/修改實體
- Hook：`ToME:runDone` 啟動設計器（若設定啟用）
- Hook：`DebugMain:generate` 加入「Remote Designer」到除錯選單
- 核心類別：`mod.class.RemoteDesigner`

---

## 總結：game/ 目錄架構關係圖

```
game/
├── loader/           ← 引擎啟動（JIT、安全、Addon superload）
├── profile-thread/   ← 非同步在線服務（TCP、認證、聊天）
├── thirdparty/       ← 第三方庫（網路、解析、加密、動畫等）
├── engines/
│   └── te4-1.7.6/
│       ├── engine/   ← 引擎核心 Lua（→ 見 engine_detail.md）
│       └── data/     ← 引擎靜態資產（圖形、字型、著色器、音效）
├── modules/
│   ├── boot/         ← 主選單（即時制 + 全音訊）
│   ├── example/      ← 回合制模板（教學用）
│   ├── example_realtime/ ← 即時制模板（教學用）
│   └── tome-1.7.6/   ← Tales of Maj'Eyal（完整遊戲）
│       ├── mod/
│       │   ├── class/         ← 核心類別（Game/Actor/Player/NPC/Party…）
│       │   ├── class/interface/ ← ToME 專用混入（Combat/Archery/ActorAI…）
│       │   ├── ai/            ← 14 個 AI 腳本（戰術/護送/影子/沙蟲…）
│       │   ├── init.lua       ← 元資料 + 145 載入提示
│       │   ├── load.lua       ← 系統初始化 + 16 槽揹包定義
│       │   ├── settings.lua   ← 使用者設定預設值
│       │   └── resolvers.lua  ← 進階物品生成
│       └── data/
│           ├── birth/         ← 職業/種族/世界 + 難度設定
│           ├── talents/       ← 13 類 200+ 技能檔案
│           ├── zones/         ← 89 個地區定義
│           ├── general/       ← 通用實體（NPC/物品/地形/商店/陷阱）
│           ├── damage_types.lua ← 40+ 傷害類型
│           ├── resources.lua  ← 11 種資源池
│           └── factions.lua   ← 25+ 個陣營
└── addons/
    ├── tome-addon-dev      ← 開發工具（FSHelper）
    ├── tome-items-vault    ← 跨角色保管庫（贊助功能）
    ├── tome-possessors     ← 附身者職業（付費 DLC）
    └── tome-remote-designer ← 即時實體設計器（開發工具）
```
