"""
anim_tree.py — Godot AnimationNodeStateMachine (.tres) 解析 / 生成工具

Phase 3 ② 工作流程工具：把「烘焙好的動畫」組成狀態機，並讓 metadata 的
相容關係（compatible_after）自動推導成轉場。

設計取向：狀態機是結構化的小資源，本工具採「解析成模型 → 修改 → 整檔重生成」，
不像 anim_inspector 對大 key 陣列做外科替換。重生成輸出乾淨、load_steps 自動重算。

使用方式：
  python anim_tree.py summary        <sm.tres> [--lib <library.tres>]
  python anim_tree.py add-state      <sm.tres> <state> <anim> [x y]
  python anim_tree.py rm-state       <sm.tres> <state>
  python anim_tree.py add-transition <sm.tres> <from> <to> [--xfade T] [--switch M] [--advance M] [--cond NAME] [--end]
  python anim_tree.py rm-transition  <sm.tres> <from> <to>
  python anim_tree.py set-blend      <sm.tres> <from> <to> <xfade_time>
  python anim_tree.py derive         <sm.tres> --lib <library.tres> [--meta <meta.json>] [--start STATE] [--reset]
  python anim_tree.py bake-combo     <sm.tres> --lib <library.tres> --name <combo> --clips a,b[,c] [--blend N] [--root-motion PATH] [--libname NAME]
  python anim_tree.py scaffold-scene <sm.tres> --lib <library.tres> [--out <scene.tscn>] [--root NAME]

旗標：
  --switch  immediate(0) | sync(1) | at_end(2)        轉場切換時機（預設 immediate）
  --advance disabled(0)  | enabled(1) | auto(2)       自動推進模式（預設 enabled）
  --cond    <StringName>                               advance_condition 條件名
  --end     讓 <to> 指向特殊 End 狀態

範例：
  python anim_tree.py summary examples/state_machine_sample.tres
  python anim_tree.py add-state      examples/state_machine_sample.tres guard guard 460 300
  python anim_tree.py add-transition examples/state_machine_sample.tres idle guard --xfade 0.15 --advance auto --cond do_guard
  python anim_tree.py set-blend      examples/state_machine_sample.tres idle punch 0.25
  # 招牌用法：依 library + metadata 一次烘出整張狀態圖
  python anim_tree.py derive examples/combo.tres --lib examples/fighter.tres --meta examples/fighter.anim.meta.json --start idle --reset
  # 烘焙連招當狀態：concat 烘出 step_in+punch 接進 library，再加成 sm 的一個狀態
  python anim_tree.py bake-combo examples/combo.tres --lib examples/fighter.tres --name dash_punch --clips step_in,punch --blend 0.1 --root-motion ".:position"
  # 對 library 交叉檢查狀態引用的動畫名是否都存在
  python anim_tree.py summary examples/combo.tres --lib examples/fighter.tres
  # 產出可載入驗證的場景（骨架依 library 軌道路徑自動建）
  python anim_tree.py scaffold-scene examples/state_machine_sample.tres --lib examples/fighter.tres --out examples/fighter_tree.tscn

備註：
  - 動畫名以「不具名（預設）AnimationLibrary」為前提，直接用 resource_name
    （如 &"idle"）。若你的 AnimationPlayer 把 library 掛成具名（如 "fighter"），
    需改成 &"fighter/idle"——derive 可加 --libname 前綴。
  - 轉場方向約定：metadata 中 X.compatible_after=[Y] 代表「X 可接在 Y 之後」，
    推導為轉場 Y → X（與 anim_metadata.py 的 compat 語意一致）。
  - Start / End 為 Godot 內部特殊節點（AnimationNodeStartState / EndState）。
"""

import re
import sys
import json
from pathlib import Path

# 複用 anim_inspector 的 .tres 解析器與 Godot 風格實數輸出
from anim_inspector import parse_tres, _split_top_level, _fmt_real, _extract_tracks


# ── enum 對照（友善名 ←→ 數字） ──────────────────────────────────────────────

SWITCH_MODES  = {"immediate": 0, "sync": 1, "at_end": 2}
ADVANCE_MODES = {"disabled": 0, "enabled": 1, "auto": 2}
SWITCH_NAMES  = {v: k for k, v in SWITCH_MODES.items()}
ADVANCE_NAMES = {v: k for k, v in ADVANCE_MODES.items()}

