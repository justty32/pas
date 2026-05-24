# 太吾繪卷 NPC 過月行為 — 分類清單

> 來源：反編譯 `~/dev/taiwu-src/Assembly-CSharp/Config/<Table>.cs` + `<Table>Item.cs`；名稱取自安裝版 `ConfigRefNameMapping/<Table>.ref.txt`（權威），說明（Desc）取自 `Language_CN/<Pack>_language.txt`。
> 抽取腳本：`extract_npc_month_behavior.py`；原始資料：`npc_month_behavior.json`。各欄位含義與接入過月迴圈的說明見 `README.md`。

本檔依「主題」分節，每筆列名稱＋說明。AiAction/AiCondition/AiNode/AiParam/BehaviorType 有 Desc；MonthlyActions/PrioritizedActions 以名稱＋可解欄位為主。

## 1. 月度行動 MonthlyActions（84 筆）— NPC 每月可執行行動清單（核心）

NPC 每月可被指派/觸發執行的行動清單（多為奇遇、招親、劇情、妖魔巢穴等「場景型」行動）。欄位：搜尋範圍 / 是否妖魔巢穴 / 可否提前行動 / 準備時長(月) / 預告時間(月) / 最短間隔(月) / 失敗後最短間隔(月)。

| Id | 名稱 | 搜尋範圍 | 妖魔巢穴 | 可提前 | 準備時長 | 預告 | 最短間隔 | 失敗間隔 |
|---:|---|---:|:---:|:---:|---:|---:|---:|---:|
| 0 | 奇遇-京城招亲-前置准备 | 1 |  | 是 | 6 | 2 | 36 | 0 |
| 1 | 奇遇-成都招亲-前置准备 | 1 |  | 是 | 6 | 2 | 36 | 0 |
| 2 | 奇遇-桂州招亲-前置准备 | 1 |  | 是 | 6 | 2 | 36 | 0 |
| 3 | 奇遇-襄阳招亲-前置准备 | 1 |  | 是 | 6 | 2 | 36 | 0 |
| 4 | 奇遇-太原招亲-前置准备 | 1 |  | 是 | 6 | 2 | 36 | 0 |
| 5 | 奇遇-广州招亲-前置准备 | 1 |  | 是 | 6 | 2 | 36 | 0 |
| 6 | 奇遇-青州招亲-前置准备 | 1 |  | 是 | 6 | 2 | 36 | 0 |
| 7 | 奇遇-江陵招亲-前置准备 | 1 |  | 是 | 6 | 2 | 36 | 0 |
| 8 | 奇遇-福州招亲-前置准备 | 1 |  | 是 | 6 | 2 | 36 | 0 |
| 9 | 奇遇-辽阳招亲-前置准备 | 1 |  | 是 | 6 | 2 | 36 | 0 |
| 10 | 奇遇-秦州招亲-前置准备 | 1 |  | 是 | 6 | 2 | 36 | 0 |
| 11 | 奇遇-大理招亲-前置准备 | 1 |  | 是 | 6 | 2 | 36 | 0 |
| 12 | 奇遇-寿春招亲-前置准备 | 1 |  | 是 | 6 | 2 | 36 | 0 |
| 13 | 奇遇-杭州招亲-前置准备 | 1 |  | 是 | 6 | 2 | 36 | 0 |
| 14 | 奇遇-扬州招亲-前置准备 | 1 |  | 是 | 6 | 2 | 36 | 0 |
| 15 | 奇遇-恶丐窝-前置准备 | 0 | 是 | 是 | 0 | 0 | 0 | 0 |
| 16 | 奇遇-贼人营寨-前置准备 | 0 | 是 | 是 | 0 | 0 | 0 | 0 |
| 17 | 奇遇-恶人谷-前置准备 | 0 | 是 | 是 | 0 | 0 | 0 | 0 |
| 18 | 奇遇-悍匪砦-前置准备 | 0 | 是 | 是 | 0 | 0 | 0 | 0 |
| 19 | 奇遇-叛徒结伙-前置准备 | 0 | 是 | 是 | 0 | 0 | 0 | 0 |
| 20 | 奇遇-迷香阵-前置准备 | 0 | 是 | 是 | 0 | 0 | 0 | 0 |
| 21 | 奇遇-异士居-前置准备 | 0 | 是 | 是 | 0 | 0 | 0 | 0 |
| 22 | 奇遇-乱葬岗-前置准备 | 0 | 是 | 是 | 0 | 0 | 0 | 0 |
| 23 | 奇遇-修罗场-前置准备 | 1 | 是 | 是 | 2 | 0 | 0 | 0 |
| 24 | 奇遇-群魔乱舞-前置准备 | 0 | 是 | 是 | 2 | 0 | 0 | 0 |
| 25 | 奇遇-弃世绝境-前置准备 | 1 | 是 | 是 | 2 | 0 | 0 | 0 |
| 26 | 奇遇-邪人死地-前置准备 | 1 | 是 | 是 | 2 | 0 | 0 | 0 |
| 27 | 奇遇-义士堂-前置准备 | 0 | 是 | 是 | 0 | 0 | 0 | 0 |
| 28 | 奇遇-任侠会盟-前置准备 | 0 | 是 | 是 | 0 | 0 | 0 | 0 |
| 29 | 奇遇-世外秘境-前置准备 | 0 | 是 | 是 | 0 | 0 | 0 | 0 |
| 30 | 奇遇-武林大会-前置准备 | 2 |  | 是 | 0 | 0 | 0 | 0 |
| 31 | 奇遇-京城招亲女-前置准备 | 1 |  | 是 | 6 | 2 | 0 | 0 |
| 32 | 奇遇-成都招亲女-前置准备 | 1 |  | 是 | 6 | 2 | 0 | 0 |
| 33 | 奇遇-桂州招亲女-前置准备 | 1 |  | 是 | 6 | 2 | 0 | 0 |
| 34 | 奇遇-襄阳招亲女-前置准备 | 1 |  | 是 | 6 | 2 | 0 | 0 |
| 35 | 奇遇-太原招亲女-前置准备 | 1 |  | 是 | 6 | 2 | 0 | 0 |
| 36 | 奇遇-广州招亲女-前置准备 | 1 |  | 是 | 6 | 2 | 0 | 0 |
| 37 | 奇遇-青州招亲女-前置准备 | 1 |  | 是 | 6 | 2 | 0 | 0 |
| 38 | 奇遇-江陵招亲女-前置准备 | 1 |  | 是 | 6 | 2 | 0 | 0 |
| 39 | 奇遇-福州招亲女-前置准备 | 1 |  | 是 | 6 | 2 | 0 | 0 |
| 40 | 奇遇-辽阳招亲女-前置准备 | 1 |  | 是 | 6 | 2 | 0 | 0 |
| 41 | 奇遇-秦州招亲女-前置准备 | 1 |  | 是 | 6 | 2 | 0 | 0 |
| 42 | 奇遇-大理招亲女-前置准备 | 1 |  | 是 | 6 | 2 | 0 | 0 |
| 43 | 奇遇-寿春招亲女-前置准备 | 1 |  | 是 | 6 | 2 | 0 | 0 |
| 44 | 奇遇-杭州招亲女-前置准备 | 1 |  | 是 | 6 | 2 | 0 | 0 |
| 45 | 奇遇-扬州招亲女-前置准备 | 1 |  | 是 | 6 | 2 | 0 | 0 |
| 46 | 奇遇-门派较武少林-前置准备 | 2 |  |  | 2 | 2 | 24 | 1 |
| 47 | 奇遇-门派较武峨眉-前置准备 | 2 |  |  | 2 | 2 | 24 | 1 |
| 48 | 奇遇-门派较武百花-前置准备 | 2 |  |  | 2 | 2 | 24 | 1 |
| 49 | 奇遇-门派较武武当-前置准备 | 2 |  |  | 2 | 2 | 24 | 1 |
| 50 | 奇遇-门派较武元山-前置准备 | 2 |  |  | 2 | 2 | 24 | 1 |
| 51 | 奇遇-门派较武狮相-前置准备 | 2 |  |  | 2 | 2 | 24 | 1 |
| 52 | 奇遇-门派较武然山-前置准备 | 2 |  |  | 2 | 2 | 24 | 1 |
| 53 | 奇遇-门派较武璇女-前置准备 | 2 |  |  | 2 | 2 | 24 | 1 |
| 54 | 奇遇-门派较武铸剑-前置准备 | 2 |  |  | 2 | 2 | 24 | 1 |
| 55 | 奇遇-门派较武空桑-前置准备 | 2 |  |  | 2 | 2 | 24 | 1 |
| 56 | 奇遇-门派较武金刚-前置准备 | 2 |  |  | 2 | 2 | 24 | 1 |
| 57 | 奇遇-门派较武五仙-前置准备 | 2 |  |  | 2 | 2 | 24 | 1 |
| 58 | 奇遇-门派较武界青-前置准备 | 2 |  |  | 2 | 2 | 24 | 1 |
| 59 | 奇遇-门派较武伏龙-前置准备 | 2 |  |  | 2 | 2 | 24 | 1 |
| 60 | 奇遇-门派较武血犼-前置准备 | 2 |  |  | 2 | 2 | 24 | 1 |
| 61 | 奇遇-春日集市-前置准备 | 0 |  |  | 2 | 2 | 0 | 0 |
| 62 | 奇遇-比武大会·拳掌-前置准备 | 2 |  |  | 2 | 2 | 0 | 0 |
| 63 | 奇遇-比武大会·指法-前置准备 | 2 |  |  | 2 | 2 | 0 | 0 |
| 64 | 奇遇-比武大会·腿法-前置准备 | 2 |  |  | 2 | 2 | 0 | 0 |
| 65 | 奇遇-比武大会·暗器-前置准备 | 2 |  |  | 2 | 2 | 0 | 0 |
| 66 | 奇遇-比武大会·剑法-前置准备 | 2 |  |  | 2 | 2 | 0 | 0 |
| 67 | 奇遇-比武大会·刀法-前置准备 | 2 |  |  | 2 | 2 | 0 | 0 |
| 68 | 奇遇-比武大会·长兵-前置准备 | 2 |  |  | 2 | 2 | 0 | 0 |
| 69 | 奇遇-比武大会·奇门-前置准备 | 2 |  |  | 2 | 2 | 0 | 0 |
| 70 | 奇遇-比武大会·软兵-前置准备 | 2 |  |  | 2 | 2 | 0 | 0 |
| 71 | 奇遇-比武大会·御射-前置准备 | 2 |  |  | 2 | 2 | 0 | 0 |
| 72 | 奇遇-比武大会·乐器-前置准备 | 2 |  |  | 2 | 2 | 0 | 0 |
| 73 | 奇遇-促织大会-前置准备 | 2 |  |  | 2 | 2 | 0 | 0 |
| 74 | 奇遇-较艺大会·锻造-前置准备 | 2 |  |  | 2 | 2 | 0 | 0 |
| 75 | 奇遇-较艺大会·制木-前置准备 | 2 |  |  | 2 | 2 | 0 | 0 |
| 76 | 奇遇-较艺大会·织锦-前置准备 | 2 |  |  | 2 | 2 | 0 | 0 |
| 77 | 奇遇-较艺大会·巧匠-前置准备 | 2 |  |  | 2 | 2 | 0 | 0 |
| 78 | 奇遇-较艺大会·医术-前置准备 | 2 |  |  | 2 | 2 | 0 | 0 |
| 79 | 奇遇-较艺大会·毒术-前置准备 | 2 |  |  | 2 | 2 | 0 | 0 |
| 80 | 奇遇-较艺大会·厨艺-前置准备 | 2 |  |  | 2 | 2 | 0 | 0 |
| 81 | 奇遇-何为正宗-前置准备 | 0 |  | 是 | 0 | 0 | 0 | 0 |
| 82 | 奇遇-三宗比武-前置准备 | 0 |  | 是 | 0 | 0 | 0 | 0 |
| 83 | 奇遇-试剑大典-前置准备 | 0 |  | 是 | 0 | 0 | 0 | 0 |

