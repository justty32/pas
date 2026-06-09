#!/usr/bin/env python3
"""靜態健檢：XML well-formed、WorldObjectDef defName/class、Keyed 鍵齊全、程式碼 Translate 鍵都有定義。

只解析本 mod 自家的可信 XML（非外部輸入），故用 stdlib ElementTree 即可。
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ok = True


def fail(m):
    global ok
    ok = False
    print("FAIL:", m)


# 1) 所有 XML well-formed（跳過建置輸出）
for p in ROOT.rglob("*.xml"):
    if "/1.6/Assemblies/" in str(p) or "/Source/obj/" in str(p) or "/Source/bin/" in str(p):
        continue
    try:
        ET.parse(p)
    except Exception as e:
        fail(f"XML 壞: {p}: {e}")

# 2) WorldObjectDef defName 與 worldObjectClass
wod = ROOT / "Defs/WorldObjectDefs/Outpost_Sampled.xml"
if wod.exists():
    root = ET.parse(wod).getroot()
    names = [d.findtext("defName") for d in root.findall("WorldObjectDef")]
    if "pas_archival_Outpost" not in names:
        fail("WorldObjectDef defName 應含 pas_archival_Outpost")
    cls = root.find(".//worldObjectClass")
    if cls is None or cls.text != "ColonyArchivalOutpost.Outpost_Sampled":
        fail("worldObjectClass 應為 ColonyArchivalOutpost.Outpost_Sampled")
else:
    fail("缺 Defs/WorldObjectDefs/Outpost_Sampled.xml")


# 3) 兩語言 Keyed 鍵集合一致
def keys(p):
    return {c.tag for c in ET.parse(p).getroot()} if p.exists() else set()


en = keys(ROOT / "Languages/English/Keyed/CAO.xml")
zh = keys(ROOT / "Languages/ChineseTraditional/Keyed/CAO.xml")
if not en:
    fail("缺英文 Keyed")
if en != zh:
    fail(f"Keyed 鍵不一致: 只在EN={en - zh} 只在ZH={zh - en}")

# 4) 程式碼引用的 "CAO.xxx".Translate 鍵都在 Keyed 內
src_keys = set()
for cs in (ROOT / "Source").rglob("*.cs"):
    if "/obj/" in str(cs) or "/bin/" in str(cs):
        continue
    for m in re.finditer(r'"(CAO\.[\w.]+)"\s*\.Translate', cs.read_text(encoding="utf-8")):
        src_keys.add(m.group(1))
missing = src_keys - en
if missing:
    fail(f"程式碼用到但 Keyed 缺: {missing}")

# 5) About.xml 相依宣告齊全
about = ROOT / "About/About.xml"
if about.exists():
    txt = about.read_text(encoding="utf-8")
    for dep in ("brrainz.harmony", "OskarPotocki.VanillaFactionsExpanded.Core", "vanillaexpanded.outposts"):
        if dep not in txt:
            fail(f"About.xml 缺相依: {dep}")
else:
    fail("缺 About/About.xml")

print("OK" if ok else "HEALTHCHECK FAILED")
sys.exit(0 if ok else 1)
