#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
太吾繪卷 奇遇／遭遇事件抽取器
==============================
從反編譯 C# 靜態初始化抽出各類奇遇／遭遇事件的「名稱 + 簡短介紹(Desc)」並輸出 JSON。

複用上一層 extract_objects.py 的 helper（split_top / iter_new_calls / load_lang / load_ref），
不重造輪子。

涵蓋資料表（皆來源 ~/dev/taiwu-src/Assembly-CSharp/Config/<Table>.cs）：
  - Adventure          (歷練奇遇，主力)  Name=arg1, Desc=arg2, Type=arg3, CombatDifficulty=arg4,
                         LifeSkillDifficulty=arg5, TimeCost=arg7  → 語言 pack Adventure_language
  - AdventureType      (奇遇類型)        DisplayName=arg1 → AdventureType_language
  - AdventureTerrain   (奇遇地形)        Name=arg1, Desc=arg2 → AdventureTerrain_language
  - TravelingEvent     (行旅遭遇)        Name=arg1, Desc=arg4 → TravelingEvent_language
  - TeaHorseCaravanEvent(茶馬商隊)       Name=arg1, Desc=arg2 → TeaHorseCaravanEvent_language
  - TaiwuBeHuntedEvent (被獵殺/緝捕)     Name=arg1, HeadEvent(主敘述)=arg2 → TaiwuBeHuntedEvent_language
  - ShopEvent          (商店/設施事件)   只有 Desc=arg1（無 Name） → ShopEvent_language

