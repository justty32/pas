#!/usr/bin/env python3
"""chain — 宣告式管線工具：把「組合維度」變成可從 shell 用的一等工具。

對應 docs/multi_function_interaction.md（組合維度）。用 JSON 宣告一條 pipeline，chain
把 stdin 依序流過每個 stage（subprocess），輸出最終結果——即「調用鏈」的顯式形式。
並能用 lib/compose_meta 的推導規則，從各 stage 的 ``--metadata`` 算出整條鏈的複合 metadata。

它把整個 lib 堆疊串起來示範：
    lib/call（跨邊界呼叫成員）+ lib/compose（pipe 串接）+ lib/trace（調用鏈追蹤）
    + lib/compose_meta（從成員 metadata 推導複合 metadata）

pipeline spec（path 相對於 spec 檔所在目錄解析）：
    {
      "name": "demo",
      "stages": [
        {"path": "funcs/upper.py", "type": "exec"},
        {"path": "funcs/reverse.py", "type": "exec", "args": ["--flag"]}
      ]
    }

用法：
    echo hi | chain --spec chain_demo.json       # 跑管線（→ IH）
    chain --spec chain_demo.json --derive        # 印從各 stage --metadata 推導的複合 metadata
    chain --metadata                             # chain 自身 metadata
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _common import ensure_ai_core_importable, ensure_lib_importable

ensure_ai_core_importable()
ensure_lib_importable()
import ai_core  # noqa: E402
from lib import call, compose, compose_meta, trace  # noqa: E402


def _resolve(stage: dict, base_dir: Path) -> list[str]:
    """把一個 stage 轉成 argv（path 依副檔名選 interpreter）。

    註：這是 router.py / switch.py 的 resolve_command 的**第三份**幾乎相同實作。
    Gap D（README）的訊號又強了一點——三處重複，正式化時應抽共用模組。此處仍各自獨立
    以維持「單檔自足」。
    """
    if stage.get("type", "exec") != "exec":
        raise ValueError(f"chain 目前只支援 type=exec，得到 {stage.get('type')!r}")
    path = (base_dir / stage["path"]).resolve()
    if path.suffix == ".py":
        argv = [sys.executable, str(path)]
    elif path.suffix == ".sh":
        argv = ["bash", str(path)]
    else:
        argv = [str(path)]
    return argv + list(stage.get("args", []))


def run_pipeline(spec: dict, base_dir: Path, stdin_text: str) -> str:
    """把 stdin 依序流過每個 stage，回最終輸出。整條包在 trace span 內。"""
    targets = [call.Subprocess(_resolve(s, base_dir)) for s in spec["stages"]]
    # 每個 stage 包裝成 str->str；compose.pipe 串起來
    fns = [(lambda t: (lambda text: call.call(t, text)))(t) for t in targets]
    pipeline = compose.pipe(*fns)
    with trace.span(f"chain:{spec.get('name', '?')}"):
        return pipeline(stdin_text)


def derive_metadata(spec: dict, base_dir: Path) -> dict:
    """呼叫每個 stage 的 --metadata，套 compose_meta 的 pipe 推導規則算複合 metadata。"""
    metafns: list[compose_meta.MetaFn] = []
    for s in spec["stages"]:
        argv = _resolve(s, base_dir)
        meta_out = call.call(call.Subprocess(argv + ["--metadata"]), "")
        meta = json.loads(meta_out)
        metafns.append(compose_meta.MetaFn(fn=lambda x: x, meta=meta, name=s["path"]))
    return compose_meta.derive_pipe(metafns)


def main() -> int:
    ai_core.register(lifecycle="one_shot", state="stateless")

    p = argparse.ArgumentParser(prog="chain", description="宣告式管線：stdin 依序流過各 stage")
    p.add_argument("--spec", required=True, help="pipeline 設定檔（JSON）")
    p.add_argument("--derive", action="store_true",
                   help="不執行，改印從各 stage --metadata 推導的複合 metadata")
    args = p.parse_args()

    spec_path = Path(args.spec)
    if not spec_path.is_file():
        print(f"錯誤：找不到 spec {spec_path}", file=sys.stderr)
        return 1
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    base_dir = spec_path.resolve().parent

    if args.derive:
        print(json.dumps(derive_metadata(spec, base_dir), ensure_ascii=False, indent=2))
        return 0

    stdin_text = "" if sys.stdin.isatty() else sys.stdin.read()
    out = run_pipeline(spec, base_dir, stdin_text)
    sys.stdout.write(out)
    if out and not out.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