## 2. AI 行動 AiAction（59 筆）— AI 行動定義（含說明）

AI 決策樹（主要為戰鬥行為樹，亦含通用）的「行動」原語，每筆含類型(EAiActionType)與說明。

| Id | 名稱 | 類型 | 說明(Desc) |
|---:|---|---|---|
| 0 | 普攻 | NormalAttack | 执行一次普攻 |
| 1 | 普攻1 | ChangeTrick | 执行变招攻击，使用记忆功法 {0} 部位与蓄式 |
| 2 | 普攻2 | ChangeTrickFlaw | 执行变招破绽，使用记忆功法 {0} 部位与蓄式 |
| 3 | 普攻3 | ChangeTrickAcupoint | 执行变招封穴 {1}，使用记忆功法 {0} 蓄式 |
| 4 | 普攻4 | ChangeTrickNeiliType | 执行变招改内力属性，使用记忆功法 {0} 蓄式 |
| 5 | 功法 | CastSkill | 施展特定功法 {0} |
| 6 | 功法1 | CastSkillAttackBest | 施展最佳摧破功法 |
| 7 | 功法2 | CastSkillDefendBest | 施展最佳护体功法 |
| 8 | 功法3 | CastSkillDefendBlock | 施展恢复招架的护体 |
| 9 | 功法4 | CastSkillAgileBuff | 施展增益类身法 |
| 10 | 功法5 | CastSkillAgileSpeed | 施展速度最快的身法 |
| 11 | 功法6 | CastSkillCastBoost | 执行施展增幅 |
| 12 | 移动0 | MoveToAttackRangeCenter | 设置目标距离为攻击范围正中 + {0} |
| 13 | 移动1 | MoveToNearbyEscape | 设置目标距离为对方攻击范围边缘 |
| 14 | 移动2 | MoveToTargetDistance | 设置目标距离为 {0} |
| 15 | 移动3 | MoveToFarthest | 设置目标距离为战场最远距离 |
| 16 | 记忆0 | MemorySetString | 设置记忆中 {0} 为 {1} |
| 17 | 记忆1 | MemorySetBoolean | 设置记忆中 {0} 为 {1} |
| 18 | 记忆2 | MemorySet | 设置记忆中 {0} 为 {1} |
| 19 | 同道指令 | UseTeammateCommand | 执行 {0} 指令 |
| 20 | 武器 | ChangeWeaponAuto | 从索引 {0} - {1} 中切换到当前距离兵器 |
| 21 | 行为 | UseOtherAction | 预约行为 {0} |
| 22 | 道具0 | UseItemHealInjury | 使用疗伤药 |
| 23 | 道具1 | UseItemHealPoison | 使用驱毒药 |
| 24 | 道具2 | UseItemHealQiDisorder | 使用内息药 |
| 25 | 道具3 | UseItemBuff | 使用增益药 |
| 26 | 道具4 | UseItemPoison | 使用毒药 |
| 27 | 道具5 | UseItemNeili | 使用血露 |
| 28 | 道具6 | UseItemWine | 使用酒 |
| 29 | 道具7 | UseItemRepairWeapon | 修理兵器 |
| 30 | 道具8 | UseItemRepairArmor | 修理防具 |
| 31 | 武器1 | ChangeWeaponIndex | 切换至索引为 {0} 的兵器 |
| 32 | 武器2 | ChangeWeaponSpecial | 切换至兵器 {0} |
| 33 | 武器3 | ChangeWeaponType | 切换至 {0} 类兵器 |
| 34 | 记忆3 | MemoryAdd | 记忆中 {0} 对应值加上 {1}，如记忆中不存在该值则取值为零进行叠加 |
| 35 | 中断0 | InterruptCasting | 中断正在施展的功法 |
| 36 | 中断1 | InterruptAffectingDefense | 中断当前运起的护体 |
| 37 | 记忆4 | MemoryInternalSetString | 设置记忆中 {0} 对应文本为 {1} 对应文本 |
| 38 | 记忆5 | MemoryInternalSetBoolean | 设置记忆中 {0} 对应布尔为 {1} 对应布尔 |
| 39 | 记忆6 | MemoryInternalSet | 设置记忆中 {0} 对应值为 {1} 对应值 |
| 40 | 记忆7 | MemorySetAllMarkCount | 设置记忆中 {0} 为 {1} 所有标记个数 |
| 41 | 记忆8 | MemorySetInjuryMarkCount | 设置记忆中 {0} 为 {1} 所有部位伤势标记个数 |
| 42 | 记忆9 | MemorySetFlawMarkCount | 设置记忆中 {0} 为 {1} 所有部位破绽标记个数 |
| 43 | 记忆10 | MemorySetAcupointMarkCount | 设置记忆中 {0} 为 {1} 所有部位封穴标记个数 |
| 44 | 记忆11 | MemorySetPoisonMarkCount | 设置记忆中 {0} 为 {1} 所有毒素标记个数 |
| 45 | 记忆12 | MemorySetMindMarkCount | 设置记忆中 {0} 为 {1} 失神标记个数 |
| 46 | 记忆13 | MemorySetFatalMarkCount | 设置记忆中 {0} 为 {1} 重创标记个数 |
| 47 | 记忆14 | MemorySetChangeTrickCountByFlawCost | 设置记忆中 {0} 为 {1} 当前可变招破绽次数（斩杀用） |
| 48 | 记忆15 | MemorySetSpecialCombatSkill | 设置记忆中 {0} 为功法 {1} |
| 49 | 移动4 | MoveToAttackRangeEdge | 设置目标距离为攻击范围 {0} 边缘 + {1} |
| 50 | 记忆16 | MemorySetLastPrepareCombatSkill | 设置记忆中 {0} 为 {1} 当前或上次施展的功法，缺省设置为 -1 |
| 51 | 优先级0 | PrioritySetHigh | 设置记忆中 {0} 对应功法为高优先级 |
| 52 | 优先级1 | PrioritySetLow | 设置记忆中 {0} 对应功法为低优先级 |
| 53 | 优先级2 | PriorityReset | 重置记忆中 {0} 对应功法已设置的优先级 |
| 54 | 记忆17 | MemorySetBestAttackCombatSkill | 设置记忆中 {0} 为当前可施展的最佳摧破功法，缺省设置为 -1 |
| 55 | 功法7 | CastSkillByMemory | 施展记忆中功法 {0} |
| 56 | 中断2 | InterruptAffectingMove | 中断当前运起的身法 |
| 57 | 解封1 | UnlockAttackWeapon | 使用兵器 {0} 执行一次解封 |
| 58 | 解封2 | UnlockAttackWeaponType | 使用兵器类型 {0} 执行一次解封 |

