# RDO 的 Papyrus 腳本：投放靠資料、腳本只補三件小事

> 素材：`Relationship Dialogue Overhaul.bsa`（116 MB，絕大多數是語音 `.fuz`）自行解包後取出的 `scripts/` 目錄。
> 解包路徑 `/tmp/rdo_bsa/scripts/`（`.pex` 98 個）與 `/tmp/rdo_bsa/scripts/source/`（`.psc` 98 個，完整可讀原始碼）。
> 本文聚焦「RDO 有沒有靠 script」——與 architecture/relationship-dialogue-overhaul.md（總論）、details/dialogue-targeting-technique.md（condition 投放）互補。

## 0. 一句話結論

RDO 的對話投放**完全不靠 script**——98 個腳本裡沒有任何一支在 runtime 決定「哪句話投給哪個 NPC」。投放是純資料（INFO + condition + 靜態 FormList），script 只負責三件 vanilla 對話框架本來就需要的瑣事：**節流計時、隨從管理、quest fragment 黏合**。BSA 還附帶完整 `.psc` 原始碼，無需反編譯即可全文閱讀，本文所有引用皆來自原始碼。

## 1. 腳本清單與數量

`scripts/source/` 共 **98 個 `.psc`**（與 98 個 `.pex` 一一對應）。對照 architecture 統計的「9765 records / 6650 新 INFO」，腳本佔比極低——平均約 68 句新台詞才攤到 1 支腳本，而那支腳本與「這句話投給誰」毫無關係。

按家族歸併後，98 支可收斂成寥寥幾類：

| 家族 | 數量 | 性質 | 代表檔 |
|---|---:|---|---|
| `RDO_IdleCommentTimer<VT>` | 20 | 每個 VoiceType 一支的**節流計時器** | `rdo_idlecommenttimerfnord.psc` |
| `RDO_NextIdleComment<VT>` | 20 | 上者的 TopicInfo fragment 觸發殼 | `rdo_nextidlecommentfnord.psc` |
| `RDO_Default*`（follow/recruit/dismiss/wait/trade/favor…） | 10 | 共用隨從/好感 TopicInfo fragment | `rdo_defaultfollowme.psc` |
| Gelebor / Isran / Valerica 隨從組（各 7） | 21 | 三名 RDO 自管隨從的完整 follower 框架 | `rdo_geleborfollowerscript.psc` |
| Kaie confront quest 組 | 6 | RDO 原創 Kaie 劇情 quest 的 fragment + alias | `rdo_kaieconfrontquestfragments.psc` |
| FfRiftenGrelka 組 | 5 | 一段 Riften 任務的 fragment + 說服/賄賂/恐嚇 | `rdo_ffriftengrelkaquestfragments.psc` |
| 其餘單支 | 16 | MCM、misc fixes、各式 TIF/SF fragment | 見 §4 |

四個「家族」（71 支）幾乎都是**機械複製**：20+20 個是「每個 VoiceType 各一份的同一支節流器」，21 個是「三名隨從各複製一份同一套 follower 邏輯」。真正獨立的內容腳本只有十來支。

注意命名與 architecture 提到的節點吻合：`a_RDOKaieConfront`（→ `rdo_kaieconfrontquestfragments.psc`）、`a_RDOAssaultActor`（對應 SM `a_RDOAssaultActorNode`）等都能在腳本側找到落點。

## 2. 唯一稱得上「投放輔助」的 script：per-VoiceType 節流

architecture 與 targeting-technique 都猜測 RDO 有「per-voicetype comment 計時節流，推進 `a_RDO_*NextComment` 全域變數」。解包後**完全證實**，而且這是全 mod 唯一與投放沾邊的 script 機制——但它管的是「多久能再講一次」，不是「投給誰」。

機制三件套（以 FemaleNord 嗓音為例）：

1. **計時器本體** `RDO_IdleCommentTimerFNORD extends Quest`（`rdo_idlecommenttimerfnord.psc`）。核心函式 `Commented()`：擲 `Utility.RandomInt(1,7)` 取一個 0.01–0.06 的 `DaysUntilNextAllowed`（約 15 分鐘到 1.5 小時遊戲時間），加上 `GameDaysPassed.GetValue()` 得 `NextAllowed`，寫回 `a_RDO_FNORDNextComment.SetValue(NextAllowed)`。

   ```papyrus
   float NextAllowed = GameDaysPassed.GetValue() + DaysUntilNextAllowed
   a_RDO_FNORDNextComment.SetValue(NextAllowed)
   ```

2. **觸發殼** `RDO_NextIdleCommentFNORD extends Quest Hidden`（`rdo_nextidlecommentfnord.psc`）。一個 CK 自動生成的 quest fragment，整支只做 `kmyquest.Commented()` 一行——掛在某筆評論 INFO 的 quest stage fragment 上，NPC 一旦講了話就推進計時器。

