# Mod 目標：讓閒置 NPC 自己找椅子坐下 — 可行性偵察

> 日期：2026-05-23　狀態：偵察完成，待選定範圍後實作

## 結論（TL;DR）

- 遊戲**原生沒有**「動態找椅子坐下」的 AI。坐著的 NPC 是**靜態**做法：把 `npc_prototype.defaultAnim` 設成坐姿（`chu_sit`/`chusheng_sit`）再手動擺位。
- **純 Workshop 做不到全域自主版**（無法 hook 閒置狀態、無法掃場景椅子、無法即時控制動畫）→ 必須 **BepInEx**。
- 但所需 building blocks 都存在，BepInEx 版**可行**，主要風險是「坐姿動畫是否在共用 animator」與「椅子座位對齊」。

## 已確認的 building blocks

### 1. 坐姿動畫（clip 存在）
db1.txt 的 `npc_prototype` 列，`defaultAnim` 欄位實際用到：
- `chu_sit` — 例：NPC 165125「张强2」(`32019` 行)，坐姿（椅/凳）
- `chusheng_sit` — 例：165249「阿古罗」、165278「郭怀瑾」
- `dazuo` / `DaZuo` — 打坐（地上盤腿），全遊戲常見
- 休閒系統(`npc_xiuxiananim`)的動畫名是 `freetime1~6`、`once1/2`、`3303_free_jiaoliu` 等（站姿閒置動作，**不含坐**）

> ⚠️ 風險：`chu_sit` 可能只存在於特定角色 rig。要先驗證它是否在**通用 NPC animator** 上，否則對任意 NPC 播 `chu_sit` 會無效。

### 2. 椅子物件（場景裡有名字）
掃 `StreamingAssets/Scene/*.assetbundle` 的 strings，找到物件命名：`Chair`、`ChairV`、`FChair`、`QCHair`、`Stool`（大小寫混雜）。
→ 可用**名稱子字串 "Chair"/"Stool"** 在場景中搜尋椅子 GameObject。

### 3. 導航到物件的函式
`AutomatManager.Script_NavMoveUnitToCloseGameObjectFront`（`AutomatManager.cs:14443`）：
- 簽名 `(npcId, nameSubstring, ?, needHide, interval)`
- 在 `WorldManager.m_WorldGameObjects` 找 key 含子字串且 active 的最近物件，導航到其正面；找不到再 `GameObject.Find(name)` 兜底。

⚠️ 但 `m_WorldGameObjects` / `m_WorldGameObjectsWithTag` **不是場景自動填充**，只由腳本函式手動登記（`AutomatManager.cs:13706~15012`）。所以椅子預設**不在**裡面。BepInEx 版需自己掃場景（`Resources.FindObjectsOfTypeAll<Transform>()` 過濾名字含 "Chair"），不能直接靠這函式。

### 4. 閒置行為的注入點
- `NpcXiuXianAnimComponent`（休閒動作元件，`SweetPotato/NpcXiuXianAnimComponent.cs`）= NPC 閒置時定時播動畫的元件。`PlayAnim()`(`:137`) 是注入點。
- `NpcController.ManagedUpdate`(`:147`) / `ConfigComponentFinished`(`:652`) = 掛新行為的位置。
- 移動：`UnitController.AutoFindWay(dest, stopDist, speed, cb, state)`（`UnitController.cs:2396`）。
- 播任意動畫：`m_AnimationComponent.PlayAnim(animName)`。

## 三種實作範圍（待選）

### A. 完整自主版（BepInEx）— 最忠於需求，工作量大
Harmony patch NPC 閒置更新；流程：
1. NPC 進入閒置一段時間 → 在半徑內掃場景椅子物件（名字含 Chair/Stool）。
2. 挑最近、未被占用的椅子 → `AutoFindWay` 走過去。
3. 到位後 snap 位置+朝向到座位錨點 → `PlayAnim("chu_sit")`。
4. 占用表避免兩個 NPC 搶同椅；玩家互動/戰鬥時起身。
- **風險**：①`chu_sit` 是否通用 ②座位對齊（每種椅高度/朝向不同）③效能（掃物件要快取）。
- 量級：估 300~500 行 plugin + 反覆現場調參。

### B. 在地坐姿 MVP（BepInEx）— 可靠、快
不找椅子，直接讓閒置 NPC **原地**偶爾播 `dazuo`/坐姿動畫（就地盤腿）。
- 砍掉「找椅子+導航+對齊」三個風險點，1~2 小時可出 demo。
- 缺點：不是「找椅子」，是「原地坐」。

### C. 腳本單一 NPC（Workshop，無需 BepInEx）
做一個**自己的新 NPC**，用 AutomatScript 圖：`NavMoveUnitToCloseGameObjectFront(自己, "Chair", …)` → 播坐姿 → 由觸發器/互動啟動。
- 只對你放的 NPC + 特定椅子有效，**不是世界既有 NPC 的自主行為**。
- 但完全在官方框架內，可上 Workshop。

## 建議路線
先做 **B 當技術驗證**（確認坐姿動畫能對任意 NPC 播），同時驗證 A 的兩個風險點；若 `chu_sit` 通用且座位對齊可控，再升級成 **A**。C 適合「只想要場景裡有個會去坐的 NPC」的輕量需求。

## 待驗證清單 → 實機驗證結果（2026-05-23 完成）

- [x] **坐姿動畫是否通用** → **否，但 `chusheng_sit` 夠通用**。實機 `HaveAnim` 統計：`chusheng_sit`=5/8、`idle`=8/8，而 `chu_sit`/`dazuo`/`sit`/`sitnew`=**0/8**（原本預設的 `chu_sit`/`dazuo` 在路人身上根本沒有，這是先前怎麼播都看不到的主因）。
- [x] **判斷 NPC 有無某 clip 的正確方法** → **`AnimationComponent.HaveAnim()`**（`:779`，真查 `animationClipDescription`）。**不可用 `PlayAnim` 回傳值**：它載不到 clip 時 fallback `CrossFade` 也回 `true`（`:646`，三分支都 `result=true`），會說謊。
- [x] **椅子方案** → **放棄**。~10GB 資產裡 "Chair" 字串僅約 19 個，實機掃 0 張 → 改「原地坐下」（方案 B）。
- [x] **定格坐姿手法** → `PlayAnim(clip, 0f, 0.99f)`（仿本體對 defaultAnim 的做法 `NpcController.cs:1257`）。
- [x] **維持坐姿不被蓋掉** → 坐下前 `m_NpcXiuXianAnimComponent.ExitXiuXian()`、壓 `m_AutomatAIScript.m_bUpdateable=false`，每幀 `!IsAnimName(clip)` 就重播。
- [x] **閒置判定** → 自己計時（`MoveComponent.IsNavStop()` 持續 N 秒）；本體 `XiuXian` 系統會自動播 `freetime1~6`，不衝突（我們坐下時先 ExitXiuXian）。

### 最終做法（已實作於 `SitOnChairMod/SitOnChairMod.cs` 0.2.0，實機確認「全都正常」）
方案 B「原地坐下」：閒置且 `HaveAnim("chusheng_sit")` 的 NPC 隨機坐下、定格、壓 AI 維持，坐滿 `SitDuration` 或被打擾/劇情就起身。實機觀察：多個路人 NPC 自主坐下、坐姿正常、互動/戰鬥會起身。
</content>
