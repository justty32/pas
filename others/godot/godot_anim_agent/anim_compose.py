"""
anim_compose.py — Godot AnimationLibrary 動作組合工具（Phase 2）

機械式拼接：把多段既有動畫接成一段新動畫。語意解構/挑動畫/排序由 Claude 在
session 內完成（查 metadata），本工具只做確定性的資料變換。詳見 PHASE2_DESIGN.md。

使用方式：
  python anim_compose.py concat <file.tres> <new_anim> <clip1> <clip2> [...] [--blend <秒>]

範例：
  python anim_compose.py concat fighter.tres idle_then_punch idle punch
  python anim_compose.py concat fighter.tres combo dodge upper_cut --blend 0.05

說明：
  - 依序把 clip1, clip2, ... 拼成新動畫 <new_anim>，寫回同檔的 AnimationLibrary。
  - 各段 times 位移到對應起始時間；相同 path 的軌道合併、依時間排序、seam 去重。
  - --blend N 讓相鄰段重疊 N 秒（MVP：僅時間重疊 + seam 去重，尚未烘焙混合值）。
  - 序列化風格沿用 anim_inspector（向量/PackedFloat 元素不帶 .0）。
"""

import re
import sys
from pathlib import Path

from anim_inspector import (
    parse_tres, _extract_tracks, _find_anim,
    _float_list_to_packed, _fmt_real,
)


def _sanitize_id(name: str) -> str:
    """動畫名 → sub_resource id 安全字串。"""
    s = re.sub(r'[^0-9A-Za-z_]', '_', name)
    return f"Animation_{s}"


def _build_anim_block(new_id: str, new_name: str,
                      length: float, merged: dict, step: str) -> str:
    """依合併後的軌道資料，組出一段完整的 [sub_resource] 文字區塊。"""
    lines = [
        f'[sub_resource type="Animation" id="{new_id}"]',
        f'resource_name = "{new_name}"',
        f'length = {_fmt_real(length)}',
        'loop_mode = 0',
        f'step = {step}',
    ]
    for i, (path, entry) in enumerate(merged.items()):
        rp = entry["raw_props"]
        keys = entry["keys"]                       # [(time, clip_idx, transition, item), ...]
        times  = _float_list_to_packed([k[0] for k in keys])
        trans  = _float_list_to_packed([k[2] for k in keys])
        values = "[" + ", ".join(k[3] for k in keys) + "]"
        lines += [
            f'tracks/{i}/type = "{entry["type"]}"',
            f'tracks/{i}/imported = {rp.get("imported", "false")}',
            f'tracks/{i}/enabled = {rp.get("enabled", "true")}',
            f'tracks/{i}/path = {rp.get("path", f"""NodePath("{path}")""")}',
            f'tracks/{i}/interp = {rp.get("interp", "1")}',
            f'tracks/{i}/loop_wrap = {rp.get("loop_wrap", "true")}',
            f'tracks/{i}/keys = {{',
            f'"times": {times},',
            f'"transitions": {trans},',
        ]
        if entry["type"] == "value" and entry.get("update") is not None:
            lines.append(f'"update": {entry["update"]},')
        lines += [f'"values": {values}', '}']
    return "\n".join(lines)


def _add_to_data(text: str, new_name: str, new_id: str) -> str:
    """在 [resource] _data = { ... } 內插入新動畫條目（前置，帶尾逗號）。"""
    m = re.search(r'_data\s*=\s*\{[ \t]*\n', text)
    if not m:
        print("⚠ 找不到 [resource] _data 區塊，未登錄新動畫（請手動加入）。")
        return text
    line = f'&"{new_name}": SubResource("{new_id}"),\n'
    return text[:m.end()] + line + text[m.end():]


