"""
anim_inspector.py — Godot AnimationLibrary (.tres / .animlib) 讀取與摘要工具

Phase 1 工作流程工具：
  讀取 → 摘要輸出 → 供 Claude 理解結構 → 修改指令 → 寫回

使用方式：
  python anim_inspector.py summary     <file.tres>
  python anim_inspector.py tracks      <file.tres> <anim>
  python anim_inspector.py set-key     <file.tres> <anim> <track_path> <time> <value>
  python anim_inspector.py scale-time  <file.tres> <anim> <factor>
  python anim_inspector.py offset      <file.tres> <anim> <track_path> <delta>
  python anim_inspector.py scale-value <file.tres> <anim> <track_path> <factor>

範例：
  python anim_inspector.py summary     player.tres
  python anim_inspector.py tracks      player.tres walk
  python anim_inspector.py set-key     player.tres walk "Body/Bone2D:rotation" 0.15 1.8
  python anim_inspector.py set-key     player.tres punch ".:position" 0.3 "Vector2(12, -4)"
  python anim_inspector.py scale-time  player.tres punch 0.7
  python anim_inspector.py offset      player.tres punch ".:position" "Vector2(5, 0)"
  python anim_inspector.py scale-value player.tres punch "Armature/UpperArm:rotation" 1.2

備註：
  Godot 的 value 軌道把 "values" 存成一般 Array（例如 [0.0, 1.8] 或
  [Vector2(0, 0), ...]），不是 PackedFloat32Array。解析器會把每個 key 解析成
  結構化分量，自動辨別 float / Vector2 / Vector3 / Vector4 / Quaternion 與
  非數值（method dict 等）。
    - set-key     ：插入/更新單一 key，輸入型別需與軌道一致（float 或 Vector*）。
    - offset      ：整條軌道逐分量平移（delta 型別需與軌道一致）。
    - scale-value ：整條軌道數值乘上純量。
    - scale-time  ：只縮放時間軸，保留 values/transitions/update，對任何軌道都安全。
  向量分量以 Godot 風格輸出（整數不帶 .0），float Array 維持 1.0 風格，
  與引擎序列化一致以減少無謂 diff。Quaternion 逐分量平移/縮放會破壞單位長度，
  工具會警告——3D 旋轉建議用 set-key 指定完整四元數。
"""

import re
import sys
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


# ── 括號感知的數值解析 ────────────────────────────────────────────────────────

def _split_top_level(s: str) -> list[str]:
    """以頂層逗號切分字串，括號/中括號/大括號內的逗號不切。"""
    parts, cur, depth = [], '', 0
    for c in s:
        if c in '([{':
            depth += 1
            cur += c
        elif c in ')]}':
            depth -= 1
            cur += c
        elif c == ',' and depth == 0:
            if cur.strip():
                parts.append(cur.strip())
            cur = ''
        else:
            cur += c
    if cur.strip():
        parts.append(cur.strip())
    return parts


def _field_value_span(keys_raw: str, field: str):
    """
    在 keys dict 原始字串中定位 "field": <value> 的 <value> 範圍 (start, end)。
    括號感知：能正確處理 PackedFloat32Array(...)、[...]、巢狀 {...} 與純量。
    找不到回傳 None。
    """
    token = f'"{field}"'
    ki = keys_raw.find(token)
    if ki == -1:
        return None
    ci = keys_raw.find(':', ki + len(token))
    if ci == -1:
        return None
    j = ci + 1
    while j < len(keys_raw) and keys_raw[j] in ' \t\n\r':
        j += 1
    start = j
    depth = 0
    while j < len(keys_raw):
        c = keys_raw[j]
        if c in '([{':
            depth += 1
        elif c in ')]}':
            if depth == 0:        # 觸到外層 dict 的結尾 }
                break
            depth -= 1
        elif c == ',' and depth == 0:
            break
        j += 1
    # 不把值後面的空白/換行算進範圍，替換時才能保留原本的排版（例如 ]\n}）
    while j > start and keys_raw[j - 1] in ' \t\n\r':
        j -= 1
    return (start, j)


def _packed_floats(raw: str):
    """PackedFloat32Array(0, 0.5, 1) → [0.0, 0.5, 1.0]；非此格式回傳 None。"""
    m = re.match(r'PackedFloat(?:32|64)Array\((.*)\)\s*$', raw.strip(), re.DOTALL)
    if not m:
        return None
    inner = m.group(1).strip()
    if not inner:
        return []
    return [float(x) for x in _split_top_level(inner)]