3. **回讀**：condition 端用 `GetGlobalValue`/`ConditionGlobal` 比較 `a_RDO_*NextComment` 與當前 `GameDaysPassed`，「冷卻未到 → 整筆 INFO 失格」。這一步**在資料（condition）裡，不在 script**。

也就是：script 只負責「把下次允許時間寫進全域變數」，至於「這個全域變數讓哪句話冷卻」「冷卻的是哪一群 NPC」，全由 condition + VoiceType 決定。架構文檔行 145 提到的 `a_RDO_FNORDNextComment` / `a_RDO_MDRNKNextComment` 等 20 個 GlobalFloat，正是這 20 支計時器各自的儲存格。

對應的 TopicInfo fragment（如 `rdo_defaultidlecomment.psc`）也只是 `GetOwningQuest().SetStage(30)` 一行——推進 stage 觸發上述計時，同樣不碰投放。

## 3. 沒有「動態維護 aaa_RDOVoices* 名單」這回事

另一個 architecture 的猜測——「把 NPC 動態加進/移出 `aaa_RDOVoices*` FormList」——**解包後證偽**。對全 98 支 script grep `RDOVoices` / `AddForm` / `RemoveAddedForm` 到 voice 名單，**零命中**。`aaa_RDOVoices*`（18 個 FormList）是 CK 裡靜態建好的，runtime 只被 `IsInList` condition 讀取，從不被 script 改寫。

唯一的 runtime FormList 寫入在 `RDO_MCMConfig.RDO_StartupChanges()`（`rdo_mcmconfig.psc:198` 起），且**與 voice 投放無關**：它在 `OnInit()` 一次性把 RDO 自製的 encounter NPC 注入三個 vanilla **LeveledActor** 列表——

```papyrus
WEAdventurerSpellswordSubChar.AddForm(_RDOLeveledActorsWEAdventurerSS.GetAt(0), 1)
LCharHunter.AddForm(_RDOEncHunters.GetAt(0), 1)
LCharOrcMissile.AddForm(_RDOEncOrcHuntersFemale.GetAt(0), 1)
```

目的（原始碼註解寫得很白）是讓「原版有配音卻沒被用到的 VoiceType」（FemaleCommander/FemaleSultry 傭兵、MaleCommonerAccented 獵人、FemaleOrc 獵人）有實際 NPC 去講那些早就錄好的台詞。這是「補 vanilla 漏網的 leveled list」，做完即 `changesDone = True` 不再執行——一次性資料修補，不是投放邏輯。

## 4. 「MCM」其實是偽 MCM：用 Quest 變數當開關

`RDO_MCMConfig`（`rdo_mcmconfig.psc`，全 mod 最大的 script，12 KB）**不是** SkyUI 的 `SKI_ConfigBase`，而是 `extends Quest Conditional`。腳本頂部註解講明原因：寫於 SE 早期、SKSE/SkyUI 尚未移植，所以改用「Quest Conditional + bool property」當設定載體：

```papyrus
Scriptname RDO_MCMConfig extends Quest Conditional
{... RDO will still work by extending Quest Conditional because the
script variables can still be accessed with the GetVMQuestVariable condition.}
bool property FemaleNordFriendVal = True Auto Conditional
bool property MaleDrunkEnemyVal  = True Auto Conditional
```

每個 VoiceType × {Friend / Enemy / Idle} 一個 bool property（數十個）。「關掉某嗓音的某類台詞」= 把對應 bool 設 False，再由台詞 INFO 上的 `GetVMQuestVariable` condition 讀這個變數放行/擋下。**設定開關依然落在 condition 投放層**，script 只是被動的變數容器 + 啟動時的一次性修補（§3）。這正呼應 targeting-technique 把 `GetVMQuestVariable`（1476 次）列為「狀態機/開關」維度。

其餘單支腳本，全是 vanilla 對話框架的標準黏合件，無一觸及投放：

