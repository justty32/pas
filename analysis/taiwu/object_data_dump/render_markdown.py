#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 taiwu_objects.json 渲染成分類 Markdown 留檔（含品級分布、城鎮命名後綴）。"""
import os, json, collections

OUT = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(OUT, "taiwu_objects.json"), encoding="utf-8"))

def clean(s):
    return (s or "").strip().replace("|", "\\|")

def dist_line(rows, field):
    c = collections.Counter(r.get(field) for r in rows if r.get(field) is not None)
    return " · ".join(f"{k}×{c[k]}" for k in sorted(c))

def table_md(rows, value_fields, val_header):
    out = ["| TemplateId | 名稱 | " + " | ".join(val_header) + " |",
           "|---:|---|" + "".join("---:|" for _ in val_header)]
    for r in rows:
        vals = ["" if r.get(f) is None else str(r.get(f)) for f in value_fields]
        out.append(f"| {r['TemplateId']} | {clean(r.get('Name'))} | " + " | ".join(vals) + " |")
    return "\n".join(out)

def section(table_key, value_fields, val_header, title=None, intro="", dist_field=None):
    r = D[table_key]
    md = [f"## {title or r['title']}（`{table_key}`，{r['count']} 筆）", ""]
    if intro:
        md += [intro, ""]
    if dist_field:
        dl = dist_line(r["rows"], dist_field)
        if dl:
            md += [f"**{val_header[value_fields.index(dist_field)]} 分布**：{dl}", ""]
    md += [table_md(r["rows"], value_fields, val_header), ""]
    return "\n".join(md)

HEADER = ("> 來源：名稱取自安裝版 `StreamingAssets/ConfigRefNameMapping/*.ref.txt`"
          "（與遊戲同步），品級／數值取自反編譯 `Assembly-CSharp/Config/*.cs` 的硬編資料，"
          "以 TemplateId 對接。抽取工具：`extract_objects.py`。\n")

G = ["品級(Grade)"]
L = ["階(Level)"]
ITEM_INTRO = "品級 Grade：物品品階範圍 **0~8**，數字越大品級越高。"

# ---------------- 01 / 03 / 04（單一主類別）----------------
# 武功：總覽 + 依「功法種類」拆 14 詳檔（每檔依品級分節，含正/逆特效＋典故）
cs_rows = D["CombatSkill"]["rows"]
SUBDIR = os.path.join(OUT, "01_武功-種類")
os.makedirs(SUBDIR, exist_ok=True)
EFFECT_NOTE = ("> 分類鍵＝`CombatSkillItem.Type`(14 類)。**正特效**＝順練效果、**逆特效**＝逆練效果"
               "（來自 `SpecialEffect` 表，由武功的 DirectEffectID/ReverseEffectID 連結）；"
               "**典故**為功法文學介紹(Desc)。特效文字中的 `$0$`/`$1$` 是遊戲即時計算的"
               "「威力成數」佔位，靜態資料無法還原，保留原樣。\n")

bytype = collections.defaultdict(list)
for r in cs_rows:
    bytype[r["Type"]].append(r)

# 各種類詳檔
for tid in sorted(bytype):
    trows = bytype[tid]
    zh = trows[0]["TypeName"]
    with open(os.path.join(SUBDIR, f"{tid:02d}_{zh}.md"), "w", encoding="utf-8") as f:
        f.write(f"# 太吾繪卷 · 武功種類 — {zh}（{len(trows)} 個）\n\n" + HEADER + "\n" + EFFECT_NOTE + "\n")
        bygrade = collections.defaultdict(list)
        for r in trows:
            bygrade[r["Grade"]].append(r)
        for g in sorted(bygrade, key=lambda x: -99 if x is None else x):
            grows = sorted(bygrade[g], key=lambda r: r["TemplateId"])
            f.write(f"## 品級 {g}（{len(grows)} 個）\n\n")
            for r in grows:
                f.write(f"### {clean(r['Name'])}（id {r['TemplateId']}）\n")
                if r["DirectEffect"]:
                    f.write(f"- **正特效**：{r['DirectEffect']}\n")
                if r["ReverseEffect"]:
                    f.write(f"- **逆特效**：{r['ReverseEffect']}\n")
                if r["Flavor"]:
                    f.write(f"- 典故：{r['Flavor']}\n")
                f.write("\n")