## 3. 行為大類 BehaviorType（5 筆）— 行為大類（道德傾向）

NPC 的道德傾向大類，決定其在過月時對各「優先級行動」的偏好（見 PrioritizedActions.MoralityPriority 的 5 個權重，順序即此表 0~4）。

| Id | 名稱 | 說明(Desc) |
|---:|---|---|
| 0 | 刚正 | 刚正不阿之侠者，处世黑白分明。 除恶则必尽，树德则必滋。世事纵有千变万化，正道总是仅此一条！ |
| 1 | 仁善 | 慈悲仁义者，品行殊高洁。 扶危能够舍己，济世能够忘我。可以报怨以德，宛然浑金璞玉一般。 |
| 2 | 中庸 | 中庸无为者，处世不偏不倚。 凡事顺其自然，但求折中调和。心中既少了正邪之分，或许终能成就开明大道？ |
| 3 | 叛逆 | 叛逆处世者，直性狭中、黑白颠倒。 “应笑”而不笑、“应喜”而不喜、“应慈”而不慈、“闻恶”而不改、“闻善”而不乐。 |
| 4 | 唯我 | 世间唯我者，凌弱者，伐异己，党邪佞，欺良善。 为达目的不择手段，唯利是图无情无义。 |

## 4. 優先級行動 PrioritizedActions（23 筆）— 優先級行動設定（過月每月先選一個高優先行為）

NPC 過月時先挑選的高優先（劇情/強制性）行為。`MoralityPriority` 為 5 種道德型的偏好權重（順序＝BehaviorType 0~4：刚正/仁善/中庸/叛逆/唯我）。名稱取自 ref（對應 `PrioritizedActionType` 的 switch templateId）。`RefuseAppointment` 為「因執行此行動而婉拒太吾召喚」的台詞（多數為空）。

