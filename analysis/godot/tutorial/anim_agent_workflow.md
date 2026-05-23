# 用自然語言編輯 Godot 動畫：godot_anim_agent 端到端教學

> 目標導向教學。工具源在 `others/godot/godot_anim_agent/`，素材在其 `examples/`。
> 設計理念見該目錄 `VISION.md` / `PHASE2_DESIGN.md`；本檔示範「從一堆動畫到一個可在 Godot 載入的狀態機」的完整流程。
> 所有指令請在 `others/godot/godot_anim_agent/` 目錄下執行（工具間以 `from anim_inspector import ...` 互相依賴）。

## 0. 心智模型：agent 是誰、工具做什麼

```
人給意圖 ──▶ Claude（session 內）翻成精確指令 ──▶ Python 工具做確定性變換 ──▶ 回 Godot 預覽
                  ▲                                                              │
                  └──────────────────── 讀回結果再決定下一步 ◀──────────────────┘
```

- **「agent」是 session 裏的 Claude**，不是那幾支 Python。語意判斷（哪段接哪段順、要不要 blend）由 Claude 做。
- **工具不臆測**：只做你叫它做的精確操作。凡是「資料裏沒有」的東西（骨長、骨骼 rest pose、場景座標）一律當**參數由呼叫者給**——這是貫穿全工具鏈的原則（見 `anim_pose.py` 骨長、`anim_compose.py fix-seam` rest 值）。
- 因此工具的價值是「確定性、可驗證、不破壞其他欄位」，而非「聰明」。

## 1. 六支工具速查

| 工具 | 職責 | 主要指令 |
|------|------|----------|
| `anim_inspector.py` | 單一動畫讀/改 | `summary` / `tracks` / `set-key` / `scale-time` / `offset` / `scale-value` |
| `anim_metadata.py` | 動畫旁置 metadata（tags / 相容性） | `init` / `show` / `set-tag` / `rm-tag` / `compat` |
| `anim_compose.py` | 多段組合成新動畫 | `concat` / `fix-seam` / `check-seams` |
| `anim_events.py` | method 軌道（動畫事件） | `list` / `add` / `rm` / `scaffold` |
| `anim_pose.py` | 程序化擺位（2-bone IK） | `aim` |
| `anim_tree.py` | AnimationNodeStateMachine 解析/生成 | `summary` / `add-state` / `add-transition` / `derive` / `bake-combo` / `scaffold-scene` / … |

範例素材 `examples/fighter.tres`：2D 格鬥角色 AnimationLibrary，4 段動畫 `idle`(loop) / `guard` / `step_in`(前踏 24px) / `punch`(含 method 事件 spawn_hit_spark)。

---

## 2. 端到端：從四段動畫到一個可驗證的連招狀態機

### Step 1 — 讀懂手上的動畫

```bash
python3 anim_inspector.py summary examples/fighter.tres          # 全 library 概覽
python3 anim_inspector.py tracks  examples/fighter.tres punch    # 看某段每個 key
```
`summary` 列出每段名稱/長度/軌道；`tracks` 把 value 軌道解析成結構化分量（float / Vector2/3/4 / Quaternion / method dict）。

### Step 2 — 標 metadata（讓後續可自動推導）

```bash
python3 anim_metadata.py init   examples/fighter.tres                  # 旁置 fighter.anim.meta.json
python3 anim_metadata.py set-tag examples/fighter.tres punch attack
python3 anim_metadata.py compat  examples/fighter.tres punch after idle    # punch 可接在 idle 之後
python3 anim_metadata.py show   examples/fighter.tres
```
**相容性語意**：`X compat after Y` → `X.compatible_after += Y`（X 可接在 Y 之後）→ 之後 `anim_tree derive` 會推成轉場 **Y → X**。

### Step 3 — 微調單一動畫

```bash
# 出拳幅度加大 20%（整條軌道乘純量）
python3 anim_inspector.py scale-value examples/fighter.tres punch "Armature/UpperArm:rotation" 1.2
# 出拳加快到 70%（只縮時間軸，安全，連 method/向量軌道都不破壞）
python3 anim_inspector.py scale-time  examples/fighter.tres punch 0.7
# 整體位移平移 / 設單一 key（型別需與軌道一致）
python3 anim_inspector.py offset  examples/fighter.tres punch ".:position" "Vector2(5, 0)"
python3 anim_inspector.py set-key examples/fighter.tres punch ".:position" 0.3 "Vector2(12, -4)"
```
寫回採「外科式逐欄位替換」：單 key 編輯整檔常只有一行 diff，保留 transitions/update 等其他欄位。

### Step 4 — 加動畫事件（method 軌道）

```bash
python3 anim_events.py list     examples/fighter.tres punch          # 看現有事件
# add <file> <anim> <track_path> <time> <method> [arg...]；arg 數字原樣、否則包字串
python3 anim_events.py add      examples/fighter.tres punch "." 0.5 play_sound "punch_whoosh"
python3 anim_events.py scaffold examples/fighter.tres                # 產 fighter_events.gd handler 樣板
```
`scaffold` 蒐集整個 library 出現的所有 method，產出 `.gd` handler 骨架（含參數數偵測與「用於哪些動畫」註解）。

### Step 5 — 程序化擺位（2-bone IK）

```bash
# aim <file> <anim> <time> <target_x> <target_y> --upper <track> --fore <track> --lengths L1,L2
# 場景參數（骨長/肩位/基準朝向）由你給，工具用餘弦定理解上臂/前臂 rotation 寫回
python3 anim_pose.py aim examples/fighter.tres punch 0.3 40 -10 \
    --upper "Armature/UpperArm:rotation" --fore "Armature/ForeArm:rotation" --lengths 30,28
```
解析式 IK，FK 反算誤差 0；`--bend down|up` 擇肘彎向，target 超出可達範圍會夾到最遠並提示殘差。

