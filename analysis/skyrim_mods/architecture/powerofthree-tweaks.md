# powerofthree's Tweaks (v1.15.1)

## 定位

SKSE plugin，本質是一包**引擎層級的修補與微調集合**。它幾乎沒有 Papyrus 內容——主體是一顆 native DLL（`po3_Tweaks.dll`），直接在 runtime hook/patch 遊戲引擎，修掉一票 crash 與 bug，順帶做一些行為調整與效能優化。

對外的 Papyrus 面**極小**：整個 `po3_Tweaks.psc`（來源 `Required/source/scripts/po3_Tweaks.psc`，共 47 行）只暴露**一個**公開函式：

```papyrus
;returns whether the following tweak is enabled
bool Function IsTweakInstalled(String asTweak) global native
```
（`Required/source/scripts/po3_Tweaks.psc:46`）

也就是說：它不是給 mod 作者拿來「呼叫功能」的 library，而是一個**背景修補器**。`IsTweakInstalled()` 唯一的用途是讓別的 mod 在 runtime 詢問「某項 tweak 有沒有開」，以便決定要不要自己再補一次。所有實際邏輯都在 DLL 裡，`.psc` 開頭那段大註解（`Required/source/scripts/po3_Tweaks.psc:2`–`44`）就是這顆 DLL 完整的 tweak 清單。

Nexus #51073（`fomod/info.xml`）。它與 JContainers 那種「補資料結構給別人用」的 library 不同——JContainers 是被別人 `import` 的依賴，而 po3 Tweaks 是裝了就生效、別人通常不感知的隱形修補層。

## 檔案結構

來源：`~/skyrim_mods/powerofthree's Tweaks FOMOD Installer/`

這是 **FOMOD installer 格式**，不是攤平好可直接拖進 `Data/` 的目錄樹：

```
powerofthree's Tweaks FOMOD Installer/
├── fomod/
│   ├── info.xml              ← Name / Author / Version=1.15.1 / Nexus #51073
│   └── ModuleConfig.xml      ← 安裝腳本（決定哪些檔案最終落到哪）
├── Required/                 ← 不論 SE/AE 都會裝（共用 Papyrus）
│   ├── scripts/po3_Tweaks.pex
│   └── source/scripts/po3_Tweaks.psc
├── SE/SKSE/Plugins/          ← 二選一：Special Edition v1.5.97 用
│   ├── po3_Tweaks.dll        (約 1.03 MB)
│   └── po3_Tweaks.pdb        (約 23.8 MB 除錯符號)
└── AE/SKSE/Plugins/          ← 二選一：Anniversary Edition v1.6.629+ 用
    ├── po3_Tweaks.dll        (約 1.04 MB)
    └── po3_Tweaks.pdb        (約 23.9 MB 除錯符號)
```

關鍵點：`SE/` 與 `AE/` 各有一份**不同的 DLL**，因為 SE（1.5.97）與 AE（1.6.x）兩條引擎分支的記憶體位址/結構佈局不同，native plugin 必須各自編譯。FOMOD 的存在就是為了根據玩家的遊戲版本，自動只裝對的那一顆。`.pdb` 是除錯符號檔（讓 crash log 能解析成函式名），體積遠大於 DLL 本身；裝不裝不影響功能，只影響崩潰時的可讀性。

## 內容：tweak 清單（共 45 項）

以下完整逐項列出 `Required/source/scripts/po3_Tweaks.psc:2`–`44` 註解中的每一個 tweak，並分為四類。註：原始註解未分類，分類為本文歸納；少數項目跨類（如「Cast Added Spells on Load」既修 bug 也改行為），歸入主要性質。

### 一、穩定性 / Crash 修正

| Tweak | 說明（推斷） |
|---|---|
| Distant Ref Load Crash | 遠距 reference 載入導致的崩潰 |
| Light Attach Crash | 光源附掛到物件時的崩潰 |
| Skinned Decal Delete | 帶蒙皮 decal 刪除時的崩潰/錯誤 |

### 二、引擎 bug 修正

