#!/usr/bin/env python3
"""Router — name → 可執行物 的 mapping，查表後以 subprocess dispatch 執行。

對應 thinking_routing.md「Router」與 thinking_sfc.md Layer 1b。

本質（thinking_routing.md）：name → 某個可執行物 的 mapping，加上執行。
mapping 來源：一個 JSON 設定檔（``--routes``）。格式：

    {
      "routes": {
        "<name>": {"path": "<可執行檔路徑>", "type": "exec"},
        "echo":   {"path": "../funcs/echo.sh", "type": "exec"}
      }
    }

router 不在意目標是檔案還是 JSON 片段——本實作先支援 "exec"（單檔程式路徑）。
SFC 的 store 片段執行交由 sfc.py 處理（Layer 1b/2），兩者職責分離（見 README）。

特性（依 ai_core 軸）：
- lifecycle: one_shot
- state: stateless（router 自身不持有狀態；被路由的目標各自宣告自己的 state）

用法：
    router.py --routes routes.json <name> [args...]   # 查表後執行
    router.py --routes routes.json --list             # 列出所有路由
    router.py --metadata
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from _common import ensure_ai_core_importable, ensure_lib_importable

ensure_ai_core_importable()
ensure_lib_importable()
import ai_core  # noqa: E402
from lib import trace  # noqa: E402  # dispatch 的調用鏈追蹤 + 跨 process 傳遞


def load_routes(routes_path: Path) -> dict:
    data = json.loads(routes_path.read_text(encoding="utf-8"))
    routes = data.get("routes")
    if not isinstance(routes, dict):
        raise ValueError("設定檔缺少 'routes' 物件")
    return routes


def resolve_command(target: dict, base_dir: Path) -> list[str]:
    """把一個 route target 轉成可被 subprocess 執行的 argv 前綴。

    target 形如 {"path": "...", "type": "exec"}。path 相對於設定檔所在目錄解析。
    """
    ttype = target.get("type", "exec")
    if ttype != "exec":
        raise ValueError(f"router 目前只支援 type=exec，得到 {ttype!r}")
    raw_path = target.get("path")
    if not raw_path:
        raise ValueError("route target 缺少 'path'")

    path = (base_dir / raw_path).resolve()
    if path.suffix == ".py":
        return [sys.executable, str(path)]
    if path.suffix == ".sh":
        return ["bash", str(path)]
    return [str(path)]


def main() -> int:
    # register 純宣告（無 import 副作用，A3）；intercept 顯式處理 --metadata。
    ai_core.register(lifecycle="one_shot", state="stateless")
    ai_core.intercept()

    parser = argparse.ArgumentParser(
        prog="router",
        description="name → 可執行物 mapping，查表後 dispatch",
    )
    parser.add_argument("--routes", required=True, help="路由設定檔（JSON）")
    parser.add_argument("--list", action="store_true", help="列出所有路由後結束")
    parser.add_argument("name", nargs="?", help="要路由的目標名稱")
    parser.add_argument(
        "rest",
        nargs=argparse.REMAINDER,
        help="要轉交給目標的引數（原樣傳遞）",
    )
    args = parser.parse_args()

    routes_path = Path(args.routes)
    if not routes_path.is_file():
        print(f"錯誤：找不到設定檔 {routes_path}", file=sys.stderr)
        return 1

    base_dir = routes_path.resolve().parent
    routes = load_routes(routes_path)

    if args.list:
        print(json.dumps({"routes": sorted(routes)}, ensure_ascii=False))
        return 0

    if not args.name:
        print("錯誤：需要指定要路由的 name（或用 --list）", file=sys.stderr)
        return 1

    if args.name not in routes:
        print(
            f"錯誤：路由表中找不到 {args.name!r}；可用：{sorted(routes)}",
            file=sys.stderr,
        )
        return 1

    cmd = resolve_command(routes[args.name], base_dir)
    cmd.extend(args.rest)

    # 在 trace span 內 dispatch，並用 child_env() 把 trace id / 父 span 帶給子 process：
    # 若被路由的目標也是 trace-aware（用 lib/trace），它的 span 會接上同一棵調用樹。
    with trace.span(f"router:{args.name}"):
        # subprocess dispatch：透傳 stdin/stdout/stderr 與 exit code（KISS：router 全透明）
        proc = subprocess.run(cmd, env=trace.child_env())
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
