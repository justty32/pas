#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""讀 adventures.json → 產出分類 Markdown（奇遇事件清單）。"""
import os, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "adventures.json"), encoding="utf-8"))

def w(path, text):
    with open(os.path.join(HERE, path), "w", encoding="utf-8") as f:
        f.write(text)

# ---------------------------------------------- 01 歷練奇遇（按 AdventureType 分節）----
adv = d["Adventure"]["rows"]
type_rows = {t["TemplateId"]: t for t in d["AdventureType"]["rows"]}
by_type = collections.defaultdict(list)
for r in adv:
    by_type[r["Type"]].append(r)

lines = ["# 太吾繪卷 · 歷練奇遇（Adventure）清單",
         "",
         f"來源：`~/dev/taiwu-src/Assembly-CSharp/Config/Adventure.cs`（共 {len(adv)} 筆）",
         "名稱／介紹來自 `Adventure_language.txt`（走語言檔行號，理由見 README 版本漂移段）。",
         "難度欄：CombatDifficulty=戰鬥難度、LifeSkillDifficulty=生活技能難度、TimeCost=耗時。",
         ""]
for tid in sorted(by_type):
    rows = by_type[tid]
    tname = type_rows.get(tid, {}).get("DisplayName") or "(未命名)"
    lines.append(f"## 類型 {tid}：{tname}（{len(rows)} 筆）")
    lines.append("")
    lines.append("| Id | 名稱 | 簡短介紹 | 戰鬥難度 | 生活難度 | 耗時 |")
    lines.append("|---:|------|----------|:---:|:---:|:---:|")
    for r in sorted(rows, key=lambda x: x["TemplateId"]):
        desc = (r["Desc"] or "").replace("|", "｜").replace("\n", " ")
        name = (r["Name"] or "").replace("|", "｜")
        lines.append(f"| {r['TemplateId']} | {name} | {desc} | "
                     f"{r['CombatDifficulty']} | {r['LifeSkillDifficulty']} | {r['TimeCost']} |")
    lines.append("")
w("01_歷練奇遇_Adventure.md", "\n".join(lines))

# -------------------------------------------------------- 02 其他遭遇事件表 ----
def table_section(key, name_field="Name", extra_cols=None):
    t = d[key]
    rows = t["rows"]
    out = [f"## {t['title']}（{key}，{t['count']} 筆）", ""]
    cols = ["Id"]
    if name_field:
        cols.append("名稱")
    cols += [c[0] for c in (extra_cols or [])]
    cols.append("簡短介紹")
    out.append("| " + " | ".join(cols) + " |")
    out.append("|" + "|".join(["---:"] + (["---"] if name_field else []) +
                                ["---"] * len(extra_cols or []) + ["---"]) + "|")
    for r in rows:
        cell = [str(r["TemplateId"])]
        if name_field:
            cell.append((r.get(name_field) or "").replace("|", "｜"))
        for _, fld in (extra_cols or []):
            cell.append(str(r.get(fld, "")).replace("|", "｜"))
        desc = (r.get("Desc") or "").replace("|", "｜").replace("\n", " ")
        cell.append(desc)
        out.append("| " + " | ".join(cell) + " |")
    out.append("")
    return out

lines = ["# 太吾繪卷 · 其他遭遇事件清單",
         "",
         "彙整非 Adventure 系列的各類遭遇事件表。各表來源見 README。",
         ""]
lines += table_section("TravelingEvent", extra_cols=[("Type", "Type")])
lines += table_section("TeaHorseCaravanEvent", extra_cols=[("事件型", "EventType")])
lines += table_section("TaiwuBeHuntedEvent")
# ShopEvent 無名稱
t = d["ShopEvent"]
lines.append(f"## {t['title']}（ShopEvent，{t['count']} 筆）")
lines.append("")
lines.append("ShopEventItem 無 Name 欄位，僅有 Desc（結果敘述）。")
lines.append("")
lines.append("| Id | 簡短介紹 |")
lines.append("|---:|------|")
for r in t["rows"]:
    desc = (r.get("Desc") or "").replace("|", "｜").replace("\n", " ")
    lines.append(f"| {r['TemplateId']} | {desc} |")
lines.append("")
w("02_其他遭遇事件.md", "\n".join(lines))

# ----------------------------------------------------------- 03 奇遇地形 ----
lines = ["# 太吾繪卷 · 奇遇地形（AdventureTerrain）", "",
         f"來源 `AdventureTerrain.cs`（{d['AdventureTerrain']['count']} 筆）。",
         "奇遇發生的地形場景，影響可遭遇的事件權重(EvtWeights)。", ""]
lines += table_section("AdventureTerrain")
w("03_奇遇地形_AdventureTerrain.md", "\n".join(lines))

print("Markdown 產出完成：01/02/03")