# 總覽
with open(os.path.join(OUT, "01_武功.md"), "w", encoding="utf-8") as f:
    f.write("# 太吾繪卷 · 武功（CombatSkill）總覽\n\n" + HEADER + "\n")
    f.write("武功依**功法種類**（Type，14 類）拆檔，各檔內再依**品級**分節，含正／逆特效與典故，"
            "詳見 [`01_武功-種類/`](01_武功-種類/)。\n\n")
    grades = sorted({r["Grade"] for r in cs_rows if r["Grade"] is not None})
    f.write("## 種類 × 品級 分布（種類名連結至詳檔）\n\n")
    f.write("| 種類 | 總數 | " + " | ".join(f"品{g}" for g in grades) + " |\n")
    f.write("|---|---:|" + "".join("---:|" for _ in grades) + "\n")
    col_tot = collections.Counter()
    for tid in sorted(bytype):
        trows = bytype[tid]
        zh = trows[0]["TypeName"]
        gc = collections.Counter(r["Grade"] for r in trows)
        for g in grades:
            col_tot[g] += gc.get(g, 0)
        cells = " | ".join(str(gc.get(g, 0)) for g in grades)
        f.write(f"| [{zh}](01_武功-種類/{tid:02d}_{zh}.md) | {len(trows)} | {cells} |\n")
    f.write(f"| **合計** | **{len(cs_rows)}** | " + " | ".join(f"**{col_tot[g]}**" for g in grades) + " |\n\n")
    f.write("## 全武功索引（名稱・品級・種類）\n\n")
    f.write("| id | 名稱 | 品級 | 種類 |\n|---:|---|---:|---|\n")
    for r in sorted(cs_rows, key=lambda r: r["TemplateId"]):
        f.write(f"| {r['TemplateId']} | {clean(r['Name'])} | {r['Grade']} | {r['TypeName']} |\n")

with open(os.path.join(OUT, "03_職稱身份.md"), "w", encoding="utf-8") as f:
    f.write("# 太吾繪卷 · 職稱／身份（OrganizationMember）名稱與階級\n\n" + HEADER + "\n")
    f.write("各勢力／聚落的「成員職稱（身份）」與其 **階級 Grade（0~8）**。"
            "Grade 8 為最高位（掌门／城主／大当家／太吾传人），0 最低（杂役／乞丐／村民）。"
            "名稱已由 ref 檔消歧（如「失心人」記為「入魔者1~9」、城主／镇长依聚落種類加前綴）。\n\n")
    f.write(section("OrganizationMember", ["Grade"], ["階級(Grade)"], "職稱／身份", dist_field="Grade"))

with open(os.path.join(OUT, "04_建築.md"), "w", encoding="utf-8") as f:
    f.write("# 太吾繪卷 · 建築（BuildingBlock）名稱與最高等級\n\n" + HEADER + "\n")
    f.write("BuildingBlock 同時涵蓋『地塊（空地/水域/石山…）』與『可建建築』，"
            "「品級」以 **MaxLevel（最高可建等級）** 表示。\n\n")
    f.write(section("BuildingBlock", ["MaxLevel"], ["最高等級(MaxLevel)"], "建築", dist_field="MaxLevel"))