# 支援的數值型別與分量數
_VEC_RE = re.compile(r'(Vector2|Vector3|Vector4|Quaternion)\s*\(([^)]*)\)\s*$')
_COMPONENT_COUNT = {"Vector2": 2, "Vector3": 3, "Vector4": 4, "Quaternion": 4}


def _parse_value_item(item: str):
    """
    解析單一 value 項目，回傳 (vtype, comps)：
      vtype : 'float' | 'Vector2' | 'Vector3' | 'Vector4' | 'Quaternion' | 'other'
      comps : 數值型別 → 分量浮點列表；'other'（method dict / 字串等）→ None
    """
    item = item.strip()
    m = _VEC_RE.match(item)
    if m:
        comps = [float(x.strip()) for x in m.group(2).split(',') if x.strip() != '']
        return (m.group(1), comps)
    try:
        return ('float', [float(item)])
    except ValueError:
        return ('other', None)


def _parse_values(raw: str):
    """
    解析 value 軌道的 "values"，回傳 dict：
      vtype : 'float' / 'Vector2' / 'Vector3' / 'Vector4' / 'Quaternion'
              / 'other'（含 method dict 等）/ 'mixed'（型別不一致，理論上不該發生）
      comps : 數值型軌道 → 每個 key 的分量列表 list[list[float]]；非數值 → None
      items : 各 key 的原始字串（顯示用）
    """
    raw = raw.strip()
    # PackedFloat32Array(...)（blend shape 等少見格式）視為純量 float
    pf = _packed_floats(raw)
    if pf is not None:
        return {"vtype": "float", "comps": [[x] for x in pf],
                "items": [_fmt_float(x) for x in pf]}
    if raw.startswith('[') and raw.endswith(']'):
        items = _split_top_level(raw[1:-1].strip())
    else:
        items = [raw]
    if not items:
        return {"vtype": "float", "comps": [], "items": []}
    parsed = [_parse_value_item(it) for it in items]
    vtypes = {p[0] for p in parsed}
    if 'other' in vtypes:
        return {"vtype": "other", "comps": None, "items": items}
    if len(vtypes) == 1:
        return {"vtype": next(iter(vtypes)),
                "comps": [p[1] for p in parsed], "items": items}
    return {"vtype": "mixed", "comps": None, "items": items}


def _clean_path(raw: str) -> str:
    """NodePath("Armature/Torso:rotation") → Armature/Torso:rotation"""
    raw = raw.strip()
    m = re.search(r'NodePath\("([^"]*)"\)', raw)
    if m:
        return m.group(1)
    return raw.strip('"')


def _extract_tracks(sub_res: dict) -> list[dict]:
    """從 sub_resource 的 props 中提取 tracks/N/* 結構（含 times/transitions/values）"""
    props = sub_res["props"]
    tracks = {}
    for key, val in props.items():
        m = re.match(r'tracks/(\d+)/(.*)', key)
        if m:
            idx = int(m.group(1))
            tracks.setdefault(idx, {})[m.group(2)] = val

    result = []
    for idx in sorted(tracks.keys()):
        t = tracks[idx]
        track = {
            "index": idx,
            "type":  t.get("type", "").strip('"'),
            "path":  _clean_path(t.get("path", "")),
        }
        keys_raw = t.get("keys", "")
        if keys_raw:
            sp = _field_value_span(keys_raw, "times")
            if sp:
                track["times"] = _packed_floats(keys_raw[sp[0]:sp[1]]) or []
            sp = _field_value_span(keys_raw, "transitions")
            if sp:
                track["transitions"] = _packed_floats(keys_raw[sp[0]:sp[1]]) or []
            sp = _field_value_span(keys_raw, "values")
            if sp:
                raw_v = keys_raw[sp[0]:sp[1]]
                pv = _parse_values(raw_v)
                track["vtype"]        = pv["vtype"]
                track["comps"]        = pv["comps"]
                track["values_items"] = pv["items"]
                track["values_raw"]   = raw_v.strip()
                # 相容：純量 float 軌道仍提供 values 為浮點列表
                if pv["vtype"] == "float" and pv["comps"] is not None:
                    track["values"] = [c[0] for c in pv["comps"]]
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
            if t.get("times"):
                times_str = f"  [{', '.join(f'{v:.3f}' for v in t['times'])}]"
            vt = t.get("vtype")
            vt_str = f"  值={vt}" if vt and vt != "float" else ""
            print(f"   [{t['index']}] {t['type']:7s} path={t['path']}{times_str}{vt_str}")
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
        times = t.get("times")
        if not times:
            print("  （無 times 資料）")
            continue
        vt    = t.get("vtype")
        comps = t.get("comps")
        items = t.get("values_items")
        if comps is not None and len(comps) == len(times):
            label = "數值" if vt == "float" else f"數值（{vt}）"
            print(f"  {'時間':>8}  {label}")
            for time, c in zip(times, comps):
                print(f"  {time:>8.4f}  {_format_value_item(vt, c)}")
        elif items and len(items) == len(times):
            print(f"  {'時間':>8}  數值（{vt}）")
            for time, val in zip(times, items):
                print(f"  {time:>8.4f}  {val}")
        else:
            print(f"  時間：{', '.join(f'{x:.4f}' for x in times)}")
            if t.get("values_raw"):
                print(f"  values（原始）：{t['values_raw']}")


