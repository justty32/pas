#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
太吾繪卷 NPC 模板（Character 表）完整抽取器
============================================
延續 ../extract_objects.py 的方法論，但 Character 表有一個特殊難點：
反編譯器把每列 `new CharacterItem(...)` 的「複合型參數」(List<short>/OrganizationInfo/
MainAttributes/CombatSkillShorts/...) 提升(hoist)成呼叫前的區域變數 argN，
呼叫處只寫 `argN` 變數名。因此不能像其他表那樣直接取字面值，
必須：
  1. 找到每個 `new CharacterItem(...)` 呼叫的字面起點。
  2. 把「上一個呼叫結尾 ~ 本呼叫起點」這段原始碼裡的所有 `argN = <expr>;` 賦值收集起來。
  3. 對呼叫的位置參數逐一解析：純字面直接取；若是 argN 變數名，回查該段賦值取其 <expr>。

CharacterItem 建構子欄位 → argN 對照（見 CharacterItem.cs:229-339）：
  arg0  TemplateId(short)          arg1  Surname(Character_language)
  arg2  GivenName(Character_language)  arg3 AnonymousTitle(Character_language)
  arg5  FixedAvatarName(string)    arg6  CreatingType(byte) ★主分類
  arg7  GroupId(short)             arg29 Gender(sbyte) ★ 0女/1男/-1隨機
  arg30 PresetBodyType(sbyte)     arg31 Race(sbyte) 0漢/1藏
  arg32 Transgender  arg33 Bisexual
  arg34 PresetFame(sbyte) 名望     arg35 Happiness
  arg36 BaseAttraction 魅力        arg37 BaseMorality 道德
  arg38 ActualAge 實齡  arg39 InitCurrAge 初始年齡
  arg40 Health  arg41 BaseMaxHealth  arg42 BirthMonth
  arg43 OrganizationInfo(OrgTemplateId,Grade,Principal,SettlementId) ★所屬門派
  arg45 IdealSect  arg46 RandomIdealSects(sbyte[])
  arg47 XiangshuType 相術  arg48 MonkType
  arg49 LifeSkillTypeInterest  arg50 CombatSkillTypeInterest  arg51 MainAttributeInterest
  arg56 BaseMainAttributes(MainAttributes 6值) ★主屬性
        [膂力,灵敏,定力,体质,根骨,悟性] (MainAttributeType.cs)
  arg24 FeatureIds(List<short>) ★初始特性  arg102 BaseCombatSkillQualifications(CombatSkillShorts 14值) ★武學資質
  arg98 BaseLifeSkillQualifications(LifeSkillShorts 16值) 技藝資質

來源（唯讀）：
  反編譯：~/dev/taiwu-src/Assembly-CSharp/Config/Character.cs, CharacterItem.cs
  名稱權威：StreamingAssets/ConfigRefNameMapping/Character.ref.txt
  特性名：CharacterFeature.ref.txt   門派名：Organization.ref.txt
