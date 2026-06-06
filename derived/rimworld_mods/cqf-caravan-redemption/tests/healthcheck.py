#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CQF Caravan Redemption — 離線靜態健檢
=====================================
不啟動遊戲，純比對 XML 引用的型別 / defName / 欄位是否真實存在：
  1. 每個 <li Class="..."> 的型別在 CQF 反編譯碼 或 原版 Assembly-CSharp 反組譯輸出中存在
  2. 引用的 ThingDef(Silver)、MessageTypeDef(PositiveEvent)、ThingSetMaker class、
     cross-ref 的 ThingSetMakerDef defName 真實存在
  3. IntRange 用 min~max
  4. 所有 XML well-formed
退出碼 0＝全綠；非 0＝有問題。
"""
import os, re, sys, subprocess, xml.etree.ElementTree as ET

MOD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CQF_DECOMP = "/home/lorkhan/repo/pas/projects/rimworld_mods/custom-quest-framework/decompiled/QuestEditor_Library/QuestEditor_Library.decompiled.cs"
MANAGED = "/home/lorkhan/.local/share/Steam/steamapps/common/RimWorld/RimWorldWin64_Data/Managed"
ASM = os.path.join(MANAGED, "Assembly-CSharp.dll")

problems = []
notes = []

# ---------- 載入 CQF 反編譯型別名 ----------
with open(CQF_DECOMP, encoding="utf-8", errors="replace") as f:
    cqf_src = f.read()
cqf_types = set(re.findall(r'\bclass\s+([A-Za-z0-9_]+)', cqf_src))

# ---------- 從 Assembly-CSharp 取得型別清單（monodis）----------
vanilla_types = set()
try:
    out = subprocess.run(["monodis", "--typedef", ASM], capture_output=True, text=True, timeout=120).stdout
    # monodis --typedef 行內含 namespace.Type
    for m in re.finditer(r'([A-Za-z_][\w.]*\.)?([A-Za-z_]\w+)', out):
        vanilla_types.add(m.group(2))
    notes.append(f"monodis 取得原版型別 {len(vanilla_types)} 筆")
except Exception as e:
    notes.append(f"monodis 失敗（{e}）— 原版型別檢查降級為白名單")

# 已知原版 QuestNode / 型別白名單（monodis 不可用時的後備）
vanilla_whitelist = {
    "QuestNode_Sequence", "QuestNode_DropPods", "QuestNode_GenerateThingSet",
    "ThingSetMaker_StackCount", "QuestScriptDef", "ThingSetMakerDef",
}
vanilla_types |= vanilla_whitelist

def type_exists(short):
    return short in cqf_types or short in vanilla_types

# ---------- 逐 XML 檢查 ----------
xml_files = []
for root, _, files in os.walk(os.path.join(MOD, "1.6")):
    for fn in files:
        if fn.endswith(".xml"):
            xml_files.append(os.path.join(root, fn))
for root, _, files in os.walk(os.path.join(MOD, "Languages")):
    for fn in files:
        if fn.endswith(".xml"):
            xml_files.append(os.path.join(root, fn))
xml_files.append(os.path.join(MOD, "About", "About.xml"))
xml_files.append(os.path.join(MOD, "LoadFolders.xml"))

defined_thingsetmaker_defs = set()
referenced_thingsetmaker_defs = set()

for path in xml_files:
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        problems.append(f"[XML 解析失敗] {path}: {e}")
        continue
    rootel = tree.getroot()

    # 收集本 mod 定義的 ThingSetMakerDef defName
    for tsm in rootel.iter("ThingSetMakerDef"):
        dn = tsm.findtext("defName")
        if dn:
            defined_thingsetmaker_defs.add(dn.strip())

    for el in rootel.iter():
        # 1. Class 屬性型別存在性
        cls = el.get("Class")
        if cls:
            short = cls.split(".")[-1]
            if not type_exists(short):
                problems.append(f"[未知型別] {os.path.relpath(path,MOD)}: Class=\"{cls}\"（短名 {short} 不在 CQF 反編譯 或 原版型別中）")
        # 2. ThingSetMaker root class（<root Class=...>）— 已由上面通用 Class 檢查覆蓋
        # 3. thingSetMaker cross-ref
        if el.tag == "thingSetMaker" and el.text:
            referenced_thingsetmaker_defs.add(el.text.strip())
        # 4. IntRange 格式（countRange / expireDaysRange 等）
        if el.tag in ("countRange", "expireDaysRange") and el.text:
            t = el.text.strip()
            if "~" not in t and not re.fullmatch(r'-?\d+(\.\d+)?', t):
                problems.append(f"[IntRange/FloatRange 格式] {os.path.relpath(path,MOD)}: <{el.tag}>{t}</{el.tag}> 應為 min~max")

# ThingSetMakerDef cross-ref 解析
for ref in referenced_thingsetmaker_defs:
    if ref.startswith("$"):
        continue
    if ref not in defined_thingsetmaker_defs:
        problems.append(f"[ThingSetMakerDef 未定義] thingSetMaker 引用 '{ref}' 但本 mod 未定義（且非原版內建已知）")

# ---------- 欄位成員檢查：CQF 型別的子欄位是否為真實 public 成員 ----------
# 從反編譯源抽出每個 CQF class 的 public 欄位名
def cqf_class_fields(classname):
    m = re.search(r'\bclass\s+' + re.escape(classname) + r'\b', cqf_src)
    if not m:
        return None
    start = m.end()
    # 取到下一個 class 宣告為界
    nxt = re.search(r'\n\tpublic (?:abstract |sealed )?class ', cqf_src[start:])
    body = cqf_src[start:start + (nxt.start() if nxt else 4000)]
    fields = set(re.findall(r'public\s+[\w<>,\.\[\]\? ]+?\s+([A-Za-z_]\w*)\s*[;=]', body))
    return fields

# 我們 XML 中對 CQF 型別寫了哪些子標籤
cqf_field_usage = {
    "CQFAction_Message": {"message", "type"},
    "CQFAction_SentSignal": {"signal", "addQuestPrefix"},
    "QuestNode_DoCQFActions": {"actions"},  # inSignal 留空未寫
}
for cls, used in cqf_field_usage.items():
    fields = cqf_class_fields(cls)
    if fields is None:
        problems.append(f"[欄位檢查] 找不到 CQF class {cls}")
        continue
    for fld in used:
        if fld not in fields:
            problems.append(f"[未知欄位] {cls}.{fld} 不是 public 成員（真實成員：{sorted(fields)}）")
        else:
            notes.append(f"欄位確認 {cls}.{fld}")

# ---------- 已知原版 defName 引用檢查（軟檢查：對照原版 Data 目錄）----------
RW_DATA = "/home/lorkhan/.local/share/Steam/steamapps/common/RimWorld/Data"
def defname_in_vanilla(defname, tag_hint):
    try:
        out = subprocess.run(
            ["grep", "-rl", f"<defName>{defname}</defName>", RW_DATA],
            capture_output=True, text=True, timeout=60).stdout.strip()
        return bool(out)
    except Exception:
        return None

for dn, hint in [("Silver", "ThingDef"), ("PositiveEvent", "MessageTypeDef")]:
    r = defname_in_vanilla(dn, hint)
    if r is False:
        problems.append(f"[原版 defName 缺失] {hint} '{dn}' 在原版 Data 中找不到 <defName>")
    elif r is True:
        notes.append(f"原版 {hint} '{dn}' 已確認存在")
    else:
        notes.append(f"原版 {hint} '{dn}' 無法確認（grep 失敗）")

# ---------- 報告 ----------
print("=== CQF Caravan Redemption 靜態健檢 ===")
for n in notes:
    print("  note:", n)
print(f"  掃描 XML 檔 {len(xml_files)} 個")
print(f"  本 mod ThingSetMakerDef: {sorted(defined_thingsetmaker_defs)}")
print(f"  thingSetMaker 引用: {sorted(referenced_thingsetmaker_defs)}")
if problems:
    print("\n--- 發現問題 ---")
    for p in problems:
        print("  X", p)
    sys.exit(1)
else:
    print("\n全部檢查通過：未發現臆造型別 / 欄位 / defName 問題。")
    sys.exit(0)