# ── 修改指令：設定單個 key ───────────────────────────────────────────────────

def cmd_set_key(filepath: str, anim_name: str,
                track_path: str, time_str: str, value_str: str) -> None:
    """
    設定指定 track 在指定時間點的數值。支援純量 float（如 rotation）與
    Vector2/Vector3/Vector4/Quaternion（如 position）。輸入型別需與軌道一致。
    若時間點不存在則插入（保持時間排序，並同步插入 transition=1）。
    寫回原始檔案；保留 transitions / update 等其他欄位。
    """
    target_time = float(time_str)
    try:
        in_vtype, in_comps = _parse_input_value(value_str)
    except ValueError as ex:
        print(ex)
        return

    text = Path(filepath).read_text(encoding="utf-8")
    data = parse_tres(text)
    anim, track = _resolve_track(data, anim_name, track_path)
    if track is None:
        return

    vtype, comps = _editable_comps(track, track_path)
    if comps is None:
        return
    if in_vtype != vtype:
        print(f"[{track_path}] 是 {vtype} 軌道，你輸入的是 {in_vtype}；型別需一致。")
        return

    times       = list(track["times"])
    comps       = [list(c) for c in comps]
    transitions = list(track.get("transitions") or [1.0] * len(times))
    has_transitions = "transitions" in track

    # 找到已存在的時間點或插入新的
    updated = False
    for i, t in enumerate(times):
        if abs(t - target_time) < 1e-5:
            print(f"更新 [{track_path}] t={target_time}: "
                  f"{_format_value_item(vtype, comps[i])} → {_format_value_item(vtype, in_comps)}")
            comps[i] = in_comps
            updated = True
            break
    if not updated:
        insert_idx = next((i for i, t in enumerate(times) if t > target_time), len(times))
        times.insert(insert_idx, target_time)
        comps.insert(insert_idx, in_comps)
        if insert_idx <= len(transitions):
            transitions.insert(insert_idx, 1.0)
        print(f"插入 [{track_path}] t={target_time}: {_format_value_item(vtype, in_comps)}")

    # 逐欄位外科式替換（保留 update 等其他欄位）
    new_text = _replace_keys_field(text, anim["id"], track["index"],
                                   "times", _float_list_to_packed(times))
    new_text = _replace_keys_field(new_text, anim["id"], track["index"],
                                   "values", _format_values_array(vtype, comps))
    if has_transitions:
        new_text = _replace_keys_field(new_text, anim["id"], track["index"],
                                       "transitions", _float_list_to_packed(transitions))

    Path(filepath).write_text(new_text, encoding="utf-8")
    print(f"已儲存：{filepath}")


# ── 修改指令：時間縮放 ───────────────────────────────────────────────────────

