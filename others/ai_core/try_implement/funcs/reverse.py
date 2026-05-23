#!/usr/bin/env python3
"""reverse.py — 把 stdin 反轉輸出（去尾端換行）。範例「函式」，遵守 --metadata 契約。

用法：
    reverse.py < foo.txt
    reverse.py --metadata
"""

from __future__ import annotations

import sys
from pathlib import Path

# 與 funcs/upper.py 同手法：自含 sys.path 以保持獨立可執行
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import ai_core  # noqa: E402

ai_core.register(lifecycle="one_shot", state="stateless")


def main() -> int:
    text = sys.stdin.read().rstrip("\n")
    sys.stdout.write(text[::-1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
