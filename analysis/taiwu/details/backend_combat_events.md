# Level 3：Backend 戰鬥事件與 DomainManager API（自製特效的能力邊界）

> 日期：2026-05-22
> 範圍：解開「backend 在哪」之謎，並列出寫自訂武功特效時可用的全部戰鬥事件、`CombatSkillEffectBase` 可覆寫方法、`DomainManager.Combat` 變更狀態的 API。
> 這份是設計**複雜機制特效**時的查表手冊。

---

## 1. 重大架構發現：Backend 是獨立的 .NET 進程

之前 Level 1/2 一直找不到 `DomainManager`、`CombatSkillEffectBase`、`GameData.DomainEvents.Events`——因為它們**完全不在 `Assembly-CSharp.dll`（Unity 前端）裡**。

真相：遊戲是 **前端（Unity）+ 後端（獨立 .NET 進程）** 雙進程架構：

```
<遊戲安裝>/
├── The Scroll of Taiwu_Data/Managed/   ← 前端 Unity（Assembly-CSharp.dll 等）
└── Backend/                            ← ★ 後端，一個獨立的 .NET 6/8 程式
    ├── GameData.exe                    ← 後端主程式
    ├── GameData.dll              22 MB ← 全部領域邏輯（戰鬥/角色/事件…）
    ├── GameData.Shared.dll       16 MB ← 共享型別、Config 系列
    ├── GameData.Shared.Enum.dll        ← 列舉
    ├── GameData.Combat.Math.dll        ← 傷害計算
    ├── GameData.Common.dll
    ├── GameData.Serializer.dll
    ├── GameData.Adventure.dll
    ├── GameData.GameDataBridge.dll
    ├── GameData.SecretInformation.dll
    ├── GameData.ArchiveData.dll
    ├── vnpipe.dll                       ← ★ 前後端 IPC（virtual named pipe）
    ├── coreclr.dll / clrjit.dll …       ← 自帶 .NET runtime
    ├── SQLite-net.dll / e_sqlite3.dll   ← 後端用 SQLite 存資料
    └── Steamworks.NET.dll
```

**這解釋了非常多東西**：
- 為什麼有 frontend plugin 與 backend plugin 兩種：它們跑在**不同進程**。
- 為什麼 YAML 要在兩邊各載一次：兩個進程各有自己的 `CombatSkill.Instance` / `SpecialEffect.Instance`。
- 為什麼 backend plugin 用 `DomainManager.Mod.*` 而非 `ModManager.*`：`ModManager` 是 Unity 前端的類，後端進程根本沒有它。
- `GameDataBridge` + `VnPipe`（Level 1 看到的）就是這兩個進程之間的橋。
- 後端是真正的「遊戲規則引擎」，前端只是顯示層。**戰鬥邏輯、武功特效全在後端**。

### 1.1 反編譯產物（本次新增）

| Assembly | 反編譯位置 | .cs 檔數 |
|---|---|---:|
| GameData.dll | `~/dev/taiwu-src/backend/GameData/` | 3595 |
| GameData.Shared.dll | `~/dev/taiwu-src/backend/GameData.Shared/` | 1782 |
| GameData.Shared.Enum.dll | `~/dev/taiwu-src/backend/GameData.Shared.Enum/` | 108 |
| GameData.Combat.Math.dll | `~/dev/taiwu-src/backend/GameData.Combat.Math/` | 21 |
| GameData.Common.dll | `~/dev/taiwu-src/backend/GameData.Common/` | 12 |
| GameData.Serializer.dll | `~/dev/taiwu-src/backend/GameData.Serializer/` | 14 |

> **寫 backend mod 時，編譯要 reference 的就是 `Backend/` 底下這些 dll**（不是 `Managed/` 那套）。這是個關鍵的 build 設定差異。

---

## 2. 完整戰鬥/遊戲事件清單

來源：`~/dev/taiwu-src/backend/GameData/GameData/DomainEvents/Events.cs`

用法（在特效類別的 `OnEnable`/`OnDisable` 內）：

```csharp
Events.RegisterHandler_<EventName>(new On<EventName>(MyHandler));      // 訂閱
Events.UnRegisterHandler_<EventName>(new On<EventName>(MyHandler));    // 退訂（OnDisable 必做）
```

