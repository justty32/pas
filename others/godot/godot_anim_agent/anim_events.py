"""
anim_events.py — Godot 動畫事件（method 軌道）管理工具（Phase 3）

method 軌道讓動畫在某一幀呼叫節點上的函式（打擊火花、音效、hitstop…）。
本工具增刪/檢視這些事件，並能 scaffold 對應的 GDScript handler 樣板。
語意（哪一幀該觸發什麼）由人/Claude 決定，工具只做確定性的軌道編輯。

使用方式：
  python anim_events.py list     <file.tres> <anim>
  python anim_events.py add      <file.tres> <anim> <track_path> <time> <method> [arg ...]
  python anim_events.py rm       <file.tres> <anim> <track_path> <time>
  python anim_events.py scaffold <file.tres> [<anim>]

範例：
  python anim_events.py list     fighter.tres punch
  python anim_events.py add      fighter.tres punch "." 0.5 play_sound "punch_whoosh"
  python anim_events.py add      fighter.tres step_in "." 0.2 footstep
  python anim_events.py rm       fighter.tres punch "." 0.3
  python anim_events.py scaffold fighter.tres

說明：
  - add 若該 path 已有 method 軌道則插入 key（保持時間排序）；沒有則新建一條 method 軌道。
  - arg 以 Godot 字面值寫入：可解析為數字者原樣，否則包成字串（"...")。
  - scaffold 蒐集整個 library（或單一動畫）出現過的所有 method，產出 <檔名>_events.gd
    handler 樣板（空函式，待你填實作）。
"""

import re
import sys
from pathlib import Path

from anim_inspector import (
    parse_tres, _find_anim, _extract_tracks, _float_list_to_packed,
    _sub_block_span, _keys_dict_span, _replace_keys_field,
)


# ── method 值解析 / 格式化 ─────────────────────────────────────────────────────

def _parse_method_value(raw: str):
    """{"args": [...], "method": &"name"} 原始字串 → (method_name, args_inner_str)。"""
    m = re.search(r'"method"\s*:\s*&?"([^"]*)"', raw)
    method = m.group(1) if m else "?"
    a = re.search(r'"args"\s*:\s*\[(.*)\]', raw, re.DOTALL)
    args = a.group(1).strip() if a else ""
    return method, args


def _fmt_arg(tok: str) -> str:
    """CLI 參數 → Godot 字面值：數字原樣，已帶引號者原樣，其餘包成字串。"""
    try:
        float(tok)
        return tok
    except ValueError:
        if len(tok) >= 2 and tok[0] == '"' and tok[-1] == '"':
            return tok
        return f'"{tok}"'


def _method_value(method: str, args: list) -> str:
    """(method, args) → {"args": [...], "method": &"name"} 字串。"""
    inner = ", ".join(_fmt_arg(a) for a in args)
    return '{\n"args": [' + inner + '],\n"method": &"' + method + '"\n}'


def _arg_count(args_inner: str) -> int:
    inner = args_inner.strip()
    if not inner:
        return 0
    # 頂層逗號數 + 1（args 內罕見巢狀，簡化處理）
    depth, n = 0, 1
    for c in inner:
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        elif c == ',' and depth == 0:
            n += 1
    return n


def _method_tracks(anim: dict):
    """回傳該動畫的 method 軌道列表（沿用 _extract_tracks，type=='method'）。"""
    return [t for t in _extract_tracks(anim) if t["type"] == "method"]


# ── list ──────────────────────────────────────────────────────────────────────

def cmd_list(filepath: str, anim_name: str) -> None:
    data = parse_tres(Path(filepath).read_text(encoding="utf-8"))
    anim = _find_anim(data, anim_name)
    if anim is None:
        print(f"找不到動畫：{anim_name}")
        return
    mtracks = _method_tracks(anim)
    if not mtracks:
        print(f"=== {anim_name} ===\n  （無 method 軌道 / 動畫事件）")
        return
    print(f"=== {anim_name} 動畫事件 ===")
    for t in mtracks:
        print(f"\n  method 軌道 path={t['path']}")
        times = t.get("times") or []
        items = t.get("values_items") or []
        if not times:
            print("    （無事件）")
        for time, raw in zip(times, items):
            method, args = _parse_method_value(raw)
            call = f"{method}({args})" if args else f"{method}()"
            print(f"    t={time:>7.4f}  {call}")