| Id | 名稱 | ActType | 基礎優先 | 道德權重[刚/仁/中/叛/唯] | 冷卻 | 時長 | 限成年 | 限非首領 | 限非僧 | 拒約台詞 |
|---:|---|---|---:|---|---:|---:|:---:|:---:|:---:|---|
| 0 | 拜师学艺 | Normal | 0 | [90, 90, 90, 90, 90] | 6 | 12 |  |  |  |  |
| 1 | 受邀赴约 | Normal | 0 | [80, 50, 80, 20, 60] | 0 | 0 |  |  |  |  |
| 2 | 保护亲友 | Normal | 0 | [60, 60, 40, 60, 10] | 3 | 4 | 是 |  |  | “我尚要保护亲友，此事不容疏漏，恕我暂时不能受你之邀……” |
| 3 | 解救亲友 | Normal | 0 | [70, 70, 50, 70, 20] | 3 | 4 | 是 |  |  | “我尚要援救亲友，此事不容疏漏，恕我暂时不能受你之邀……” |
| 4 | 祭拜故人 | Normal | 0 | [30, 40, 10, 0, 30] | 12 | 3 |  |  |  |  |
| 5 | 探访亲友 | Normal | 0 | [20, 30, 30, 10, 0] | 6 | 3 |  | 是 |  |  |
| 6 | 寻找宝藏 | Normal | 0 | [0, 10, 60, 30, 70] | 3 | 6 |  |  |  |  |
| 7 | 天材地宝 | Normal | 0 | [10, 20, 70, 40, 80] | 0 | 6 |  |  |  |  |
| 8 | 寻仇报复 | Normal | 0 | [40, 0, 0, 80, 50] | 6 | 6 |  |  |  |  |
| 9 | 奇书争夺 | Normal | 0 | [100, 100, 100, 100, 100] | 36 | 24 | 是 | 是 |  | “我尚要寻求奇书，此事不容疏漏，恕我暂时不能受你之邀……” |
| 10 | 收养弃婴 | Normal | 0 | [50, 80, 20, 50, 40] | 0 | 3 | 是 |  | 是 | “我尚要收养弃婴，此事不容疏漏，恕我暂时不能受你之邀……” |
| 11 | 抗击三魔 | SectStory | 90 | [100, 100, 100, 100, 100] | 0 | -1 |  |  |  | “我尚要抵御三魔，此事不容疏漏，恕我暂时不能受你之邀……” |
| 12 | 消灭敌人 | SectStory | 90 | [100, 100, 100, 100, 100] | 0 | -1 |  |  |  | “我尚要驱逐来敌，此事不容疏漏，恕我暂时不能受你之邀……” |
| 13 | 同门相残 | SectStory | 90 | [100, 100, 100, 100, 100] | 0 | -1 |  |  |  | “我尚要挑战同门，此事不容疏漏，恕我暂时不能受你之邀……” |
| 14 | 似曾相识 | DreamBack | 99 | [100, 100, 100, 100, 100] | 0 | 0 |  |  |  |  |
| 15 | 守卫公库 | Normal | 100 | [100, 80, 60, 30, 40] | 0 | -1 |  |  |  | “我尚要守卫库房，此事不容疏漏，恕我暂时不能受你之邀……” |
| 16 | 治疗死气 | Normal | 0 | [80, 90, 70, 60, 50] | 3 | 6 |  | 是 |  | “我尚要医治疯症，此事不容疏漏，恕我暂时不能受你之邀……” |
| 17 | 抓捕逃犯 | Normal | 0 | [80, 50, 30, 60, 20] | 0 | -1 | 是 |  |  | “我尚要抓捕逃犯，此事不容疏漏，恕我暂时不能受你之邀……” |
| 18 | 畏罪潜逃 | Normal | 100 | [100, 100, 100, 100, 100] | 0 | -1 |  |  |  | “我尚有要事在身，性命攸关，不容疏漏，恕我暂时不能受你之邀……” |
| 19 | 寻求庇护 | Normal | 101 | [100, 100, 100, 100, 100] | 0 | -1 |  |  |  | “我尚有要事在身，性命攸关，不容疏漏，恕我暂时不能受你之邀……” |
| 20 | 押送囚犯 | Normal | 100 | [100, 100, 100, 100, 100] | 0 | -1 |  |  |  | “我尚要押送囚犯，此事不容疏漏，恕我暂时不能受你之邀……” |
| 21 | 村民身份 | Normal | 100 | [100, 100, 100, 100, 100] | 0 | -1 |  |  |  | “我尚有太吾村事务在身，不容疏漏，恕我暂时不能受你之邀……” |
| 22 | 追杀太吾 | Normal | 0 | [80, 50, 30, 60, 20] | 3 | -1 | 是 |  |  | “我尚有要事在身，此事不容疏漏，恕我暂时不能受你之邀……” |

## 5. 村民自動行動（太吾村）

### 5.1 村民職務安排 VillagerRoleArrangement（13 筆）— 村民職務安排（村民過月自動執行的職務）

玩家為太吾村村民指派的職務；村民過月時自動執行對應產出（對應優先級行動 id=21「村民身份」VillagerRoleArrangementAction）。`ShortName` 在反編譯語言檔多為空（版本漂移）。