- **TopicInfo fragment（TIF/SF）**：`rdo_thisquestsetstagetif.psc`（`ThisQuest.SetCurrentStageID(StageToSet)`）、`rdo_startquesttif.psc`（`QuestToBegin.Start()`）、`rdo_startspousestore.psc`、`rdo_showfriendgiftmenu.psc`、`rdo_changegiftfactionrank.psc`、`rdo_actordrawweapon.psc`、`rdo_dlc1bossfightdialogue.psc`、`rdo_tg08bmnordbanditkill.psc`——每支都是一兩行的 CK fragment 殼。
- **alias 腳本**：`rdo_clearaliasscript.psc`（`OnDeath → Self.Clear()`，死亡清 alias，與 ModForge 的 `RDO_ClearAliasScript` 同型）、`rdo_playeraliasquestfixesonload.psc`（`OnPlayerLoadGame → MiscQuestScript.RDO_ApplyFixes()`）。
- **共用 quest 腳本** `RDO_MiscSharedInfoQuestScript`（`rdo_miscsharedinfoquestscript.psc`，6 KB）：`RDO_MakeFollower/MakeSpouse`（加減 vanilla 隨從/婚姻陣營）、`RDO_SetGiftFactionRank`（送禮升 `a_RDOGiftFaction` rank、滿級反而 `SetRelationshipRank(-1)`）、`RDO_ApplyFixes`（修 vanilla 漏洞：救過 Saadia / 復原 Gildergreen 後 NPC 關係竟不變 → 補成 friend）。全是「改 faction/relationship 數值」的小工具函式。
- **say-once 載體** `rdo_sayoncevariablesscript.psc`：空 `Quest Conditional`，純粹給「非 Start-Game-Enabled quest 的 Say-Once 旗標」當變數掛點。

## 5. 隨從框架：自管 follower，重抄 vanilla 模式

唯一「有份量」的 script 內容是隨從系統，但它服務的是 **RDO 原創/恢復的具名隨從**（Gelebor、Isran、Valerica，各 7 支；外加 Kaie 劇情），不是對話投放：

- **`RDO_GeleborFollowerScript extends Quest Conditional`**（`rdo_geleborfollowerscript.psc`）自己實作 recruit/wait/follow/dismiss/setFollowDistance：`SetPlayerTeammate()`、`ForceRefTo`、`IgnoreFriendlyHits()`、近/中/遠跟隨用三個 bool（`RDOFollowDistance{Close,Medium,Far}`）+ `EvaluatePackage()`——典型的 self-managed follower，跟隨距離一樣靠 `Conditional` bool 給 AI package 的 condition 讀。
- **`RDO_Default*` 系列（10 支）**走另一條路——直接呼叫 **vanilla 的** `DialogueFollowerScript`：`(GetOwningQuest() as DialogueFollowerScript).FollowerFollow()`、`(pDialogueFollower as DialogueFollowerScript).SetFollower(akspeaker)`。這是把通用 NPC 接上原版隨從系統的「免寫 script」捷徑，對應 ModForge 筆記 It.32 偏好的「vanilla SetFollower」路徑。

這驗證了 sofia-follower.md 與 modforge-relevance.md 的判斷：**單一/少數具名隨從用 vanilla quest 機制就夠，不需要 SKSE 資料結構**。RDO 的 follower script 全程零 native 依賴。

## 6. script vs 純資料的比例判斷（明確結論）

| 行為 | 載體 | 靠 script？ |
|---|---|---|
| 「哪句台詞投給哪個 NPC」 | INFO + condition（VoiceType/Faction/Rank/RandomPercent…） | **完全不靠** |
| 「目標名單 / 排除名單」 | 18 個靜態 FormList + `IsInList` | **完全不靠**（FormList 是 CK 靜態資料） |
| 「功能開關（某嗓音某類台詞開/關）」 | MCM bool property + `GetVMQuestVariable` | 變數載體是 script，**判斷在 condition** |
| 「同嗓音不刷屏」節流 | 20 支計時器寫 `a_RDO_*NextComment` GlobalFloat | **靠 script**（唯一與投放相關，但只管「何時」非「給誰」） |
| quest 階段推進 / 對話起手 | TIF/SF fragment（一兩行殼） | 靠 script（vanilla 框架本來就要） |
| 具名隨從管理 | follower quest script | 靠 script（與對話投放無關） |
| vanilla 關係漏洞修補 | `RDO_ApplyFixes` 等 | 靠 script（一次性數值修補） |

換算規模感：6650 句新台詞 + 海量 condition + 18 FormList = **資料**；98 支 script 裡真正獨立的內容腳本約十餘支，其餘是 40 支機械複製的節流器/觸發殼 + 21 支三名隨從的同套框架複製。**RDO 的行為 95% 以上靠 record + condition + 靜態 FormList，script 只補節流、隨從、fragment 黏合三類 vanilla 框架瑣事。** 沒有任何一支 script 在做「規模化投放」的決策——投放是宣告式的資料，不是命令式的程式。

## 7. 對 ModForge 的意義

解包結果**正面印證** dialogue-targeting-technique.md 與 modforge-relevance.md 的核心判斷：要複製 RDO 式對話包，重點在 **spec/builder（condition + FormList + vanilla override）**，而非生成複雜 Papyrus。

具體推論：

