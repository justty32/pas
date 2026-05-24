#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
太吾繪卷 物件資料抽取器
=======================
原理：遊戲的 config 資料硬編在反編譯的 Assembly-CSharp/Config/<Table>.cs（靜態初始化），
單列資料類 <Table>Item.cs 的建構子本體記錄了「欄位 = argN」的對應；名稱欄位是
  Name = LocalStringManager.GetConfig("<Pack>_language", argN)
即 <Pack>_language.txt 的「第 argN 行」(0-based)。

因此：
  1. 解析 <Table>Item.cs 建構子 → 欄位→參數位置、名稱欄位的語言檔
  2. 解析 <Table>.cs 每個 `new <Table>Item(...)` 列 → 取對應位置的字面值
  3. 名稱 = 語言檔[索引]，品級 = 字面整數

來源（唯讀，不修改遊戲）：
  反編譯：~/dev/taiwu-src/Assembly-CSharp/Config/
  語言檔：<game>/The Scroll of Taiwu_Data/StreamingAssets/Language_CN/
"""
import os, re, json, sys

GAME = os.path.expanduser("~/.local/share/Steam/steamapps/common/The Scroll Of Taiwu")
SA = os.path.join(GAME, "The Scroll of Taiwu_Data/StreamingAssets")
LANG_DIR = os.path.join(SA, "Language_CN")
REF_DIR = os.path.join(SA, "ConfigRefNameMapping")   # 名稱↔TemplateId，與安裝版同步（權威）
SRC_DIR = os.path.expanduser("~/dev/taiwu-src/Assembly-CSharp/Config")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------- ref：id→中文顯示名 ----
# 格式：name\nid\nname\nid...（name 在偶數行、id 在奇數行）。是安裝版即時資料，
# 不受反編譯版「語言檔行號漂移」影響，故作為名稱的第一來源。
_ref_cache = {}
def load_ref(table):
    if table in _ref_cache:
        return _ref_cache[table]
    path = os.path.join(REF_DIR, table + ".ref.txt")
    id2name = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            toks = [t.rstrip("\r") for t in f.read().split("\n")]
        for i in range(0, len(toks) - 1, 2):
            name, sid = toks[i], toks[i + 1]
            m = re.fullmatch(r"-?\d+", sid.strip())
            if m and name and name != "None":
                id2name[int(m.group(0))] = name
    _ref_cache[table] = id2name
    return id2name

# ---------------------------------------------------------------- 語言檔 ----
_lang_cache = {}
def load_lang(pack):
    if pack in _lang_cache:
        return _lang_cache[pack]
    path = os.path.join(LANG_DIR, pack + ".txt")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    lines = [ln.rstrip("\r") for ln in content.split("\n")]  # GetConfig 用 Split('\n') 取行
    _lang_cache[pack] = lines
    return lines

def lang_get(pack, idx):
    if idx is None or idx < 0:
        return ""
    lines = load_lang(pack)
    if 0 <= idx < len(lines):
        return lines[idx].replace("\\n", " ")
    return f"<{pack}_{idx}_invalid>"

# -------------------------------------------------- C# 解析輔助：平衡切分 ----
def split_top(s):
    """以最外層逗號切分；尊重 () [] {} 與字串。"""
    args, cur, depth, instr = [], [], 0, None
    i = 0
    while i < len(s):
        c = s[i]
        if instr:
            cur.append(c)
            if c == "\\":
                if i + 1 < len(s):
                    cur.append(s[i + 1]); i += 2; continue
            elif c == instr:
                instr = None
        else:
            if c in "\"'":
                instr = c; cur.append(c)
            elif c in "([{":
                depth += 1; cur.append(c)
            elif c in ")]}":
                depth -= 1; cur.append(c)
            elif c == "," and depth == 0:
                args.append("".join(cur).strip()); cur = []
            else:
                cur.append(c)
        i += 1
    if "".join(cur).strip():
        args.append("".join(cur).strip())
    return args

def iter_new_calls(text, item_cls):
    """擷取所有 `new <item_cls>(...)` 的平衡參數字串。"""
    pat = "new " + item_cls + "("
    out, i = [], 0
    while True:
        j = text.find(pat, i)
        if j < 0:
            break
        start = j + len(pat)
        depth, k, instr = 1, start, None
        while k < len(text) and depth > 0:
            c = text[k]
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
        out.append(text[start:k - 1])
        i = k
    return out

# ----------------------------------------- 解析 <Table>Item.cs 建構子映射 ----
def parse_ctor(item_cls):
    """回傳 (param_pos, name_pack, field_pos)
       param_pos: {argName: 位置}
       name_pack: {欄位名: 語言pack}  (該欄位由 GetConfig 取得)
       field_pos:{欄位名: 參數位置}
    """
    path = os.path.join(SRC_DIR, item_cls + ".cs")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    # 找參數最多的建構子（資料建構子，而非無參預設）
    best = None
    for m in re.finditer(r"public\s+" + re.escape(item_cls) + r"\s*\(", src):
        # 擷取簽名括號內
        s = m.end()
        depth, k = 1, s
        while k < len(src) and depth > 0:
            if src[k] == "(":
                depth += 1
            elif src[k] == ")":
                depth -= 1
            k += 1
        sig = src[s:k - 1]
        # 擷取本體 { ... }
        b = src.find("{", k)
        depth, kk = 1, b + 1
        while kk < len(src) and depth > 0:
            if src[kk] == "{":
                depth += 1
            elif src[kk] == "}":
                depth -= 1
            kk += 1
        body = src[b + 1:kk - 1]
        params = [p.strip() for p in split_top(sig) if p.strip()]
        if best is None or len(params) > len(best[0]):
            best = (params, body)
    params, body = best
    param_pos = {}
    for idx, p in enumerate(params):
        nm = p.split()[-1] if p.split() else p
        param_pos[nm] = idx
    name_pack, field_pos = {}, {}
    for line in body.splitlines():
        line = line.strip().rstrip(";")
        # 欄位 = GetConfig("Pack_language", argN)
        m = re.match(r"(\w+)\s*=\s*LocalStringManager\.GetConfig\(\"(\w+)\",\s*(\w+)\)", line)
        if m:
            fld, pack, arg = m.group(1), m.group(2), m.group(3)
            if arg in param_pos:
                name_pack[fld] = pack
                field_pos[fld] = param_pos[arg]
            continue
        # 欄位 = argN   （直接賦值）
        m = re.match(r"(\w+)\s*=\s*(\w+)$", line)
        if m and m.group(2) in param_pos:
            field_pos[m.group(1)] = param_pos[m.group(2)]
    return param_pos, name_pack, field_pos

# ------------------------------------------------------ 抽取單一資料表 ----
def parse_int(v):
    v = v.strip()
    m = re.fullmatch(r"-?\d+", v)
    return int(m.group(0)) if m else None

def extract_table(table_cls, name_field, value_fields):
    """value_fields: 想抽的數值欄位清單(依存在與否)。回傳 rows + 統計。"""
    item_cls = table_cls + "Item"
    param_pos, name_pack, field_pos = parse_ctor(item_cls)
    if name_field not in field_pos:
        raise RuntimeError(f"{item_cls}: 找不到名稱欄位 {name_field}")
    name_pos = field_pos[name_field]
    pack = name_pack.get(name_field)
    val_pos = {f: field_pos[f] for f in value_fields if f in field_pos}
    id_pos = field_pos.get("TemplateId")

    id2name = load_ref(table_cls)   # 權威名稱（安裝版同步）

    data_path = os.path.join(SRC_DIR, table_cls + ".cs")
    with open(data_path, encoding="utf-8") as f:
        text = f.read()
    rows, unresolved, src_ref, src_lang = [], 0, 0, 0
    for argstr in iter_new_calls(text, item_cls):
        args = split_top(argstr)
        if len(args) <= name_pos:
            continue  # 預設無參建構子
        args = [re.sub(r"^arg\d+:\s*", "", a) for a in args]  # 去除具名參數標籤
        tid = parse_int(args[id_pos]) if id_pos is not None and id_pos < len(args) else None
        # 名稱：先 ref（版本對齊），缺漏/重名再回退語言檔行號
        name, nsrc = None, None
        if tid is not None and tid in id2name:
            name, nsrc = id2name[tid], "ref"
        else:
            nidx = parse_int(args[name_pos])
            if pack and nidx is not None:
                name, nsrc = lang_get(pack, nidx), "lang"
        row = {"TemplateId": tid, "Name": name, "NameSrc": nsrc}
        for f, p in val_pos.items():
            row[f] = parse_int(args[p]) if p < len(args) else None
        if not name:
            unresolved += 1
        elif nsrc == "ref":
            src_ref += 1
        else:
            src_lang += 1
        rows.append(row)
    return {"table": table_cls, "name_field": name_field, "pack": pack,
            "value_fields": list(val_pos.keys()), "count": len(rows),
            "unresolved": unresolved, "name_from_ref": src_ref, "name_from_lang": src_lang,
            "rows": rows}

# ------------------------------------- 武功：種類 + 品級 + 特效介紹 ----
COMBATSKILL_TYPE = {0: "內功", 1: "身法", 2: "絕技", 3: "拳掌", 4: "指法", 5: "腿法",
                    6: "暗器", 7: "劍法", 8: "刀法", 9: "長兵", 10: "奇門", 11: "軟兵",
                    12: "御射", 13: "樂器"}

def _braced_ints(argval):
    """從 `new int[N] { a, b }` 取出 {} 內的整數（避開陣列長度 N）。"""
    m = re.search(r"\{([^{}]*)\}", argval)
    return [int(x) for x in re.findall(r"-?\d+", m.group(1))] if m else []

def build_special_effect_descs():
    """SpecialEffect 表：TemplateId → {full, short}。
    Desc = arg19(int[]) → SpecialEffect_language 各行；len>=2 時 [-1] 為完整機制描述。"""
    lines = load_lang("SpecialEffect_language")
    def L(i):
        return lines[i].replace("\\n", " ").strip() if 0 <= i < len(lines) else ""
    text = open(os.path.join(SRC_DIR, "SpecialEffect.cs"), encoding="utf-8").read()
    eff = {}
    for argstr in iter_new_calls(text, "SpecialEffectItem"):
        args = [re.sub(r"^arg\d+:\s*", "", a) for a in split_top(argstr)]
        if len(args) <= 19:
            continue
        tid = parse_int(args[0])
        if tid is None:
            continue
        idxs = _braced_ints(args[19])
        eff[tid] = {"full": L(idxs[-1]) if idxs else "", "short": L(idxs[0]) if idxs else ""}
    return eff

def extract_combatskill_rich():
    """武功完整資訊：名稱(ref) + 品級(arg2) + 種類(arg6) + 正/逆特效(arg16/17→SpecialEffect) + 典故(arg3)。"""
    eff = build_special_effect_descs()
    ref_cs = load_ref("CombatSkill")
    cs_lang = load_lang("CombatSkill_language")
    def cslang(i):
        return cs_lang[i].replace("\\n", " ").strip() if (i is not None and 0 <= i < len(cs_lang)) else ""
    def fx(eid):
        return eff.get(eid, {}).get("full", "") if (eid is not None and eid >= 0) else ""
    text = open(os.path.join(SRC_DIR, "CombatSkill.cs"), encoding="utf-8").read()
    rows = []
    for argstr in iter_new_calls(text, "CombatSkillItem"):
        args = [re.sub(r"^arg\d+:\s*", "", a) for a in split_top(argstr)]
        if len(args) <= 22:
            continue
        tid = parse_int(args[0])
        typ = parse_int(args[6])
        name = ref_cs.get(tid) or cslang(parse_int(args[1]))
        rows.append({
            "TemplateId": tid,
            "Name": name,
            "Grade": parse_int(args[2]),
            "Type": typ,
            "TypeName": COMBATSKILL_TYPE.get(typ, str(typ)),
            "DirectEffect": fx(parse_int(args[16])),    # 正特效（順練）
            "ReverseEffect": fx(parse_int(args[17])),   # 逆特效（逆練）
            "Flavor": cslang(parse_int(args[3])),        # 典故／介紹
        })
    return {"table": "CombatSkill", "name_field": "Name", "pack": "CombatSkill_language",
            "value_fields": ["Grade", "Type"], "count": len(rows),
            "unresolved": sum(1 for r in rows if not r["Name"]),
            "name_from_ref": sum(1 for r in rows if r["Name"]), "name_from_lang": 0,
            "title": "武功", "rows": rows}

# ----------------------------------------------------------- 主程序 ----
# 6 大類別 + 補充。(表類名, 名稱欄位, [數值欄位], 中文標題)
SPECS = [
    # 武功改用專用抽取器（extract_combatskill_rich，含種類/特效），不走通用 SPECS。
    ("Weapon",            "Name",      ["Grade", "ItemType", "ItemSubType"], "物品·武器"),
    ("Armor",             "Name",      ["Grade", "ItemType", "ItemSubType"], "物品·防具"),
    ("Accessory",         "Name",      ["Grade", "ItemType", "ItemSubType"], "物品·飾品"),
    ("Clothing",          "Name",      ["Grade", "ItemType", "ItemSubType"], "物品·衣物"),
    ("Carrier",           "Name",      ["Grade", "ItemType", "ItemSubType"], "物品·坐騎代步"),
    ("CraftTool",         "Name",      ["Grade", "ItemType", "ItemSubType"], "物品·工具"),
    ("Medicine",          "Name",      ["Grade", "ItemType", "ItemSubType"], "物品·藥品"),
    ("Food",              "Name",      ["Grade", "ItemType", "ItemSubType"], "物品·食物"),
    ("Material",          "Name",      ["Grade", "ItemType", "ItemSubType"], "物品·材料"),
    ("Misc",              "Name",      ["Grade", "ItemType", "ItemSubType"], "物品·雜物"),
    ("SkillBook",         "Name",      ["Grade", "ItemType", "ItemSubType"], "物品·書籍"),
    ("Cricket",           "Name",      ["Grade"],                            "物品·促織"),
    ("OrganizationMember","GradeName", ["Grade"],                            "職稱／身份"),
    ("BuildingBlock",     "Name",      ["MaxLevel", "Type"],                 "建築"),
    ("LifeSkill",         "Name",      ["Grade", "Type"],                    "補充·技藝(生活技能)"),
    ("ConsummateLevel",   "Name",      ["Grade"],                            "補充·絕技境界"),
    ("Profession",        "Name",      [],                                   "補充·志向營生(職業)"),
    ("CharacterTitle",    "Name",      [],                                   "補充·稱號"),
    ("Organization",      "Name",      [],                                   "補充·門派／勢力"),
    # 使用者追加：武學類型、動物、毒、傳承、見聞
    ("CombatSkillType",   "Name",      [],                                   "補充·武學類型"),
    ("Chicken",           "Name",      ["Grade"],                            "補充·動物·元雞"),
    ("Jiao",              "Name",      ["Level"],                            "補充·動物·蛟"),
    ("Poison",            "Name",      [],                                   "補充·毒"),
    ("Legacy",            "Name",      ["Grade"],                            "補充·傳承"),
    ("InformationInfo",   "Name",      ["Grade"],                            "補充·見聞情報"),
    # 第二批追加（使用者「兩者都做」）
    ("TeaWine",           "Name",      ["Grade"],                            "茶酒"),
    ("Merchant",          "UiName",    ["Level"],                            "商隊(商人模板)"),
    ("MerchantType",      "Name",      ["Level"],                            "商人類型"),
    ("DestinyType",       "Name",      [],                                   "命格"),
    ("CharacterFeature",  "Name",      ["Level"],                            "人物特性"),
    ("ProtagonistFeature","Name",      [],                                   "主角特性"),
    ("Character",         "Surname",   [],                                   "NPC生成模板"),
    ("MapBlock",          "Name",      ["Level"],                            "地形(地圖塊)"),
    ("MapArea",           "Name",      [],                                   "地區"),
    ("LandFormType",      "Name",      [],                                   "地貌類型"),
    ("SecretInformation", "Name",      [],                                   "秘聞"),
    ("NeiliType",         "Name",      [],                                   "內力類型"),
    ("TrickType",         "Name",      [],                                   "絕招類型"),
    ("MakeItemType",      "Name",      [],                                   "製造類型"),
    ("MakeItemSubType",   "Name",      [],                                   "製造子類型"),
]

# ------------------------------------------------ 城鎮命名（後綴分析）----
def extract_townnames():
    """LocalTownNames.TownNameCore 為硬編字串字面值；依 id 區間分型，統計後綴(末字)。"""
    src = open(os.path.join(SRC_DIR, "LocalTownNames.cs"), encoding="utf-8").read()
    rng = {k: int(re.search(rf"{k}\s*=\s*(\d+)", src).group(1))
           for k in ["VillageStart", "VillageEnd", "TownStart", "TownEnd",
                     "WalledTownStart", "WalledTownEnd"]}
    pairs = re.findall(r'new TownNameItem\((\d+),\s*"([^"]*)"\)', src)
    def typ(i):
        if rng["VillageStart"] <= i <= rng["VillageEnd"]:        return "村庄(Village)"
        if rng["TownStart"] <= i <= rng["TownEnd"]:              return "市镇(Town)"
        if rng["WalledTownStart"] <= i <= rng["WalledTownEnd"]:  return "关寨(WalledTown)"
        return "其他"
    import collections
    by = collections.defaultdict(list)
    for sid, name in pairs:
        if name:
            by[typ(int(sid))].append({"id": int(sid), "name": name})
    out = {"ranges": rng, "by_type": {}}
    for t, items in by.items():
        suf = collections.Counter(it["name"][-1] for it in items)
        out["by_type"][t] = {"count": len(items),
                             "suffix": dict(suf.most_common()),
                             "names": items}
    return out

def org_name_suffix(org_rows):
    """門派/勢力名後綴(末字)統計 —— Sect 型聚落以組織名命名。"""
    import collections
    c = collections.Counter(r["Name"][-1] for r in org_rows
                            if r["Name"] and not r["Name"].startswith("sectmainstory"))
    return dict(c.most_common())

def main():
    result, summary = {}, []
    # 武功（專用：種類 + 品級 + 正逆特效 + 典故）
    cs = extract_combatskill_rich()
    result["CombatSkill"] = cs
    summary.append((cs["title"], "CombatSkill", cs["count"], cs["unresolved"]))
    for table, namef, vals, title in SPECS:
        try:
            r = extract_table(table, namef, vals)
            r["title"] = title
            result[table] = r
            summary.append((title, table, r["count"], r["unresolved"]))
        except Exception as e:
            summary.append((title, table, f"ERROR: {e}", -1))
            result[table] = {"error": str(e), "title": title, "table": table}
    # 城鎮命名（後綴）
    result["_TownNames"] = extract_townnames()
    if "Organization" in result and "rows" in result["Organization"]:
        result["_TownNames"]["sect_org_name_suffix"] = org_name_suffix(result["Organization"]["rows"])

    with open(os.path.join(OUT_DIR, "taiwu_objects.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"{'標題':<20}{'表':<22}{'列數':>6}{'未解':>6}{'ref':>6}{'lang':>6}")
    print("-" * 66)
    for title, table in [(s[0], s[1]) for s in summary]:
        r = result[table]
        if "error" in r:
            print(f"{title:<20}{table:<22}  ERROR: {r['error']}")
        else:
            print(f"{title:<20}{table:<22}{r['count']:>6}{r['unresolved']:>6}"
                  f"{r['name_from_ref']:>6}{r['name_from_lang']:>6}")

if __name__ == "__main__":
    main()