def cmd_scale_time(filepath: str, anim_name: str, factor_str: str) -> None:
    """
    對指定動畫的所有 track 乘上時間縮放因子，並同步更新 length。
    只縮放時間，保留 values/transitions/update —— 對任何軌道類型都安全。
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

    # 只縮放每個 track 的 times
    for track in tracks:
        if not track.get("times"):
            continue
        new_times = [round(t * factor, 6) for t in track["times"]]
        new_text = _replace_keys_field(new_text, anim["id"], track["index"],
                                       "times", _float_list_to_packed(new_times))

    # 更新 length
    old_len = float(anim["props"].get("length", "1.0"))
    new_len = round(old_len * factor, 6)
    new_text = _replace_sub_prop(new_text, anim["id"], "length", f"{new_len}")
    print(f"length: {old_len:.4f} → {new_len:.4f}")

    Path(filepath).write_text(new_text, encoding="utf-8")
    print(f"時間縮放 ×{factor}，已儲存：{filepath}")


# ── 修改指令：整條軌道數值平移 ───────────────────────────────────────────────

def cmd_offset(filepath: str, anim_name: str,
               track_path: str, delta_str: str) -> None:
    """
    對指定 track 的每個 key 數值加上 delta（型別需與軌道一致）。
    float 軌道：delta=0.2；Vector2 軌道：delta="Vector2(5, 0)"。
    只動 values，保留 times/transitions/update。
    """
    try:
        d_vtype, d_comps = _parse_input_value(delta_str)
    except ValueError as ex:
        print(ex)
        return

    text = Path(filepath).read_text(encoding="utf-8")
    data = parse_tres(text)
    anim, track = _resolve_track(data, anim_name, track_path)
    if track is None:
        return
    vtype, comps = _editable_comps(track, track_path)
    if comps is None:
        return
    if d_vtype != vtype:
        print(f"[{track_path}] 是 {vtype} 軌道，delta 是 {d_vtype}；型別需一致。")
        return
    if vtype == "Quaternion":
        print("⚠ Quaternion 逐分量平移會破壞單位長度；3D 旋轉建議改用 set-key 指定完整四元數。")

    new_comps = [[round(c + d, 6) for c, d in zip(key, d_comps)] for key in comps]
    new_text = _replace_keys_field(text, anim["id"], track["index"],
                                   "values", _format_values_array(vtype, new_comps))
    Path(filepath).write_text(new_text, encoding="utf-8")
    print(f"[{track_path}] {len(comps)} 個 key 平移 {_format_value_item(vtype, d_comps)}，"
          f"已儲存：{filepath}")


# ── 修改指令：整條軌道數值縮放 ───────────────────────────────────────────────

def cmd_scale_value(filepath: str, anim_name: str,
                    track_path: str, factor_str: str) -> None:
    """
    對指定 track 的每個 key 數值（所有分量）乘上純量 factor。
    例如出拳幅度加大 20%：scale-value punch "Armature/UpperArm:rotation" 1.2。
    只動 values，保留 times/transitions/update。
    """
    factor = float(factor_str)
    text = Path(filepath).read_text(encoding="utf-8")
    data = parse_tres(text)
    anim, track = _resolve_track(data, anim_name, track_path)
    if track is None:
        return
    vtype, comps = _editable_comps(track, track_path)
    if comps is None:
        return
    if vtype == "Quaternion":
        print("⚠ Quaternion 逐分量縮放會破壞單位長度；3D 旋轉建議改用 set-key 指定完整四元數。")

    new_comps = [[round(c * factor, 6) for c in key] for key in comps]
    new_text = _replace_keys_field(text, anim["id"], track["index"],
                                   "values", _format_values_array(vtype, new_comps))
    Path(filepath).write_text(new_text, encoding="utf-8")
    print(f"[{track_path}] {len(comps)} 個 key 數值 ×{factor}，已儲存：{filepath}")


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


def _resolve_track(data: dict, anim_name: str, track_path: str):
    """找動畫與指定 path 的 track；找不到時印出提示並回傳 (None, None)。"""
    anim = _find_anim(data, anim_name)
    if anim is None:
        print(f"找不到動畫：{anim_name}")
        return None, None
    tracks = _extract_tracks(anim)
    matched = [t for t in tracks if t["path"] == track_path]
    if not matched:
        print(f"找不到 track：{track_path}")
        print("可用 track：")
        for t in tracks:
            print(f"  {t['path']}")
        return None, None
    return anim, matched[0]


def _editable_comps(track: dict, track_path: str):
    """取得可編輯數值軌道 (vtype, comps)；非數值（method/dict）回傳 (None, None)。"""
    vtype = track.get("vtype")
    comps = track.get("comps")
    if vtype in (None, "other", "mixed") or comps is None:
        print(f"[{track_path}] 的值類型為 {vtype or '未知'}，僅支援 "
              f"float / Vector2/Vector3/Vector4 / Quaternion 數值軌道"
              f"（method/dict 等請手動編輯）。")
        return None, None
    return vtype, comps


def _parse_input_value(s: str):
    """解析使用者輸入：'1.8' 或 'Vector2(12, -4)' → (vtype, comps)。失敗 raise ValueError。"""
    vtype, comps = _parse_value_item(s)
    if vtype == 'other':
        raise ValueError(
            f"無法解析數值：{s}（支援 float 或 Vector2/Vector3/Vector4/Quaternion(...)）")
    return vtype, comps


def _fmt_float(v: float) -> str:
    """以 Godot 風格輸出浮點數（整數值保留 .0，避免科學記號）"""
    s = repr(float(v))
    return s


def _float_list_to_packed(values: list[float]) -> str:
    """浮點數列表 → Godot PackedFloat32Array(...) 字串。
    元素比照引擎 rtos：整數值不帶 .0（與 value Array 的 float 不同）。"""
    return f"PackedFloat32Array({', '.join(_fmt_real(v) for v in values)})"


def _fmt_real(v: float) -> str:
    """Godot 風格實數（向量分量用）：整數值不帶 .0，與引擎序列化一致。"""
    v = float(v)
    if v == int(v) and abs(v) < 1e16:
        return str(int(v))
    return repr(v)


def _format_value_item(vtype: str, comps: list) -> str:
    """單一 value 還原成 Godot 字面值：float→'1.8'，Vector2→'Vector2(12, -4)'。"""
    if vtype == "float":
        return _fmt_float(comps[0])
    return f"{vtype}({', '.join(_fmt_real(c) for c in comps)})"


def _format_values_array(vtype: str, comps: list) -> str:
    """整個 values 陣列還原：[v0, v1, ...]。"""
    return "[" + ", ".join(_format_value_item(vtype, c) for c in comps) + "]"


def _sub_block_span(text: str, sub_id: str):
    """回傳指定 sub_resource 區塊在 text 中的 (start, end)。找不到回傳 None。"""
    start = text.find(f'id="{sub_id}"')
    if start == -1:
        return None
    m = re.search(r'\n\[(?:sub_resource|resource)', text[start:])
    end = (start + m.start()) if m else len(text)
    return (start, end)


def _keys_dict_span(block: str, track_idx: int):
    """在 sub_resource 區塊中定位 tracks/<idx>/keys 的 {...} 範圍 (start, end)。"""
    m = re.search(r'tracks/' + str(track_idx) + r'/keys\s*=\s*', block)
    if not m:
        return None
    j = m.end()
    if j >= len(block) or block[j] != '{':
        return None
    depth = 0
    start = j
    while j < len(block):
        if block[j] == '{':
            depth += 1
        elif block[j] == '}':
            depth -= 1
            if depth == 0:
                return (start, j + 1)
        j += 1
    return None


def _replace_keys_field(text: str, sub_id: str, track_idx: int,
                        field: str, new_value_str: str) -> str:
    """
    外科式替換：在指定 sub_resource 的 tracks/<idx>/keys dict 中，
    把 "field" 的值換成 new_value_str，其餘欄位與格式原封不動。
    """
    sub = _sub_block_span(text, sub_id)
    if sub is None:
        return text
    s, e = sub
    block = text[s:e]

    kspan = _keys_dict_span(block, track_idx)
    if kspan is None:
        return text
    ds, de = kspan
    dict_str = block[ds:de]

    vspan = _field_value_span(dict_str, field)
    if vspan is None:
        return text
    vs, ve = vspan
    new_dict = dict_str[:vs] + new_value_str + dict_str[ve:]
    new_block = block[:ds] + new_dict + block[de:]
    return text[:s] + new_block + text[e:]


def _replace_sub_prop(text: str, sub_id: str, prop: str, new_val_str: str) -> str:
    """替換指定 sub_resource 區塊中某個頂層屬性（如 length）的值。"""
    sub = _sub_block_span(text, sub_id)
    if sub is None:
        return text
    s, e = sub
    block = text[s:e]
    m = re.search(r'(?m)^(' + re.escape(prop) + r'\s*=\s*)(.*)$', block)
    if not m:
        return text
    new_block = block[:m.start(2)] + new_val_str + block[m.end(2):]
    return text[:s] + new_block + text[e:]


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
    elif cmd == "offset":
        if len(sys.argv) < 6:
            print("用法：anim_inspector.py offset <file> <anim> <track_path> <delta>")
            sys.exit(1)
        cmd_offset(file, sys.argv[3], sys.argv[4], sys.argv[5])
    elif cmd == "scale-value":
        if len(sys.argv) < 6:
            print("用法：anim_inspector.py scale-value <file> <anim> <track_path> <factor>")
            sys.exit(1)
        cmd_scale_value(file, sys.argv[3], sys.argv[4], sys.argv[5])
    else:
        print(f"未知指令：{cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