"""
import os, re, json, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
sys.path.insert(0, PARENT)
from extract_objects import split_top, iter_new_calls, load_ref, load_lang, SRC_DIR  # 複用既有 helper

OUT_DIR = HERE

# ---- CharacterItem 欄位 → argN 位置（與 CharacterItem.cs 建構子一致）----
POS = {
    "TemplateId": 0, "Surname": 1, "GivenName": 2, "AnonymousTitle": 3,
    "FixedAvatarName": 5, "CreatingType": 6, "GroupId": 7,
    "FeatureIds": 24, "Gender": 29, "PresetBodyType": 30, "Race": 31,
    "PresetFame": 34, "Happiness": 35, "BaseAttraction": 36, "BaseMorality": 37,
    "ActualAge": 38, "InitCurrAge": 39, "Health": 40, "BaseMaxHealth": 41,
    "BirthMonth": 42, "OrganizationInfo": 43, "IdealSect": 45,
    "XiangshuType": 47, "MonkType": 48,
    "LifeSkillTypeInterest": 49, "CombatSkillTypeInterest": 50, "MainAttributeInterest": 51,
    "BaseMainAttributes": 56, "BaseLifeSkillQualifications": 98,
    "BaseCombatSkillQualifications": 102,
}

CREATING_TYPE = {0: "固定角色(命名NPC/劇情角色)", 1: "智能角色(地區人口生成模板)",
                 2: "隨機敵人(動物/隨機怪)", 3: "固定敵人(劇情敵/首領)"}
GENDER = {-1: "隨機", 0: "女", 1: "男"}
RACE = {0: "漢", 1: "藏族"}
MAIN_ATTR_NAMES = ["膂力", "灵敏", "定力", "体质", "根骨", "悟性"]  # MainAttributeType.cs
# CombatSkillShorts 14 值索引（同 extract_objects.COMBATSKILL_TYPE）
COMBAT_SKILL_TYPE = ["內功", "身法", "絕技", "拳掌", "指法", "腿法", "暗器",
                     "劍法", "刀法", "長兵", "奇門", "軟兵", "御射", "樂器"]

def parse_int(v):
    v = v.strip()
    m = re.fullmatch(r"-?\d+", v)
    return int(m.group(0)) if m else None

# ------------------------------------------- 抓取每個呼叫(含起點偏移) ----
def scan_calls(src, item_cls="CharacterItem"):
    """回傳 [(start_offset, end_offset, argstr), ...] 依出現序。"""
    pat = "new " + item_cls + "("
    out, i = [], 0
    while True:
        j = src.find(pat, i)
        if j < 0:
            break
        start = j + len(pat)
        depth, k, instr = 1, start, None
        while k < len(src) and depth > 0:
            c = src[k]
            if instr:
                if c == "\\":
                    k += 2; continue
                if c == instr:
                    instr = None
            else:
                if c in "\"'":
                    instr = c
                elif c in "([{":
                    depth += 1
                elif c in ")]}":
                    depth -= 1
            k += 1
        out.append((j, k, src[start:k - 1]))
        i = k
    return out

# ------------------------------------ 解析一段原始碼裡的 argN = expr; ----
_ASSIGN_RE = re.compile(r"(?:^|\n)\s*(?:[\w.<>\[\]]+\s+)?(arg\d*)\s*=\s*")
def collect_locals(segment):
    """從程式片段擷取 {argName: 右值表達式字串}，後出現的覆蓋先出現的。"""
    locals_map = {}
    for m in _ASSIGN_RE.finditer(segment):
        name = m.group(1)
        rhs_start = m.end()
        # 平衡掃描到該語句結尾的 ';'（尊重 () [] {} 與字串）
        depth, k, instr = 0, rhs_start, None
        while k < len(segment):
            c = segment[k]
            if instr:
                if c == "\\":
                    k += 2; continue
                if c == instr:
                    instr = None
            else:
                if c in "\"'":
                    instr = c
                elif c in "([{":
                    depth += 1
                elif c in ")]}":
                    depth -= 1
                elif c == ";" and depth == 0:
                    break
            k += 1
        locals_map[name] = segment[rhs_start:k].strip()
    return locals_map

def resolve(token, locals_map):
    """位置參數 token：若是 argN 變數名→回查右值；否則原樣回傳。"""
    token = token.strip()
    if re.fullmatch(r"arg\d*", token) and token in locals_map:
        return locals_map[token]
    return token

# ------------------------------------------------ 複合型值解析輔助 ----
def ctor_ints(expr, ctor_name):
    """從 `new <ctor_name>(a, b, ...)` 取出引數整數清單；default(...)→0；non-int→None 佔位。"""
    m = re.search(re.escape("new " + ctor_name) + r"\s*\(", expr)
    if not m:
        return None
    inner_start = m.end()
    depth, k, instr = 1, inner_start, None
    while k < len(expr) and depth > 0:
        c = expr[k]
        if instr:
            if c == "\\":
                k += 2; continue
            if c == instr:
                instr = None
        else:
            if c in "\"'":
                instr = c
            elif c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
        k += 1
    inner = expr[inner_start:k - 1]
    vals = []
    for a in split_top(inner):
        a = a.strip()
        if a.startswith("default("):
            vals.append(0)
        else:
            vals.append(parse_int(a))
    return vals

def list_short(expr):
    """`new List<short> { a, b }` 或 `new List<short>()` → [a, b] / []。"""
    m = re.search(r"\{([^{}]*)\}", expr)
    if not m:
        return []
    return [int(x) for x in re.findall(r"-?\d+", m.group(1))]

def org_info(expr):
    """new OrganizationInfo(OrgTemplateId, Grade, principal:..., SettlementId)。"""
    vals = []
    m = re.search(r"new OrganizationInfo\s*\(([^)]*)\)", expr)
    if not m:
        return None
    for a in split_top(m.group(1)):
        a = re.sub(r"^\w+:\s*", "", a.strip())  # 去 principal: 等具名標籤
        if a in ("true", "false"):
            vals.append(1 if a == "true" else 0)
        else:
            vals.append(parse_int(a))
    return vals  # [OrgTemplateId, Grade, Principal, SettlementId]

# ---------------------------------------------------------------- 主抽取 ----
def extract():
    src = open(os.path.join(SRC_DIR, "Character.cs"), encoding="utf-8").read()
    ref = load_ref("Character")
    feat_ref = load_ref("CharacterFeature")
    org_ref = load_ref("Organization")
    calls = scan_calls(src)

    rows = []
    prev_end = 0
    for (start, end, argstr) in calls:
        segment = src[prev_end:start]          # 本呼叫前的賦值區
        locals_map = collect_locals(segment)
        prev_end = end

        raw = split_top(argstr)
        args = [re.sub(r"^arg\d+:\s*", "", a) for a in raw]  # 去具名標籤(注意：是建構子形參名 argN:)

        def get(field):
            p = POS[field]
            return resolve(args[p], locals_map) if p < len(args) else None

        tid = parse_int(get("TemplateId"))
        name = ref.get(tid)

        ct = parse_int(get("CreatingType"))
        gender = parse_int(get("Gender"))
        race = parse_int(get("Race"))

        # 主屬性
        attrs = ctor_ints(get("BaseMainAttributes") or "", "MainAttributes")
        if attrs == [30, 30, 30, 30, 30, 30] or attrs is None:
            attrs_disp = None  # 預設值，視為「未特化」
        else:
            attrs_disp = {MAIN_ATTR_NAMES[i]: attrs[i] for i in range(min(6, len(attrs)))}

        # 武學資質（14 值）
        csq = ctor_ints(get("BaseCombatSkillQualifications") or "", "CombatSkillShorts")
        if csq and any(v for v in csq if v):
            csq_disp = {COMBAT_SKILL_TYPE[i]: csq[i] for i in range(min(14, len(csq))) if csq[i]}
        else:
            csq_disp = None

        # 技藝資質（16 值，僅記非全 0）
        lsq = ctor_ints(get("BaseLifeSkillQualifications") or "", "LifeSkillShorts")
        lsq_disp = lsq if (lsq and any(v for v in lsq if v)) else None

        # 初始特性
        feat_ids = list_short(get("FeatureIds") or "")
        feats = [{"id": fid, "name": feat_ref.get(fid, f"#{fid}")} for fid in feat_ids]

        # 所屬門派
        oi = org_info(get("OrganizationInfo") or "")
        org = None
        if oi:
            org_tid = oi[0]
            org = {"OrgTemplateId": org_tid, "Grade": oi[1],
                   "OrgName": org_ref.get(org_tid),
                   "Principal": bool(oi[2]) if oi[2] is not None else None,
                   "SettlementId": oi[3]}

        def pv(field):  # 純整數欄位
            v = get(field)
            return parse_int(v) if v is not None else None

        row = {
            "TemplateId": tid,
            "Name": name,
            "CreatingType": ct,
            "CreatingTypeName": CREATING_TYPE.get(ct, str(ct)),
            "Gender": gender,
            "GenderName": GENDER.get(gender, str(gender)),
            "Race": race,
            "RaceName": RACE.get(race, str(race)),
            "FixedAvatarName": (get("FixedAvatarName") or "null").strip('"') or None,
            "GroupId": pv("GroupId"),
            "PresetFame": pv("PresetFame"),
            "BaseAttraction": pv("BaseAttraction"),
            "BaseMorality": pv("BaseMorality"),
            "ActualAge": pv("ActualAge"),
            "InitCurrAge": pv("InitCurrAge"),
            "Health": pv("Health"),
            "BaseMaxHealth": pv("BaseMaxHealth"),
            "MainAttributes": attrs_disp,
            "CombatSkillQualifications": csq_disp,
            "LifeSkillQualifications": lsq_disp,
            "Features": feats,
            "Organization": org,
        }
        rows.append(row)

    return rows

# ------------------------------------------------ 分類維度統計 ----
def classify(rows):
    import collections
    by_ct = collections.Counter(r["CreatingTypeName"] for r in rows)
    by_gender = collections.Counter(r["GenderName"] for r in rows)
    by_race = collections.Counter(r["RaceName"] for r in rows)
    # 智能角色（CreatingType==1）= 地區×性別 人口模板：拆地區
    regions = collections.Counter()
    for r in rows:
        if r["CreatingType"] == 1 and r["Name"]:
            m = re.match(r"(.+?)[男女]$", r["Name"])
            if m:
                regions[m.group(1)] += 1
            else:
                regions[r["Name"]] += 1
    return {
        "by_creating_type": dict(by_ct),
        "by_gender": dict(by_gender),
        "by_race": dict(by_race),
        "intelligent_regions": dict(regions),
        "with_features": sum(1 for r in rows if r["Features"]),
        "with_main_attrs": sum(1 for r in rows if r["MainAttributes"]),
        "with_combat_qual": sum(1 for r in rows if r["CombatSkillQualifications"]),
        "with_org": sum(1 for r in rows if r["Organization"]),
        "unresolved_name": sum(1 for r in rows if not r["Name"]),
    }

# ---------------------------------------------------------------- EventActors ----
# 事件角色（劇情立繪人物）：另一類「NPC 模板」，僅供事件對話/立繪，無戰鬥屬性。
# 欄位(見 EventActorsItem.cs:26-37)：Name(EventActors_language) Texture Gender
#   Age(byte[2] 年齡區間) Attraction(short[2] 魅力區間) Clothing IsMonk PresetBodyType
def extract_event_actors():
    src = open(os.path.join(SRC_DIR, "EventActors.cs"), encoding="utf-8").read()
    ref = load_ref("EventActors")
    lang = load_lang("EventActors_language")
    def L(i):
        return lang[i].replace("\\n", " ") if (i is not None and 0 <= i < len(lang)) else ""
    def ints(expr):
        # 取 `new T[N] { a, b }` 大括號內的值（避開陣列長度 N）；無大括號則退回全部數字
        m = re.search(r"\{([^{}]*)\}", expr)
        body = m.group(1) if m else expr
        return [int(x) for x in re.findall(r"-?\d+", body)]
    rows = []
    for argstr in iter_new_calls(src, "EventActorsItem"):
        a = [re.sub(r"^arg\d+:\s*", "", x) for x in split_top(argstr)]
        if len(a) < 9:
            continue
        tid = parse_int(a[0])
        name = ref.get(tid) or L(parse_int(a[1]))
        gender = parse_int(a[3])
        age = ints(a[4])
        attr = ints(a[5])
        rows.append({
            "TemplateId": tid, "Name": name,
            "Texture": a[2].strip('"') if a[2] != "null" else None,
            "Gender": gender, "GenderName": GENDER.get(gender, str(gender)),
            "AgeRange": age, "AttractionRange": attr,
            "Clothing": parse_int(a[6]),
            "IsMonk": a[7].strip() == "true",
            "PresetBodyType": parse_int(a[8]),
        })
    return rows


# ------------------------------------------------------ Markdown 產出 ----
def _attr_str(a):
    return "/".join(str(a[k]) for k in MAIN_ATTR_NAMES) if a else "—"

def _csq_str(c):
    return " ".join(f"{k}{v}" for k, v in c.items()) if c else "—"

def _feat_str(fs):
    return "、".join(f["name"] for f in fs) if fs else "—"

def write_markdown(rows, event_actors, summary):
    import collections
    L = []
    w = L.append
    w("# 太吾繪卷 · 各類 NPC 模板（完整欄位）\n")
    w("> 來源：反編譯 `~/dev/taiwu-src/Assembly-CSharp/Config/Character.cs`（882 列 `new CharacterItem(...)`），"
      "名稱權威 `StreamingAssets/ConfigRefNameMapping/Character.ref.txt`。"
      "欄位含義與 argN 對照見同目錄 `README.md`。\n")
    w("> 與 `../12_NPC與商隊模板.md` 的關係：12_ 只列**名稱清單**（882 個 TemplateId↔名稱）；"
      "本檔補上**每模板的分類維度與關鍵欄位**（生成類型／性別／種族／所屬門派／主屬性／武學資質／初始特性）。\n")

    w("## 分類維度\n")
    w("主分類＝`CreatingType`（CharacterItem.cs:237，"
      "`CreatingType.cs`：0 固定角色／1 智能角色／2 隨機敵人／3 固定敵人）。"
      "次維度＝性別 `Gender`(arg29)、種族 `Race`(arg31)、所屬門派 `OrganizationInfo`(arg43)。\n")
    w("| CreatingType | 含義 | 筆數 |")
    w("|---|---|---:|")
    for ct, nm in CREATING_TYPE.items():
        cnt = sum(1 for r in rows if r["CreatingType"] == ct)
        w(f"| {ct} | {nm} | {cnt} |")
    w(f"\n性別分佈：{summary['by_gender']}　種族分佈：{summary['by_race']}\n")
    w(f"有初始特性 {summary['with_features']}／有特化主屬性 {summary['with_main_attrs']}"
      f"／有武學資質 {summary['with_combat_qual']}／全部 882 筆都帶 OrganizationInfo。\n")

    # ---- 第 1 類：智能角色＝地區×性別 人口生成模板 ----
    w("## 一、智能角色（地區 × 性別 人口生成模板）`CreatingType=1`\n")
    w("這 32 筆是世界人口的「種子模板」：依 16 地區 × 男/女 各一，"
      "屬性/資質皆走預設(主屬性 30/30/30/30/30/30)，實際數值由生成時隨機。"
      "命名規則＝`<地區><性別>`。`Race` 僅藏族=1，其餘地區=0(漢)。\n")
    w("| TemplateId | 名稱 | 性別 | 種族 |")
    w("|---:|---|---|---|")
    for r in rows:
        if r["CreatingType"] == 1:
            w(f"| {r['TemplateId']} | {r['Name']} | {r['GenderName']} | {r['RaceName']} |")
    w("")

    # ---- 第 2 類：固定角色（命名 NPC）----
    def section(title, ct, note):
        sel = [r for r in rows if r["CreatingType"] == ct]
        w(f"## {title}（`CreatingType={ct}`，{len(sel)} 筆）\n")
        w(note + "\n")
        # 依所屬門派分組
        by_org = collections.defaultdict(list)
        for r in sel:
            by_org[r["Organization"]["OrgName"]].append(r)
        for org in sorted(by_org, key=lambda o: -len(by_org[o])):
            grp = by_org[org]
            w(f"### 所屬：{org}（{len(grp)} 筆）\n")
            w("| Id | 名稱 | 性別 | 年齡 | 魅力 | HP | 主屬性(膂/灵/定/体/根/悟) | 武學資質 | 初始特性 |")
            w("|---:|---|---|---:|---:|---:|---|---|---|")
            for r in sorted(grp, key=lambda x: x["TemplateId"]):
                age = r["ActualAge"] if (r["ActualAge"] or 0) > 0 else "—"
                w(f"| {r['TemplateId']} | {r['Name']} | {r['GenderName']} | {age} "
                  f"| {r['BaseAttraction'] if (r['BaseAttraction'] or -1)>=0 else '—'} "
                  f"| {r['BaseMaxHealth'] or '—'} | {_attr_str(r['MainAttributes'])} "
                  f"| {_csq_str(r['CombatSkillQualifications'])} | {_feat_str(r['Features'])} |")
            w("")

    section("二、固定角色（命名 NPC / 劇情角色）", 0,
            "含主角親屬(莫家)、各派化身、特殊劇情人物、部分固定野獸/精怪。"
            "屬 IsFixedPresetType（不會演化），多帶固定特性與所屬門派(化身類 OrgTemplateId=41 剑冢化身)。")
    section("三、固定敵人（劇情敵 / 首領 / 野獸）", 3,
            "IsFixedPreset＋不可演化。包含可作座騎的野獸(SpecialTemmateType=BeastCarrier，OrgTemplateId=40 野兽)、"
            "劇情 BOSS、外道首領等，多帶實打實的主屬性與武學資質。")
    section("四、隨機敵人（隨機怪 / 路人惡徒）", 2,
            "RandomEnemy：地圖隨機遭遇用，屬性多走預設、靠 GroupId/RandomEnemyId 控制成群生成。")

    # ---- EventActors ----
    w("## 五、事件角色（EventActors，立繪/對話用，292 筆）\n")
    w("> 來源 `Config/EventActors.cs`，欄位見 `EventActorsItem.cs:26-37`。"
      "這是**另一種 NPC 模板**：只給事件演出用的立繪人物，無戰鬥屬性，"
      "僅定義 性別／年齡區間／魅力區間／服飾／是否僧侶。與 Character 表獨立(各自 TemplateId)。\n")
    w("| Id | 名稱 | 性別 | 年齡區間 | 魅力區間 | 僧侶 |")
    w("|---:|---|---|---|---|---|")
    for r in event_actors:
        ar = f"{r['AgeRange'][0]}~{r['AgeRange'][1]}" if len(r["AgeRange"]) == 2 else str(r["AgeRange"])
        at = f"{r['AttractionRange'][0]}~{r['AttractionRange'][1]}" if len(r["AttractionRange"]) == 2 else str(r["AttractionRange"])
        w(f"| {r['TemplateId']} | {r['Name']} | {r['GenderName']} | {ar} | {at} | {'是' if r['IsMonk'] else ''} |")
    w("")

    with open(os.path.join(OUT_DIR, "NPC模板總覽.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


def main():
    rows = extract()
    summary = classify(rows)
    event_actors = extract_event_actors()
    write_markdown(rows, event_actors, summary)
    with open(os.path.join(OUT_DIR, "event_actors.json"), "w", encoding="utf-8") as f:
        json.dump({"source": "Config/EventActors.cs", "count": len(event_actors),
                   "rows": event_actors}, f, ensure_ascii=False, indent=1)
    print(f"事件角色(EventActors): {len(event_actors)} 筆")
    out = {
        "source": "~/dev/taiwu-src/Assembly-CSharp/Config/Character.cs",
        "name_authority": "StreamingAssets/ConfigRefNameMapping/Character.ref.txt",
        "count": len(rows),
        "classification": summary,
        "rows": rows,
    }
    with open(os.path.join(OUT_DIR, "npc_templates.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"總筆數: {len(rows)}")
    print("分類(CreatingType):", summary["by_creating_type"])
    print("性別:", summary["by_gender"])
    print("種族:", summary["by_race"])
    print("智能角色地區:", summary["intelligent_regions"])
    print(f"有特性 {summary['with_features']} / 有特化主屬性 {summary['with_main_attrs']}"
          f" / 有武學資質 {summary['with_combat_qual']} / 有所屬門派 {summary['with_org']}"
          f" / 未解名 {summary['unresolved_name']}")

if __name__ == "__main__":
    main()
