"""
anim_inspector.py — Godot AnimationLibrary (.tres / .animlib) 讀取與摘要工具

Phase 1 工作流程工具：
  讀取 → 摘要輸出 → 供 Claude 理解結構 → 修改指令 → 寫回

使用方式：
  python anim_inspector.py summary  <file.tres>
  python anim_inspector.py tracks   <file.tres> <animation_name>
  python anim_inspector.py set-key  <file.tres> <anim> <track_path> <time> <value>
  python anim_inspector.py scale-time <file.tres> <anim> <factor>

範例：
  python anim_inspector.py summary  player.tres
  python anim_inspector.py tracks   player.tres walk
  python anim_inspector.py set-key  player.tres walk "Body/Bone2D:rotation" 0.15 1.8
  python anim_inspector.py scale-time player.tres punch 0.7
"""

import re
import sys
import ast
import copy
from pathlib import Path


# ── 解析器 ────────────────────────────────────────────────────────────────────

def parse_tres(text: str) -> dict:
    """
    解析 Godot .tres 文字格式，回傳結構化資料：
    {
        "header": {"type": "AnimationLibrary", ...},
        "sub_resources": [{"type": "Animation", "id": "...", "props": {...}}, ...],
        "resource": {"props": {...}}  # 頂層 [resource] 區塊
    }
    """
    result = {"header": {}, "sub_resources": [], "resource": {"props": {}}}

    # 解析 [gd_resource ...] 標頭
    header_match = re.search(r'\[gd_resource([^\]]*)\]', text)
    if header_match:
        result["header"] = _parse_attrs(header_match.group(1))

    # 解析所有 [sub_resource type="..." id="..."] 區塊
    sub_pattern = re.compile(
        r'\[sub_resource([^\]]+)\]\n(.*?)(?=\[sub_resource|\[resource\]|\Z)',
        re.DOTALL
    )
    for m in sub_pattern.finditer(text):
        attrs = _parse_attrs(m.group(1))
        props = _parse_props(m.group(2))
        result["sub_resources"].append({
            "type": attrs.get("type", ""),
            "id":   attrs.get("id", ""),
            "props": props
        })

    # 解析 [resource] 頂層區塊
    res_match = re.search(r'\[resource\]\n(.*)', text, re.DOTALL)
    if res_match:
        result["resource"]["props"] = _parse_props(res_match.group(1))

    return result


def _parse_attrs(attr_str: str) -> dict:
    """解析 key="value" 屬性字串"""
    attrs = {}
    for m in re.finditer(r'(\w+)\s*=\s*"([^"]*)"', attr_str):
        attrs[m.group(1)] = m.group(2)
    return attrs


def _parse_props(block: str) -> dict:
    """
    解析 key = value 屬性塊（支援多行 dict/array 值）。
    回傳 {key: raw_value_string}。
    """
    props = {}
    lines = block.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^(\S+)\s*=\s*(.*)', line)
        if not m:
            i += 1
            continue
        key = m.group(1)
        val = m.group(2)
        # 處理多行 dict/array（以 { 或 [ 開頭，等到對應的 } 或 ] 結束）
        open_char = val.strip()[:1] if val.strip() else ''
        if open_char in ('{', '['):
            close_char = '}' if open_char == '{' else ']'
            depth = val.count(open_char) - val.count(close_char)
            while depth > 0 and i + 1 < len(lines):
                i += 1
                val += '\n' + lines[i]
                depth += lines[i].count(open_char) - lines[i].count(close_char)
        props[key] = val.strip()
        i += 1
    return props


def _extract_float_array(godot_array_str: str) -> list[float]:
    """
    從 Godot PackedFloat32Array(0, 0.2, 0.5) 或 Array[float](...)
    提取浮點數列表。
    """
    m = re.search(r'PackedFloat32Array\(([^)]*)\)', godot_array_str)
    if not m:
        m = re.search(r'Array\[float\]\(([^)]*)\)', godot_array_str)
    if m:
        raw = m.group(1).strip()
        if not raw:
            return []
        return [float(x.strip()) for x in raw.split(',') if x.strip()]
    return []


