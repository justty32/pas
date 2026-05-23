#!/usr/bin/env python3
"""Indexer — 掃描指定資料夾的可執行檔，逐一呼叫 ``--metadata``，彙整成靜態索引。

對應 thinking_routing.md「Indexer」與 thinking_sfc.md 的 Indexer 行
（掃描可執行檔 → 產出靜態索引）。

特性（依 ai_core 軸）：
- lifecycle: one_shot — 掃完即結束
- state: stateless — 純讀取掃描，不改外部狀態（輸出檔由呼叫方指定，視為一般輸出）

行為：
- 掃描 ``--dir`` 下「看起來可執行」的檔案（具 exec 權限，或副檔名為 .py / .sh）
- 對每個檔案執行 ``<file> --metadata``，解析其回傳的 JSON
- 彙整成索引；``--format json``（預設）或 ``--format md``
- 無法執行 / 不回傳合法 JSON 的檔案，記到 index 的 ``errors`` 區，不中斷整體掃描

用法：
    indexer.py --dir ../funcs                      # 印 JSON 索引到 stdout
    indexer.py --dir ../funcs --format md          # 印 markdown 索引
    indexer.py --dir ../funcs --output index.json  # 寫到檔案
    indexer.py --metadata                          # 工具自身 metadata
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from _common import ensure_ai_core_importable

ensure_ai_core_importable()
import ai_core  # noqa: E402

# 注意：register() 的呼叫放在 main() 裡，而非 module 頂層。
# 原因（一個發現的缺口，見 README）：register() 在 import 時就跑 _intercept 並可能 exit，
# 也會佔住「只能 register 一次」的全域旗標。若放頂層，其他工具（如 hub）就無法 import 本檔
# 重用 build_index——一 import 就會觸發 register。把它移進 main() 後，本檔可當 library 被 import。


# 視為可執行的副檔名（即使沒有 exec 權限位元，這些也嘗試呼叫）
_EXECUTABLE_SUFFIXES = {".py", ".sh"}


def _looks_executable(p: Path) -> bool:
    if not p.is_file():
        return False
    if p.name.startswith(".") or p.name.startswith("_"):
        return False  # 隱藏檔與底線開頭（如 _common.py）跳過
    if p.suffix in _EXECUTABLE_SUFFIXES:
        return True
    return os.access(p, os.X_OK)


def _invoke_metadata(path: Path, timeout: float) -> dict:
    """執行 ``<path> --metadata`` 並解析 JSON。

    回傳 dict；失敗時拋出帶可讀訊息的例外，由呼叫端收集到 errors。
    """
    # .py / .sh 用對應 interpreter 呼叫，避免 exec 權限或 shebang 問題（KISS）
    if path.suffix == ".py":
        cmd = [sys.executable, str(path), "--metadata"]
    elif path.suffix == ".sh":
        cmd = ["bash", str(path), "--metadata"]
    else:
        cmd = [str(path), "--metadata"]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"--metadata 回傳非零 exit code {proc.returncode}: {proc.stderr.strip()}"
        )
    out = proc.stdout.strip()
    if not out:
        raise RuntimeError("--metadata 沒有輸出任何內容")
    return json.loads(out)


def build_index(scan_dir: Path, timeout: float) -> dict:
    """掃描資料夾，回傳索引 dict。"""
    entries: dict[str, dict] = {}
    errors: dict[str, str] = {}

    for child in sorted(scan_dir.iterdir()):
        if not _looks_executable(child):
            continue
        name = child.name
        try:
            meta = _invoke_metadata(child, timeout)
            entries[name] = {
                "path": str(child.resolve()),
                "metadata": meta,
            }
        except Exception as exc:  # noqa: BLE001 — spike：收集所有失敗，不讓單一檔擋住整批
            errors[name] = f"{type(exc).__name__}: {exc}"

    return {
        "scan_dir": str(scan_dir.resolve()),
        "count": len(entries),
        "functions": entries,
        "errors": errors,
    }


def render_markdown(index: dict) -> str:
    lines: list[str] = []
    lines.append(f"# 函式索引（{index['scan_dir']}）")
    lines.append("")
    lines.append(f"共 {index['count']} 個函式。")
    lines.append("")
    for name, info in index["functions"].items():
        meta = info["metadata"]
        lifecycle = meta.get("lifecycle", "one_shot")
        state = meta.get("state", "stateless")
        lines.append(f"## {name}")
        lines.append("")
        lines.append(f"- 路徑：`{info['path']}`")
        lines.append(f"- lifecycle：`{lifecycle}`")
        lines.append(f"- state：`{state}`")
        lines.append(f"- metadata：`{json.dumps(meta, ensure_ascii=False)}`")
        lines.append("")
    if index["errors"]:
        lines.append("## 掃描錯誤")
        lines.append("")
        for name, err in index["errors"].items():
            lines.append(f"- `{name}`：{err}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    # --metadata 攔截需在 argparse 之前；register 只攔截「--metadata 為唯一引數」的情況
    ai_core.register(lifecycle="one_shot", state="stateless")

    parser = argparse.ArgumentParser(
        prog="indexer",
        description="掃描資料夾的可執行檔並彙整 --metadata 索引",
    )
    parser.add_argument("--dir", required=True, help="要掃描的資料夾")
    parser.add_argument(
        "--format",
        choices=["json", "md"],
        default="json",
        help="輸出格式（預設 json）",
    )
    parser.add_argument("--output", help="輸出檔路徑；未指定時印到 stdout")
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="每個 --metadata 呼叫的逾時秒數（預設 10）",
    )
    args = parser.parse_args()

    scan_dir = Path(args.dir)
    if not scan_dir.is_dir():
        print(f"錯誤：{scan_dir} 不是資料夾", file=sys.stderr)
        return 1

    index = build_index(scan_dir, args.timeout)

    if args.format == "json":
        rendered = json.dumps(index, ensure_ascii=False, indent=2)
    else:
        rendered = render_markdown(index)

    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        print(f"已寫入 {args.output}（{index['count']} 個函式）", file=sys.stderr)
    else:
        print(rendered)

    return 0


if __name__ == "__main__":
    sys.exit(main())
