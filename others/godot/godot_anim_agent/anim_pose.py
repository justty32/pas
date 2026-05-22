"""
anim_pose.py — 程序化擺位 / 2-bone IK（Phase 3 ③）

給定目標座標，用反向運動學解出兩節骨骼（上臂/前臂）的旋轉，寫回 .tres 對應時間的 key。
純數學、確定性；骨骼長度與基準朝向由呼叫者帶入（它們在 skeleton/場景裏，不在動畫檔），
工具不臆測。延續 agent 主軸：人/Claude 給意圖與場景參數，工具做確定性運算。

使用方式：
  python anim_pose.py aim <file.tres> <anim> <time> <target_x> <target_y>
        --upper <track> --fore <track> --lengths <L1,L2>
        [--bend down|up] [--shoulder <X,Y>] [--base <B1,B2 弧度>]

範例：
  python anim_pose.py aim fighter.tres punch 0.3 40 -10 \
        --upper "Armature/UpperArm:rotation" --fore "Armature/ForeArm:rotation" \
        --lengths 30,28

說明：
  - 座標為動畫所在的 2D 框架（Godot 2D：+Y 朝下）。target 為手（末端）要命中的點。
  - --lengths L1,L2：上臂、前臂長度（必填）。
  - --shoulder X,Y：鏈條根（肩）位置，預設 0,0；target 會換算成相對肩的座標。
  - --base B1,B2：rotation=0 時上臂的世界朝向、前臂相對上臂的朝向（弧度），預設 0,0。
  - --bend down|up：兩組 IK 解擇一（肘部彎向）；若彎錯邊就換另一個。
  - target 超出可達範圍時夾到最遠/最近並提示。
  - 解完用 set-key 寫回 upper / fore 兩條 rotation 軌道，並印出 FK 反算的命中點供核對。
"""

import sys
import math
from pathlib import Path

from anim_inspector import parse_tres, _find_anim, _extract_tracks, cmd_set_key


def _solve_2bone(tx, ty, L1, L2, base1, base2, bend):
    """
    解 2-bone IK。target (tx,ty) 已相對肩關節。bend: +1 / -1 擇一組解。
    回傳 (r1, r2, info)：r1 上臂 rotation、r2 前臂 rotation（相對上臂），皆弧度。
    """
    eps = 1e-6
    D = math.hypot(tx, ty)
    reach, inner = L1 + L2, abs(L1 - L2)
    clamped = None
    Dc = D
    if D > reach:
        Dc, clamped = reach - eps, f"超出最遠伸展 {reach}，夾到最大可達"
    elif D < inner:
        Dc, clamped = inner + eps, f"近於最小可達 {inner}，夾到最小"
    # 依夾過的距離縮放 target（保留方向）
    if D > eps:
        sx, sy = tx * Dc / D, ty * Dc / D
    else:
        sx, sy = Dc, 0.0

    theta = math.atan2(sy, sx)
    cos_a1 = (Dc * Dc + L1 * L1 - L2 * L2) / (2 * L1 * Dc)
    a1 = math.acos(max(-1.0, min(1.0, cos_a1)))
    dir1 = theta + bend * a1                       # 上臂世界朝向
    ex, ey = L1 * math.cos(dir1), L1 * math.sin(dir1)
    dir2 = math.atan2(sy - ey, sx - ex)            # 前臂世界朝向（肘指向 target）

    def _wrap(a):
        return math.atan2(math.sin(a), math.cos(a))

    r1 = _wrap(dir1 - base1)
    r2 = _wrap(dir2 - dir1 - base2)

    # FK 反算（用寫回的 r1/r2 + base 重建手位置，核對是否命中）
    f_dir1 = base1 + r1
    fex, fey = L1 * math.cos(f_dir1), L1 * math.sin(f_dir1)
    f_dir2 = f_dir1 + base2 + r2
    hx, hy = fex + L2 * math.cos(f_dir2), fey + L2 * math.sin(f_dir2)

    return r1, r2, {"clamped": clamped, "elbow": (ex, ey),
                    "hand": (hx, hy), "target_used": (sx, sy)}