# ── add ───────────────────────────────────────────────────────────────────────

def cmd_add(filepath: str, anim_name: str, track_path: str,
            time_str: str, method: str, args: list) -> None:
    target_time = float(time_str)
    text = Path(filepath).read_text(encoding="utf-8")
    data = parse_tres(text)
    anim = _find_anim(data, anim_name)
    if anim is None:
        print(f"找不到動畫：{anim_name}")
        return

    mtracks = _method_tracks(anim)
    matched = [t for t in mtracks if t["path"] == track_path]
    new_value = _method_value(method, args)
    call = f"{method}({', '.join(_fmt_arg(a) for a in args)})" if args else f"{method}()"

    if matched:
        # 插入既有 method 軌道
        track = matched[0]
        times = list(track.get("times") or [])
        items = list(track.get("values_items") or [])
        trans = list(track.get("transitions") or [1.0] * len(times))
        idx = next((i for i, t in enumerate(times) if t > target_time), len(times))
        times.insert(idx, target_time)
        items.insert(idx, new_value)
        if idx <= len(trans):
            trans.insert(idx, 1.0)
        new_text = _replace_keys_field(text, anim["id"], track["index"],
                                       "times", _float_list_to_packed(times))
        new_text = _replace_keys_field(new_text, anim["id"], track["index"],
                                       "values", "[" + ", ".join(items) + "]")
        if "transitions" in track:
            new_text = _replace_keys_field(new_text, anim["id"], track["index"],
                                           "transitions", _float_list_to_packed(trans))
        Path(filepath).write_text(new_text, encoding="utf-8")
        print(f"插入事件 [{track_path}] t={target_time}: {call}")
        print(f"已儲存：{filepath}")
    else:
        # 新建 method 軌道
        new_text = _append_method_track(text, anim["id"], track_path,
                                        target_time, new_value)
        if new_text is None:
            print(f"無法在 {anim_name} 建立 method 軌道。")
            return
        Path(filepath).write_text(new_text, encoding="utf-8")
        print(f"新建 method 軌道 [{track_path}] 並插入 t={target_time}: {call}")
        print(f"已儲存：{filepath}")


def _append_method_track(text: str, sub_id: str, track_path: str,
                         time: float, value_str: str):
    """在指定 sub_resource 末端附加一條新的 method 軌道。"""
    span = _sub_block_span(text, sub_id)
    if span is None:
        return None
    s, e = span
    block = text[s:e]
    idxs = [int(m) for m in re.findall(r'tracks/(\d+)/type', block)]
    new_idx = (max(idxs) + 1) if idxs else 0
    if idxs:
        kspan = _keys_dict_span(block, max(idxs))
        insert_at = kspan[1] if kspan else len(block.rstrip())
    else:
        insert_at = len(block.rstrip())

    track_text = (
        f'\ntracks/{new_idx}/type = "method"\n'
        f'tracks/{new_idx}/imported = false\n'
        f'tracks/{new_idx}/enabled = true\n'
        f'tracks/{new_idx}/path = NodePath("{track_path}")\n'
        f'tracks/{new_idx}/interp = 1\n'
        f'tracks/{new_idx}/loop_wrap = true\n'
        f'tracks/{new_idx}/keys = {{\n'
        f'"times": {_float_list_to_packed([time])},\n'
        f'"transitions": {_float_list_to_packed([1.0])},\n'
        f'"values": [{value_str}]\n'
        f'}}'
    )
    new_block = block[:insert_at] + track_text + block[insert_at:]
    return text[:s] + new_block + text[e:]


# ── rm ────────────────────────────────────────────────────────────────────────

