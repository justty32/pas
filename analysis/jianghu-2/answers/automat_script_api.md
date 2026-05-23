# AutomatScript 腳本 API 全集 — mod 行為腳本可用函式

> 日期：2026-05-23
> 來源：`AutomatManager.cs`（22941 行）的 `handlerMap`，共 **963 個唯一函式**
> 完整清單：`others/automat_script_functions.txt`（963 行，一行一函式）
> 前置脈絡：mod 用 `scriptsclient` 表 + `Graphml/Bin/*.bytes` 帶腳本（見 `answers/mod_db1_schema_validation.md`）

## 0. 這是什麼

`AutomatScript` 是遊戲的**視覺化腳本系統**（yEd graphML 圖）。一張圖 = 節點（呼叫一個函式）+ 邊（流程走向，可掛條件）。圖被編譯成 `.bytes`，由 `AutomatManager` 在執行期解譯。**所有劇情演出、NPC 行為序列、觸發事件都是這套腳本驅動的**（先前看到的 WayPoint 事件、隨機 NPC 行為，最終都走 `AutomatScriptManager.ExeScript`）。

mod 能用的就是 `handlerMap` 裡這 963 個函式——**不能新增函式**（要新函式得 BepInEx）。

## 1. 呼叫慣例

- 每個函式實作為 `bool Script_X(AutomatScript component, CallFunc funcParams)`（`AutomatManager.cs:17` 委派 `HandlerExeFunc`）。
- 節點文字 = `函式名(arg0,arg1,...)`，例：`AutoFindPath(226.7669,238.3556,98.63643,90,1102451)`。
- 參數是**位置參數**，實作用 `funcParams.GetToken(idx)` 取值：`tok.number`(float) / `tok.Integer`(long) / 字串（`CallFunc.cs`）。
- **回傳 bool**：動作節點回傳是否完成/成功；條件節點（掛在邊上）回傳 true=走這條邊。
- **mod ID 自動重映射**：函式內對 NPC/物品 ID 會呼叫 `DataMgr.ConditionMakeInt64(component.ModId, ref id, XxxPrototype.IsModReserve)`（見 `Script_AutoFindPath` @ `:1882`）。即 **mod 腳本裡寫的 ID 會自動換算到該 mod 的保留範圍**——這就是跨 mod 不撞 ID 的關鍵，你在腳本裡用「本地」ID 即可。

### 1.1 動作 vs 條件 — 同名常有三態
很多函式有三個版本，命名規律：
- `Xxx` — 動作節點（執行並推進）
- `XxxCondition` — 條件節點（純判斷，用在邊上）
- `XxxDialogCondition` — 對話流程中的條件版

例：`AutoFindPath` / `AutoFindPathCondition` / `AutoFindPathDialogCondition`；`SetNpcPostion` / `SetNpcPostionCondition`；`IsMoveFinished` / `IsMoveFinishedCondition` / `IsMoveFinishedDialogCondition`。

條件節點前綴慣例：`Is*`(180 個) / `Has*`/`Have*`(29) / `Check*`(39) / `*Condition` 結尾(35)。

## 2. 分類速查（代表函式）

> 完整列舉見 txt 檔；以下挑各類最常用的。括號 ≈ 推測參數。

### 2.1 移動 / 尋路（~53）
- `AutoFindPath(x,y,z,dirY[,npcId])` — 尋路到座標，可選指定 NPC、到達後轉向 dirY
- `AutoFindPathWalk(...)` — 用走路（非跑）尋路；`AutoFindPathBySpeed` — 指定速度
- `MoveToPlayer` / `MoveToTarget` / `MoveToPosition` / `MoveToBack` — 各種移動目標
- `MoveToTargetRotateAuto(2/3)` — 移動並自動面向
- `SetNpcPostion(npcId,x,y,z,dirY)` — 直接瞬移擺位（無動畫）
- `TeleportToPosition` / `TeleportToBornPoint` / `TeleportRandomNpc`
- `MoveAlongWayPoint` / `MoveAlongPoint` / `NavSelfToPatrolPoint` — 沿路徑點走
- `BanMove` / `StopMove` — 禁止/停止移動
- `LookAtHero` / `LookAtTarget` / `FaceTo...` — 轉向
- `EnableOrDisableNpcPatrol` — 開關 NPC 巡邏
- 完成判斷：`IsMoveFinished(npcId)` / `IsMoveAlongPointFinish` / `IsRotateFinish`