1. **不需要生成「投放邏輯」的 Papyrus**。RDO 規模再大也沒寫一行「決定投給誰」的 script——這件事 ModForge 應該也用純 condition + FormList 在 build 期產出，與其現有 `BuildCondition` dispatch 路線一致（modforge-relevance.md §二.1 列的 `GetIsVoiceType`/`IsInList` 補 case 即可）。
2. **FormList builder 是靜態產物**，不必生成任何維護它的 script——RDO 的 18 個 voice 名單全靜態。ModForge 加 FormList builder 是純 record 生成工作。
3. **真正需要生成的 script 只有三類小東西**，且 ModForge 多半已有對應能力：
   - 節流計時器（per-VoiceType 寫 GlobalFloat）——ModForge 已能生成 GLOB + quest fragment 風格 Papyrus（CLAUDE.md「已落地：Quest 階段 / MFSE_AdvanceStage」），這類「擲骰寫全域變數」的 fragment 是同型工作。
   - 一兩行的 TIF/SF fragment（SetStage / Start quest）——ModForge 的 `Generator.QuestFragments.cs` 正是做這個。
   - alias `OnDeath → Clear()` / `OnPlayerLoadGame → 修補`——ModForge 已有 alias 腳本生成（`RDO_ClearAliasScript` 與 ModForge 既有的 alias OnActivate 同型）。
4. **MCM 開關可以「偽 MCM」起步**：RDO 證明 SE 早期連 SkyUI 都不用，純 `Quest Conditional` bool + `GetVMQuestVariable` 就能做功能開關。ModForge 若要做對話包的開關，最低成本路線是生成這種偽 MCM quest，而非一開始就上 `SKI_ConfigBase`（後者是 modforge-relevance.md §二.3 的進階 opt-in）。

一句話收束：**RDO 把「規模」全押在資料，把 script 壓到 vanilla 框架的最小公倍數。ModForge 要抄 RDO，抄的是它的 spec 範式（override + condition 模板 + FormList），生成的 Papyrus 反而比 ModForge 現有 trigger 庫還簡單。**

## 解包方法與還原程度

**第一關 — 解 BSA（自寫 Python extractor）**

- pip BSA 庫（`bethesda_structs` / `bsa` / `libbsa`）本機皆無、`7z 26.01` 無法把此檔當 archive 開啟、系統無 `bsarch`/`bsab`。改走自寫 extractor。
- 讀 header（`/tmp/bsa_extract.py`）：magic `BSA\0`、version **105**（SSE）、archiveFlags `0x33`（= include-dir-names | include-file-names | **compressed** | bit5）、folderCount 73、fileCount 5619、fileFlags `0x11b`。
- v105 的 folder record 為 24 bytes（uint64 offset）；file record 16 bytes；folder-name block 與 file-name block 依格式逐段解析。檔案大小高位 bit `0x40000000` = 該檔壓縮旗標**反轉** archive 預設。
- 壓縮為 **zlib**（非 lz4——本機無 lz4 模組，但 SSE BSA 用 zlib，Python stdlib `zlib.decompress` 即可，前 4 bytes 為原始大小）。
- 只抽 `scripts/`（`.pex`）與 `scripts/source/`（`.psc`），**跳過所有 sound/voice/`.fuz`**（佔 116 MB 絕大體積）。成功抽出 **196 檔 = 98 `.pex` + 98 `.psc`**，解壓後大小合理（數百 B 到 12 KB）。

**第二關 — 讀 `.pex`：不需要**

BSA 內附完整 `scripts/source/*.psc` 原始碼，與 `.pex` 一一對應。本文全部引用直接取自 `.psc` 純文字，**還原程度 100%（即原始碼，非反編譯重建）**，無需 Champollion / PEX string-table 解析 / `strings`。

**取證索引**

- 解包腳本：`/tmp/bsa_extract.py`；輸出：`/tmp/rdo_bsa/scripts/`（.pex）、`/tmp/rdo_bsa/scripts/source/`（.psc）。
- 節流：`rdo_idlecommenttimerfnord.psc`（`Commented()` 寫 `a_RDO_FNORDNextComment`）、`rdo_nextidlecommentfnord.psc`（fragment 殼）。
- 名單證偽：`grep -rniE "RDOVoices|AddForm" /tmp/rdo_bsa/scripts/source` 僅命中 `rdo_mcmconfig.psc:198+` 的 LeveledActor 注入。
- 偽 MCM：`rdo_mcmconfig.psc:1`（`extends Quest Conditional` + 頂部註解）。
- 隨從：`rdo_geleborfollowerscript.psc`、`rdo_defaultfollowme.psc`/`rdo_defaultrecruit.psc`（呼叫 vanilla `DialogueFollowerScript`）。
- 共用工具：`rdo_miscsharedinfoquestscript.psc`（`RDO_MakeFollower`/`RDO_SetGiftFactionRank`/`RDO_ApplyFixes`）。