| Tweak | 說明（推斷） |
|---|---|
| Map Marker Placement Fix | 地圖標記放置錯誤 |
| Restore 'Can't Be Taken Book' Flag | 還原「不可拿取書籍」旗標被引擎吞掉的行為 |
| Projectile Range Fix | 投射物射程計算錯誤 |
| CombatToNormal Dialogue Fix | 由戰鬥轉回平常時的對話狀態錯誤 |
| Cast Added Spells on Load | 載入存檔後重新施放被加上的常駐法術（修「buff 掉了」） |
| Cast No-Death-Dispel Spells on Load | 載入後重放「死亡不解除」類法術 |
| IsFurnitureAnimType Fix | 家具動畫類型判定錯誤 |
| No Conjuration Spell Absorb | 召喚系法術不該被法術吸收（修錯誤吸收） |
| EffectShader Z-Buffer Fix | 特效 shader 的深度緩衝錯誤 |
| ToggleCollision Fix | `tcl` 主控台指令行為修正 |
| Jumping Bonus Fix | 跳躍加成計算錯誤 |
| Toggle Global AI Fix | `tai`（全域 AI 開關）行為修正 |
| VR CrosshairRefEvent Fix (VR only) | VR 準星 ref 事件修正（僅 VR 版） |

### 三、Gameplay 行為微調

多數是**選擇性**改變既有行為，偏好向工具/QoL，而非平衡性改動。

| Tweak | 說明（推斷） |
|---|---|
| Use Furniture In Combat | 允許在戰鬥中使用家具 |
| Offensive Spell AI | 改善 NPC 攻擊性法術的 AI |
| Load EditorIDs | runtime 保留 EditorID（讓主控台可用 EditorID 定址，預設引擎只剩 FormID） |
| Breathing Sounds | 呼吸聲相關 |
| Faction Stealing | 派系所屬物的偷竊判定 |
| Voice Modulation | 語音調變 |
| Game Time Affects Sounds | 遊戲時間流速影響音效 |
| Dynamic Snow Material | 動態雪材質 |
| Disable Water Ripples On Hover | 滑鼠懸停時不產生水波紋 |
| Screenshot Notification To Console | 截圖通知改印到主控台 |
| No Attack Messages | 抑制攻擊類訊息 |
| Sit To Wait | 坐下時可等待 |
| Disable God Mode | 停用無敵模式（`tgm`） |
| No Hostile Spell Absorb | 敵對法術不觸發法術吸收 |
| Grabbing Is Stealing | 用 grab（Z 鍵抓取）移動他人物品視為偷竊 |
| Load Door Activate Prompt | 載入門時的啟用提示 |
| No Poison Prompt | 抑制塗毒確認提示 |
| Silent Sneak Power Attacks | 潛行強攻不發出聲響 |
| Remember Lock Pick Angle (VR only) | 記住開鎖角度（僅 VR 版） |

### 四、效能優化

| Tweak | 說明（推斷） |
|---|---|
| Fast RandomInt() | 加速 `Utility.RandomInt()` 原生實作 |
| Fast RandomFloat() | 加速 `Utility.RandomFloat()` 原生實作 |
| Clean Orphaned ActiveEffects | 清理孤立的 ActiveEffect（減少存檔膨脹/卡頓） |
| Update GameHour Timers | 修正/優化 GameHour 計時器更新 |
| Stack Dump Timeout Modifier | 調整 Papyrus stack dump 的逾時門檻（緩解腳本壓力日誌） |

合計：穩定性 3 + 引擎 bug 16 + gameplay 21 + 效能 5 = **45 項**。

## FOMOD 安裝流程

讀 `fomod/ModuleConfig.xml` 後可確認其安裝邏輯。它**不能**像 JContainers 那樣直接平鋪，因為 SE 與 AE 的 DLL 互斥——若兩顆都丟進 `Data/SKSE/Plugins/` 會撞檔，且裝錯版本會直接 CTD。FOMOD 就是用來在安裝期做這個二選一。

流程分兩段：

1. **必裝部分**（`requiredInstallFiles`）：把 `Required/` 整個資料夾複製到 `Data/` 根（`destination=""`），即共用的 `po3_Tweaks.pex` + `.psc`。這段無條件執行，因為 Papyrus 介面對兩版本相同。

2. **單一安裝步驟「Main」→ 群組「DLL」**（`installStep name="Main"`，`group type="SelectExactlyOne"`）：強制玩家**恰好選一個**：
   - **SSE v1.6.629+ (Anniversary Edition)** → 安裝 `AE/SKSE/Plugins` 到 `SKSE/Plugins`
   - **SSE v1.5.97 (Special Edition)** → 安裝 `SE/SKSE/Plugins` 到 `SKSE/Plugins`

   每個選項帶 `typeDescriptor` / `dependencyType`，會偵測 `gameDependency version`：
   - 偵測到遊戲為 **1.6** → AE 選項標記為 `Recommended`、SE 標記為 `Optional`；
   - 偵測到 **1.5** → 反過來，SE 為 `Recommended`、AE 為 `Optional`。

   也就是 FOMOD 會根據實際遊戲版本**預先推薦**正確的那顆 DLL，但仍由玩家最終確認（`SelectExactlyOne` 保證不會漏選或多選）。