### 2.2 鏡頭 / 過場（~62）
- `BeginCinematic` / `EndCinematic` / `RunCinematic(2)` / `CinematicResume` — 過場開關
- `ShowBlackScreen(ms,strId,?)` / `HideBlackScreen` / `BlackScreen` / `StartBlackScreen(New)` — 黑幕轉場
- `Fade` / `FadeIn` / `FadeOut` / `ChangeFadeSprite` — 淡入淡出
- `CameraLookAtUnit` / `LookAtHero(ById)` / `SetCameraRotateAroundPoint`
- `SetCameraCinematicMove` / `SetCameraCinematicFollowNpc` / `SetCameraCinematic2Target`
- `LoadTimeline` / `PauseTimeLine` / `ResumeTimeLine` / `StopTimeLine`（Unity Timeline 整合）
- 完成判斷：`IsEndCinematic` / `IsTimelineFinished` / `IsCameraActivityFinish` / `IsHideBlackScreenFinished`

### 2.3 對話 / 氣泡（~62）
- `PopDialog` / `PopDialogByDefine` / `PopAutoDialog(ByNpcId)` / `PopConditionDialog` / `PopRandomDialog` — 各式彈對話
- `PopAnswer(New)` / `PopRandomAnswer` — 彈選項（玩家選擇）
- `Dialog` / `ExitDialog` / `PopStringDlg` / `PopMsgBox` — 基礎對話框
- `PopPaopaoSelf` / `WayPointEventPopBubbleDialogue` / `CloseRandomNpcBubble` — 頭頂氣泡
- `PopHireView` / `PopMusicView` / `PopPushBoxView` / `PopMassageView` — 彈各種專用面板
- 完成判斷：`IsEndDialog` / `IsYesDialog`(玩家選是) / `IsAnswerDialogFinish` / `IsBubbleFinised`

### 2.4 戰鬥 / 法術（~80）
- `CastSpell` / `CastSpellByGuid` / `CastSpellByDesignType` / `CastInRangeSpell` / `CastSpellFromList` — 施法
- `Attack` / `CastAttackEffect` / `CastCinimaticSpell`(演出法術)
- `AddHostility` / `RemoveHostility` / `TuneNeutrality2Hostility` / `TuneHostility2Neutrality` — 敵意切換
- `AddFightState` / `RemoveFightState` / `SetInWarnCombat` / `MoveToEnterCombatPos` — 進出戰鬥
- `SetNpcDead(WithCurNpc)` / `ResetHPMP` / `SetNpcsHpLock` — 生死/血量控制
- `LearnSpell` / `EquipSpell` / `UnEquipSpell` — 武學
- `PauseFightScript` / `ResumeFightScript` — 戰鬥腳本暫停
- 條件：`IsDead` / `IsPlayerDead` / `IsInSightCombat` / `IsCastingSpell` / `IsInSpellRange` / `HasEnemyInSight`

### 2.5 道具 / 經濟（~55）
- `AddItemByItemId(WithCurNpc)` / `AddRandomItems` / `AddNpcEquip` — 給物品/裝備
- `RemoveItem` / `RemoveNpcEquip` / `RemoveNpcCorrelationItems` — 移除
- `EquipItem` / `UnitUseItemImmediately` / `UnitUseItemWithCount` — 裝備/使用
- `LootItemByGroupId` / `NpcLootItem` / `RobAssignItemFormNpc` / `StealItemFromInteractNpc` — 掉落/搶/偷
- `AddMail(Role)` — 寄信；`WayPointEventGiveMoney` — 給錢
- `SetShopPriceBuy` / `SetShopPriceSell` — 改商店價
- `OpenSelectQuestReward` / `ZDL_OpenRewardSelectView` — 選擇獎勵
- 條件：`CheckBagFreeSlot` / `IsUnitOwnedSingleItemCount` / `HasSingleItemByType` / `IsPlayerHasNpcTargetItem`