# 特殊節點類型
START_TYPE = "AnimationNodeStartState"
END_TYPE   = "AnimationNodeEndState"
ANIM_TYPE  = "AnimationNodeAnimation"
TRANS_TYPE = "AnimationNodeStateMachineTransition"

# Transition 屬性預設值（取自引擎 / 官方文件）。重生成時只輸出「非預設」者，
# 與 Godot 編輯器存檔行為一致（減少無謂 diff）。
TRANS_DEFAULTS = {
    "xfade_time":        "0.0",
    "xfade_curve":       None,
    "switch_mode":       "0",
    "advance_mode":      "1",
    "advance_condition": '&""',
    "advance_expression": '""',
    "break_loop_at_end": "false",
    "reset":             "true",
    "priority":          "1",
}


# ── 解析：.tres → 結構化模型 ──────────────────────────────────────────────────

def _subresource_id(raw: str):
    """SubResource("Foo_bar") → "Foo_bar"；非此格式回傳 None。"""
    m = re.search(r'SubResource\("([^"]+)"\)', raw)
    return m.group(1) if m else None


def _parse_vector2(raw: str):
    """Vector2(200, 50) → (200.0, 50.0)；失敗回傳 None。"""
    m = re.search(r'Vector2\(\s*([-\d.eE]+)\s*,\s*([-\d.eE]+)\s*\)', raw)
    return (float(m.group(1)), float(m.group(2))) if m else None


def load_sm(path: str) -> dict:
    """
    讀取 AnimationNodeStateMachine .tres，回傳模型：
    {
      "uid": "uid://..." | None,
      "graph_offset": (x, y) | None,
      "state_machine_type": "0" | None,   # 原始字串，預設 Root 時為 None
      "states": [ {name, node_type, node_props:{k:rawval}, pos:(x,y)|None}, ... ],
      "transitions": [ {from, to, props:{k:rawval}}, ... ],
    }
    states 以「Start、End 優先，其餘照 resource 區塊出現序」排列。
    """
    text = Path(path).read_text(encoding="utf-8")
    data = parse_tres(text)

    if data["header"].get("type") != "AnimationNodeStateMachine":
        raise ValueError(
            f"{path} 不是 AnimationNodeStateMachine（header type="
            f"{data['header'].get('type')!r}）")

    subs = {s["id"]: s for s in data["sub_resources"]}
    rprops = data["resource"]["props"]

    # 依出現序蒐集 state 名稱（從 states/<name>/node 鍵）
    state_order, seen = [], set()
    for key in rprops:
        m = re.match(r'states/(.+)/node$', key)
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            state_order.append(m.group(1))

    states = []
    for name in state_order:
        node_ref = rprops.get(f"states/{name}/node", "")
        sid = _subresource_id(node_ref)
        sub = subs.get(sid, {})
        node_type = sub.get("type", "")
        node_props = dict(sub.get("props", {}))
        pos_raw = rprops.get(f"states/{name}/position")
        states.append({
            "name": name,
            "node_type": node_type,
            "node_props": node_props,
            "pos": _parse_vector2(pos_raw) if pos_raw else None,
        })

    # 轉場：transitions = ["from", "to", SubResource(id), ...] 三元組
    transitions = []
    traw = rprops.get("transitions", "").strip()
    if traw.startswith("[") and traw.endswith("]"):
        elems = _split_top_level(traw[1:-1].strip())
        for i in range(0, len(elems) - 2, 3):
            frm = elems[i].strip().strip('"')
            to  = elems[i + 1].strip().strip('"')
            tid = _subresource_id(elems[i + 2])
            tprops = dict(subs.get(tid, {}).get("props", {}))
            transitions.append({"from": frm, "to": to, "props": tprops})

    # 排序：Start、End 置前
    def _rank(s):
        return {"Start": 0, "End": 1}.get(s["name"], 2)
    states.sort(key=_rank)

    # Godot 4.4+ 格式不再序列化 Start/End sub_resource，但 transitions 仍可引用。
    # 補回虛擬節點，讓後續邏輯（_find_state、cmd_summary 端點檢查）不報假錯。
    existing_names = {s["name"] for s in states}
    for tr in transitions:
        for endpoint, ntype, default_pos in [
            (tr["from"], START_TYPE, (40, 50)),
            (tr["to"],   END_TYPE,   (460, 50)),
        ]:
            if endpoint in ("Start", "End") and endpoint not in existing_names:
                ntype_use = START_TYPE if endpoint == "Start" else END_TYPE
                states.insert(0, {"name": endpoint, "node_type": ntype_use,
                                  "node_props": {}, "pos": None})
                existing_names.add(endpoint)
    states.sort(key=_rank)

    return {
        "uid": data["header"].get("uid"),
        "graph_offset": _parse_vector2(rprops["graph_offset"]) if "graph_offset" in rprops else None,
        "state_machine_type": rprops.get("state_machine_type"),
        "states": states,
        "transitions": transitions,
    }


