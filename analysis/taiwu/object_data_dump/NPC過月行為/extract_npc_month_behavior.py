#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
太吾繪卷 NPC 過月行為 資料抽取器
================================
抽取「NPC 在月份更替/過月時的各種行動與 AI 決策設定」相關資料表，輸出 JSON。

複用上層 extract_objects.py 的 helper（split_top / iter_new_calls / parse_ctor /
load_ref / load_lang / lang_get / parse_int），不重造輪子。

來源（唯讀）：
  反編譯：~/dev/taiwu-src/Assembly-CSharp/Config/<Table>.cs + <Table>Item.cs
  語言檔：<game>/.../StreamingAssets/Language_CN/<Pack>_language.txt
  名稱權威：<game>/.../StreamingAssets/ConfigRefNameMapping/<Table>.ref.txt

設計重點：
  * 名稱一律優先取 ref（與安裝版同步、按 TemplateId 對齊），缺漏才回退語言檔行號。
    本批所有 12 張表的 ref 皆齊全且按 TemplateId 命名（連無 Name 欄位的
    AiData/AiGroup/AiRelations/PrioritizedActions 也由 ref 提供顯示名）。
  * Type 欄位在資料列是 `EXxxType.YyyName` 字面（非整數），故另寫 enum 後綴擷取。