### 2.6 任務 / 委託 / 觸發（~30）
- `AcceptQuestById` / `FinishQuestById` / `UnFinishedQuest` / `AddFailedQuest` — 任務狀態
- `AddQuestTime(NotAddXiuWei)` / `QuestConditionAdd` / `SetQuestFollowNpc` — 任務細節
- `ForceAcceptEntrust` / `ForceKillEntrust` / `WayPointEventAcceptWeiTuo` / `WayPointEventFaBuWeiTuo` — 委託
- `SetXuanShangQuestState` / `FinishOrFailXuanShang` — 懸賞
- `PauseTriggerUpdate` / `ResumeTriggerUpdate` / `SubtractTriggerCount` / `SetNotTriggerNextTime` — 觸發器控制
- 條件：`HasFinishedQuest` / `HasUnFinishedQuest` / `IsNpcHaveEntrust` / `IsTriggerActived`

### 2.7 NPC / 刷怪 / 隊伍（最多，~243 含各種 Set/Is）
- 擺位/顯隱：`SetNpcPostion` / `SetNpcShowHide(Range/Condition)` / `ActiveSpawnPoint`
- 可互動性：`SetNpcInteractable` / `SetNpcCanChat` / `SetNpcClick` / `SetNpcCanBeAttack(Range)` / `SetNpcCantBeAttack`
- 刷怪點：`RefreshSpawnPoint` / `ClearSpawnPoint` / `ForceRefreshSpawnPointAllChild` / `CheckKilledSpawnPointCount`
- 隊伍：`AddTeamMember` / `RemoveTeamMember` / `KickFromTeam` / `InviteToTeam`
- 鏢隊：`CreateBiaoTeam` / `ClearBiaoTeam` / `IsBiaoTeamAlive` / `SelectBiaoTeamBattleState`
- 師徒：`AddTudiByID` / `RemoveTudiByID`
- 潛行：`SetNpcReactToQianXing`
- `ChangeNpcSubType` — 改 NPC 子型別

### 2.8 場景 / 物件 / 機關（~66）
- `ActiveGameObject(InRoot)` / `ShowOrHideGameObject(ByPrefab)` / `InstantiateGameobject` — 物件顯隱/生成
- `GameObjectPlayAnim` / `GameObjectAnimatorSetBool` / `GameObjectDoLocalPosition/Rotate/Scale` — 物件動畫/位移
- `ChangeSceneState` / `AddSceneState` / `ChangeSceneInteractiveState` — 場景狀態機
- `PlayAnimBySceneInteractiveState` — 依場景互動狀態播動畫
- `ActiveDianTi`(電梯) / `GameObjectDemolish` / `CheckDemolishObject` — 機關/拆除
- `AddHouseManager` / `RemoveHouseManager` — 房屋系統
- `SaveGameobjectPos` / `SetGameobjectFromSavePos` — 物件位置存讀
- 材質特效：`GameObjectCopyMaterial` / `SetGameObjectMaterialColor` / `SetGameObjectEmissiveIntensity`
- 條件：`HasGameObject` / `SceneIsLoaded` / `IsGameObjectPositionInPosArea` / `CheckAreaHaveTagGameObject`

### 2.9 屬性 / 數值 / 計數器（~59）
- `AddUnitAttri(Temp)` / `GetUnitAttri(Fly)` / `IsUnitAttri` — 單位屬性增改查
- `AddTalentPoint` / `NpcAddTalent` / `NpcDeleteTalent` / `IsNpcLearntTalent` — 天賦
- `AddUnitStunt` / `RemoveUnitStunt` / `CheckUnitHaveStunt` — 絕技
- `AddCounter` / `StartCounter` / `ClearCounter` / `HasCounterCounted` — 計數器（流程記數）
- `AddTmpState` / `ClearTmpState` / `AddSceneState` — 暫態旗標
- `AddUnitGongLiRatio` / `AddFactionGongLiRatio` — 功力倍率