【關鍵資料坑：版本漂移】
反編譯源(~/dev/taiwu-src，2026-05-22)與安裝版的 ConfigRefNameMapping/語言檔 **不同版本**。
驗證(見 README)：Adventure/AdventureType/ShopEvent 的 ref 檔 id→name 與反編譯源「對不上」，
但反編譯源的 arg1/arg2 行號在「安裝版語言檔」內仍能取出 **內部自洽的 Name+Desc 配對**
(name 行與 desc 行相鄰且語意一致)。因此本腳本一律走「語言檔行號」路線，
不採 ref 名稱(避免 Name 來自新版 id 排序、Desc 來自舊版行號 → 張冠李戴)。
TeaHorseCaravanEvent / TaiwuBeHuntedEvent 的 ref 恰好仍對齊，但為一致性也走語言檔。
"""
import os, re, json, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)            # .../object_data_dump
sys.path.insert(0, PARENT)
import extract_objects as EO              # 複用 helper

SRC_DIR = EO.SRC_DIR
OUT = os.path.join(HERE, "adventures.json")

def L(pack, idx):
    """語言檔取行：idx<0 視為空字串；字面 \\n 還原為換行後再壓成單行空白以利彙整。"""
    if idx is None or idx < 0:
        return ""
    lines = EO.load_lang(pack)
    if 0 <= idx < len(lines):
        return lines[idx].replace("\\n", "\n")
    return f"<{pack}_{idx}_invalid>"

def Lshort(pack, idx, limit=120):
    """簡短介紹：取首段（首個換行前），過長截斷。"""
    s = L(pack, idx)
    first = s.split("\n", 1)[0].strip()
    if len(first) > limit:
        first = first[:limit] + "…"
    return first

def pint(v):
    return EO.parse_int(v)

def args_of(text, item_cls):
    """逐列 → 去具名標籤後的參數字串清單。"""
    for argstr in EO.iter_new_calls(text, item_cls):
        yield [re.sub(r"^arg\d+:\s*", "", a) for a in EO.split_top(argstr)]

def read(table):
    with open(os.path.join(SRC_DIR, table + ".cs"), encoding="utf-8") as f:
        return f.read()

# ---------------------------------------------------------- AdventureType ----
def extract_adventure_type():
    """id → DisplayName（走反編譯源 arg1 行號 + 反編譯版語言檔，與 Adventure.Type 對齊）。"""
    text = read("AdventureType")
    pack = "AdventureType_language"
    rows = {}
    for a in args_of(text, "AdventureTypeItem"):
        if len(a) < 2:
            continue
        tid = pint(a[0]); nidx = pint(a[1])
        name = L(pack, nidx).strip()
        rows[tid] = {"TemplateId": tid, "DisplayName": name,
                     "IsTrivial": a[2] if len(a) > 2 else None,
                     "ColorName": a[3].strip('"') if len(a) > 3 else None}
    return rows

# ------------------------------------------------------------- Adventure ----
def extract_adventure(type_map):
    text = read("Adventure")
    pack = "Adventure_language"
    rows = []
    for a in args_of(text, "AdventureItem"):
        if len(a) < 8:
            continue
        tid  = pint(a[0]); ni = pint(a[1]); di = pint(a[2])
        typ  = pint(a[3]); cd = pint(a[4]); ld = pint(a[5]); tc = pint(a[7])
        tname = type_map.get(typ, {}).get("DisplayName", "") if typ is not None else ""
        rows.append({
            "TemplateId": tid,
            "Name": L(pack, ni).strip(),
            "Desc": Lshort(pack, di),
            "DescFull": L(pack, di).strip(),
            "Type": typ,
            "TypeName": tname,
            "CombatDifficulty": cd,
            "LifeSkillDifficulty": ld,
            "TimeCost": tc,
        })
    return rows

# -------------------------------------------------------- AdventureTerrain ----
def extract_terrain():
    text = read("AdventureTerrain")
    pack = "AdventureTerrain_language"
    rows = []
    for a in args_of(text, "AdventureTerrainItem"):
        if len(a) < 3:
            continue
        tid = pint(a[0])
        rows.append({"TemplateId": tid,
                     "Name": L(pack, pint(a[1])).strip(),
                     "Desc": Lshort(pack, pint(a[2])),
                     "DescFull": L(pack, pint(a[2])).strip()})
    return rows

# ---------------------------------------------------------- TravelingEvent ----
def extract_traveling():
    """Name=arg1, Type(enum)=arg3, Desc=arg4。enum 取點號後字尾。"""
    text = read("TravelingEvent")
    pack = "TravelingEvent_language"
    rows = []
    for a in args_of(text, "TravelingEventItem"):
        if len(a) < 5:
            continue
        tid = pint(a[0])
        typ_enum = a[3].split(".")[-1].strip() if "." in a[3] else a[3].strip()
        rows.append({"TemplateId": tid,
                     "Name": L(pack, pint(a[1])).strip(),
                     "Type": typ_enum,
                     "Desc": Lshort(pack, pint(a[4])),
                     "DescFull": L(pack, pint(a[4])).strip()})
    return rows

# ----------------------------------------------------- TeaHorseCaravanEvent ----
TEAHORSE_EVTTYPE = {-1: "未分類", 0: "?", 1: "知名度", 2: "資源/物資"}  # 概略，僅供參考
def extract_teahorse():
    """Name=arg1, Desc=arg2, EventType=arg3, ForwardHappen=arg5, ReturnHappen=arg6。"""
    text = read("TeaHorseCaravanEvent")
    pack = "TeaHorseCaravanEvent_language"
    rows = []
    for a in args_of(text, "TeaHorseCaravanEventItem"):
        if len(a) < 4:
            continue
        tid = pint(a[0]); et = pint(a[3])
        rows.append({"TemplateId": tid,
                     "Name": L(pack, pint(a[1])).strip(),
                     "Desc": Lshort(pack, pint(a[2])),
                     "DescFull": L(pack, pint(a[2])).strip(),
                     "EventType": et})
    return rows

# ------------------------------------------------------ TaiwuBeHuntedEvent ----
def extract_behunted():
    """緝捕方門派名。
    【資料坑】反編譯源 arg1(Name)/arg2(HeadEvent) 行號採「每門派 14 行區塊」步幅，
    但安裝版語言檔每區塊多一行(15 行)，故自 row1 起逐列累積偏移、敘述文字錯位。
    Name 改用 ref（TaiwuBeHuntedEvent.ref 已驗證 id==TemplateId 對齊、為 15 個門派名）。
    敘述(HeadEvent)因偏移不可靠，僅標記 ref 名稱為簡介，不取可能錯位的語言檔行。"""
    text = read("TaiwuBeHuntedEvent")
    id2name = EO.load_ref("TaiwuBeHuntedEvent")
    rows = []
    for a in args_of(text, "TaiwuBeHuntedEventItem"):
        if len(a) < 3:
            continue
        tid = pint(a[0])
        name = id2name.get(tid, "")
        rows.append({"TemplateId": tid,
                     "Name": name,
                     "Desc": f"被「{name}」列為緝捕對象的遭遇事件（觸發/抵抗/勸服/收買/投降/懲戒分支）",
                     "NameSrc": "ref"})
    return rows

# ------------------------------------------------------------- ShopEvent ----
def extract_shop():
    """只有 Desc=arg1（無 Name）。以 Parameters(arg2) 首個非空字串標記事件涉及對象。"""
    text = read("ShopEvent")
    pack = "ShopEvent_language"
    rows = []
    for a in args_of(text, "ShopEventItem"):
        if len(a) < 2:
            continue
        tid = pint(a[0])
        rows.append({"TemplateId": tid,
                     "Desc": Lshort(pack, pint(a[1]), limit=160),
                     "DescFull": L(pack, pint(a[1])).strip()})
    return rows

# ---------------------------------------------------------------- 主程序 ----
def main():
    type_map = extract_adventure_type()
    adv = extract_adventure(type_map)

    # AdventureType 分布（依 Adventure.Type 計數）
    import collections
    dist = collections.Counter(r["Type"] for r in adv)
    type_table = []
    for tid in sorted(type_map):
        it = type_map[tid]
        type_table.append({"TemplateId": tid, "DisplayName": it["DisplayName"],
                            "IsTrivial": it["IsTrivial"], "ColorName": it["ColorName"],
                            "AdventureCount": dist.get(tid, 0)})

    result = {
        "_meta": {
            "source_decompiled": SRC_DIR,
            "lang_dir": EO.LANG_DIR,
            "note": "名稱與介紹一律走語言檔行號(Name=lang[argN])以保 Name+Desc 內部自洽；"
                    "ref 因版本漂移於 Adventure/AdventureType/ShopEvent 不可靠，未採用。",
        },
        "AdventureType": {"title": "奇遇類型", "count": len(type_table), "rows": type_table},
        "Adventure":     {"title": "歷練奇遇", "pack": "Adventure_language",
                          "count": len(adv), "rows": adv},
        "AdventureTerrain": {"title": "奇遇地形", "rows": extract_terrain()},
        "TravelingEvent":   {"title": "行旅遭遇", "rows": extract_traveling()},
        "TeaHorseCaravanEvent": {"title": "茶馬商隊事件", "rows": extract_teahorse()},
        "TaiwuBeHuntedEvent":   {"title": "被獵殺/緝捕事件", "rows": extract_behunted()},
        "ShopEvent":            {"title": "商店/設施事件(僅介紹)", "rows": extract_shop()},
    }
    for k in result:
        if isinstance(result[k], dict) and "rows" in result[k]:
            result[k]["count"] = len(result[k]["rows"])

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    # 終端摘要
    print(f"{'表':<24}{'列數':>6}")
    print("-" * 30)
    for k in ["AdventureType", "Adventure", "AdventureTerrain", "TravelingEvent",
              "TeaHorseCaravanEvent", "TaiwuBeHuntedEvent", "ShopEvent"]:
        print(f"{k:<24}{result[k]['count']:>6}")
    print("\nAdventureType 分布(依 Adventure.Type):")
    for it in type_table:
        print(f"  id {it['TemplateId']:>2}  {it['DisplayName'] or '(空)':<8} "
              f"trivial={it['IsTrivial']:<6} 奇遇數={it['AdventureCount']}")

if __name__ == "__main__":
    main()
