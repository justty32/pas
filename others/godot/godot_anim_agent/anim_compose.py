"""
anim_compose.py — Godot AnimationLibrary 動作組合工具（Phase 2）

機械式拼接：把多段既有動畫接成一段新動畫。語意解構/挑動畫/排序由 Claude 在
session 內完成（查 metadata），本工具只做確定性的資料變換。詳見 PHASE2_DESIGN.md。

使用方式：
  python anim_compose.py concat <file.tres> <new_anim> <clip1> <clip2> [...] \
         [--blend <秒>] [--root-motion <track_path>]
  python anim_compose.py check-seams <file.tres> <anim> [--at T1,T2,...] [--threshold X]

範例：
  python anim_compose.py concat fighter.tres idle_then_punch idle punch
  python anim_compose.py concat fighter.tres combo guard punch --blend 0.3
  python anim_compose.py concat fighter.tres advance step_in punch --root-motion ".:position"
  python anim_compose.py check-seams fighter.tres combo --at 0.5

說明：
  - concat 依序把 clip1, clip2, ... 拼成新動畫 <new_anim>，寫回同檔的 AnimationLibrary。
    各段 times 位移到對應起始時間；相同 path 的軌道合併、依時間排序、seam 去重。
  - --blend N 讓相鄰段重疊 N 秒，並在重疊窗對「兩段共有、型別一致」的數值軌道
    做 cross-fade 值混合烘焙（純量/向量逐分量線性；Quaternion 用 SLERP）。
  - --root-motion PATH 指定位移軌道：後段接續前段終點累加，避免拼接後角色滑回原點
    （該軌道不參與 cross-fade）。
  - check-seams 報告數值軌道在指定時間點（或全軌道）的速度突變/瞬跳，協助判斷
    seam 是否頓挫；修正手段通常是 concat --blend 或手調 key。
  - 序列化風格沿用 anim_inspector（向量/PackedFloat 元素不帶 .0）。
"""

import re
import sys
import math
from pathlib import Path

from anim_inspector import (
    parse_tres, _extract_tracks, _find_anim,
    _float_list_to_packed, _fmt_real, _format_value_item,
)

NUMERIC = {"float", "Vector2", "Vector3", "Vector4", "Quaternion"}


def _sample(keys, t: float):
    """keys = 已排序 [(time, comps)]，回傳 t 處線性插值的 comps；端點外夾住。"""
    if not keys:
        return []
    if t <= keys[0][0]:
        return list(keys[0][1])
    if t >= keys[-1][0]:
        return list(keys[-1][1])
    for i in range(len(keys) - 1):
        t0, c0 = keys[i]
        t1, c1 = keys[i + 1]
        if t0 <= t <= t1:
            if t1 == t0:
                return list(c1)
            w = (t - t0) / (t1 - t0)
            return [a + (b - a) * w for a, b in zip(c0, c1)]
    return list(keys[-1][1])


def _slerp(qa, qb, w: float):
    """四元數 (x,y,z,w) 球面線性插值，回傳單位四元數；近乎平行時退化為 nlerp。"""
    dot = sum(a * b for a, b in zip(qa, qb))
    if dot < 0.0:                      # 取最短弧
        qb, dot = [-x for x in qb], -dot
    if dot > 0.9995:                   # 幾乎重合 → 線性後正規化
        res = [a + (b - a) * w for a, b in zip(qa, qb)]
    else:
        theta_0 = math.acos(max(-1.0, min(1.0, dot)))
        theta = theta_0 * w
        s0 = math.cos(theta) - dot * math.sin(theta) / math.sin(theta_0)
        s1 = math.sin(theta) / math.sin(theta_0)
        res = [s0 * a + s1 * b for a, b in zip(qa, qb)]
    norm = math.sqrt(sum(x * x for x in res)) or 1.0
    return [x / norm for x in res]