| Id | 名稱 | 所屬角色(VillagerRole) | 說明(Desc) |
|---:|---|---:|---|
| 0 | 义诊扶危 | 2 | <color=#pinkyellow>举炊备膳：可以派遣多名农户前往<color=#orange>「食窖」</color>进行烹饪…</color>  - 派遣主事至<color=#orange>「食窖」</color>后，方能「举炊备膳」，亦可派遣伙计加快烹饪的进度…  -<SpName=mousetip_jiyi_14>「厨艺」造诣越高，烹饪出品级较高的食物的概率越高…  - 可以消耗<SpName=mousetip_ziyuan_0>「食材」加快烹饪的进度… |
| 1 | 外出经商 | 3 | <color=#pinkyellow>采集资源：可派遣农户在地格上采集指定的资源…</color> |
| 2 | 江湖游艺 | 3 | <color=#pinkyellow>迁移资源：在派遣农户时选择「迁移」，将以毁坏资源丰饶的地形为代价，获取对应的心材…</color>  -<SpName=mousetip_qiyuan_6>「合道」越高，迁移的成功率越高… |
| 3 | 看守剑冢 | 3 | <color=#pinkyellow>精耕细作：在农户迁移资源时，有几率得到更高级的「资源心材」…</color>  -<SpName=mousetip_qiyuan_6>「合道」越高，获得高级「资源心材」的几率越高… |
| 4 | 太吾使者 | 3 | <color=#pinkyellow>制造物品：可以派遣多名匠人前往<color=#orange>「火炼室」</color><color=#orange>「木工房」</color><color=#orange>「绣楼」</color><color=#orange>「巧匠屋」</color>进行制造…</color>  - 派遣主事至<color=#orange>「火炼室」</color><color=#orange>「木工房」</color><color=#orange>「绣楼」</color><color=#orange>「巧匠屋」</color>后，方能制造物品，亦可派遣伙计加快制造的进度…  - 对应<SpName=mousetip_lifeskillcircular>「技艺」造诣越高，制造出品级较高物品的几率越高…  - 可以消耗对应的制造资源加快制造的进度… |
| 5 | 资源采集 | 4 | <color=#pinkyellow>制药炼毒：可以派遣多名大夫前往<color=#orange>「药房」</color><color=#orange>「幽室」</color>炼制药物及毒药…</color>  - 派遣掌柜至<color=#orange>「药房」</color><color=#orange>「幽室」</color>后，方能炼药制毒，亦可派遣门生加快炼制的进度…  - 对应<SpName=mousetip_lifeskillcircular>「技艺」造诣越高，制造出品级较高药毒的几率越高…  - 可以消耗<SpName=mousetip_ziyuan_5>「药材」加快制造的进度… |
| 6 | 资源迁移 | 4 | <color=#pinkyellow>义诊扶危：指定一个开通驿站的地区，派遣大夫为该地区的人物<SpName=mousetip_injury>「疗伤」<SpName=mousetip_poison>「驱毒」<SpName=mousetip_neixiwenluan>「调息」<SpName=mousetip_jiankang>「复元」，并收获<SpName=mousetip_enyi>「地区恩义」…</color>  -<SpName=mousetip_qiyuan_0>「冷静」越高，可为<SpName=mousetip_character>「身份」品阶越高的病患进行治疗…  -<SpName=mousetip_jiyi_8>「医术」或<SpName=mousetip_jiyi_9>「毒术」造诣越高，或病患的<SpName=mousetip_character>「身份」品阶越高，获得的<SpName=mousetip_enyi>「地区恩义」越多… |
| 7 | 精耕细作 | 4 | <color=#pinkyellow>养心调志：派遣大夫进行「义诊扶危」时，可减少该地区「入邪之人」受到的<SpName=mousetip_rumo>「相枢邪念」侵袭…</color>  -<SpName=mousetip_qiyuan_0>「冷静」越高，<SpName=mousetip_jiyi_8>「医术」或<SpName=mousetip_jiyi_9>「毒术」造诣越高，减少的<SpName=mousetip_rumo>「相枢邪念」越多… |
| 8 | 养心调志 | 4 | <color=#pinkyellow>经商行贾：指定一个开通驿站的地区，派遣商人前往该地区买卖物品…</color>  -<SpName=mousetip_qiyuan_2>「热情」越高，可当地与<SpName=mousetip_character>「身份」品阶越高的人物进行买卖…  -<SpName=mousetip_jiyi_15>「杂学」造诣越高，买入物品价格越低，卖出物品价格越高… |
| 9 | 商会联络 | 5 | <color=#pinkyellow>商会联络：商人受派遣「经商行贾」时，可每月增加受派遣地区商会的<SpName=mousetip_multilove>「好感」…</color>  -<SpName=mousetip_qiyuan_2>「热情」越高，<SpName=mousetip_jiyi_15>「杂学」造诣越高，增加的商会<SpName=mousetip_multilove>「好感」越多…  - 派遣至商会总部所在地时，可增加此商会更多<SpName=mousetip_multilove>「好感」… |
| 10 | 江湖联络 | 5 |  |
| 11 | 挺身降魔 | 5 |  |
| 12 | 举炊备膳 | 5 |  |

### 5.2 村民角色 VillagerRole（7 筆）— 村民角色（職業類別，職務安排的母類）

村民的職業母類（農戶/匠人/大夫…），其下掛各職務安排。`EffectTexts` 為效果項標籤（部分索引在反編譯語言檔越界＝版本漂移）。

| Id | 名稱 | 對應職稱(OrganizationMember) | 效果項數 | 效果標籤(節選) |
|---:|---|---:|---:|---|
| 0 | 太吾村农户 | 17 | 5 | 迁移成功率、心材升级几率、采集次数、+{0}%、+{0}次 |
| 1 | 太吾村匠人 | 16 | 5 | 修理次数、获得精制物品几率、升级精制物品几率、最高可义诊病患、减轻相枢邪念侵袭 |
| 2 | 太吾村大夫 | 15 | 7 | +{0}阶、生效、最高可买卖经商、增加商会好感、改变安定或文化次数 |
| 3 | 太吾村商人 | 14 | 6 | +{0}人、收集剑冢见闻几率、抵御化身时受伤几率、获得特性几率、降低相枢邪念侵袭 |
| 4 | 太吾村文人 | 13 | 9 | 提高、可修改额外法规数目、人情世故影响人物对数、缘来如此生效概率、+{0}条 |
| 5 | 太吾村护冢 | 12 | 10 |  |
| 6 | 太吾村村长 | 11 | 5 |  |

## 6. AI 決策樹家族（NPC/戰鬥 AI 設定表）

這些是 AI 行為樹（含戰鬥 AI 與通用 AI）的設定原語。名稱皆能由 ref 解出；AiAction 已於 §2 列出，此處列其餘各表。

### 6.1 AiNode（3 筆）— AI 決策樹節點種類（順序/分支/行為）

| Id | 名稱 | 類型 | 是否行為節點 | 說明(Desc) |
|---:|---|---|:---:|---|
| 0 | 顺序 | Linear |  | 顺序执行所有子节点直到行为节点 |
| 1 | 分支 | Branch |  | 根据条件判定接下来执行的节点 |
| 2 | 行为 | Action | 是 | 执行特定行为 |

### 6.2 AiCondition（114 筆）— AI 決策條件定義（含說明）

AI 決策樹的「條件」原語（分支節點的判定）。