def cmd_rm(filepath: str, anim_name: str, track_path: str, time_str: str) -> None:
    target_time = float(time_str)
    text = Path(filepath).read_text(encoding="utf-8")
    data = parse_tres(text)
    anim = _find_anim(data, anim_name)
    if anim is None:
        print(f"找不到動畫：{anim_name}")
        return
    matched = [t for t in _method_tracks(anim) if t["path"] == track_path]
    if not matched:
        print(f"[{track_path}] 沒有 method 軌道。")
        return
    track = matched[0]
    times = list(track.get("times") or [])
    items = list(track.get("values_items") or [])
    trans = list(track.get("transitions") or [1.0] * len(times))
    hit = next((i for i, t in enumerate(times) if abs(t - target_time) < 1e-5), None)
    if hit is None:
        print(f"[{track_path}] t={target_time} 沒有事件。可用 list 查看。")
        return
    method, _ = _parse_method_value(items[hit])
    del times[hit], items[hit]
    if hit < len(trans):
        del trans[hit]
    new_text = _replace_keys_field(text, anim["id"], track["index"],
                                   "times", _float_list_to_packed(times))
    new_text = _replace_keys_field(new_text, anim["id"], track["index"],
                                   "values", "[" + ", ".join(items) + "]")
    if "transitions" in track:
        new_text = _replace_keys_field(new_text, anim["id"], track["index"],
                                       "transitions", _float_list_to_packed(trans))
    Path(filepath).write_text(new_text, encoding="utf-8")
    print(f"移除事件 [{track_path}] t={target_time}: {method}()")
    print(f"已儲存：{filepath}")


# ── scaffold ────────────────────────────────────────────────────────────────--

def cmd_scaffold(filepath: str, anim_name: str = None) -> None:
    data = parse_tres(Path(filepath).read_text(encoding="utf-8"))
    anims = [r for r in data["sub_resources"] if r["type"] == "Animation"]
    if anim_name:
        anims = [a for a in anims if a["props"].get("resource_name", "").strip('"') == anim_name]
        if not anims:
            print(f"找不到動畫：{anim_name}")
            return

    methods = {}   # method -> (arg_count, set(用到的動畫))
    for a in anims:
        aname = a["props"].get("resource_name", a["id"]).strip('"')
        for t in _method_tracks(a):
            for raw in (t.get("values_items") or []):
                m, args = _parse_method_value(raw)
                methods.setdefault(m, [_arg_count(args), set()])[1].add(aname)

    if not methods:
        print("整個 library 沒有 method 事件，無需 scaffold。")
        return

    lines = [
        "extends Node",
        "# 動畫事件 handler —— 由 anim_events.py scaffold 產生",
        "# 接到擁有 AnimationPlayer 的角色節點上；method 軌道會在對應幀呼叫這些函式。",
        "",
    ]
    for m in sorted(methods):
        argc, used = methods[m]
        params = ", ".join(f"arg{i}" for i in range(argc))
        lines.append(f"# 用於：{', '.join(sorted(used))}")
        lines.append(f"func {m}({params}) -> void:")
        lines.append("\tpass # TODO 實作")
        lines.append("")

    out = Path(filepath).with_suffix("").as_posix() + "_events.gd"
    Path(out).write_text("\n".join(lines), encoding="utf-8")
    print(f"已產生 handler 樣板（{len(methods)} 個 method）：{out}\n")
    print("\n".join(lines))


# ── CLI ─────────────────────────────────────────────────────────────────────--

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(0 if len(sys.argv) < 2 else 1)
    cmd, file = sys.argv[1], sys.argv[2]

    if cmd == "list":
        if len(sys.argv) < 4:
            print("用法：anim_events.py list <file> <anim>"); sys.exit(1)
        cmd_list(file, sys.argv[3])
    elif cmd == "add":
        if len(sys.argv) < 7:
            print("用法：anim_events.py add <file> <anim> <track_path> <time> <method> [arg ...]")
            sys.exit(1)
        cmd_add(file, sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7:])
    elif cmd == "rm":
        if len(sys.argv) < 6:
            print("用法：anim_events.py rm <file> <anim> <track_path> <time>"); sys.exit(1)
        cmd_rm(file, sys.argv[3], sys.argv[4], sys.argv[5])
    elif cmd == "scaffold":
        cmd_scaffold(file, sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        print(f"未知指令：{cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