def _sample_quat(keys, t: float):
    """四元數軌道取樣：clip 內以 SLERP 插值。keys = 已排序 [(time, quat)]。"""
    if not keys:
        return []
    if t <= keys[0][0]:
        return list(keys[0][1])
    if t >= keys[-1][0]:
        return list(keys[-1][1])
    for i in range(len(keys) - 1):
        t0, q0 = keys[i]
        t1, q1 = keys[i + 1]
        if t0 <= t <= t1:
            return list(q1) if t1 == t0 else _slerp(q0, q1, (t - t0) / (t1 - t0))
    return list(keys[-1][1])


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
        keys = entry["keys"]                       # [(time, transition, item), ...]
        times  = _float_list_to_packed([k[0] for k in keys])
        trans  = _float_list_to_packed([k[1] for k in keys])
        values = "[" + ", ".join(k[2] for k in keys) + "]"
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
               blend: float = 0.0, root_motion_path: str = None) -> None:
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

    # 各段起始偏移；相鄰段有效重疊夾在兩段長度內（避免負偏移）
    n = len(clips)
    lengths = [c["length"] for c in clips]
    eff_blend = [min(blend, lengths[i], lengths[i + 1]) for i in range(n - 1)]
    offsets, acc = [], 0.0
    for i in range(n):
        offsets.append(round(acc, 6))
        if i < n - 1:
            acc += lengths[i] - eff_blend[i]
    total_length = round(offsets[-1] + lengths[-1], 6)
    # 全域重疊窗 windows[i] = (start, end) 介於 clip i 與 i+1
    windows = [(offsets[i + 1], round(offsets[i] + lengths[i], 6)) for i in range(n - 1)]

    # 蒐集每條軌道在各 clip 的段落（payload：數值軌道→comps list；其餘→原始字串）
    info_by_path = {}    # path -> {type, raw_props, update, vtypes, segs:{ci:[(t,trans,payload)]}}
    for ci, clip in enumerate(clips):
        for tr in clip["tracks"]:
            path  = tr["path"]
            vtype = tr.get("vtype")
            comps = tr.get("comps")
            is_num = comps is not None and vtype in NUMERIC
            info = info_by_path.get(path)
            if info is None:
                info = {"type": tr["type"], "raw_props": tr["raw_props"],
                        "update": tr.get("update"), "vtypes": set(), "segs": {}}
                info_by_path[path] = info
            info["vtypes"].add(vtype)
            times = tr.get("times") or []
            trans = tr.get("transitions") or [1.0] * len(times)
            items = tr.get("values_items") or []
            seg = []
            for k in range(len(times)):
                t  = round(times[k] + offsets[ci], 6)
                tv = trans[k] if k < len(trans) else 1.0
                payload = (list(comps[k]) if is_num and k < len(comps)
                           else (items[k] if k < len(items) else "0.0"))
                seg.append((t, tv, payload))
            info["segs"][ci] = seg

    # Root motion 累加：讓指定位移軌道在 seam 接續前一段終點，不瞬移回原點
    rm_total = rm_vtype = None
    if root_motion_path:
        rinfo = info_by_path.get(root_motion_path)
        if rinfo is None:
            print(f"⚠ --root-motion 找不到軌道 '{root_motion_path}'，跳過累加。")
        else:
            only = next(iter(rinfo["vtypes"])) if len(rinfo["vtypes"]) == 1 else None
            numeric_ok = only in NUMERIC and only != "float" and all(
                (not s) or isinstance(s[0][2], list) for s in rinfo["segs"].values())
            if not numeric_ok:
                print(f"⚠ --root-motion '{root_motion_path}' 非向量位移軌道（{only}），跳過累加。")
            else:
                end_pos = None
                for ci in sorted(rinfo["segs"].keys()):
                    seg = rinfo["segs"][ci]
                    if not seg:
                        continue
                    firstval, lastval = seg[0][2], seg[-1][2]
                    off = ([0.0] * len(firstval) if end_pos is None
                           else [e - f for e, f in zip(end_pos, firstval)])
                    rinfo["segs"][ci] = [
                        (t, tr, [round(c + o, 6) for c, o in zip(comps, off)])
                        for (t, tr, comps) in seg]
                    end_pos = [round(lv + o, 6) for lv, o in zip(lastval, off)]
                rinfo["root_motion"] = True
                rm_total, rm_vtype = end_pos, only

    # 逐軌道組裝最終 keys：可混合的數值軌道在重疊窗內烘焙 cross-fade
    merged = {}          # path -> {type, raw_props, update, keys:[(t,trans,item)]}
    present = {}         # path -> set(clip_idx)
    crossfaded = set()   # 實際發生 cross-fade 的軌道
    for path, info in info_by_path.items():
        segs = info["segs"]
        present[path] = set(segs.keys())
        only = next(iter(info["vtypes"])) if len(info["vtypes"]) == 1 else None
        blendable = (only in NUMERIC and
                     all((not s) or isinstance(s[0][2], list) for s in segs.values()))
        keys = []
        if blendable and blend > 0 and not info.get("root_motion"):
            active = [(windows[i][0], windows[i][1], i) for i in range(n - 1)
                      if eff_blend[i] > 1e-9 and i in segs and (i + 1) in segs]

            def _in_active(t, _a=active):
                return any(s - 1e-6 <= t <= e + 1e-6 for (s, e, _) in _a)

            # 非重疊區的原始 key
            for seg in segs.values():
                for (t, tr, comps) in seg:
                    if not _in_active(t):
                        keys.append((t, tr, _format_value_item(only, comps)))
            # 重疊區：取兩段在窗內 key 時間的聯集 + 端點，逐點線性混合
            for (s, e, i) in active:
                a_keys = [(t, c) for (t, _, c) in segs[i]]
                b_keys = [(t, c) for (t, _, c) in segs[i + 1]]
                sample_ts = {round(s, 6), round(e, 6)}
                for (t, _, _) in segs[i] + segs[i + 1]:
                    if s - 1e-6 <= t <= e + 1e-6:
                        sample_ts.add(t)
                for t in sorted(sample_ts):
                    w = 0.0 if e <= s else max(0.0, min(1.0, (t - s) / (e - s)))
                    if only == "Quaternion":
                        blended = [round(x, 6) for x in
                                   _slerp(_sample_quat(a_keys, t), _sample_quat(b_keys, t), w)]
                    else:
                        a, b = _sample(a_keys, t), _sample(b_keys, t)
                        blended = [round(av + (bv - av) * w, 6) for av, bv in zip(a, b)]
                    keys.append((round(t, 6), 1.0, _format_value_item(only, blended)))
            if active:
                crossfaded.add(path)
        else:
            for seg in segs.values():
                for (t, tr, payload) in seg:
                    item = payload if isinstance(payload, str) else _format_value_item(only, payload)
                    keys.append((t, tr, item))

        keys.sort(key=lambda x: x[0])
        deduped = []
        for k in keys:
            if deduped and abs(deduped[-1][0] - k[0]) < 1e-5:
                deduped[-1] = k
            else:
                deduped.append(k)
        merged[path] = {"type": info["type"], "raw_props": info["raw_props"],
                        "update": info["update"], "keys": deduped}

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
        print(f"  [{i}] {clip['name']:16s} 起始 {offsets[i]}s  長度 {lengths[i]}s")
    if crossfaded:
        print(f"  cross-fade 軌道（{len(crossfaded)}）：{', '.join(sorted(crossfaded))}")
    if rm_total is not None:
        print(f"  root motion 累加（{root_motion_path}）：終點位移 = {_format_value_item(rm_vtype, rm_total)}")
    partial = [p for p, s in present.items() if len(s) < len(clips)]
    if partial:
        print("ℹ 下列軌道非全程出現；缺席段落 Godot 會 hold 最近的關鍵幀（非循環不外插），"
              "多半停在靜止姿勢。若該軌起手/收尾不在靜止值，可能需要 fix-seam（待實作）：")
        for p in partial:
            seg = sorted(clips[i]["name"] for i in present[p])
            print(f"    {p}  （僅出現於：{', '.join(seg)}）")
    print(f"已儲存：{filepath}")