| Id | 名稱 | 類型 | 說明(Desc) |
|---:|---|---|---|
| 0 | 延迟 | Delay | 每 {0} 返回一次真值 |
| 1 | 概率 | CheckPercentProb | 当判定 {0}% 概率通过时返回真值 |
| 2 | 首次 | First | 每场战斗首次执行到该条件时返回真值 |
| 3 | 功法0 | EquipCombatSkill | 当 {0} 运功栏含有 {1} 时返回真值 |
| 4 | 功法1 | BreakCombatSkill | 当 {0} 已突破 {1} {2} 时返回真值 |
| 5 | 功法2 | LearnCombatSkill | 当 {0} 已习得 {1} 时返回真值 |
| 6 | 位置0 | InCurrentAttackRange | 当前距离 +{1} 处于 {0} 的普攻或施展中摧破攻击范围时返回真值 |
| 7 | 位置1 | InCombatSkillRange | 当前距离 +{1} 处于 {0} 的功法 {2} 施展范围时返回真值 |
| 8 | 位置2 | AnyAttackRangeEdge | 当 {0} 存在有效的攻击范围边缘时返回真值 |
| 9 | 记忆等于0 | MemoryEqualString | 当记忆中 {0} 对应值与 {1} 相同时返回真值 |
| 10 | 记忆等于1 | MemoryEqualBoolean | 当记忆中 {0} 对应值与 {1} 相同时返回真值 |
| 11 | 记忆等于2 | MemoryEqual | 当记忆中 {0} 对应值与 {1} 相同时返回真值 |
| 12 | 记忆不等0 | MemoryNotEqualString | 当记忆中 {0} 无对应值或与 {1} 不相同时返回真值 |
| 13 | 记忆不等1 | MemoryNotEqualBoolean | 当记忆中 {0} 无对应值或与 {1} 不相同时返回真值 |
| 14 | 记忆不等2 | MemoryNotEqual | 当记忆中 {0} 无对应值或与 {1} 不相同时返回真值 |
| 15 | 记忆大于 | MemoryAbove | 当记忆中 {0} 对应值大于 {1} 时返回真值 |
| 16 | 记忆小于 | MemoryBelow | 当记忆中 {0} 对应值小于 {1} 时返回真值 |
| 17 | 战斗难度 | CombatDifficulty | 当角色为太吾或战斗难度不低于 {0} 时返回真值 |
| 18 | 目标距离0 | TargetDistanceNearby | 目标距离偏向 {0} |
| 19 | 目标距离1 | TargetDistanceIsNot | 目标距离不为 {0} |
| 20 | 目标距离2 | TargetDistanceIsNotFarthest | 目标距离不为最远距离 |
| 21 | 正在施展0 | CastingSkillType | {0} 正在施展 {1} |
| 22 | 正在施展1 | CastingSkill | {0} 正在施展功法 {1} |
| 23 | 功法进度0 | CastingProgressMoreOrEqual | {1} 功法施展进度不低于 {0}% 时返回真值 |
| 24 | 功法进度1 | CastingProgressLess | {1} 功法施展进度低于 {0}% 时返回真值 |
| 25 | 招架 | BlockPercentLess | 当 {1} 剩余招架值低于 {0}% 时返回真值 |
| 26 | 逃跑0 | IsCharacterHalfFallen | 当 {0} 战败标记过半时返回真值 |
| 27 | 逃跑1 | CheckBanFlee | 当己方不可逃跑或判定禁用逃跑通过时返回真值 |
| 28 | 逃跑2 | CheckFleeNormal | 当己方满足逃跑条件时返回真值 |
| 29 | 逃跑3 | InHazard | 当己方处于危险中时返回真值 |
| 30 | 选项0 | OptionAttack | 可以进行普攻 |
| 31 | 选项1 | OptionChangeTrick | 可以进行变招 |
| 32 | 选项2 | OptionChangeTrickFlaw | 可以变招破绽 |
| 33 | 选项3 | OptionChangeTrickAcupoint | 可以变招封穴 {0} |
| 34 | 选项4 | OptionChangeTrickNeiliType | 可以变招改内力属性 |
| 35 | 选项5 | OptionChangeWeapon | 当索引 {0} - {1} 之间存在可切换且处于攻击范围的武器时返回真值 |
| 36 | 选项6 | OptionTryDodge | 可以进行逃脱移动 |
| 37 | 选项7 | OptionOtherAction | 可以进行行为 {0} |
| 38 | 选项8 | OptionTeammateCommand | 存在可用的 {0} 指令 |
| 39 | 选项9 | OptionProactiveSkillType | 存在可用的 {0} 功法 |
| 40 | 选项10 | OptionCastBoost | 存在可用的施展增幅 |
| 41 | 选项11 | OptionCastDefendBlock | 存在恢复招架护体 |
| 42 | 选项12 | OptionCastAgileBuff | 存在增益身法 |
| 43 | 选项13 | OptionUseItemHealInjury | 存在可用的疗伤药 |
| 44 | 选项14 | OptionUseItemHealPoison | 存在可用的驱毒药 |
| 45 | 选项15 | OptionUseItemHealQiDisorder | 存在可用的内息药 |
| 46 | 选项16 | OptionUseItemBuff | 存在可用的增益药 |
| 47 | 选项17 | OptionUseItemPoison | 存在可用的毒药 |
| 48 | 选项18 | OptionUseItemNeili | 存在可用的血露 |
| 49 | 选项19 | OptionUseItemWine | 存在可用的酒 |
| 50 | 选项20 | OptionUseItemRepairWeapon | 存在可修理的兵器 |
| 51 | 选项21 | OptionUseItemRepairArmor | 存在可修理的防具 |
| 52 | 战斗类型 | CombatTypeEqual | 当战斗类型为 {0} 时返回真值 |
| 53 | 运起0 | AnyAffectingAgile | 当 {0} 已运起身法时返回真值 |
| 54 | 运起1 | SpecialAffectingAgile | 当 {0} 已运起身法 {1} {2} 时返回真值 |
| 55 | 运起2 | AnyAffectingDefense | 当 {0} 已运起护体时返回真值 |
| 56 | 运起3 | SpecialAffectingDefense | 当 {0} 已运起护体 {1} {2} 时返回真值 |
| 57 | 太吾 | IsTaiwu | 仅自身为太吾时返回真值 |
| 58 | 标记0 | InjuryMarkCountMoreOrEqual | 当 {0} {2} {3} 伤标记不低于 {1} 个时返回真值 |
| 59 | 标记1 | FlawMarkCountMoreOrEqual | 当 {0} {2} 破绽标记不低于 {1} 个时返回真值 |
| 60 | 标记2 | AcupointMarkCountMoreOrEqual | 当 {0} {2} 封穴标记不低于 {1} 个时返回真值 |
| 61 | 标记3 | PoisonMarkCountMoreOrEqual | 当 {0} {2} 标记不低于 {1} 个时返回真值 |
| 62 | 标记4 | MindMarkCountMoreOrEqual | 当 {0} 失神标记不低于 {1} 个时返回真值 |
| 63 | 标记5 | FatalMarkCountMoreOrEqual | 当 {0} 重创标记不低于 {1} 个时返回真值 |
| 64 | 标记6 | DieMarkCountMoreOrEqual | 当 {0} 必死标记不低于 {1} 个时返回真值 |
| 65 | 标记7 | QiDisorderMarkCountMoreOrEqual | 当 {0} 内息标记不低于 {1} 个时返回真值 |
| 66 | 标记8 | StateMarkCountMoreOrEqual | 当 {0} 状态标记不低于 {1} 个时返回真值 |
| 67 | 标记9 | HealthMarkCountMoreOrEqual | 当 {0} 健康标记不低于 {1} 个时返回真值 |
| 68 | 标记10 | HasGrowingWug | 当 {0} 有 {1} 且 {2} 的 {3} 蛊时返回真值 |
| 69 | 标记11 | HasGrownWug | 当 {0} 有 {1} 成蛊时返回真值 |
| 70 | 标记12 | HasKingWug | 当 {0} 有 {1} 王蛊时返回真值 |
| 71 | 标记13 | NeiliAllocationPercentMoreOrEqual | 当 {0} {1} 真气不低于 {2}% 时返回真值 |
| 72 | 功法效果 | CombatSkillEffectCountMoreOrEqual | 当 {0} 功法 {1} {2} 有 {3} 层效果时返回真值 |
| 73 | 脚力值 | MobilityPercentMoreOrEqual | 当 {1} 脚力值不低于 {0}% 时返回真值 |
| 74 | 疲怠中 | MobilityLocking | 弃用条件，当前会始终返回假值 |
| 75 | 精纯 | ConsummateLevelMoreOrEqual | 当角色为太吾或 {0} 精纯值不低于 {1} 时返回真值 |
| 76 | 阶段 | BossPhaseMoreOrEqual | 当战斗阶段不低于 {0} 时返回真值（首个阶段为零） |
| 77 | 式槽 | TrickCountMoreOrEqual | 当 {0} 式槽中 {1} 式数量不低于 {2} 个时返回真值 |
| 78 | 选项22 | OptionChangeWeaponIndex | 当索引为 {0} 的兵器可被切换时返回真值 |
| 79 | 选项23 | OptionChangeWeaponSpecial | 当存在可切换的兵器 {0} 时返回真值 |
| 80 | 选项24 | OptionChangeWeaponType | 当存在可切换的 {0} 类兵器时返回真值 |
| 81 | 当前武器0 | CurrentWeaponIsSpecial | 当 {0} 兵器为 {1} 时返回真值 |
| 82 | 当前武器1 | CurrentWeaponIsType | 当 {0} 兵器类型为 {1} 时返回真值 |
| 83 | 内力属性 | NeiliTypeFiveElementEqual | 当 {0} 内力属性五行为 {1} 时返回真值 |
| 84 | 标记14 | AllMarkCountMoreOrEqual | 当 {0} 所有标记不低于 {1} 个时返回真值 |
| 85 | 标记15 | OuterOrInnerInjuryMarkCountMoreOrEqual | 当 {0} 所有部位 {2} 伤标记不低于 {1} 个时返回真值 |
| 86 | 标记16 | AllInjuryMarkCountMoreOrEqual | 当 {0} 所有部位伤势标记不低于 {1} 个时返回真值 |
| 87 | 标记17 | AllFlawMarkCountMoreOrEqual | 当 {0} 所有部位破绽标记不低于 {1} 个时返回真值 |
| 88 | 标记18 | AllAcupointMarkCountMoreOrEqual | 当 {0} 所有部位封穴标记不低于 {1} 个时返回真值 |
| 89 | 记忆内大于 | MemoryInternalAbove | 当记忆中 {0} 对应值大于 {1} 对应值时返回真值 |
| 90 | 记忆内小于 | MemoryInternalBelow | 当记忆中 {0} 对应值小于 {1} 对应值时返回真值 |
| 91 | 记忆等于施展 | MemoryEqualCasting | 当记忆中 {0} 对应值与 {1} 正在施展的功法相同时返回真值 |
| 92 | 位置3 | AttackRangeEdgeMore | 当 {0} 攻击范围 {1} 边缘大于另一方攻击范围相同边缘时返回真值 |
| 93 | 位置4 | AttackRangeEdgeLess | 当 {0} 攻击范围 {1} 边缘小于另一方攻击范围相同边缘时返回真值 |
| 94 | 环境0 | EnvironmentLastNormalAttackAnyMiss | 上次普攻为当前武器，且首次攻击或追击被化解时返回真值 |
| 95 | 当前武器2 | CurrentWeaponIsIndex | 当 {0} 兵器索引为 {1} 时返回真值 |
| 96 | 正在施展2 | CastingDirectOrReverseSkill | {0} 正在施展功法 {1} {2} |
| 97 | 选项25 | OptionCastSpecialCombatSkill | 自身可施展功法 {0} 时返回真值 |
| 98 | 选项26 | OptionCastDirectOrReverseCombatSkill | 自身可施展功法 {0} 且该功法为 {1} 时返回真值 |
| 99 | 状态0 | BuffStatePowerSumMoreOrEqual | 当 {1} 存在名称为 {0} 的增益状态且总强度不低于 {2} 时返回真值 |
| 100 | 状态1 | DebuffStatePowerSumMoreOrEqual | 当 {1} 存在名称为 {0} 的损害状态且总强度不低于 {2} 时返回真值 |
| 101 | 状态2 | SpecialStatePowerSumMoreOrEqual | 当 {1} 存在名称为 {0} 的特殊状态且总强度不低于 {2} 时返回真值 |
| 102 | 位置5 | InMemoryCombatSkillRange | 当前距离 +{2} 处于 {1} 记忆中 {0} 对应值施展范围时返回真值 |
| 103 | 选项27 | OptionCastMemoryCombatSkill | 自身可施展记忆中 {0} 时返回真值 |
| 104 | 位置6 | CurrentDistanceEqual | 当前距离等于 {0} 时返回真值 |
| 105 | 位置7 | CurrentDistanceAbove | 当前距离大于 {0} 时返回真值 |
| 106 | 位置8 | CurrentDistanceBelow | 当前距离小于 {0} 时返回真值 |
| 107 | 环境1 | EnvironmentLastNormalAttackOutOfRange | 上次落空的普攻为当前武器，且未进行攻击时返回真值 |
| 108 | 选项28 | OptionUnlockAttackWeapon | 当存在可解封的兵器 {0} 时返回真值 |
| 109 | 选项29 | OptionUnlockAttackWeaponType | 当存在可解封的兵器类型 {0} 时返回真值 |
| 110 | 解封值 | UnlockAttackValuePercentMoreOrEqual | 当 {1} 有兵器 {2} 解封进度不低于 {0}% 时返回真值 |
| 111 | 选项30 | OptionInterruptCasting | 当角色正在施展功法且允许中断施展时返回真值 |
| 112 | 选项31 | OptionInterruptAffectingDefense | 当角色已运起护体且允许中断护体时返回真值 |
| 113 | 选项32 | OptionInterruptAffectingMove | 当角色已运起身法且允许中断身法时返回真值 |