def _extract_tracks(sub_res: dict) -> list[dict]:
    """從 sub_resource 的 props 中提取 tracks/N/* 結構"""
    props = sub_res["props"]
    tracks = {}
    for key, val in props.items():
        m = re.match(r'tracks/(\d+)/(.*)', key)
        if m:
            idx = int(m.group(1))
            field = m.group(2)
            if idx not in tracks:
                tracks[idx] = {}
            tracks[idx][field] = val

    result = []
    for idx in sorted(tracks.keys()):
        t = tracks[idx]
        track = {
            "index": idx,
            "type":  t.get("type", "").strip('"'),
            "path":  t.get("path", "").strip('"').replace("NodePath(\"", "").rstrip("\")")
        }
        # 嘗試提取 keys/times
        keys_raw = t.get("keys", "")
        if keys_raw:
            times_m = re.search(r'"times":\s*(PackedFloat32Array\([^)]*\))', keys_raw)
            vals_m  = re.search(r'"values":\s*(PackedFloat32Array\([^)]*\))', keys_raw)
            if times_m:
                track["times"]  = _extract_float_array(times_m.group(1))
            if vals_m:
                track["values"] = _extract_float_array(vals_m.group(1))
        result.append(track)
    return result


# ── 摘要指令 ─────────────────────────────────────────────────────────────────

def cmd_summary(filepath: str) -> None:
    """輸出 AnimationLibrary 所有動畫的摘要（名稱、長度、骨骼列表）"""
    text = Path(filepath).read_text(encoding="utf-8")
    data = parse_tres(text)

    print(f"=== {filepath} ===")
    print(f"類型：{data['header'].get('type', '未知')}\n")

    anims = [r for r in data["sub_resources"] if r["type"] == "Animation"]
    if not anims:
        print("（未找到 Animation sub_resource）")
        return

    for anim in anims:
        name   = anim["props"].get("resource_name", f'<id={anim["id"]}>').strip('"')
        length = anim["props"].get("length", "?")
        tracks = _extract_tracks(anim)
        print(f"── 動畫：{name}  長度={length}s  tracks={len(tracks)}")
        for t in tracks:
            times_str = ""
            if "times" in t:
                times_str = f"  [{', '.join(f'{v:.3f}' for v in t['times'])}]"
            print(f"   [{t['index']}] {t['type']:12s}  path={t['path']}{times_str}")
        print()


# ── track 詳情指令 ────────────────────────────────────────────────────────────

def cmd_tracks(filepath: str, anim_name: str) -> None:
    """輸出指定動畫的所有 track 詳情（時間點 + 數值）"""
    text = Path(filepath).read_text(encoding="utf-8")
    data = parse_tres(text)

    anim = _find_anim(data, anim_name)
    if anim is None:
        print(f"找不到動畫：{anim_name}")
        return

    tracks = _extract_tracks(anim)
    print(f"=== {anim_name} ===")
    for t in tracks:
        print(f"\n[{t['index']}] type={t['type']}  path={t['path']}")
        if "times" in t and "values" in t:
            pairs = list(zip(t["times"], t["values"]))
            print(f"  {'時間':>8}  {'數值':>12}")
            for time, val in pairs:
                print(f"  {time:>8.4f}  {val:>12.6f}")
        else:
            print("  （無法解析 keys 資料）")


# ── 修改指令：設定單個 key ───────────────────────────────────────────────────

def cmd_set_key(filepath: str, anim_name: str,
                track_path: str, time_str: str, value_str: str) -> None:
    """
    設定指定 track 在指定時間點的數值。
    若時間點不存在則插入（保持時間排序）。
    寫回原始檔案。
    """
    target_time  = float(time_str)
    target_value = float(value_str)
    text = Path(filepath).read_text(encoding="utf-8")
    data = parse_tres(text)

    anim = _find_anim(data, anim_name)
    if anim is None:
        print(f"找不到動畫：{anim_name}")
        return

    tracks = _extract_tracks(anim)
    matched = [t for t in tracks if t["path"] == track_path]
    if not matched:
        print(f"找不到 track：{track_path}")
        print("可用 track：")
        for t in tracks:
            print(f"  {t['path']}")
        return

    track = matched[0]
    times  = list(track.get("times",  []))
    values = list(track.get("values", []))

    # 找到已存在的時間點或插入新的
    inserted = False
    for i, t in enumerate(times):
        if abs(t - target_time) < 1e-5:
            print(f"更新 [{track_path}] t={target_time}: {values[i]:.6f} → {target_value:.6f}")
            values[i] = target_value
            inserted = True
            break
    if not inserted:
        # 找到插入位置（保持時間排序）
        insert_idx = next((i for i, t in enumerate(times) if t > target_time), len(times))
        times.insert(insert_idx, target_time)
        values.insert(insert_idx, target_value)
        print(f"插入 [{track_path}] t={target_time}: {target_value:.6f}")

    # 寫回檔案：替換對應 track 的 keys 區塊
    new_text = _replace_track_keys(text, anim["id"], track["index"], times, values)
    Path(filepath).write_text(new_text, encoding="utf-8")
    print(f"已儲存：{filepath}")


# ── 修改指令：時間縮放 ───────────────────────────────────────────────────────