# ── 生成：模型 → .tres 文字 ───────────────────────────────────────────────────

def _sanitize(name: str) -> str:
    return re.sub(r'[^A-Za-z0-9]', '_', name)


def _state_sub_id(st: dict) -> str:
    if st["node_type"] == START_TYPE:
        return "AnimationNodeStartState_start"
    if st["node_type"] == END_TYPE:
        return "AnimationNodeEndState_end"
    return f"{st['node_type']}_{_sanitize(st['name'])}"


def _trans_sub_id(tr: dict) -> str:
    return f"Transition_{_sanitize(tr['from'])}_{_sanitize(tr['to'])}"


def _vec2(pos) -> str:
    x, y = pos
    return f"Vector2({_fmt_real(x)}, {_fmt_real(y)})"


def _nondefault_trans_props(props: dict) -> dict:
    """只保留與預設不同的 transition 屬性（未知屬性一律保留以利 round-trip）。"""
    out = {}
    for k, v in props.items():
        if k in TRANS_DEFAULTS and str(v).strip() == str(TRANS_DEFAULTS[k]):
            continue
        out[k] = v
    return out


def dump_sm(model: dict) -> str:
    """模型 → 完整 .tres 文字（Godot 4.4+ 格式）。

    Start / End 是引擎內建節點：不輸出對應的 sub_resource，也不輸出
    states/Start/ 或 states/End/ 條目——Godot 自動管理它們。
    load_steps 已在 Godot 4.4+ 格式移除，不輸出。
    """
    states, transitions = model["states"], model["transitions"]
    # Start/End 不寫入 .tres（引擎內建，Godot 自動管理）
    regular_states = [s for s in states if s["node_type"] not in (START_TYPE, END_TYPE)]

    # 各 sub_resource 區塊（只輸出非 Start/End 狀態）
    blocks = []
    for st in regular_states:
        sid = _state_sub_id(st)
        lines = [f'[sub_resource type="{st["node_type"]}" id="{sid}"]']
        for k, v in st["node_props"].items():
            lines.append(f"{k} = {v}")
        blocks.append("\n".join(lines))
    for tr in transitions:
        tid = _trans_sub_id(tr)
        lines = [f'[sub_resource type="{TRANS_TYPE}" id="{tid}"]']
        for k, v in _nondefault_trans_props(tr["props"]).items():
            lines.append(f"{k} = {v}")
        blocks.append("\n".join(lines))

    uid = model.get("uid")
    header = (f'[gd_resource type="AnimationNodeStateMachine" format=3'
              + (f' uid="{uid}"' if uid else "") + "]")

    # [resource] 區塊（只輸出非 Start/End 狀態）
    res_lines = []
    if model.get("state_machine_type") is not None:
        res_lines.append(f'state_machine_type = {model["state_machine_type"]}')
    for st in regular_states:
        res_lines.append(f'states/{st["name"]}/node = SubResource("{_state_sub_id(st)}")')
        pos = st["pos"] if st["pos"] is not None else (0, 0)
        res_lines.append(f'states/{st["name"]}/position = {_vec2(pos)}')
    if transitions:
        elems = []
        for tr in transitions:
            elems.append(f'"{tr["from"]}"')
            elems.append(f'"{tr["to"]}"')
            elems.append(f'SubResource("{_trans_sub_id(tr)}")')
        res_lines.append("transitions = [" + ", ".join(elems) + "]")
    go = model.get("graph_offset")
    if go is not None and (go[0] != 0 or go[1] != 0):
        res_lines.append(f'graph_offset = {_vec2(go)}')

    parts = [header, ""]
    for b in blocks:
        parts.append(b)
        parts.append("")
    parts.append("[resource]")
    parts.extend(res_lines)
    return "\n".join(parts) + "\n"