def cmd_aim(filepath, anim_name, time_str, tx, ty,
            upper, fore, L1, L2, base1, base2, bend, shoulder):
    text = Path(filepath).read_text(encoding="utf-8")
    data = parse_tres(text)
    anim = _find_anim(data, anim_name)
    if anim is None:
        print(f"找不到動畫：{anim_name}")
        return
    paths = {t["path"] for t in _extract_tracks(anim)}
    for p in (upper, fore):
        if p not in paths:
            print(f"找不到軌道：{p}\n可用軌道：{', '.join(sorted(paths))}")
            return

    # target 換算成相對肩
    rx, ry = tx - shoulder[0], ty - shoulder[1]
    r1, r2, info = _solve_2bone(rx, ry, L1, L2, base1, base2, bend)

    print(f"=== aim {anim_name} @t={time_str}：target=({tx}, {ty}) ===")
    if info["clamped"]:
        print(f"  ⚠ {info['clamped']}")
    hx, hy = info["hand"]
    hx_abs, hy_abs = hx + shoulder[0], hy + shoulder[1]
    print(f"  解：{upper} = {r1:.4f} rad ({math.degrees(r1):.1f}°)")
    print(f"      {fore}  = {r2:.4f} rad ({math.degrees(r2):.1f}°)")
    print(f"  FK 命中：({hx_abs:.2f}, {hy_abs:.2f})  "
          f"誤差={math.hypot(hx_abs - tx, hy_abs - ty):.4f}")

    # 寫回兩條 rotation 軌道（重用 set-key：存在則更新，否則插入）
    cmd_set_key(filepath, anim_name, upper, time_str, repr(round(r1, 6)))
    cmd_set_key(filepath, anim_name, fore, time_str, repr(round(r2, 6)))


def _pair(s, typ=float):
    parts = [typ(x) for x in s.split(",")]
    if len(parts) != 2:
        raise ValueError
    return parts


def main():
    if len(sys.argv) < 2 or sys.argv[1] != "aim":
        print(__doc__)
        sys.exit(0 if len(sys.argv) < 2 else 1)

    args = sys.argv[2:]
    opts = {"--upper": None, "--fore": None, "--lengths": None,
            "--bend": "down", "--shoulder": "0,0", "--base": "0,0"}
    for key in list(opts):
        if key in args:
            i = args.index(key)
            if i + 1 >= len(args):
                print(f"{key} 缺少值")
                sys.exit(1)
            opts[key] = args[i + 1]
            del args[i:i + 2]

    if len(args) < 5:
        print("用法：anim_pose.py aim <file> <anim> <time> <target_x> <target_y> "
              "--upper <track> --fore <track> --lengths L1,L2 "
              "[--bend down|up] [--shoulder X,Y] [--base B1,B2]")
        sys.exit(1)
    if not (opts["--upper"] and opts["--fore"] and opts["--lengths"]):
        print("--upper / --fore / --lengths 為必填。")
        sys.exit(1)

    filepath, anim_name, time_str, tx_s, ty_s = args[0], args[1], args[2], args[3], args[4]
    try:
        L1, L2 = _pair(opts["--lengths"])
        shoulder = _pair(opts["--shoulder"])
        base1, base2 = _pair(opts["--base"])
    except ValueError:
        print("--lengths / --shoulder / --base 需為兩個逗號分隔的數字。")
        sys.exit(1)
    bend = 1.0 if opts["--bend"] == "down" else -1.0

    cmd_aim(filepath, anim_name, time_str, float(tx_s), float(ty_s),
            opts["--upper"], opts["--fore"], L1, L2, base1, base2, bend, shoulder)


if __name__ == "__main__":
    main()