所有 handler 第一個參數都是 `DataContext context`。以下省略它只列其餘參數。

### 2.1 戰鬥流程
| 事件 | 額外參數 | 時機 |
|---|---|---|
| `CombatBegin` | — | 戰鬥開始 |
| `CombatSettlement` | `sbyte combatStatus` | 戰鬥結算 |
| `CombatEnd` | — | 戰鬥結束 |
| `ChangeNeiliAllocationAfterCombatBegin` | `CombatCharacter, NeiliAllocation` | 開戰後改真氣分配 |
| `ChangeBossPhase` | — | Boss 換階段 |
| `CombatCharChanged` | `bool isAlly` | 出戰角色切換 |
| `CombatCharFallen` | `CombatCharacter` | 角色倒下 |
| `CombatStateMachineUpdateEnd` | `CombatCharacter` | 狀態機每次更新結束 |

### 2.2 出招／準備／攻擊（劍法特效最常用）
| 事件 | 額外參數 |
|---|---|
| `ChangePreparingSkillBegin` | `int charId, short prevSkillId, short currSkillId` |
| `PrepareSkillEffectNotYetCreated` | `CombatCharacter, short skillId` |
| `PrepareSkillBegin` | `int charId, bool isAlly, short skillId` |
| `PrepareSkillProgressChange` | `int charId, bool isAlly, short skillId, sbyte preparePercent` |
| `PrepareSkillChangeDistance` | `CombatCharacter attacker, defender, short skillId` |
| `PrepareSkillEnd` | `int charId, bool isAlly, short skillId` |
| `CastAttackSkillBegin` | `CombatCharacter attacker, defender, short skillId` |
| `AttackSkillAttackBegin` | `attacker, defender, short skillId, int index, bool hit` |
| `AttackSkillAttackHit` | `attacker, defender, short skillId, int index, bool critical` |
| `AttackSkillAttackEnd` | `attacker, defender, short skillId, int index, bool hit` |
| `CastSkillEnd` | `int charId, bool isAlly, short skillId, sbyte power, bool interrupted` |
| `CastSkillAllEnd` | `int charId, short skillId` |
| `CastSkillCosted` / `CastSkillTrickCosted` | `CombatCharacter, short skillId[, List<NeedTrick>]` |
| `CastAgileOrDefenseWithoutPrepareBegin` / `…End` | `int charId, short skillId` |
| `CastLegSkillWithAgile` | `CombatCharacter, short legSkillId` |

### 2.3 普通攻擊
`NormalAttackPrepareEnd`、`NormalAttackOutOfRange`、`NormalAttackBegin`、`NormalAttackCalcHitEnd`、`NormalAttackCalcCriticalEnd`、`NormalAttackEnd`、`NormalAttackAllEnd`、`UnlockAttack`、`UnlockAttackEnd`。

### 2.4 殺式/招式（Trick）
| 事件 | 額外參數 |
|---|---|
| `GetTrick` | `int charId, bool isAlly, sbyte trickType, bool usable` |
| `GetShaTrick` | `int charId, bool isAlly, bool real` |
| `RearrangeTrick` | `int charId, bool isAlly` |
| `OverflowTrickRemoved` | `int charId, bool isAlly, int removedCount` |
| `ChangeTrickCountChanged` | `CombatCharacter, int addValue` |
| `JiTrickInsteadCostTricks` / `UselessTrickInsteadJiTricks` | `CombatCharacter, int count` |

### 2.5 傷害/傷勢/破綻/穴道/必死
| 事件 | 額外參數 |
|---|---|
| `AddInjury` | `CombatCharacter, sbyte bodyPart, bool isInner, sbyte value, bool changeToOld` |
| `AddDirectDamageValue` | `int attackerId, defenderId, sbyte bodyPart, bool isInner, int damageValue, short combatSkillId` |
| `AddDirectInjury` | `attackerId, defenderId, isAlly, bodyPart, outerMarkCount, innerMarkCount, combatSkillId` |
| `BounceInjury` | `…, outerMarkCount, innerMarkCount`（反震） |
| `FlawAdded` / `FlawRemoved` | `CombatCharacter, sbyte bodyPart, sbyte level`（破綻） |
| `AcuPointAdded` / `AcuPointRemoved` | `CombatCharacter, sbyte bodyPart, sbyte level`（穴道） |
| `AddMindMark` / `AddMindDamage` | `CombatCharacter, int count` / `…, int damageValue, markCount, skillId`（心神） |
| `AddFatalDamageMark` / `AddDirectFatalDamageMark` | 必死標記 |
| `AddDirectPoisonMark` | `attacker, defender, sbyte poisonType, short skillId, int markCount` |