def cmd_scale_time(filepath: str, anim_name: str, factor_str: str) -> None:
    """
    對指定動畫的所有 track 乘上時間縮放因子，並同步更新 length。
    例如 factor=0.7 代表加快到原本的 70%。
    """
    factor = float(factor_str)
    text = Path(filepath).read_text(encoding="utf-8")
    data = parse_tres(text)

    anim = _find_anim(data, anim_name)
    if anim is None:
        print(f"找不到動畫：{anim_name}")
        return

    tracks = _extract_tracks(anim)
    new_text = text

    # 縮放所有 track 的 times
    for track in tracks:
        if "times" not in track:
            continue
        new_times  = [t * factor for t in track["times"]]
        new_values = track.get("values", [])
        new_text = _replace_track_keys(new_text, anim["id"], track["index"],
                                       new_times, new_values)

    # 更新 length
    old_length_m = re.search(
        r'(\[sub_resource[^\]]*id="' + re.escape(anim["id"]) + r'"[^\]]*\].*?)'
        r'(length\s*=\s*[\d.]+)',
        new_text, re.DOTALL
    )
    if old_length_m:
        old_len = float(anim["props"].get("length", "1.0"))
        new_len = old_len * factor
        new_text = new_text[:old_length_m.start(2)] + \
                   f"length = {new_len:.6f}" + \
                   new_text[old_length_m.end(2):]
        print(f"length: {old_len:.4f} → {new_len:.4f}")

    Path(filepath).write_text(new_text, encoding="utf-8")
    print(f"時間縮放 ×{factor}，已儲存：{filepath}")


# ── 內部工具函數 ─────────────────────────────────────────────────────────────

def _find_anim(data: dict, name: str):
    """依名稱找 Animation sub_resource（name 比對 resource_name 屬性）"""
    for r in data["sub_resources"]:
        if r["type"] != "Animation":
            continue
        rname = r["props"].get("resource_name", "").strip('"')
        if rname == name:
            return r
    return None


def _float_list_to_packed(values: list[float]) -> str:
    """將浮點數列表轉為 Godot PackedFloat32Array(...) 字串"""
    inner = ", ".join(f"{v}" for v in values)
    return f"PackedFloat32Array({inner})"


def _replace_track_keys(text: str, sub_id: str, track_idx: int,
                        new_times: list[float], new_values: list[float]) -> str:
    """
    在原始文字中找到指定 sub_resource + track 的 keys 屬性並替換。
    keys 格式：
      tracks/N/keys = {
      "times": PackedFloat32Array(...),
      "values": PackedFloat32Array(...)
      }
    """
    # 建立新的 keys 值
    new_keys = (
        '{\n'
        f'"times": {_float_list_to_packed(new_times)},\n'
        f'"values": {_float_list_to_packed(new_values)}\n'
        '}'
    )

    # 定位到對應 sub_resource 區塊
    sub_start = text.find(f'id="{sub_id}"')
    if sub_start == -1:
        return text
    # 找到下一個 [sub_resource 或 [resource] 作為區塊結尾
    sub_end_m = re.search(r'\[(?:sub_resource|resource)\]', text[sub_start:])
    sub_end = (sub_start + sub_end_m.start()) if sub_end_m else len(text)
    block = text[sub_start:sub_end]

    # 在區塊內找到 tracks/N/keys = { ... }
    key_pattern = re.compile(
        r'(tracks/' + str(track_idx) + r'/keys\s*=\s*)(.*?)(\n(?=tracks/|\Z))',
        re.DOTALL
    )
    m = key_pattern.search(block)
    if not m:
        return text

    new_block = block[:m.start(2)] + new_keys + block[m.end(2):]
    return text[:sub_start] + new_block + text[sub_end:]


# ── CLI 入口 ─────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(0)

    cmd  = sys.argv[1]
    file = sys.argv[2]

    if cmd == "summary":
        cmd_summary(file)
    elif cmd == "tracks":
        if len(sys.argv) < 4:
            print("用法：anim_inspector.py tracks <file> <animation_name>")
            sys.exit(1)
        cmd_tracks(file, sys.argv[3])
    elif cmd == "set-key":
        if len(sys.argv) < 7:
            print("用法：anim_inspector.py set-key <file> <anim> <track_path> <time> <value>")
            sys.exit(1)
        cmd_set_key(file, sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
    elif cmd == "scale-time":
        if len(sys.argv) < 5:
            print("用法：anim_inspector.py scale-time <file> <anim> <factor>")
            sys.exit(1)
        cmd_scale_time(file, sys.argv[3], sys.argv[4])
    else:
        print(f"未知指令：{cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
