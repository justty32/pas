#!/usr/bin/env python3
"""Switch — 有條件邏輯的 router（條件式 dispatcher）。

對應 thinking_routing.md「Switch」：在 mapping 之外加入條件判斷
（若需求滿足某條件 → 導航到程式 A；否則 → 程式 B）。
典型例子：依輸入語言（C / Python）路由到不同 linter。

== 待設計決策：Switch 的條件表達方式（spike 選擇） ==
為符合 KISS，本實作把「條件」設計成一張**規則表（rule list）**，每條規則檢查
某個「key 的值」是否等於某常數，命中就路由到對應 target。key 的值來源有兩種：

  1. ``arg``  — 取自 CLI flag（如 ``--lang c`` 提供的 lang）
  2. ``ext``  — 取自輸入檔副檔名（如 input.py → "py"）

設定檔格式（JSON）：

    {
      "switch": {
        "on": "lang",                 # 要判斷的變數名（switch 變數）
        "source": "arg",              # arg | ext；變數值的來源
        "rules": [
          {"equals": "c",      "target": {"path": "./c_linter.sh",  "type": "exec"}},
          {"equals": "python", "target": {"path": "./py_linter.sh", "type": "exec"}}
        ],
        "default": {"path": "./generic_linter.sh", "type": "exec"}   # 選填
      }
    }

選此格式的理由：純資料、無 DSL、無 eval；命中規則是單純的字串相等比較，
LLM 容易生成、人容易讀、且不引入任何相依（不重造輪子也不造規則引擎）。
更複雜的條件（範圍、正則）留待正式規範決定，spike 不過度工程化。

特性（依 ai_core 軸）：lifecycle one_shot、state stateless。

用法：
    switch.py --config switch.json --lang c -- <args...>
    switch.py --config switch.json --input foo.py -- <args...>   # source=ext 時用副檔名
    switch.py --metadata
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from _common import ensure_ai_core_importable

ensure_ai_core_importable()
import ai_core  # noqa: E402


def resolve_command(target: dict, base_dir: Path) -> list[str]:
    """與 router.resolve_command 同邏輯（spike 不抽共用模組，見 README 缺口回報）。"""
    ttype = target.get("type", "exec")
    if ttype != "exec":
        raise ValueError(f"switch 目前只支援 type=exec，得到 {ttype!r}")
    raw_path = target.get("path")
    if not raw_path:
        raise ValueError("target 缺少 'path'")
    path = (base_dir / raw_path).resolve()
    if path.suffix == ".py":
        return [sys.executable, str(path)]
    if path.suffix == ".sh":
        return ["bash", str(path)]
    return [str(path)]


def decide_value(spec: dict, args: argparse.Namespace) -> str | None:
    """依 source 取出 switch 變數的值。"""
    source = spec.get("source", "arg")
    if source == "arg":
        # on 指定的變數名，從 --lang / --on 取值
        return args.lang
    if source == "ext":
        if not args.input:
            return None
        return Path(args.input).suffix.lstrip(".")
    raise ValueError(f"未知的 source：{source!r}（只支援 arg / ext）")


def pick_target(spec: dict, value: str | None) -> dict | None:
    for rule in spec.get("rules", []):
        if rule.get("equals") == value:
            return rule["target"]
    return spec.get("default")


def main() -> int:
    ai_core.register(lifecycle="one_shot", state="stateless")
    ai_core.intercept()

    parser = argparse.ArgumentParser(
        prog="switch",
        description="條件式 dispatcher：依輸入條件路由到不同目標",
    )
    parser.add_argument("--config", required=True, help="switch 設定檔（JSON）")
    parser.add_argument("--lang", help="source=arg 時的判斷值（如 c / python）")
    parser.add_argument("--input", help="source=ext 時，從此檔副檔名取判斷值")
    parser.add_argument("--explain", action="store_true",
                        help="只印出會路由到哪個 target，不實際執行")
    parser.add_argument(
        "rest",
        nargs=argparse.REMAINDER,
        help="要轉交給目標的引數（用 -- 分隔）",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_file():
        print(f"錯誤：找不到設定檔 {config_path}", file=sys.stderr)
        return 1

    base_dir = config_path.resolve().parent
    spec = json.loads(config_path.read_text(encoding="utf-8")).get("switch")
    if not isinstance(spec, dict):
        print("錯誤：設定檔缺少 'switch' 物件", file=sys.stderr)
        return 1

    value = decide_value(spec, args)
    target = pick_target(spec, value)

    if target is None:
        print(
            f"錯誤：條件 {spec.get('on')}={value!r} 無對應規則，且無 default",
            file=sys.stderr,
        )
        return 1

    cmd = resolve_command(target, base_dir)

    if args.explain:
        print(json.dumps(
            {"on": spec.get("on"), "value": value, "target": target,
             "command": cmd},
            ensure_ascii=False,
        ))
        return 0

    # REMAINDER 會包含分隔用的 "--"，去掉它再轉交
    rest = [a for a in args.rest if a != "--"]
    cmd.extend(rest)
    proc = subprocess.run(cmd)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