"""
import os, re, sys, json

# 引入上層通用 helper
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(THIS_DIR)
sys.path.insert(0, PARENT)
from extract_objects import (  # noqa: E402
    SRC_DIR, split_top, iter_new_calls, parse_ctor,
    load_ref, load_lang, lang_get, parse_int,
)

OUT_DIR = THIS_DIR


# --------------------------------------------------- enum 後綴擷取 ----
def enum_suffix(argval):
    """從 `EAiActionType.NormalAttack` 取 `NormalAttack`；非 enum 字面回 None。"""
    m = re.fullmatch(r"E\w+Type\.(\w+)", argval.strip())
    return m.group(1) if m else None


def read_src(table_cls):
    with open(os.path.join(SRC_DIR, table_cls + ".cs"), encoding="utf-8") as f:
        return f.read()


def clean_args(argstr):
    """切分一列參數，並剝掉具名參數標籤 argN:。"""
    return [re.sub(r"^arg\d+:\s*", "", a) for a in split_top(argstr)]


def name_of(table_cls, tid, lang_pack=None, lang_idx=None):
    """名稱：先 ref（權威）、再回退語言檔行號。"""
    id2name = load_ref(table_cls)
    if tid is not None and tid in id2name:
        return id2name[tid], "ref"
    if lang_pack is not None and lang_idx is not None:
        return lang_get(lang_pack, lang_idx), "lang"
    return None, None


# ============================================================ 各表抽取 ====

def extract_monthly_actions():
    """MonthlyActions：NPC 每月可執行行動清單（核心）。
    schema（MonthlyActionsItem.cs:54）：
      arg0 TemplateId / arg1 Name(MonthlyActions_language) /
      arg2 EnterMonthList / arg3 MapState / arg4 MapArea / arg5 MapBlockSubType /
      arg6 CharacterSearchRange / arg7 MajorTargetMoveVisible /
      arg10 AdventureId / arg11 NotificationId / arg12 IsEnemyNest /
      arg13~16 AllowTemporary*/WillConvert* / arg17 CanActionBeforehand /
      arg18 PreparationDuration / arg19 PreannouncingTime /
      arg20 MinInterval / arg21 MinFailureInterval
    """
    table, item = "MonthlyActions", "MonthlyActionsItem"
    pack = "MonthlyActions_language"
    rows = []
    for argstr in iter_new_calls(read_src(table), item):
        a = clean_args(argstr)
        if len(a) < 22:
            continue
        tid = parse_int(a[0])
        name, nsrc = name_of(table, tid, pack, parse_int(a[1]))
        rows.append({
            "TemplateId": tid,
            "Name": name,
            "NameSrc": nsrc,
            "CharacterSearchRange": parse_int(a[6]),
            "IsEnemyNest": a[12].strip() == "true",
            "CanActionBeforehand": a[17].strip() == "true",
            "PreparationDuration": parse_int(a[18]),
            "PreannouncingTime": parse_int(a[19]),
            "MinInterval": parse_int(a[20]),
            "MinFailureInterval": parse_int(a[21]),
        })
    return _wrap(table, "NPC 每月可執行行動清單（核心）", pack, rows)


def _extract_ai_tuple(table, item, pack, type_enum_label):
    """AiAction / AiCondition：共用 schema（IAiConfigTuple）：
      arg0 TemplateId / arg1 Type(enum) / arg2 Name(<pack>) / arg3 Desc(<pack>) /
      arg4 ParamStrings / arg5 ParamInts / arg6 GroupId
    """
    rows = []
    for argstr in iter_new_calls(read_src(table), item):
        a = clean_args(argstr)
        if len(a) < 7:
            continue
        tid = parse_int(a[0])
        name, nsrc = name_of(table, tid, pack, parse_int(a[2]))
        rows.append({
            "TemplateId": tid,
            "Name": name,
            "NameSrc": nsrc,
            "Type": enum_suffix(a[1]),
            "Desc": lang_get(pack, parse_int(a[3])),
            "GroupId": parse_int(a[6]),
        })
    return rows


def extract_ai_action():
    """AiAction：戰鬥/世界 AI 行動定義（含說明）。AiActionItem.cs:32。"""
    pack = "AiAction_language"
    rows = _extract_ai_tuple("AiAction", "AiActionItem", pack, "EAiActionType")
    return _wrap("AiAction", "AI 行動定義（含說明）", pack, rows)


def extract_ai_condition():
    """AiCondition：AI 決策條件定義（含說明）。AiConditionItem.cs:32。"""
    pack = "AiCondition_language"
    rows = _extract_ai_tuple("AiCondition", "AiConditionItem", pack, "EAiConditionType")
    return _wrap("AiCondition", "AI 決策條件定義（含說明）", pack, rows)


def extract_behavior_type():
    """BehaviorType：行為大類（道德傾向）。BehaviorTypeItem.cs:20。
      arg0 TemplateId / arg1 Name / arg2 Desc / arg3 ExchangeBook / arg4 Icon /
      arg5 BetrayTips(int[]→language list)
    """
    table, item = "BehaviorType", "BehaviorTypeItem"
    pack = "BehaviorType_language"
    rows = []
    for argstr in iter_new_calls(read_src(table), item):
        a = clean_args(argstr)
        if len(a) < 6:
            continue
        tid = parse_int(a[0])
        name, nsrc = name_of(table, tid, pack, parse_int(a[1]))
        # BetrayTips：arg5 是 int[]，各元素為語言檔行號
        tip_idx = [int(x) for x in re.findall(r"-?\d+", re.search(r"\{([^{}]*)\}", a[5]).group(1))] \
            if re.search(r"\{([^{}]*)\}", a[5]) else []
        rows.append({
            "TemplateId": tid,
            "Name": name,
            "NameSrc": nsrc,
            "Desc": lang_get(pack, parse_int(a[2])),
            "ExchangeBook": parse_int(a[3]),
            "BetrayTips": [lang_get(pack, i) for i in tip_idx],
        })
    return _wrap(table, "行為大類（道德傾向）", pack, rows)


def extract_prioritized_actions():
    """PrioritizedActions：優先級行動設定。PrioritizedActionsItem.cs:42。
      無 Name 欄位；名稱取自 ref（按 TemplateId，對應 PrioritizedActionType switch）。
      arg0 TemplateId / arg1 ActType(enum) / arg2 FailToCreateActionCoolDown /
      arg3 ActionCoolDown / arg4 Duration / arg5 BasePriority / arg6 MoralityPriority[5] /
      arg7 IsPrevActionInterrupted / arg8 IsAdultOnly / arg9 IsNonLeader /
      arg10 IsNonTaiwuTeammate / arg11 IsNonMonk / arg12 LoafChance /
      arg13 OrgTemplateId / arg14 OrgGrade / arg15 ActionJointChance /
      arg16 RefuseAppointment(PrioritizedActions_language)
    """
    table, item = "PrioritizedActions", "PrioritizedActionsItem"
    pack = "PrioritizedActions_language"
    rows = []
    for argstr in iter_new_calls(read_src(table), item):
        a = clean_args(argstr)
        if len(a) < 17:
            continue
        tid = parse_int(a[0])
        name, nsrc = name_of(table, tid)  # 純 ref（無 Name 欄位）
        morality = [int(x) for x in re.findall(r"-?\d+", re.search(r"\{([^{}]*)\}", a[6]).group(1))] \
            if re.search(r"\{([^{}]*)\}", a[6]) else []
        rows.append({
            "TemplateId": tid,
            "Name": name,
            "NameSrc": nsrc,
            "ActType": enum_suffix(a[1]),
            "BasePriority": parse_int(a[5]),
            "MoralityPriority": morality,   # [刚正,仁善,中庸,叛逆,唯我] 5 種道德型權重
            "ActionCoolDown": parse_int(a[3]),
            "Duration": parse_int(a[4]),
            "IsAdultOnly": a[8].strip() == "true",
            "IsNonLeader": a[9].strip() == "true",
            "IsNonMonk": a[11].strip() == "true",
            "RefuseAppointment": lang_get(pack, parse_int(a[16])),
        })
    return _wrap(table, "優先級行動設定（過月每月先選一個高優先行為）", pack, rows)


def extract_villager_role_arrangement():
    """VillagerRoleArrangement：村民職務安排（太吾村村民過月自動執行的職務）。
    VillagerRoleArrangementItem.cs:22。
      arg0 TemplateId / arg1 VillagerRole / arg2 ShortName / arg3 Name /
      arg4 DisplayIcon / arg5 DisplayIcon2 / arg6 Desc（皆 VillagerRoleArrangement_language）
    """
    table, item = "VillagerRoleArrangement", "VillagerRoleArrangementItem"
    pack = "VillagerRoleArrangement_language"
    rows = []
    for argstr in iter_new_calls(read_src(table), item):
        a = clean_args(argstr)
        if len(a) < 7:
            continue
        tid = parse_int(a[0])
        name, nsrc = name_of(table, tid, pack, parse_int(a[3]))
        rows.append({
            "TemplateId": tid,
            "Name": name,
            "NameSrc": nsrc,
            "ShortName": lang_get(pack, parse_int(a[2])),
            "Desc": lang_get(pack, parse_int(a[6])),
            "VillagerRole": parse_int(a[1]),
        })
    return _wrap(table, "村民職務安排（村民過月自動執行的職務）", pack, rows)


def extract_villager_role():
    """VillagerRole：村民角色（職業類別）。VillagerRoleItem.cs:27。
      無單一 Name；名稱取 ref。arg4 EffectTextList(int[]→VillagerRole_language) 為效果說明。
    """
    table, item = "VillagerRole", "VillagerRoleItem"
    pack = "VillagerRole_language"
    rows = []
    for argstr in iter_new_calls(read_src(table), item):
        a = clean_args(argstr)
        if len(a) < 9:
            continue
        tid = parse_int(a[0])
        name, nsrc = name_of(table, tid)  # 純 ref
        eff_idx = [int(x) for x in re.findall(r"-?\d+", re.search(r"\{([^{}]*)\}", a[3]).group(1))] \
            if re.search(r"\{([^{}]*)\}", a[3]) else []
        rows.append({
            "TemplateId": tid,
            "Name": name,
            "NameSrc": nsrc,
            "OrganizationMember": parse_int(a[1]),
            "EffectTexts": [lang_get(pack, i) for i in eff_idx],
        })
    return _wrap(table, "村民角色（職業類別，職務安排的母類）", pack, rows)


def extract_ai_node():
    """AiNode：AI 決策樹節點種類。AiNodeItem.cs:27。
      arg0 TemplateId / arg1 Type(enum) / arg2 Name / arg3 Desc / arg4 IsAction
    """
    table, item = "AiNode", "AiNodeItem"
    pack = "AiNode_language"
    rows = []
    for argstr in iter_new_calls(read_src(table), item):
        a = clean_args(argstr)
        if len(a) < 5:
            continue
        tid = parse_int(a[0])
        name, nsrc = name_of(table, tid, pack, parse_int(a[2]))
        rows.append({
            "TemplateId": tid,
            "Name": name,
            "NameSrc": nsrc,
            "Type": enum_suffix(a[1]),
            "Desc": lang_get(pack, parse_int(a[3])),
            "IsAction": a[4].strip() == "true",
        })
    return _wrap(table, "AI 決策樹節點種類（順序/分支/行為）", pack, rows)


def extract_ai_param():
    """AiParam：AI 參數型別。AiParamItem.cs:20。
      arg0 TemplateId / arg1 Type(enum) / arg2 Name / arg3 Desc /
      arg4 PrintingAliases(int[]) / arg5 AnalysisAliases(string[])
    """
    table, item = "AiParam", "AiParamItem"
    pack = "AiParam_language"
    rows = []
    for argstr in iter_new_calls(read_src(table), item):
        a = clean_args(argstr)
        if len(a) < 4:
            continue
        tid = parse_int(a[0])
        name, nsrc = name_of(table, tid, pack, parse_int(a[2]))
        rows.append({
            "TemplateId": tid,
            "Name": name,
            "NameSrc": nsrc,
            "Type": enum_suffix(a[1]),
            "Desc": lang_get(pack, parse_int(a[3])),
        })
    return _wrap(table, "AI 參數型別（決策樹條件/行動的取值型別）", pack, rows)


def extract_ai_data():
    """AiData：AI 藍圖資料項（Path 指向行為樹藍圖檔/條目）。AiDataItem.cs:14。
      無 Name/Desc 欄位（名稱取 ref）。arg0 TemplateId / arg1 Path(字串字面) / arg2 GroupId
    """
    table, item = "AiData", "AiDataItem"
    rows = []
    for argstr in iter_new_calls(read_src(table), item):
        a = clean_args(argstr)
        if len(a) < 3:
            continue
        tid = parse_int(a[0])
        name, nsrc = name_of(table, tid)  # 純 ref
        path = a[1].strip().strip('"') if a[1].strip().lower() != "null" else None
        rows.append({
            "TemplateId": tid,
            "Name": name,
            "NameSrc": nsrc,
            "Path": path,
            "GroupId": parse_int(a[2]),
        })
    return _wrap(table, "AI 藍圖資料項（具名行為樹，如「太吾」「莫女」等）", None, rows)


def extract_ai_group():
    """AiGroup：AI 分組（將多個 GroupId 聚合）。AiGroupItem.cs:13。
      無 Name/Desc（名稱取 ref）。arg0 TemplateId / arg1 GroupIds(List<int>)
    """
    table, item = "AiGroup", "AiGroupItem"
    rows = []
    for argstr in iter_new_calls(read_src(table), item):
        a = clean_args(argstr)
        if len(a) < 2:
            continue
        tid = parse_int(a[0])
        name, nsrc = name_of(table, tid)  # 純 ref
        gids = [int(x) for x in re.findall(r"-?\d+", re.search(r"\{([^{}]*)\}", a[1]).group(1))] \
            if re.search(r"\{([^{}]*)\}", a[1]) else []
        rows.append({
            "TemplateId": tid,
            "Name": name,
            "NameSrc": nsrc,
            "GroupIds": gids,
        })
    return _wrap(table, "AI 分組（通用/戰鬥…，將條件/行動歸類）", None, rows)


def extract_ai_relations():
    """AiRelations：關係觸發 AI（NPC 互動後關係如何變化）。AiRelationsItem.cs:27。
      無 Name/Desc（名稱取 ref，如「结下仇怨」「爱慕」）。
      arg0 TemplateId / arg1 PersonalityType / arg2 MinFavorability / arg3 MaxFavorability /
      arg4 Probability(RelationTriggerOnBehaviorChance[]) / arg5~8 各種調整值
    """
    table, item = "AiRelations", "AiRelationsItem"
    rows = []
    for argstr in iter_new_calls(read_src(table), item):
        a = clean_args(argstr)
        if len(a) < 9:
            continue
        tid = parse_int(a[0])
        name, nsrc = name_of(table, tid)  # 純 ref
        rows.append({
            "TemplateId": tid,
            "Name": name,
            "NameSrc": nsrc,
            "PersonalityType": parse_int(a[1]),
            "NoncontradictoryBehaviorAjust": parse_int(a[5]),
            "NoncontradictoryFameAjust": parse_int(a[6]),
            "EnemySectMemberAdjust": parse_int(a[7]),
            "FriendlySectMemberAdjust": parse_int(a[8]),
        })
    return _wrap(table, "關係觸發 AI（互動後好感/仇怨等關係如何變化）", None, rows)


# ------------------------------------------------------------ 包裝 ----
def _wrap(table, title, pack, rows):
    unresolved = sum(1 for r in rows if not r.get("Name"))
    return {
        "table": table,
        "title": title,
        "pack": pack,
        "count": len(rows),
        "unresolved": unresolved,
        "name_from_ref": sum(1 for r in rows if r.get("NameSrc") == "ref"),
        "name_from_lang": sum(1 for r in rows if r.get("NameSrc") == "lang"),
        "rows": rows,
    }


EXTRACTORS = [
    ("MonthlyActions", extract_monthly_actions),
    ("AiAction", extract_ai_action),
    ("BehaviorType", extract_behavior_type),
    ("PrioritizedActions", extract_prioritized_actions),
    ("VillagerRoleArrangement", extract_villager_role_arrangement),
    ("VillagerRole", extract_villager_role),
    ("AiNode", extract_ai_node),
    ("AiCondition", extract_ai_condition),
    ("AiParam", extract_ai_param),
    ("AiData", extract_ai_data),
    ("AiGroup", extract_ai_group),
    ("AiRelations", extract_ai_relations),
]


def main():
    result = {}
    print(f"{'表':<26}{'列數':>6}{'未解':>6}{'ref':>6}{'lang':>6}")
    print("-" * 50)
    for key, fn in EXTRACTORS:
        r = fn()
        result[key] = r
        print(f"{key:<26}{r['count']:>6}{r['unresolved']:>6}"
              f"{r['name_from_ref']:>6}{r['name_from_lang']:>6}")
    with open(os.path.join(OUT_DIR, "npc_month_behavior.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print("\n→ 已寫出 npc_month_behavior.json")


if __name__ == "__main__":
    main()
