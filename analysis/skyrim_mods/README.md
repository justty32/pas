# skyrim_mods —— 七個參考 mod 分析

分析對象：`~/skyrim_mods/` 下已解壓的 Skyrim SE mod。它們是 **ModForge**（`~/repo/ModForge`，一個用 Mutagen 程式化生成 Skyrim plugin 的工具）的**參考素材**——不是要改它們，而是拆解它們「怎麼做到」，回饋給 ModForge 的 spec / builder 設計。

> 本分析用的 ESP record dump 由 ModForge CLI 產生：
> `dotnet run --project src/ModForge.Cli -- dump <in.esp>`
> （Sofia 1741 / RDO 9765 / SkyUI 7 / UIExtensions 9 records；BSA 內的 SWF/script/voice/mesh 無工具解包，故分析聚焦於 ESP record 層 + 可讀的 `.psc` 原始碼。）

## 七個 mod 的性質分類

| Mod | 類型 | 內容載體 | 對 ModForge 的價值 |
|---|---|---|---|
| **JContainers SE** | SKSE 資料結構 library | DLL + Lua + 12 個 `.psc` | 容器/路徑定址/持久化 DB（強但重） |
| **PapyrusUtil SE/AE** | SKSE 儲存/工具 library | DLL + 6 個 `.psc`（源碼齊） | **輕量** per-form KV（StorageUtil）+ 外部 JSON（JsonUtil） |
| **powerofthree's Tweaks** | SKSE 引擎修正/微調 | DLL（SE/AE 各一）+ 1 `.psc` | 引擎層 bug 清單（45 項）；生成內容的「環境假設」 |
| **SkyUI** | UI 替換 + MCM 框架 | ESP(7 quest) + BSA(SWF) | **MCM 設定選單**框架（`extends SKI_ConfigBase`） |
| **UIExtensions** | runtime UI 元件 library | ESP(9 record) + BSA(SWF) | 臨時互動元件（清單/輸入/輪盤選單） |
| **Sofia Follower** | 完整語音隨從 mod | ESP + 2 BSA | **隨從內容如何組織**（quest/scene/package 分工）的工業範本 |
| **Relationship Dialogue Overhaul (RDO)** | 大型對話 overhaul | ESP + BSA | **大規模對話如何精準投放**（voice-type+faction+relationship） |

兩條軸線：
- **依賴 library**（JContainers、PapyrusUtil、powerofthree、SkyUI、UIExtensions）—— 給別的 mod 撐腰，本身無玩法；ModForge 若用，都是「進階選項、不該預設依賴」。
- **內容範本**（Sofia、RDO）—— 對 ModForge 的隨從 / 劇情 / 對話方向最有借鏡價值。

> **釐清**：`~/skyrim_mods/` 裡 Nexus #32444「All in one (all game versions)」**不是 UIExtensions**，而是 **Address Library for SKSE Plugins**（meh321）——22 個 `version-*.bin` / `versionlib-*.bin`，是幾乎所有 SKSE plugin（含上面的 JContainers/PapyrusUtil/UIExtensions/po3）的共同前置，本身無玩法、無 record、無腳本。真正的 UIExtensions 是 `UIExtensions v1-2-0-17561-1-2-0.7z`（Nexus #17561），已正確解壓分析。

## 文件導覽

- `architecture/jcontainers.md` —— JContainers 結構與 Papyrus API 面
- `architecture/papyrusutil.md` —— PapyrusUtil 六模組 API（StorageUtil / JsonUtil…）
- `architecture/powerofthree-tweaks.md` —— po3 Tweaks 的 45 項 tweak 與 FOMOD 結構
- `architecture/skyui.md` —— SkyUI 的 7 個 SKI_* quest 與 MCM 框架
- `architecture/uiextensions.md` —— UIExtensions 的 8 個 UI menu 元件
- `architecture/sofia-follower.md` —— Sofia 的 record 解剖（quest×30 / scene×28 / package×54…）
- `architecture/relationship-dialogue-overhaul.md` —— RDO 的 override 策略與 SM 節點
- `details/dialogue-targeting-technique.md` —— **RDO 的對話投放技術**（condition 頻率實證）
- `others/modforge-relevance.md` —— **綜合：ModForge 能借鏡什麼**（對照現有 spec）
- `session_log.md` —— 操作日誌

## 一句話結論

- 想擴 ModForge 的**隨從生成** → 讀 `sofia-follower.md`：一個隨從 = 主控 quest + 數十個 comment quest + scene 串 phase→topic + 大量 package。
- 想擴 ModForge 的**對話規模化** → 讀 `details/dialogue-targeting-technique.md`：RDO 用 `GetIsVoiceType`(9245)×`GetInFaction`(7224)×`GetRelationshipRank`(1683) 把一句話投到對的 NPC 嘴裡。
- 想擴 ModForge 的**runtime 狀態存儲** → 讀 `papyrusutil.md`（輕量 per-form KV，入門成本低）或 `jcontainers.md`（容器/路徑定址，功能強概念重）；二者都比 GLOB 適合複雜狀態，但都是 native 依賴。
- 想給生成的 mod 加**設定選單** → 讀 `skyui.md`：生成 `extends SKI_ConfigBase` 的 quest+script；想加**臨時互動 UI**（選清單/輸入文字）→ 讀 `uiextensions.md`。
- 五個 library（JContainers/PapyrusUtil/po3/SkyUI/UIExtensions）對 ModForge 的共同結論：**有用但都是 native/SWF 依賴，應做成 opt-in，預設維持零外部依賴**。