def _fmt_vel(s: list) -> str:
    """速度向量格式化：單分量→'-2.0/s'，多分量→'(-2.0, 0.0)/s'。"""
    if len(s) == 1:
        return f"{round(s[0], 2)}/s"
    return "(" + ", ".join(f"{round(x, 2)}" for x in s) + ")/s"


def cmd_check_seams(filepath: str, anim_name: str,
                    at_times: list = None, threshold: float = 3.0) -> None:
    """
    連續性診斷：報告數值軌道在指定時間點（或全軌道）的速度突變與瞬跳，
    協助判斷組合後的 seam 是否會頓挫。修正手段通常是 concat --blend 或手調 key。
    """
    text = Path(filepath).read_text(encoding="utf-8")
    data = parse_tres(text)
    anim = _find_anim(data, anim_name)
    if anim is None:
        print(f"找不到動畫：{anim_name}")
        return

    findings = []
    for tr in _extract_tracks(anim):
        vt = tr.get("vtype")
        comps = tr.get("comps")
        times = tr.get("times") or []
        if comps is None or vt not in NUMERIC or len(times) < 2:
            continue

        def slope(i, j):
            dt = times[j] - times[i]
            if dt <= 1e-9:
                return None
            return [(comps[j][c] - comps[i][c]) / dt for c in range(len(comps[i]))]

        for i in range(len(times)):
            if at_times is not None and not any(abs(times[i] - a) < 1e-3 for a in at_times):
                continue
            # 瞬跳：與前一 key 幾乎同時但值不同
            if i > 0 and (times[i] - times[i - 1]) <= 1e-3:
                jump = max(abs(comps[i][c] - comps[i - 1][c]) for c in range(len(comps[i])))
                if jump > 1e-6:
                    findings.append((tr["path"], times[i], "瞬跳", jump,
                                     _format_value_item(vt, comps[i - 1]),
                                     _format_value_item(vt, comps[i])))
                continue
            # 速度突變：內部 key 的進出斜率變化
            if 0 < i < len(times) - 1:
                s_in, s_out = slope(i - 1, i), slope(i, i + 1)
                if s_in is None or s_out is None:
                    continue
                d = max(abs(s_out[c] - s_in[c]) for c in range(len(s_in)))
                if d > threshold:
                    findings.append((tr["path"], times[i], "速度突變", d,
                                     _fmt_vel(s_in), _fmt_vel(s_out)))

    where = (f"（檢查點 {', '.join(_fmt_real(a) for a in at_times)}s）"
             if at_times else f"（全軌道，閾值 Δ>{threshold}）")
    print(f"=== seam 連續性檢查：{anim_name} {where} ===")
    if not findings:
        print("  ✓ 未發現超過閾值的不連續")
        return
    for path, t, kind, mag, a, b in sorted(findings, key=lambda x: (x[1], x[0])):
        print(f"  t={_fmt_real(t):>6}  {kind}  {path}")
        print(f"            {a}  →  {b}   (Δ={round(mag, 3)})")
    print(f"  共 {len(findings)} 處；可用 concat --blend 在組合時平滑，或手調對應 key。")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "concat":
        blend = 0.0
        if "--blend" in args:
            bi = args.index("--blend")
            try:
                blend = float(args[bi + 1])
            except (IndexError, ValueError):
                print("--blend 需要一個秒數，例如 --blend 0.05")
                sys.exit(1)
            del args[bi:bi + 2]
        root_motion_path = None
        if "--root-motion" in args:
            ri = args.index("--root-motion")
            if ri + 1 >= len(args):
                print('--root-motion 需要一個軌道路徑，例如 --root-motion ".:position"')
                sys.exit(1)
            root_motion_path = args[ri + 1]
            del args[ri:ri + 2]
        if len(args) < 4:
            print("用法：anim_compose.py concat <file> <new_anim> <clip1> <clip2> [...] "
                  "[--blend <秒>] [--root-motion <track_path>]")
            sys.exit(1)
        cmd_concat(args[0], args[1], args[2:], blend, root_motion_path)

    elif cmd == "check-seams":
        at_times, threshold = None, 3.0
        if "--at" in args:
            ai = args.index("--at")
            try:
                at_times = [float(x) for x in args[ai + 1].split(",")]
            except (IndexError, ValueError):
                print("--at 需要逗號分隔的秒數，例如 --at 0.5,1.1")
                sys.exit(1)
            del args[ai:ai + 2]
        if "--threshold" in args:
            ti = args.index("--threshold")
            try:
                threshold = float(args[ti + 1])
            except (IndexError, ValueError):
                print("--threshold 需要一個數值")
                sys.exit(1)
            del args[ti:ti + 2]
        if len(args) < 2:
            print("用法：anim_compose.py check-seams <file> <anim> [--at T1,T2,...] [--threshold X]")
            sys.exit(1)
        cmd_check_seams(args[0], args[1], at_times, threshold)

    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