# ---------------- 05 城鎮種類 + 命名後綴 ----------------
SETTLEMENT = [
    (0, "Village", "村庄", "最小型聚落，農牧為主。", "村 / 乡"),
    (1, "Town", "市镇", "人口眾多、與大道相連的城鎮。", "镇 / 驿"),
    (2, "WalledTown", "关寨／县城", "以圍牆關寨護衛的水陸要隘。", "寨 / 口 / 关 / 砦"),
    (3, "City", "城（城池／州府）", "規模最大的世俗聚落。", "（用所屬組織名，無隨機後綴）"),
    (4, "Sect", "门派据点", "門派所據的山門／谷地。", "（用門派名，如 派 / 谷 / 门 / 宗 / 庄）"),
    (5, "TaiwuVillage", "太吾村", "玩家家園聚落。", "（固定名「太吾村」）"),
]
tn = D["_TownNames"]
with open(os.path.join(OUT, "05_城鎮種類.md"), "w", encoding="utf-8") as f:
    f.write("# 太吾繪卷 · 城鎮種類與命名後綴\n\n")
    f.write("> 種類列舉：`EOrganizationSettlementType`；命名資料：`Config/LocalTownNames.cs` "
            "的 `TownNameCore`（硬編字串）；命名規則見 `WorldMapModel.GetSettlementName`："
            "有隨機名 id 者用鎮名池，否則用所屬組織名。\n\n")
    f.write("## 一、城鎮種類（6 型，序即規模由小到大）\n\n")
    f.write("| 序(Enum) | 列舉名 | 中文 | 說明 | 命名後綴 |\n|---:|---|---|---|---|\n")
    for i, en, zh, desc, suf in SETTLEMENT:
        f.write(f"| {i} | {en} | {zh} | {desc} | {suf} |\n")
    f.write("\n## 二、命名後綴（末字）統計\n\n")
    f.write("世俗聚落（村庄／市镇／关寨）的名字來自 `TownNameCore` 隨機池，**末字即種類標記**：\n\n")
    f.write("| 聚落種類 | 名稱數 | 後綴分布（後綴×數量） |\n|---|---:|---|\n")
    order = ["村庄(Village)", "市镇(Town)", "关寨(WalledTown)"]
    for t in order:
        info = tn["by_type"][t]
        sufs = " · ".join(f"**{k}**×{v}" for k, v in info["suffix"].items())
        f.write(f"| {t} | {info['count']} | {sufs} |\n")
    f.write("\n> **關於「堡」**：原版 `TownNameCore` 鎮名池中**不含「堡」**結尾；"
            "「丰城驿」「禹城乡」等的「城」是地名前綴而非後綴。\n"
            "> 「堡」「庄／山庄」「谷」「派」這類多見於 **門派／勢力名（Organization）**，"
            "用於 Sect 型據點命名（如 铸剑山庄、百花谷；玩家自製的「陳家堡」即屬此類）。\n\n")
    sect_suf = tn.get("sect_org_name_suffix", {})
    f.write("門派／勢力名末字分布（Sect 型據點命名來源，含地名型勢力故較雜）：\n\n")
    f.write(" · ".join(f"{k}×{v}" for k, v in sect_suf.items()) + "\n\n")
    f.write("## 三、完整鎮名清單（依種類）\n\n")
    for t in order:
        info = tn["by_type"][t]
        names = "、".join(it["name"].strip() for it in info["names"])
        f.write(f"### {t}（{info['count']}）\n\n{names}\n\n")