def save_sm(path: str, model: dict) -> None:
    Path(path).write_text(dump_sm(model), encoding="utf-8")
    print(f"已儲存：{path}")


# ── 模型操作小工具 ────────────────────────────────────────────────────────────

def _find_state(model, name):
    return next((s for s in model["states"] if s["name"] == name), None)


def _find_transition(model, frm, to):
    return next((t for t in model["transitions"]
                 if t["from"] == frm and t["to"] == to), None)


def _ensure_special(model, name, node_type, default_pos):
    """確保 Start / End 特殊狀態存在。"""
    if _find_state(model, name) is None:
        model["states"].insert(0 if name == "Start" else len(model["states"]),
                               {"name": name, "node_type": node_type,
                                "node_props": {}, "pos": default_pos})


def _auto_pos(model):
    """為新狀態挑一個不重疊的網格座標。"""
    n = sum(1 for s in model["states"] if s["node_type"] not in (START_TYPE, END_TYPE))
    return (200 + (n % 4) * 220, 160 + (n // 4) * 140)


def _apply_trans_flags(props: dict, flags: dict) -> None:
    """把 add-transition / set-blend 的旗標套進 transition 原始屬性 dict。"""
    if "xfade" in flags:
        props["xfade_time"] = _fmt_real(float(flags["xfade"]))
    if "switch" in flags:
        props["switch_mode"] = str(_resolve_enum(flags["switch"], SWITCH_MODES, "switch"))
    if "advance" in flags:
        props["advance_mode"] = str(_resolve_enum(flags["advance"], ADVANCE_MODES, "advance"))
    if "cond" in flags:
        props["advance_condition"] = f'&"{flags["cond"]}"'


def _resolve_enum(val, table, label):
    """接受友善名（immediate）或數字（0）。"""
    v = str(val).strip()
    if v in table:
        return table[v]
    if v.isdigit() and int(v) in table.values():
        return int(v)
    raise ValueError(f"--{label} 不合法：{val}（可用 {'/'.join(table)} 或數字）")


# ── 指令 ─────────────────────────────────────────────────────────────────────

def _library_anim_names(lib_path: str) -> set:
    """讀 AnimationLibrary，回傳所有動畫 resource_name 的集合。"""
    data = parse_tres(Path(lib_path).read_text(encoding="utf-8"))
    return {r["props"].get("resource_name", r["id"]).strip('"')
            for r in data["sub_resources"] if r["type"] == "Animation"}


def _anim_basename(ref: str) -> str:
    """&"fighter/idle" → "idle"；&"idle" → "idle"（去 library 前綴與 StringName 包裝）。"""
    s = ref.strip().lstrip("&").strip('"')
    return s.rsplit("/", 1)[-1]


def cmd_summary(path: str, lib: str = None) -> None:
    model = load_sm(path)
    print(f"=== {path} ===")
    smt = {"0": "Root", "1": "Nested", "2": "Grouped", None: "Root（預設）"}
    print(f"類型：AnimationNodeStateMachine（{smt.get(model['state_machine_type'], model['state_machine_type'])}）")

    # --lib 交叉檢查：狀態引用的動畫名是否真的存在於 library
    lib_names = _library_anim_names(lib) if lib else None
    missing = []

    real_states = [s for s in model["states"] if s["node_type"] not in (START_TYPE, END_TYPE)]
    print(f"\n── 狀態（{len(real_states)} 個動畫狀態，另含 Start/End）")
    for st in model["states"]:
        flag = ""
        if st["node_type"] == ANIM_TYPE:
            anim = st["node_props"].get("animation", "?").strip().lstrip("&").strip('"')
            extra = f"  動畫={anim}"
            if lib_names is not None and _anim_basename(anim) not in lib_names:
                flag = "  ⚠ library 無此動畫"
                missing.append((st["name"], anim))
        elif st["node_type"] in (START_TYPE, END_TYPE):
            extra = "  （特殊節點）"
        else:
            extra = f"  ({st['node_type']})"
        pos = f"@{tuple(int(c) for c in st['pos'])}" if st["pos"] else ""
        print(f"   {st['name']:14s}{extra}  {pos}{flag}")

    print(f"\n── 轉場（{len(model['transitions'])} 條）")
    state_names = {s["name"] for s in model["states"]}
    for tr in model["transitions"]:
        p = tr["props"]
        xfade = p.get("xfade_time", "0.0")
        sw = SWITCH_NAMES.get(int(p.get("switch_mode", "0")), p.get("switch_mode"))
        adv = ADVANCE_NAMES.get(int(p.get("advance_mode", "1")), p.get("advance_mode"))
        cond = p.get("advance_condition", '&""').strip().lstrip("&").strip('"')
        bits = [f"xfade={xfade}", f"switch={sw}", f"advance={adv}"]
        if cond:
            bits.append(f"cond={cond}")
        if str(p.get("break_loop_at_end", "false")) == "true":
            bits.append("break_loop_at_end")
        warn = ""
        if tr["from"] not in state_names or tr["to"] not in state_names:
            warn = "  ⚠ 端點不存在"
        print(f"   {tr['from']:12s} → {tr['to']:12s}  [{', '.join(bits)}]{warn}")

    if lib_names is not None:
        print()
        if missing:
            print(f"⚠ 對 {lib}：{len(missing)} 個狀態引用了 library 沒有的動畫——"
                  + "、".join(f"{n}({a})" for n, a in missing))
        else:
            print(f"✓ 對 {lib}：所有動畫狀態都對得上 library。")


def cmd_add_state(path, name, anim, pos=None) -> None:
    model = load_sm(path)
    if _find_state(model, name):
        print(f"狀態已存在：{name}")
        return
    if pos is None:
        pos = _auto_pos(model)
    model["states"].append({
        "name": name, "node_type": ANIM_TYPE,
        "node_props": {"animation": f'&"{anim}"'}, "pos": pos,
    })
    print(f"新增狀態：{name}（動畫 {anim}）@{tuple(int(c) for c in pos)}")
    save_sm(path, model)


def cmd_rm_state(path, name) -> None:
    model = load_sm(path)
    if not _find_state(model, name):
        print(f"找不到狀態：{name}")
        return
    if name in ("Start", "End"):
        print(f"不可移除特殊狀態：{name}")
        return
    model["states"] = [s for s in model["states"] if s["name"] != name]
    before = len(model["transitions"])
    model["transitions"] = [t for t in model["transitions"]
                            if t["from"] != name and t["to"] != name]
    dropped = before - len(model["transitions"])
    print(f"移除狀態：{name}" + (f"（連帶移除 {dropped} 條轉場）" if dropped else ""))
    save_sm(path, model)


def cmd_add_transition(path, frm, to, flags) -> None:
    model = load_sm(path)
    if flags.get("end"):
        to = "End"
        _ensure_special(model, "End", END_TYPE, (460, 50))
    for endpoint in (frm, to):
        if _find_state(model, endpoint) is None:
            print(f"⚠ 端點狀態不存在：{endpoint}（仍會建立轉場，但 Godot 載入時會忽略）")
    tr = _find_transition(model, frm, to)
    if tr is None:
        tr = {"from": frm, "to": to, "props": {}}
        model["transitions"].append(tr)
        verb = "新增"
    else:
        verb = "更新"
    _apply_trans_flags(tr["props"], flags)
    print(f"{verb}轉場：{frm} → {to}")
    save_sm(path, model)


def cmd_rm_transition(path, frm, to) -> None:
    model = load_sm(path)
    if _find_transition(model, frm, to) is None:
        print(f"找不到轉場：{frm} → {to}")
        return
    model["transitions"] = [t for t in model["transitions"]
                            if not (t["from"] == frm and t["to"] == to)]
    print(f"移除轉場：{frm} → {to}")
    save_sm(path, model)


def cmd_set_blend(path, frm, to, xfade) -> None:
    cmd_add_transition(path, frm, to, {"xfade": xfade})


def cmd_derive(path, flags) -> None:
    """
    依 AnimationLibrary + metadata 烘出狀態機：
      - 每個 library 動畫 → 一個 AnimationNodeAnimation 狀態
      - metadata 每組 X.compatible_after=[Y] → 轉場 Y → X
      - --start STATE：建立 Start → STATE
      - --reset：忽略現有檔案，從空白（Start/End）重建
    """
    lib = flags.get("lib")
    if not lib:
        print("derive 需要 --lib <library.tres>")
        return
    libname = flags.get("libname")  # 具名 library 前綴，如 "fighter"

    # 取得 library 內動畫名
    ldata = parse_tres(Path(lib).read_text(encoding="utf-8"))
    anim_names = [r["props"].get("resource_name", r["id"]).strip('"')
                  for r in ldata["sub_resources"] if r["type"] == "Animation"]
    if not anim_names:
        print(f"{lib} 內找不到 Animation。")
        return

    def anim_ref(n):
        return f"{libname}/{n}" if libname else n

    if flags.get("reset") or not Path(path).exists():
        model = {"uid": None, "graph_offset": None, "state_machine_type": None,
                 "states": [], "transitions": []}
    else:
        model = load_sm(path)

    _ensure_special(model, "Start", START_TYPE, (40, 50))

    # 建狀態（已存在則略過）
    added = 0
    for n in anim_names:
        if _find_state(model, n) is None:
            model["states"].append({
                "name": n, "node_type": ANIM_TYPE,
                "node_props": {"animation": f'&"{anim_ref(n)}"'},
                "pos": _auto_pos(model),
            })
            added += 1

    # 依 metadata 推導轉場
    derived = 0
    if flags.get("meta"):
        meta = json.loads(Path(flags["meta"]).read_text(encoding="utf-8"))
        for x, entry in meta.items():
            for y in entry.get("compatible_after", []):
                # X 可接在 Y 之後 → 轉場 Y → X
                if x in anim_names and y in anim_names and not _find_transition(model, y, x):
                    model["transitions"].append({"from": y, "to": x, "props": {}})
                    derived += 1

    # Start → 指定起始狀態
    start_to = flags.get("start") or ("idle" if "idle" in anim_names else anim_names[0])
    if _find_state(model, start_to) and not _find_transition(model, "Start", start_to):
        model["transitions"].append({"from": "Start", "to": start_to, "props": {}})

    print(f"derive：{added} 個新狀態、{derived} 條由 metadata 推導的轉場、"
          f"Start → {start_to}。")
    save_sm(path, model)
    print()
    cmd_summary(path)


# ── bake-combo：烘焙連招 → library 動畫 → 狀態機狀態 ─────────────────────────

def cmd_bake_combo(sm_path, flags) -> None:
    """
    招牌願景「烘焙連招當狀態」：一步把 anim_compose 的 concat 結果接進狀態機。
      1) 對 library 跑 concat（多段連招烘成一段新動畫，支援 --blend / --root-motion）
      2) 把該新動畫當成 AnimationNodeAnimation 狀態加進 sm
    """
    import anim_compose
    lib   = flags.get("lib")
    name  = flags.get("name")
    clips = flags.get("clips")
    if not (lib and name and clips):
        print("bake-combo 需要 --lib <library.tres> --name <combo> --clips a,b[,c...]")
        return
    clip_list = [c.strip() for c in clips.split(",") if c.strip()]
    if len(clip_list) < 2:
        print("--clips 至少要兩段（逗號分隔），例如 --clips step_in,punch")
        return
    blend = float(flags["blend"]) if "blend" in flags else 0.0
    rmpath = flags.get("root-motion")
    libname = flags.get("libname")

    # 烘焙前先確認新名不存在於 library（concat 自己也會擋，但這樣才能決定是否續做 add-state）
    if name in _library_anim_names(lib):
        print(f"library 已有動畫 '{name}'；換個 --name 或先刪除。")
        return

    print(f"① 烘焙連招 → {lib}")
    anim_compose.cmd_concat(lib, name, clip_list, blend, rmpath)
    if name not in _library_anim_names(lib):     # concat 因故未成功（缺 clip 等）
        print("烘焙未成功，略過加入狀態機。")
        return

    print(f"\n② 加入狀態機 → {sm_path}")
    ref = f"{libname}/{name}" if libname else name
    model = load_sm(sm_path) if Path(sm_path).exists() else \
        {"uid": None, "graph_offset": None, "state_machine_type": None,
         "states": [], "transitions": []}
    if _find_state(model, name):
        print(f"狀態機已有狀態 '{name}'（library 已更新，但狀態不重複加）。")
        return
    model["states"].append({
        "name": name, "node_type": ANIM_TYPE,
        "node_props": {"animation": f'&"{ref}"'}, "pos": _auto_pos(model),
    })
    print(f"新增狀態：{name}（動畫 {ref}）")
    save_sm(sm_path, model)
    print("\n提示：用 add-transition 把這個連招狀態接進圖，例如 "
          f"`add-transition {sm_path} idle {name} --advance auto --cond do_{name}`。")


# ── scaffold-scene：產生可載入驗證的 .tscn 接線範本 ──────────────────────────

# Vis 小色塊配色（依節點序輪替），純為驗證時看得見動作
_VIS_COLORS = [
    "Color(0.9, 0.5, 0.3, 1)", "Color(0.4, 0.7, 0.9, 1)",
    "Color(0.5, 0.85, 0.5, 1)", "Color(0.85, 0.8, 0.4, 1)",
    "Color(0.8, 0.5, 0.8, 1)",
]


def _library_node_targets(lib_path: str):
    """
    從 AnimationLibrary 的所有軌道路徑推導出要建的節點：
      回傳 (direct, all_paths)
      direct    : 被軌道直接指到的節點路徑集合（"" 代表 root）
      all_paths : direct 連同所有祖先前綴（用來補中介節點），不含 root
    """
    data = parse_tres(Path(lib_path).read_text(encoding="utf-8"))
    direct = set()
    for r in data["sub_resources"]:
        if r["type"] != "Animation":
            continue
        for t in _extract_tracks(r):
            node = t["path"].split(":")[0].strip()
            if node in ("", "."):
                direct.add("")           # root
            else:
                direct.add(node)
    all_paths = set()
    for p in direct:
        if not p:
            continue
        segs = p.split("/")
        for i in range(1, len(segs) + 1):
            all_paths.add("/".join(segs[:i]))
    return direct, all_paths


def _node_block(name, ntype, parent, props=None):
    head = f'[node name="{name}" type="{ntype}"'
    if parent is not None:
        head += f' parent="{parent}"'
    head += "]"
    lines = [head]
    for k, v in (props or {}).items():
        lines.append(f"{k} = {v}")
    return "\n".join(lines)


def _vis_block(parent, idx, is_root=False):
    """掛在被動畫節點下的小 Polygon2D，讓播放時看得到位移/旋轉。"""
    color = _VIS_COLORS[idx % len(_VIS_COLORS)]
    if is_root:
        poly = "PackedVector2Array(-10, -10, 10, -10, 10, 10, -10, 10)"
    else:
        # 從節點原點往下的細長條，旋轉時擺動明顯
        poly = "PackedVector2Array(-6, 0, 6, 0, 6, 44, -6, 44)"
    return _node_block("Vis", "Polygon2D", parent,
                       {"color": color, "polygon": poly})


def cmd_scaffold_scene(sm_path, flags) -> None:
    """
    產生 .tscn 接線範本：root Node2D + AnimationPlayer(掛 library) +
    依 library 軌道路徑自動建出的 Node2D 骨架(各掛小 Polygon2D) + AnimationTree(接 sm)。
    下次開 Godot 雙擊即可：看 AnimationTree 面板的狀態圖、按播放看 idle 動起來。
    """
    lib = flags.get("lib")
    if not lib:
        print("scaffold-scene 需要 --lib <library.tres>")
        return
    root_name = flags.get("root", "Fighter")
    out = flags.get("out") or str(Path(sm_path).with_name(Path(sm_path).stem + "_scene.tscn"))
    # ext_resource 走 res:// + 檔名；examples 非 Godot 專案，使用者放進專案後按需調整路徑
    lib_res = flags.get("libres") or f"res://{Path(lib).name}"
    sm_res  = flags.get("smres")  or f"res://{Path(sm_path).name}"

    direct, all_paths = _library_node_targets(lib)

    ext = [
        f'[ext_resource type="AnimationLibrary" path="{lib_res}" id="1_lib"]',
        f'[ext_resource type="AnimationNodeStateMachine" path="{sm_res}" id="2_sm"]',
    ]

    blocks = []
    # root
    root_props = {}
    blocks.append(_node_block(root_name, "Node2D", None, root_props))
    vis_idx = 0
    if "" in direct:
        blocks.append(_vis_block(".", vis_idx, is_root=True)); vis_idx += 1
    # AnimationPlayer（不具名 library → 動畫名直接用）
    blocks.append(_node_block("AnimationPlayer", "AnimationPlayer", ".",
                              {"libraries": '{\n&"": ExtResource("1_lib")\n}'}))
    # 依路徑深度排序建骨架（父先於子）
    for path in sorted(all_paths, key=lambda p: (p.count("/"), p)):
        segs = path.split("/")
        name = segs[-1]
        parent = "/".join(segs[:-1]) or "."
        blocks.append(_node_block(name, "Node2D", parent))
        if path in direct:
            blocks.append(_vis_block(path, vis_idx)); vis_idx += 1
    # AnimationTree（接狀態機）
    blocks.append(_node_block("AnimationTree", "AnimationTree", ".", {
        "tree_root": 'ExtResource("2_sm")',
        "anim_player": 'NodePath("../AnimationPlayer")',
        "active": "true",
    }))

    load_steps = len(ext) + 1
    header = f"[gd_scene load_steps={load_steps} format=3]"
    text = header + "\n\n" + "\n".join(ext) + "\n\n" + "\n\n".join(blocks) + "\n"
    Path(out).write_text(text, encoding="utf-8")

    targets = ", ".join(sorted(p or "(root)" for p in direct))
    print(f"已產生：{out}")
    print(f"  骨架節點（依 library 軌道推導）：{targets}")
    print(f"  ext_resource：{lib_res} / {sm_res}")
    print("\n用法：把這三個檔放進你的 Godot 專案（同層；非根目錄則改 ext_resource 的 res:// 路徑），")
    print("  開 .tscn → 選 AnimationTree 節點看狀態圖能否載入 → 按播放看 idle 擺動。")
    print("  要切到 punch：在 AnimationTree 面板點該狀態，或用腳本 $AnimationTree.get('parameters/playback').travel(\"punch\")。")
    print("  ⚠ 若 Godot 回存後此檔有 diff（uid / 屬性排序 / &\"\" 寫法），回報我據此微調生成器。")


# ── 旗標解析 ──────────────────────────────────────────────────────────────────

def _parse_flags(argv, valued, boolean):
    """簡易旗標解析：valued 取值（--xfade 0.2），boolean 為開關（--reset）。
    回傳 (flags_dict, positional_list)。"""
    flags, pos = {}, []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            key = a[2:]
            if key in boolean:
                flags[key] = True
            elif key in valued:
                flags[key] = argv[i + 1]
                i += 1
            else:
                print(f"未知旗標：{a}")
                sys.exit(1)
        else:
            pos.append(a)
        i += 1
    return flags, pos


# ── CLI 入口 ─────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(0)

    cmd, file = sys.argv[1], sys.argv[2]
    rest = sys.argv[3:]

    try:
        if cmd == "summary":
            flags, pos = _parse_flags(rest, valued={"lib"}, boolean=set())
            cmd_summary(file, flags.get("lib"))
        elif cmd == "add-state":
            flags, pos = _parse_flags(rest, valued=set(), boolean=set())
            if len(pos) < 2:
                print("用法：add-state <sm.tres> <state> <anim> [x y]")
                sys.exit(1)
            xy = (float(pos[2]), float(pos[3])) if len(pos) >= 4 else None
            cmd_add_state(file, pos[0], pos[1], xy)
        elif cmd == "rm-state":
            cmd_rm_state(file, rest[0])
        elif cmd == "add-transition":
            flags, pos = _parse_flags(
                rest, valued={"xfade", "switch", "advance", "cond"}, boolean={"end"})
            if len(pos) < 2 and not flags.get("end"):
                print("用法：add-transition <sm.tres> <from> <to> [旗標…]")
                sys.exit(1)
            to = pos[1] if len(pos) > 1 else "End"
            cmd_add_transition(file, pos[0], to, flags)
        elif cmd == "rm-transition":
            cmd_rm_transition(file, rest[0], rest[1])
        elif cmd == "set-blend":
            cmd_set_blend(file, rest[0], rest[1], rest[2])
        elif cmd == "derive":
            flags, pos = _parse_flags(
                rest, valued={"lib", "meta", "start", "libname"}, boolean={"reset"})
            cmd_derive(file, flags)
        elif cmd == "bake-combo":
            flags, pos = _parse_flags(
                rest, valued={"lib", "name", "clips", "blend", "root-motion", "libname"},
                boolean=set())
            cmd_bake_combo(file, flags)
        elif cmd == "scaffold-scene":
            flags, pos = _parse_flags(
                rest, valued={"lib", "out", "root", "libres", "smres"}, boolean=set())
            cmd_scaffold_scene(file, flags)
        else:
            print(f"未知指令：{cmd}")
            print(__doc__)
            sys.exit(1)
    except (ValueError, IndexError) as ex:
        print(f"錯誤：{ex}")
        sys.exit(1)


if __name__ == "__main__":
    main()
