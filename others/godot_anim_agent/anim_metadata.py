"""
anim_metadata.py — 動畫 Metadata JSON 管理工具

每個 Godot 動畫旁置一份 .meta.json，記錄：
  - tags（attack / dodge / upper_body / air_ok ...）
  - 入場/出場幀
  - 入場/出場速度（各骨骼）
  - root motion delta
  - 相容性（before / after）

使用方式：
  python anim_metadata.py init    <file.tres>           # 從 .tres 自動生成空 metadata
  python anim_metadata.py show    <file.tres> [<anim>]  # 顯示 metadata
  python anim_metadata.py set-tag <file.tres> <anim> <tag>   # 加入 tag
  python anim_metadata.py rm-tag  <file.tres> <anim> <tag>   # 移除 tag
  python anim_metadata.py compat  <file.tres> <anim> before|after <other_anim>
"""

import sys
import json
from pathlib import Path

# anim_inspector 的解析器
from anim_inspector import parse_tres, _extract_tracks


def _meta_path(tres_path: str) -> Path:
    """<file>.tres → <file>.anim.meta.json"""
    p = Path(tres_path)
    return p.with_suffix(".anim.meta.json")


def _load_meta(tres_path: str) -> dict:
    mp = _meta_path(tres_path)
    if mp.exists():
        return json.loads(mp.read_text(encoding="utf-8"))
    return {}


def _save_meta(tres_path: str, meta: dict) -> None:
    mp = _meta_path(tres_path)
    mp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已儲存：{mp}")


def _anim_names(tres_path: str) -> list[str]:
    text = Path(tres_path).read_text(encoding="utf-8")
    data = parse_tres(text)
    return [
        r["props"].get("resource_name", r["id"]).strip('"')
        for r in data["sub_resources"]
        if r["type"] == "Animation"
    ]


def _empty_entry(name: str) -> dict:
    return {
        "name":              name,
        "tags":              [],
        "entry_frame":       0,
        "exit_frame":        -1,    # -1 = 最後一幀
        "exit_velocity":     {},    # {"BonePath": float}
        "root_motion_delta": {"x": 0.0, "y": 0.0},
        "compatible_after":  [],
        "compatible_before": []
    }


# ── 指令 ─────────────────────────────────────────────────────────────────────

def cmd_init(tres_path: str) -> None:
    """從 .tres 自動生成空 metadata（不覆蓋已有條目）"""
    meta = _load_meta(tres_path)
    names = _anim_names(tres_path)
    for name in names:
        if name not in meta:
            meta[name] = _empty_entry(name)
            print(f"新增條目：{name}")
        else:
            print(f"已存在：{name}（跳過）")
    _save_meta(tres_path, meta)


def cmd_show(tres_path: str, anim_name: str = None) -> None:
    meta = _load_meta(tres_path)
    if not meta:
        print("尚無 metadata（請先執行 init）")
        return
    if anim_name:
        if anim_name not in meta:
            print(f"找不到：{anim_name}")
            return
        print(json.dumps(meta[anim_name], ensure_ascii=False, indent=2))
    else:
        for name, entry in meta.items():
            tags = ", ".join(entry.get("tags", [])) or "（無標籤）"
            after  = ", ".join(entry.get("compatible_after",  [])) or "—"
            before = ", ".join(entry.get("compatible_before", [])) or "—"
            print(f"  {name:20s}  tags=[{tags}]  after=[{after}]  before=[{before}]")


def cmd_set_tag(tres_path: str, anim_name: str, tag: str) -> None:
    meta = _load_meta(tres_path)
    if anim_name not in meta:
        meta[anim_name] = _empty_entry(anim_name)
    if tag not in meta[anim_name]["tags"]:
        meta[anim_name]["tags"].append(tag)
        print(f"[{anim_name}] 加入 tag: {tag}")
    else:
        print(f"[{anim_name}] 已有 tag: {tag}")
    _save_meta(tres_path, meta)


def cmd_rm_tag(tres_path: str, anim_name: str, tag: str) -> None:
    meta = _load_meta(tres_path)
    if anim_name not in meta or tag not in meta[anim_name]["tags"]:
        print(f"找不到 tag '{tag}' 於 [{anim_name}]")
        return
    meta[anim_name]["tags"].remove(tag)
    print(f"[{anim_name}] 移除 tag: {tag}")
    _save_meta(tres_path, meta)


def cmd_compat(tres_path: str, anim_name: str, direction: str, other: str) -> None:
    """
    設定動畫相容性：
      before <other>：anim_name 可以在 other 之前播放
      after  <other>：anim_name 可以在 other 之後播放
    """
    meta = _load_meta(tres_path)
    if anim_name not in meta:
        meta[anim_name] = _empty_entry(anim_name)
    field = "compatible_before" if direction == "before" else "compatible_after"
    if other not in meta[anim_name][field]:
        meta[anim_name][field].append(other)
        print(f"[{anim_name}] {field} += {other}")
    else:
        print(f"[{anim_name}] {field} 已包含 {other}")
    _save_meta(tres_path, meta)


# ── CLI 入口 ─────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(0)

    cmd  = sys.argv[1]
    file = sys.argv[2]

    if cmd == "init":
        cmd_init(file)
    elif cmd == "show":
        anim = sys.argv[3] if len(sys.argv) > 3 else None
        cmd_show(file, anim)
    elif cmd == "set-tag":
        cmd_set_tag(file, sys.argv[3], sys.argv[4])
    elif cmd == "rm-tag":
        cmd_rm_tag(file, sys.argv[3], sys.argv[4])
    elif cmd == "compat":
        cmd_compat(file, sys.argv[3], sys.argv[4], sys.argv[5])
    else:
        print(f"未知指令：{cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