### 6.3 AiParam（25 筆）— AI 參數型別（決策樹條件/行動的取值型別）

| Id | 名稱 | 類型 | 說明(Desc) |
|---:|---|---|---|
| 0 | 整数 | Int | 输入任意整数，但不可大于等于十亿或小于等于负十亿 |
| 1 | 布尔 | Bool | 输入任意布尔，如 True、False |
| 2 | 功法 | CombatSkill | 输入功法名，必须与配置表中功法名完全相同，若存在同名功法则会显示警告并应用首个该名称功法 |
| 3 | 敌我 | IsAlly | 输入任意布尔，True 代表己方，False 代表对方 |
| 4 | 文本 | String | 输入任意文本，如 “abc123”、“示例” |
| 5 | 战斗难度 | CombatDifficulty | 输入战斗难度名称，如普通、困难、极难、必死 |
| 6 | 同道指令 | TeammateCommand | 输入一般同道指令名称，如攻击、防御、牵制等，不可输入负面指令 |
| 7 | 主动功法类型 | ProactiveSkillType | 输入主动功法类型，如摧破、轻灵、护体 |
| 8 | 其它行为类型 | OtherActionType | 输入其它行为类型，如疗伤、驱毒、逃跑 |
| 9 | 前后 | IsForward | 输入任意布尔，True 代表前方，False 代表后方 |
| 10 | 部位 | BodyPartType | 输入部位名，如头颈、左臂、右腿 |
| 11 | 表达式 | Expression | 输入含有七元赋性类型的表达式，如 20 + 聪颖 × 40 ÷ 100 |
| 12 | 正逆 | IsDirect | 输入任意布尔，True 代表正练，False 代表逆练 |
| 13 | 内外 | IsInner | 输入任意布尔，True 代表内，False 代表外 |
| 14 | 毒素 | PoisonType | 输入毒素类型，如烈毒、幻毒 |
| 15 | 蛊虫成长 | IsNotOnlyInCombat | 输入任意布尔，True 代表已成长的，False 代表未成长的 |
| 16 | 蛊虫识主 | IsGood | 输入任意布尔，True 代表已识主的，False 代表未识主的 |
| 17 | 蛊虫类型 | WugType | 输入蛊虫类型，如赤目,魑魅,黑血,心魔,尸螭,冰蚕,金蚕,青髓，也可简化输入 0~7 来指代 |
| 18 | 真气类型 | NeiliAllocationType | 输入真气类型，如摧破、轻灵、护体、奇窍，也可简化输入 0~3 来指代 |
| 19 | 蓄式 | TrickType | 输入蓄式名，如劈、刺、撩 |
| 20 | 武器 | Weapon | 输入兵器名，如湛卢、巨阙 |
| 21 | 武器类型 | WeaponSubType | 输入兵器类型，如针匣、对刺、剑、刀 |
| 22 | 五行 | FiveElementsType | 输入五行类型，如金刚、紫霞、玄阴、纯阳、归元、混元，也可简化输入 0~5 来指代 |
| 23 | 战斗类型 | CombatType | 输入战斗类型，如切磋、恶斗、死斗、接招 |
| 24 | 战斗状态名 | CombatStateName | 输入战斗状态名称，如轻身术、驭使负屃 |