# ---------------- 02 物品（拆 3 檔）＋ 06~15 多表檔 ----------------
# (檔名, 檔標題, 檔前言, [ (表, 值欄位, 表頭, 區段標題, 分布欄位) ... ])
GROUPS = [
    ("02a_物品-武器.md", "物品 · 武器", ITEM_INTRO, [
        ("Weapon", ["Grade"], G, "武器", "Grade"),
    ]),
    ("02b_物品-防具飾品衣物.md", "物品 · 防具／飾品／衣物", ITEM_INTRO, [
        ("Armor", ["Grade"], G, "防具", "Grade"),
        ("Accessory", ["Grade"], G, "飾品", "Grade"),
        ("Clothing", ["Grade"], G, "衣物", "Grade"),
    ]),
    ("02c_物品-消耗品.md", "物品 · 消耗品", ITEM_INTRO, [
        ("Medicine", ["Grade"], G, "藥品", "Grade"),
        ("Food", ["Grade"], G, "食物", "Grade"),
        ("TeaWine", ["Grade"], G, "茶酒", "Grade"),
    ]),
    ("02d_物品-材料書籍雜項.md", "物品 · 材料／書籍／工具／坐騎／促織", ITEM_INTRO, [
        ("Material", ["Grade"], G, "材料", "Grade"),
        ("Misc", ["Grade"], G, "雜物", "Grade"),
        ("SkillBook", ["Grade"], G, "書籍", "Grade"),
        ("CraftTool", ["Grade"], G, "工具", "Grade"),
        ("Carrier", ["Grade"], G, "坐騎／代步", "Grade"),
        ("Cricket", ["Grade"], G, "促織", "Grade"),
    ]),
    ("06_技藝武學.md", "補充 · 技藝・絕技境界・武學類型", "", [
        ("LifeSkill", ["Grade"], G, "技藝（生活技能 LifeSkill）", "Grade"),
        ("ConsummateLevel", ["Grade"], G, "絕技境界（ConsummateLevel）", "Grade"),
        ("CombatSkillType", [], [], "武學類型（拳/掌/剑…）", None),
    ]),
    ("07_動物與毒.md", "補充 · 動物（元雞・蛟）與毒", "", [
        ("Chicken", ["Grade"], G, "動物·元雞", "Grade"),
        ("Jiao", ["Level"], L, "動物·蛟", "Level"),
        ("Poison", [], [], "毒", None),
    ]),
    ("08_傳承.md", "補充 · 傳承（傳承功法）", "", [
        ("Legacy", ["Grade"], G, "傳承（Legacy）", "Grade"),
    ]),
    ("09_見聞情報.md", "補充 · 見聞／情報", "", [
        ("InformationInfo", ["Grade"], G, "見聞／情報（InformationInfo）", "Grade"),
    ]),
    ("10_人物與組織.md", "補充 · 志向營生・稱號・門派勢力", "", [
        ("Profession", [], [], "志向／營生（Profession）", None),
        ("CharacterTitle", [], [], "稱號（CharacterTitle，含時效）", None),
        ("Organization", [], [], "門派／勢力（Organization）", None),
    ]),
    ("11_命格與特性.md", "命格與特性", "", [
        ("DestinyType", [], [], "命格（六道）", None),
        ("ProtagonistFeature", [], [], "主角特性", None),
        ("CharacterFeature", ["Level"], L, "人物特性（天賦/體質等）", "Level"),
    ]),
    ("12_NPC與商隊模板.md", "NPC 生成模板與商隊", "", [
        ("Character", [], [], "NPC 生成模板（依地區×性別×類型）", None),
        ("MerchantType", ["Level"], L, "商人類型（商號）", "Level"),
        ("Merchant", ["Level"], L, "商隊模板", "Level"),
    ]),
    ("13_地形與地區.md", "地形・地區・地貌", "", [
        ("MapArea", [], [], "地區（世界地圖區域）", None),
        ("MapBlock", ["Level"], L, "地形（地圖塊）", "Level"),
        ("LandFormType", [], [], "地貌類型", None),
    ]),
    ("14_秘聞.md", "秘聞", "", [
        ("SecretInformation", [], [], "秘聞（SecretInformation）", None),
    ]),
    ("15_類型枚舉.md", "類型枚舉（內力・絕招・製造）", "", [
        ("NeiliType", [], [], "內力類型", None),
        ("TrickType", [], [], "絕招類型", None),
        ("MakeItemType", [], [], "製造類型", None),
        ("MakeItemSubType", [], [], "製造子類型", None),
    ]),
]
for fname, ftitle, intro, specs in GROUPS:
    with open(os.path.join(OUT, fname), "w", encoding="utf-8") as f:
        f.write(f"# 太吾繪卷 · {ftitle}\n\n" + HEADER + "\n")
        if intro:
            f.write(intro + "\n\n")
        for tbl, vf, vh, title, df in specs:
            if tbl in D and "rows" in D[tbl]:
                f.write(section(tbl, vf, vh, title, dist_field=df))

# 移除被取代的舊單一大檔
import glob
_written = {fname for fname, *_ in GROUPS}
for p in glob.glob(os.path.join(OUT, "02*.md")):
    if os.path.basename(p) not in _written:   # 清掉舊的物品分檔命名
        os.remove(p)
for old in ["06_補充.md"]:
    p = os.path.join(OUT, old)
    if os.path.exists(p):
        os.remove(p)

print("已輸出 01,02a-d,03,04,05 + 06-15")
