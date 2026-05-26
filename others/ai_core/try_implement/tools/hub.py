#!/usr/bin/env python3
"""hub — Function Hub（CLAUDE.md 元件 4；規範未定，本版按我的想法定義）。

thinking_routing.md 說 Hub「將脫離網路概念，進入另一個領域」，但完整定義未定。
使用者授權我自行拍板，這是我的【最小可用定義】：

    Hub = 把整個函式生態，轉成「給 LLM 看的 skill 清單」的透鏡。

它在 Indexer 之上多做兩件事：
1. **語意化**：把每個函式的 metadata 轉成一條「技能」描述（名稱 + 一句話用途 + 執行提示）。
2. **預算化（核心）**：套用 context budget。清單超過預算時自動「做摘要 / 收斂」，
   避免 list 太大撐爆 LLM context——這正是 CLAUDE.md 標記的設計待辦
   （"hub 要能對函式做摘要 (shorter conclusion)"）。

== 為什麼這屬於「另一個領域」==
Indexer/Router/Switch 都在「程式對程式」的世界（查表、分派、執行）。Hub 服務的對象是
**LLM 本身**：它把工具生態整理成 LLM 能讀、且大小受控的動作空間。給 LLM 一個有界、
有描述的工具集 = 在「編排層」約束 LLM 的隨機性（見 docs/llm_taming_framework.md）。

== 用法 ==
    hub --scan ../funcs                          # 印 skill 清單（預設格式 skills）
    hub --scan ../funcs --budget 200             # 限制 200 字元，超過就收斂成精簡版
    hub --scan ../funcs --format json|md|skills
    hub --metadata

== 設計決策 ==
1. summary 來源優先序：metadata 的 description/summary 欄位 → 沒有就從軸值合成
   （如 one_shot+stateless →「純函式工具」）。⚠ 八軸【沒有】語意用途欄位（Gap C），
   故 hub 只能合成粗略 summary；真要好用的 skill 清單，需要描述軸或 AI 生成摘要
   （= thinking_routing「Indexer 升級版」）。本工具把這個缺口暴露得很具體。
2. 預算超出時的收斂策略：full（多行/技能）→ compact（一行/技能 name — summary）→
   truncated（截斷 summary 並附「省略 N 項」說明）。逐級退讓，KISS。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _common import ensure_ai_core_importable

ensure_ai_core_importable()
import ai_core  # noqa: E402
from indexer import build_index  # noqa: E402  # 重用 Indexer 的掃描（已可安全 import）


def _synthesize_summary(meta: dict) -> str:
    """八軸沒有語意用途欄位時，從軸值合成一句粗略 summary（Gap C 的退路）。"""
    lifecycle = meta.get("lifecycle", "one_shot")
    state = meta.get("state", "stateless")
    bits = []
    bits.append("常駐服務" if lifecycle == "persistent" else "一次性")
    bits.append("會寫外部狀態" if state == "stateful_external" else "無副作用")
    g = meta.get("guarantee")
    if g == "idempotent":
        bits.append("可安全重試")
    elif g == "transactional":
        bits.append("具事務性")
    return "、".join(bits)


def to_skill(name: str, info: dict) -> dict:
    """把一條 index entry 轉成 skill 描述。"""
    meta = info.get("metadata", {})
    # description/summary 不在八軸內，但若函式自行宣告（如 SFC store）就優先用
    summary = meta.get("description") or meta.get("summary") or _synthesize_summary(meta)
    return {
        "name": name,
        "summary": summary,
        "lifecycle": meta.get("lifecycle", "one_shot"),
        "side_effects": meta.get("state") == "stateful_external",
        "retriable": meta.get("guarantee") in ("idempotent", "transactional"),
        "path": info.get("path"),
    }


def build_skill_list(scan_dir: Path, timeout: float) -> list[dict]:
    index = build_index(scan_dir, timeout)
    return [to_skill(name, info) for name, info in index["functions"].items()]


# ---- 三級渲染（配合 budget 逐級收斂）----

def _render_full(skills: list[dict]) -> str:
    lines = ["你可使用以下工具："]
    for s in skills:
        flags = []
        if s["side_effects"]:
            flags.append("有副作用")
        if s["retriable"]:
            flags.append("可重試")
        flag_str = f"（{', '.join(flags)}）" if flags else ""
        lines.append(f"- {s['name']}：{s['summary']}{flag_str}")
    return "\n".join(lines)


def _render_compact(skills: list[dict]) -> str:
    return "可用工具：\n" + "\n".join(f"- {s['name']} — {s['summary']}" for s in skills)


def _render_truncated(skills: list[dict], budget: int) -> str:
    header = "可用工具（精簡）："
    out = [header]
    used = len(header)
    shown = 0
    for s in skills:
        line = f"- {s['name']}: {s['summary'][:24]}"
        if used + len(line) + 1 > budget and shown > 0:
            break
        out.append(line)
        used += len(line) + 1
        shown += 1
    omitted = len(skills) - shown
    if omitted > 0:
        out.append(f"…（另有 {omitted} 項工具未列出，請用 --budget 放寬或分頁查詢）")
    return "\n".join(out)


def render_skills(skills: list[dict], budget: int | None) -> str:
    """套 budget 逐級收斂：full → compact → truncated。"""
    full = _render_full(skills)
    if budget is None or len(full) <= budget:
        return full
    compact = _render_compact(skills)
    if len(compact) <= budget:
        return compact
    return _render_truncated(skills, budget)


def render_md(skills: list[dict]) -> str:
    lines = ["# Skill 清單", "", f"共 {len(skills)} 項工具。", ""]
    for s in skills:
        lines.append(f"## {s['name']}")
        lines.append(f"- 用途：{s['summary']}")
        lines.append(f"- lifecycle：`{s['lifecycle']}`")
        lines.append(f"- 有副作用：{'是' if s['side_effects'] else '否'}")
        lines.append(f"- 可重試：{'是' if s['retriable'] else '否'}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ai_core.register(lifecycle="one_shot", state="stateless")
    ai_core.intercept()

    p = argparse.ArgumentParser(prog="hub", description="把函式生態轉成給 LLM 的 skill 清單")
    p.add_argument("--scan", required=True, help="要掃描的函式資料夾")
    p.add_argument("--format", choices=["skills", "json", "md"], default="skills")
    p.add_argument("--budget", type=int, default=None,
                   help="skills 格式的字元預算；超過自動收斂")
    p.add_argument("--timeout", type=float, default=10.0)
    args = p.parse_args()

    scan_dir = Path(args.scan)
    if not scan_dir.is_dir():
        print(f"錯誤：{scan_dir} 不是資料夾", file=sys.stderr)
        return 1

    skills = build_skill_list(scan_dir, args.timeout)

    if args.format == "json":
        print(json.dumps({"count": len(skills), "skills": skills}, ensure_ascii=False, indent=2))
    elif args.format == "md":
        print(render_md(skills))
    else:
        print(render_skills(skills, args.budget))
    return 0


if __name__ == "__main__":
    sys.exit(main())