### Step 6 — 烘焙連招（多段組合）

```bash
# step_in 前踏接 punch，重疊 0.1s cross-fade，位移累加避免滑回原點
python3 anim_compose.py concat examples/fighter.tres advance step_in punch \
    --blend 0.1 --root-motion ".:position"
```
- `--blend N`：相鄰段重疊 N 秒，在重疊窗對「兩段共有、型別一致」的數值軌道做 cross-fade（純量/向量線性、Quaternion 走 SLERP）。
- `--root-motion PATH`：後段位移接續前段終點累加，seam 不瞬移回原點。

組完若有軌道**非全程出現**（如 advance 的 UpperArm 只在 punch 段），缺席段 Godot 會 hold 最近 key。若該 hold 值非靜止會在 seam 突兀，用 `fix-seam` 在頭/尾補靜止 key（**rest 值由你給**，因為 rest pose 在 skeleton 不在動畫檔）：

```bash
python3 anim_compose.py fix-seam examples/fighter.tres advance \
    --hold "Armature/UpperArm:rotation=0.0,Armature/ForeArm:rotation=0.0"
python3 anim_compose.py check-seams examples/fighter.tres advance    # 診斷速度突變/瞬跳
```
`check-seams` 只報告、不修：速度突變無法自動區分「刻意俐落」與「頓挫」，供人眼判斷。

### Step 7 — 組狀態機

最快路徑：**`derive` 一次烘出整張圖**（library 動畫→狀態、metadata `compatible_after`→轉場、Start→起始）：

```bash
python3 anim_tree.py derive examples/combo.tres \
    --lib examples/fighter.tres --meta examples/fighter.anim.meta.json --start idle --reset
```

也可手動增量編輯，或把 Step 6 烘好的連招**一步變成狀態**：

```bash
python3 anim_tree.py add-state      examples/combo.tres guard guard
python3 anim_tree.py add-transition examples/combo.tres idle guard --xfade 0.15 --advance auto --cond do_guard
python3 anim_tree.py set-blend      examples/combo.tres idle punch 0.25
# 招牌：烘連招 + 直接接成狀態（內部複用 anim_compose.concat）
python3 anim_tree.py bake-combo examples/combo.tres --lib examples/fighter.tres \
    --name dash_punch --clips step_in,punch --blend 0.1 --root-motion ".:position"
# 收尾檢查：每個狀態引用的動畫名是否真的存在於 library
python3 anim_tree.py summary examples/combo.tres --lib examples/fighter.tres
```
`add-transition` 的 `--switch immediate|sync|at_end`、`--advance disabled|enabled|auto`、`--cond <條件名>` 對應 Godot 轉場屬性；重生成時只寫非預設值，與編輯器存檔行為一致。

### Step 8 — 產生可在 Godot 載入驗證的場景

```bash
python3 anim_tree.py scaffold-scene examples/state_machine_sample.tres \
    --lib examples/fighter.tres --out examples/fighter_tree.tscn
```
骨架（root + Armature/Torso/UpperArm/ForeArm）**依 library 軌道路徑自動推導**，每個被動畫節點掛小 Polygon2D，接好 AnimationPlayer(掛 lib) + AnimationTree(tree_root=狀態機, active)。把 `.tscn` + 狀態機 `.tres` + library `.tres` 三檔放進 Godot 專案開 `.tscn`：選 AnimationTree 看狀態圖能否載入、按播放看 idle 擺動。

---

## 3. .tres / .tscn 格式重點（供工具與除錯參考）

- AnimationLibrary：`[gd_resource type="AnimationLibrary"]`，每段動畫一個 `[sub_resource type="Animation"]`，`[resource] _data = { &"name": SubResource(...) }` 登錄。value 軌道 `values` 是一般 Array（`[0.0, Vector2(...), {method dict}]`），**不是** PackedFloat32Array。
- AnimationNodeStateMachine：序列化鍵 `states/<名>/node`、`states/<名>/position`、`transitions`（三元組扁平陣列 `[from,to,SubResource,...]`）；Start/End 是內部節點 `AnimationNodeStartState`/`EndState`。完整 reference：`analysis/godot/details/animation_node_state_machine_tres_format.md`。
- 序列化風格：向量分量與 PackedFloat 元素整數不帶 `.0`（`_fmt_real`），value Array 的純量 float 維持 `1.0`——與引擎一致以減少 diff。

## 4. 已知限制與待辦

- **無預覽（先天）**：工具不渲染，最終一定要進 Godot 看。Step 8 的場景就是把這步變雙擊。
- **Phase 3② 狀態機範本目前是逆向合成、未經真機**：首次進 Godot 載入後再存一次、`git diff` 揪版本差異（uid / 屬性排序 / `&""` 寫法），回報後微調生成器。
- **3D 動畫軌道未支援**：標準 3D bone 用 `rotation_3d`/`position_3d`/`scale_3d` 專屬軌道（平坦 PackedFloat，與 value 軌道 dict 不同格式），等真實 `Skeleton3D` 匯出確認格式。SLERP/root motion 邏輯已備好。
- `check-seams` 只診斷不自動修；`fix-seam` 的 rest→首 key 之間仍線性插值（自然預備動作），要硬 hold 需在首 key 前一刻再 `set-key`。

## 5. 一句話總結

讀（inspector）→ 標（metadata）→ 調（inspector / pose）→ 事件（events）→ 烘（compose）→ 組（tree）→ 驗（tree scaffold-scene + Godot）。
每一步都是確定性變換、可反讀驗證、不破壞無關欄位；語意決策留在 session 裏的 Claude。