### 2.6 毒/物外/真氣/距離/武器
`AddPoison`、`PoisonAffected`、`AddWug`/`RemoveWug`（物外）、`NeiliAllocationChanged`、`CostBreathAndStance`、`CostAttackPrepareValue`、`ChangeWeapon`、`WeaponCdEnd`、`CombatChangeDurability`、`MoveBegin`/`MoveEnd`/`MoveStateChanged`、`DistanceChanged`/`IgnoredForceChangeDistance`、`SkillEffectChange`、`SkillSilence`/`SkillSilenceEnd`、`CombatBlockReduceDamage`/`CombatBlockCosted`/`CombatBlockingEnd`、`CombatCostNeiliConfirm`、`DamageCompareDataCalcFinished`、`InterruptOtherAction`、`HealedInjury`/`HealedPoison`/`UsedMedicine`、`WisdomCosted`。

### 2.7 戰鬥外（過月/移動/生活）
| 事件 | 額外參數 | 時機 |
|---|---|---|
| `AdvanceMonthBegin` | — | 過月開始 |
| `PostAdvanceMonthBegin` | — | 過月開始後 |
| `AdvanceMonthFinish` | — | **過月結束（武學 mod 用來送武功）** |
| `PassingLegacyWhileAdvancingMonth` | — | 過月傳承 |
| `TaiwuMove` | `MapBlockData from, to, int actionPointCost` | 太吾在大地圖移動 |
| `CharacterLocationChanged` | `int charId, Location src, dest` | |
| `MakeLove` | `Character, Character target, sbyte state` | |
| `EatingItem` / `UsedMedicine` | `Character, ItemKey` | |
| `XiangshuInfectionFeatureChangedEnd` | `Character, short featureId` | 相書感染 |

> 完整 delegate 簽名見 `Events.cs:29-222`，註冊方法見 `Events.cs:1306` 起。每個事件都有對應的 `UnRegisterHandler_*`。

---

## 3. 特效類別可覆寫的方法

繼承鏈：`你的特效` → `CombatSkillEffectBase` → `SpecialEffectBase`
（`~/dev/taiwu-src/backend/GameData/GameData/Domains/SpecialEffect/SpecialEffectBase.cs` + `.../CombatSkill/CombatSkillEffectBase.cs`）

### 3.1 生命週期（最常覆寫）
| 方法 | 時機 |
|---|---|
| `void OnEnable(DataContext context)` | 特效掛上（裝備武功/開戰時）→ 在此 `RegisterHandler_*` |
| `void OnDisable(DataContext context)` | 特效移除 → 在此 `UnRegisterHandler_*` |
| `void OnDataAdded(DataContext context)` | 特效資料加入後 |
| `void OnProcess(DataContext context, int counterType)` | 計時器觸發（搭配 `CalcFrameCounterPeriods` 做週期性效果） |
| `bool IsOn(int counterType)` | 計時器是否啟用 |
| `IEnumerable<int> CalcFrameCounterPeriods()` | 定義週期（回傳 frame 數） |

### 3.2 數值修改器（被動改屬性/數值，不靠事件）
`SpecialEffectBase` 有一整組 `GetModifiedValue(AffectedDataKey dataKey, T dataValue)` 多載（`SpecialEffectBase.cs:248-308`），型別涵蓋 `int`/`bool`/`long`/`HitOrAvoidInts`/`OuterAndInnerInts`/`List<NeedTrick>` 等。