### 6.4 AiData（25 筆）— AI 藍圖資料項（具名行為樹，如「太吾」「莫女」等）

具名 AI 藍圖資料項：`Name`=角色/劇情名（ref），`Path`=行為樹藍圖路徑。無 Desc。

| Id | 名稱 | Path | GroupId |
|---:|---|---|---:|
| 0 | 太吾 | `taiwu` | 1 |
| 1 | 无名之人逃跑 | `sect-story/baihua-anonym-escape` | 1 |
| 2 | 莫女 | `sword-tomb/monv` | 1 |
| 3 | 大岳瑶常 | `sword-tomb/dayue-yaochang` | 1 |
| 4 | 九寒 | `sword-tomb/jiuhan` | 1 |
| 5 | 金凰儿 | `sword-tomb/jin-huanger` | 1 |
| 6 | 衣以侯 | `sword-tomb/yi-yihou` | 1 |
| 7 | 卫起 | `sword-tomb/wei-qi` | 1 |
| 8 | 以向 | `sword-tomb/yixiang` | 1 |
| 9 | 血枫 | `sword-tomb/xuefeng` | 1 |
| 10 | 术方 | `sword-tomb/shufang` | 1 |
| 11 | 焕心 | `sword-tomb/huanxin` | 1 |
| 12 | 相枢 | `sword-tomb/xiangshu` | 1 |
| 13 | 小和尚 | `tutorial/little-monk` | 1 |
| 14 | 复生之人 | `sect-story/baihua-anonym` | 1 |
| 15 | 少林互动魔头0 | `sect-story/shaolin-slayer-trial-demon0` | 1 |
| 16 | 少林互动魔头3 | `sect-story/shaolin-slayer-trial-demon3` | 1 |
| 17 | 少林互动魔头6 | `sect-story/shaolin-slayer-trial-demon6` | 1 |
| 18 | 少林互动魔头7 | `sect-story/shaolin-slayer-trial-demon7` | 1 |
| 19 | 少林互动魔头11 | `sect-story/shaolin-slayer-trial-demon11` | 1 |
| 20 | 少林互动魔头2 | `sect-story/shaolin-slayer-trial-demon2` | 1 |
| 21 | 少林互动魔头4 | `sect-story/shaolin-slayer-trial-demon4` | 1 |
| 22 | 少林互动魔头17 | `sect-story/shaolin-slayer-trial-demon17` | 1 |
| 23 | 少林互动魔头10 | `sect-story/shaolin-slayer-trial-demon10` | 1 |
| 24 | 少林互动魔头12 | `sect-story/shaolin-slayer-trial-demon12` | 1 |

### 6.5 AiGroup（3 筆）— AI 分組（通用/戰鬥…，將條件/行動歸類）

AI 分組（聚合多個 GroupId）。無 Desc。id=2 在安裝版 ref 無名稱（資料坑，見 README）。

| Id | 名稱 | GroupIds |
|---:|---|---|
| 0 | 通用 | [0, 1, 2] |
| 1 | 战斗 | [1] |
| 2 | （ref 無名） | [2] |

### 6.6 AiRelations（13 筆）— 關係觸發 AI（互動後好感/仇怨等關係如何變化）

關係觸發 AI：NPC 互動後好感/仇怨等社交關係如何變化（過月關係更新階段 `_CharacterRelationsUpdate` 用）。無 Desc；名稱即關係事件名（ref）。`PersonalityType` 對應 BehaviorType 道德型。

| Id | 名稱 | PersonalityType | 非衝突行為調整 | 非衝突名望調整 | 敵對門派調整 | 友好門派調整 |
|---:|---|---:|---:|---:|---:|---:|
| 0 | 结下仇怨 | 3 | -500 | -500 | 1000 | -1000 |
| 1 | 化解仇怨 | 0 | -500 | -500 | -1000 | 1000 |
| 2 | 爱慕 | 2 | 0 | 0 | 0 | 0 |
| 3 | 表白 | 3 | 0 | 0 | 0 | 0 |
| 4 | 分手 | 0 | 0 | 0 | 0 | 0 |
| 5 | 求婚 | 4 | 0 | 0 | 0 | 0 |
| 6 | 结为好友 | 2 | -500 | -500 | -1000 | 1000 |
| 7 | 断绝友谊 | 0 | -500 | -500 | 1000 | -1000 |
| 8 | 义结金兰 | 2 | -500 | -500 | -1000 | 1000 |
| 9 | 割袍断义 | 0 | -500 | -500 | 1000 | -1000 |
| 10 | 拜认父母 | 4 | 0 | 0 | 0 | 0 |
| 11 | 收养子女 | 4 | 0 | 0 | 0 | 0 |
| 12 | 离婚 | 4 | 0 | 0 | 0 | 0 |