### 2.10 門派 / 勢力 / 好感 / 關係（~25）
- `AddMenpaiHaogan` / `GetMenpaiHaogan` / `ModifyMenPaiHaogan` / `ShowMenpaiHaogan` — 門派好感
- `AddMenPaiShengWang` / `IsMenPaiShengWangMoreThan` — 聲望
- `NpcJoinMenPai` / `NpcLeaveMenPai` / `NpcMenPaiShenFenLevelUp` — 門派身份
- `AddNpcSocialValue` / `IsNpcSocialValue` / `SetNpcSocialTalkData` — 社交值
- `AddNeutrality` / `RelationShipAddMate` / `SetMenPaiRelation` — 關係/中立
- `IsPlayerNpcHaoGanValue` — 玩家對 NPC 好感判斷

### 2.11 時間 / 流程控制 / 等待（~78，多為 Is*Finish 等待節點）
- `WaitForSeconds(sec)` — 等待
- `StartTimer` / `StopTimer` / `HasTimerCounted` — 計時器
- `CheckGameTime` / `CheckDay` / `CheckTimeIsHour` — 遊戲時間判斷
- `AddPlayerPlayTime` / `AddQuestTime`
- 大量 `Is...Finish` 等待節點：`IsPlayAnimFinish` / `IsMoveFinished` / `IsRotateFinish` / `IsTimelineFinished` / `IsNpcAutoChatFinished` / `IsHuaYuanFinish` / `IsConditionsFinished`…（搭配前面動作做「等它做完再繼續」）

### 2.12 音效（~20）
- `AudioPlayMusic` / `AudioPlayPlayerAreaMusic` / `AudioPreloadMusic` / `AudioStopSpecialMusic` — 音樂
- `AudioPlaySfx` / `PlayNpcSfx` / `PlayAttackerSfx` / `PlayVictimSfx` — 音效
- `OpenMusicGame` / `CheckMusicGameSuc` — 音樂小遊戲
- `HideNpcBuffSfx` / `HidePlayerBuffSfx` / `RemoveNpcSfx` — 特效音關閉
- 條件：`IsAudioEnd`

## 3. 怎麼用在 mod 裡

1. 用遊戲內的 **mod 編輯器**（`ModSpace`）建立 yEd 腳本圖，節點只能用上面這些函式。
2. 編譯後輸出到 mod 的 `Graphml/Bin/<name>.bytes`，並在 `db1_Mod.txt` 的 `scriptsclient` 段註冊 `腳本ID#檔名#`。
3. 在需要觸發腳本的地方掛 ID（例：`npc_interact` 的 `script` 欄、`areatrigger`、任務）。腳本 ID 屬 mod 範圍時，`Automat.cs:79-82` 會從 mod 資料夾載入執行。
4. 腳本內引用的 NPC/物品 ID 用你 mod 的本地 ID 即可，引擎自動 `ConditionMakeInt64` 重映射。

## 4. 典型腳本範例（拆自「化凡秘章」`id_11345672`）

一段「NPC 走過去 → 等到位 → 黑幕 → 瞬移」的演出：
```
Entry
 └→ AutoFindPath(226.77,238.36,98.64,90,1102451)   # NPC 1102451 走到點
     └─[IsMoveFinished(1102451)]→                   # 邊條件：等走到
        ShowBlackScreen(3000,510001,8)              # 黑幕 3 秒
         └→ SetNpcPostion(1,251.94,234.24,123.20,0) # 黑幕中瞬移
             └→ Exit()
```
這就是「劇情式 NPC 走位/演出」mod 的標準寫法——**完全不需要 BepInEx**。

## 5. 邊界提醒
- 只能用這 963 個既有函式，**不能新增**。要新行為函式 / 改函式內部邏輯 → BepInEx。
- 與「NPC 自主環境行為」(巡邏/休閒/環境音 4 張表) 無關——那是另一條 data 路徑且不可 mod（見 `details/npc_environment_interaction.md`）。但你可用本腳本系統做「**被觸發的**」NPC 走位演出，效果上能補一部分。
</content>