機制：在 `OnEnable` 設好 `AffectDatas`（`Dictionary<AffectedDataKey, EDataModifyType>`），遊戲計算對應數值時會回呼 `GetModifiedValue` 讓你改。範例見 Qimen9 的 `AffectDatas.Add(new AffectedDataKey(CharacterId, 199, ...), ...)`。

→ **「被動加成型」特效（如劍法 +X% 傷害、降低消耗）用這條路，不需要訂閱事件。**

### 3.3 CombatSkillEffectBase 專屬成員（查表）
| 成員 | 型別 | 意義 |
|---|---|---|
| `IsDirect` | `bool` | 正練(true)/逆練(false) |
| `SkillTemplateId` | `short` | 此特效綁定的武功 TemplateId |
| `EffectId` | `int` | 正練回 DirectEffectId、逆練回 ReverseEffectId |
| `CharacterId` | `int`（繼承自 base） | 持有者角色 id |
| `CombatChar` / `CurrEnemyChar` | `CombatCharacter` | 自己 / 當前敵人 |
| `ShowSpecialEffectTips(byte idx)` | 方法 | 顯示第 idx 條 tip（對應 YAML `ShortDesc[idx]`） |
| `CombatCharPowerMatchAffectRequire(int idx=0)` | `bool` | 當前威力是否達到 `AffectRequirePower[idx]` 門檻 |
| `SetIsDirect(context, bool)` | 方法 | |

事件 handler 內幾乎都用 `if (charId == CharacterId && skillId == SkillTemplateId)` 過濾「是不是我這招觸發的」。

---

## 4. `DomainManager.Combat` 變更狀態 API（特效的「動詞」）

來源：`~/dev/taiwu-src/backend/GameData/GameData/Domains/Combat/CombatDomain.cs`。在特效內透過 `DomainManager.Combat.<Method>(context, ...)` 呼叫。

### 4.1 殺式/招式
```csharp
AddTrick(ctx, CombatCharacter, sbyte trickType, bool addedByAlly=true)
AddTrick(ctx, CombatCharacter, sbyte trickType, int count, bool addedByAlly=true)
RemoveTrick(ctx, CombatCharacter, sbyte trickType, byte count=1, bool removedByAlly=true) → bool
GetMaxTrickCount(CombatCharacter) → int
GetUsableTrickCount / GetUselessTrickCount(CombatCharacter) → int
ChangeChangeTrickProgress(ctx, CombatCharacter, int changeValue)
```
（trickType 常數：19 = 殺式「殺」。其他 type 待補，見 §6）

### 4.2 傷勢/破綻/穴道
```csharp
AddInjury(ctx, char, sbyte bodyPart, bool isInner, sbyte value, bool updateDefeatMark=false, bool changeToOld=false)
AddRandomInjury(ctx, char, bool inner, int count=1, sbyte value=1, bool changeToOld=false, sbyte bodyPartType=-1)
RemoveInjury / RemoveHalfInjury / SetInjuries(...)
AddFlaw(ctx, char, sbyte level, CombatSkillKey, sbyte bodyPart=-1, int count=1, bool raiseEvent=true)        // 破綻
RemoveFlaw / RemoveAllFlaw / RemoveHalfFlawOrAcupoint(...)
AddAcupoint(ctx, char, sbyte level, CombatSkillKey, sbyte bodyPart=-1, int count=1, bool raiseEvent=true)    // 穴道
RemoveAcupoint / RemoveAllAcupoint(...)
GetBrokenBodyPartCount(char) → int
```

### 4.3 傷害/必死/反震/心神
```csharp
AddInjuryDamageValue(attacker, defender, sbyte bodyPart, int outerDamage, int innerDamage, short skillId, bool updateDefeatMark=true)
AddFatalDamageValue(ctx, char, int damageValue, int type=-1, sbyte bodyPart=-1, short skillId=-1, EDamageType=None) → int
AddBounceDamage(CombatContext, sbyte hitType[, short skillId, CValuePercent bouncePercent])
GetFinalCriticalOdds(char) → int
```

