#!/usr/bin/env python3
"""upper.py — 把 stdin（或 --input 檔）轉大寫輸出。範例「函式」，遵守 --metadata 契約。

用法：
    upper.py < foo.txt
    upper.py --input foo.txt
    upper.py --metadata
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 讓此範例 func 也能 import ai_core（與 tools/_common 同手法，但自含以保持獨立可執行）
# funcs/upper.py → try_implement → ai_core(repo 根) = parents[2]，src 在根目錄下
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import ai_core  # noqa: E402

ai_core.register(lifecycle="one_shot", state="stateless")


def main() -> int:
    parser = argparse.ArgumentParser(prog="upper", description="轉大寫")
    parser.add_argument("--input", help="輸入檔；未指定時讀 stdin")
    args = parser.parse_args()

    if args.input:
        text = Path(args.input).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    sys.stdout.write(text.upper())
    return 0


if __name__ == "__main__":
    sys.exit(main())