def cmd_concat(filepath: str, new_anim: str, clip_names: list[str],
               blend: float = 0.0) -> None:
    text = Path(filepath).read_text(encoding="utf-8")
    data = parse_tres(text)

    if _find_anim(data, new_anim) is not None:
        print(f"動畫 '{new_anim}' 已存在；請換個名稱或先刪除。")
        return

    # 蒐集 clip（依給定順序）
    clips = []
    for name in clip_names:
        anim = _find_anim(data, name)
        if anim is None:
            print(f"找不到動畫：{name}")
            return
        clips.append({
            "name":   name,
            "length": float(anim["props"].get("length", "0")),
            "tracks": _extract_tracks(anim),
            "step":   anim["props"].get("step", "0.1"),
        })
    if len(clips) < 2:
        print("concat 至少需要 2 段動畫。")
        return

    # 各段起始偏移（blend>0 時相鄰段重疊）
    offsets, acc = [], 0.0
    for i, clip in enumerate(clips):
        offsets.append(round(acc, 6))
        acc += clip["length"] - (blend if i < len(clips) - 1 else 0.0)
    total_length = round(offsets[-1] + clips[-1]["length"], 6)

    # 依 path 合併軌道
    merged = {}          # path -> {type, raw_props, update, keys}
    present = {}         # path -> set(clip_idx)
    for ci, clip in enumerate(clips):
        for tr in clip["tracks"]:
            path = tr["path"]
            entry = merged.get(path)
            if entry is None:
                entry = {"type": tr["type"], "raw_props": tr["raw_props"],
                         "update": tr.get("update"), "keys": []}
                merged[path] = entry
                present[path] = set()
            present[path].add(ci)
            times = tr.get("times") or []
            trans = tr.get("transitions") or [1.0] * len(times)
            items = tr.get("values_items") or []
            for k in range(len(times)):
                t  = round(times[k] + offsets[ci], 6)
                tv = trans[k] if k < len(trans) else 1.0
                it = items[k] if k < len(items) else "0.0"
                entry["keys"].append((t, ci, tv, it))

    # 每條軌道：依 (時間, clip 序) 排序，再對近乎同時的 key 去重（保留較後段）
    for entry in merged.values():
        entry["keys"].sort(key=lambda x: (x[0], x[1]))
        deduped = []
        for k in entry["keys"]:
            if deduped and abs(deduped[-1][0] - k[0]) < 1e-5:
                deduped[-1] = k
            else:
                deduped.append(k)
        entry["keys"] = deduped

    # 組出新區塊並寫回三處（load_steps / sub_resource / _data）
    new_id = _sanitize_id(new_anim)
    block  = _build_anim_block(new_id, new_anim, total_length, merged, clips[0]["step"])

    res_idx = text.find("[resource]")
    if res_idx == -1:
        print("⚠ 找不到 [resource] 區塊，無法插入新 sub_resource。")
        return
    new_text = text[:res_idx] + block + "\n\n" + text[res_idx:]
    new_text = re.sub(r'(load_steps=)(\d+)',
                      lambda m: f'{m.group(1)}{int(m.group(2)) + 1}', new_text, count=1)
    new_text = _add_to_data(new_text, new_anim, new_id)

    Path(filepath).write_text(new_text, encoding="utf-8")

    # 報告
    print(f"已組合 '{new_anim}'：{' + '.join(clip_names)}"
          f"{f'（blend {blend}s）' if blend else ''}")
    print(f"  length = {total_length}s，{len(merged)} 條軌道")
    for i, clip in enumerate(clips):
        print(f"  [{i}] {clip['name']:16s} 起始 {offsets[i]}s  長度 {clip['length']}s")
    partial = [p for p, s in present.items() if len(s) < len(clips)]
    if partial:
        print("⚠ 下列軌道非全程出現，缺席段落不補 hold key（可能漂移，見 PHASE2_DESIGN §3.1）：")
        for p in partial:
            seg = sorted(clips[i]["name"] for i in present[p])
            print(f"    {p}  （僅出現於：{', '.join(seg)}）")
    print(f"已儲存：{filepath}")


def main():
    if len(sys.argv) < 2 or sys.argv[1] != "concat":
        print(__doc__)
        sys.exit(0 if len(sys.argv) < 2 else 1)

    args = sys.argv[2:]
    blend = 0.0
    if "--blend" in args:
        bi = args.index("--blend")
        try:
            blend = float(args[bi + 1])
        except (IndexError, ValueError):
            print("--blend 需要一個秒數，例如 --blend 0.05")
            sys.exit(1)
        del args[bi:bi + 2]

    if len(args) < 4:
        print("用法：anim_compose.py concat <file> <new_anim> <clip1> <clip2> [...] [--blend <秒>]")
        sys.exit(1)

    filepath, new_anim, clip_names = args[0], args[1], args[2:]
    cmd_concat(filepath, new_anim, clip_names, blend)


if __name__ == "__main__":
    main()