### 4.4 真氣/架勢/提氣/行動力/距離
```csharp
ChangeBreathValue(ctx, char, int addValue, bool changedByEffect=false, CombatCharacter changer=null) → int   // 提氣
ChangeStanceValue(ctx, char, int addValue, ...) → int                                                       // 架勢
ChangeMobilityValue(ctx, char, int addValue, ..., bool costBySkill=false)                                   // 行動力
ChangeDistance(ctx, mover, int addDistance[, bool isForced[, bool canStop]]) → bool
SetTargetDistance(ctx, short, bool isAlly=true)
ChangeDisorderOfQiRandomRecovery(ctx, char, int delta, bool changeToOld=false)                              // 內息紊亂
```

### 4.5 戰鬥狀態/治療/自動釋放
```csharp
AddCombatState(ctx, char, sbyte stateType, short stateId[, int power[, bool reverse[, bool applyEffect[, int srcCharId]]]])
RemoveCombatState(ctx, char, sbyte stateType, short stateId)
CastSkillFree(ctx, character, short skillId, ECombatCastFreePriority priority=Normal)   // ★ 無消耗自動釋放武功
HealHealth / HealQiDisorder(patientId, doctor, bool isExpensiveHeal=false) → short
SetMoveState / SetDisplayPosition / SetTimeScale(...)
```

→ `CastSkillFree` 就是 mod 描述裡「自動釋放該功法」的底層 API；mod 還額外 Postfix patch 它來拋自製事件 `CastSkillFree`（見解剖報告 §6.3）。

---

## 5. 對「劍法 + 複雜機制」設計的可行性結論（給 B 用）

使用者要劍法 + 複雜機制特效。基於上述能力邊界，**以下機制都做得到**：

1. **狀態累積 + 條件觸發**：用 `OnEnable` 設一個欄位（如 `_stack`），訂閱 `GetShaTrick`/`AddInjury`/`AttackSkillAttackHit` 等事件累加，達閾值時 `ShowSpecialEffectTips` + 用 §4 動詞改狀態。範式直接抄 Qimen9（九星落/七杀符同款）。
2. **連動自動釋放**：訂閱 `CastSkillEnd`/`UnlockAttackEnd`，條件成立呼 `DomainManager.Combat.CastSkillFree(...)`。
3. **被動加成（劍法 +X% 傷害 / 減消耗）**：用 `AffectDatas` + `GetModifiedValue` 多載，不需事件。
4. **正逆練不同效果**：用 `IsDirect` 分支，YAML 內 DirectEffectID / ReverseEffectID 指向同一個 ClassName 但行為靠 `IsDirect` 區分（mod 標準做法）。
5. **金剛宗劍法的「強化主功法」聯動**（解剖報告提到的佛王劍體系）：訂閱 `CastAttackSkillBegin`，偵測場上是否有特定 skillId，動態 buff。

**唯一要注意的邊界**：所有這些都在 **backend** 跑，特效類別必須編進 backend plugin，且命名空間掛 `GameData.Domains.SpecialEffect.*`。前端 plugin 只負責讓 UI 認得新武功，不寫戰鬥邏輯。

---

## 6. 仍待補（不阻擋 B，但日後要查）
- **trickType 常數表**：目前只確認 19=殺式。完整列舉在 `GameData.Shared.Enum` 或 `CombatDomain` 常數，需查。
- **bodyPart 常數**：AddInjury 的 sbyte bodyPart 對應哪些部位。
- **stateType / stateId**：`AddCombatState` 的兩個參數語意。
- **`AffectedDataKey` 第二參數（dataType）對照表**：Qimen9 用了 199，需查 `AffectedDataKey` 的 dataType 列舉。
- **`power` 與「成」的換算**：CastSkillEnd 的 sbyte power（0–10 對應 0–十成？）。

---

## 7. 參考檔案
- `~/dev/taiwu-src/backend/GameData/GameData/DomainEvents/Events.cs`（事件總表）
- `~/dev/taiwu-src/backend/GameData/GameData/Domains/SpecialEffect/SpecialEffectBase.cs`
- `~/dev/taiwu-src/backend/GameData/GameData/Domains/SpecialEffect/CombatSkill/CombatSkillEffectBase.cs`
- `~/dev/taiwu-src/backend/GameData/GameData/Domains/Combat/CombatDomain.cs`
- `<遊戲>/Backend/` 目錄（架構證據）