**可選 tweak 開關？沒有。** ModuleConfig 只有「SE/AE 二選一」這一個分支，並未把 45 項 tweak 拆成可勾選的 FOMOD 選項。所有 tweak 是否啟用，是由 DLL 旁邊的 INI 設定檔（runtime 讀取，不在此 installer 包內）控制，而非安裝期決定。安裝期的唯一決策就是引擎版本對應的 DLL。

## 對 ModForge 的意義

ModForge（`~/repo/ModForge`）是程式化生成 Skyrim plugin 的工具，產出 quest / dialogue / scene / NPC / weapon 等各式 record。powerofthree's Tweaks 修掉的多是**引擎層 bug**，與 ModForge 生成的內容有幾個務實的交集點。

### (a) 可假設玩家裝了哪些常見修正——但僅止於「假設」，不是「依賴」

po3 Tweaks 是 SE/AE 社群的**準標配**之一（與 SKSE、Address Library、USSEP 同級的普及度）。其中幾項剛好覆蓋 ModForge 生成內容的踩坑區：

- **Projectile Range Fix**：ModForge 已能生成自訂 PROJ/EXPL（CLAUDE.md「已落地功能 → Projectile (PROJ) + Explosion (EXPL)」）。自訂投射物的射程行為若遇上 vanilla 的計算錯誤，這項修正會讓表現更接近預期。ModForge 仍應以 vanilla 未修正的行為為基準設計，把 po3 當作「裝了會更好」而非「裝了才對」。
- **Distant Ref Load Crash**：ModForge 在自訂 worldspace 放置大量 reference（placements / 自訂 cell）時，遠距載入正是高風險區。這項修正能降低終端使用者載入崩潰的機率，但 ModForge 不能因此放鬆對 placement 數量與分佈的節制。
- **Cast Added Spells / No-Death-Dispel Spells on Load**：若 ModForge 生成的內容依賴常駐 buff（ability/常駐法術），這兩項修正能緩解「載入存檔後 buff 消失」的經典問題。

結論：ModForge 生成時可以在文檔/README 層級**建議**玩家裝 po3 Tweaks 以獲得更穩定的體驗，但**生成的 plugin 本身不得在功能上預設它存在**。

### (b) Load EditorIDs 對 ModForge debug 流程有實質幫助

ModForge 的開發循環高度依賴主控台診斷（CLAUDE.md 列出的 `smtree` / `scnscan` / `packagediag` / `lightdiag` 等 diag 指令，以及 in-game 測試 workflow）。Skyrim 引擎在 runtime **預設丟棄 EditorID**，主控台只能用 FormID 定址生成出來的 record——但 ModForge 生成時是以 EditorID 命名 record 的，FormID 要在 build 後才能對上。

**Load EditorIDs** 這項 tweak 讓 EditorID 在 runtime 保留，主控台可直接 `help "<EditorID>"` 或用 EditorID 引用物件。對 ModForge 的 in-game 驗證流程（package → zip → 進遊戲測）來說，這把「我生成的那個 quest/NPC 的 FormID 是多少」這個反覆出現的查找步驟大幅簡化。**這是開發者機器上值得常駐的工具，但屬於 debug 便利，不影響成品行為。**

### (c) 這是 native DLL 依賴，ModForge 不該強制依賴它

po3 Tweaks 的修補全在 DLL 裡，且 SE/AE 各一份、綁特定遊戲版本（見上節 FOMOD 邏輯）。ModForge 若讓生成的 plugin 在 record 層級依賴某項 po3 行為（例如假設 Projectile Range 已修正才能正常運作），就等於：

1. 強迫終端使用者裝對版本的 native DLL；
2. 把 plugin 的正確性綁到一個 ModForge 無法驗證、會隨遊戲更新失效的外部 binary 上。

這與 ModForge 對 JContainers 的態度一致（見 `jcontainers.md`「對 ModForge 的意義」）：native 依賴屬於**進階/可選**層，不該進入預設生成路徑。

務實定位：**po3 Tweaks 對 ModForge 開發者是好用的環境（尤其 Load EditorIDs），對 ModForge 產出物則是「相容即可、不依賴」的外部修補層。**
