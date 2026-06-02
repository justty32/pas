# godot_anim_agent — 進度保存

> 最後更新：2026-05-23。這份是「回來就能接上」的狀態快照。
> 設計理念見 `VISION.md`、`PHASE2_DESIGN.md`；操作流水帳見 `../../analysis/godot/session_log.md`。

## 一句話：這是什麼

用自然語言編輯 Godot 動畫的工作流。**人給意圖 → Claude 翻成精確指令 → Python 工具做確定性變換 → 回 Godot 預覽**。
「agent」是 session 裏的 Claude，不是那幾支 Python（工具不做語意判斷，只做你叫它做的精確操作）。

## 整體狀態

| 階段 | 內容 | 狀態 |
|------|------|------|
| Phase 1 | 單一動畫讀寫 | ✅ 完成 |
| Phase 2 | 動作組合（2D / value 軌道） | ✅ 完成 |
| Phase 3 ① | 動畫事件 / method 軌道 | ✅ 完成 |
| Phase 3 ③ | 程序化擺位 / 2-bone IK | ✅ 完成 |
| Phase 3 ② | AnimationTree / 狀態機 | ✅ 完成（合成範本，**待真機驗證**） |
| 3D 動畫軌道 | rotation_3d/position_3d/scale_3d | ⏸ **阻塞：等使用者匯出** |

## 現有工具（都在本目錄，實測於 `examples/fighter.tres`）

- **`anim_inspector.py`** — 單一動畫讀/改：`summary` / `tracks` / `set-key`（float 與 Vector2/3/4/Quaternion）/ `scale-time` / `offset` / `scale-value`
- **`anim_metadata.py`** — 動畫旁置 metadata：`init` / `show` / `set-tag` / `rm-tag` / `compat`
- **`anim_compose.py`** — 多段組合：`concat`（`--blend` cross-fade，純量/向量線性、Quaternion SLERP；`--root-motion` 位移累加）/ `fix-seam`（`--hold "path=rest值"` 對非全程軌道頭/尾補靜止 key，rest 值由呼叫者給）/ `check-seams`（速度突變/瞬跳診斷）
- **`anim_events.py`** — method 軌道（動畫事件）：`list` / `add`（既有插入或新建軌道）/ `rm` / `scaffold`（產 `.gd` handler 樣板）
- **`anim_pose.py`** — 2-bone IK：`aim`（骨長/基準朝向當參數收，解上臂/前臂 rotation 寫回，FK 反算誤差 0）
- **`anim_tree.py`** — AnimationNodeStateMachine 解析/生成（解析成模型→改→整檔重生成，load_steps 自動重算）：
  - `summary`（加 `--lib` 對 library 交叉檢查狀態引用的動畫名是否存在）/ `add-state` / `rm-state` / `add-transition`（`--xfade`/`--switch`/`--advance`/`--cond`/`--end`）/ `rm-transition` / `set-blend`
  - **`derive`**（招牌：依 library 動畫建狀態 + metadata 的 compatible_after 推導轉場 Y→X + Start→起始）
  - **`bake-combo`**（招牌願景「烘焙連招當狀態」：複用 anim_compose.cmd_concat 把多段連招烘成 library 新動畫＋接成狀態，支援 `--blend`/`--root-motion`）
  - **`scaffold-scene`**（產 .tscn 接線範本：骨架依 library 軌道路徑自動建 Node2D+小 Polygon2D、接好 AnimationPlayer+AnimationTree，讓真機驗證變雙擊）

## 範例素材（`examples/`）

- `fighter.tres` — 2D 格鬥角色，4 段動畫：`idle` / `guard` / `step_in`（前踏 24px）/ `punch`（含 method 軌道 spawn_hit_spark）
- `fighter.anim.meta.json` — 四段的 tags 與 compatible_after
- `fighter_events.gd` — scaffold 示範產物
- `state_machine_sample.tres` — Phase 3 ② 合成範本（idle/punch+Start/End、3 轉場其中 2 條調離預設）；**待真機驗證**
- `combo.tres` — `anim_tree.py derive` 產物示範（吃 fighter.tres+meta 烘出 4 狀態+6 推導轉場+Start→idle）
- `fighter_tree.tscn` — `anim_tree.py scaffold-scene` 產物：可載入驗證的場景（root Node2D + AnimationPlayer 掛 fighter.tres + 自動建的 Armature 骨架 + AnimationTree 接 state_machine_sample.tres）。**這就是真機驗證入口**

## ✅ A. Phase 3 ② AnimationTree（已自行解鎖，待真機驗證）

使用者不便匯出範本，改走「**從引擎原始碼逆向格式**」：
- 格式逐項有據（鍵名來自 `animation_node_state_machine.cpp`、屬性/預設來自官方文件、
  Start/End 為內部類別 `AnimationNodeStartState`/`EndState`）。完整 reference 留檔於
  `../../analysis/godot/details/animation_node_state_machine_tres_format.md`。
- 已生成 `examples/state_machine_sample.tres`（合成）並寫好 `anim_tree.py`，
  load→dump→load round-trip 自洽、`derive` 從 fighter.tres+meta 烘出 `examples/combo.tres` 正常。

**唯一待辦（要你動手，已備好雙擊入口）**：把 `examples/` 的
`fighter_tree.tscn` + `state_machine_sample.tres` + `fighter.tres` 三檔放進你的 Godot 專案
（同層；非根目錄則改 .tscn 裏 ext_resource 的 `res://` 路徑），開 `fighter_tree.tscn`：
1. 選 AnimationTree 節點，看狀態圖能否載入（idle/punch 兩狀態 + 轉場）。
2. 按播放，看 Armature 骨架的 idle 擺動。
3. 在 Godot 再存一次，`git diff fighter_tree.tscn state_machine_sample.tres` 看是否有格式差異
   （uid / 屬性排序 / `&""` 寫法）。
有差異回報，我據此微調 `anim_tree.py` 生成器。**目前格式可信但未經真機。**

## ⏸ B. 3D 動畫軌道支援（仍阻塞）
**需要你給一份含 `Skeleton3D` 動畫的 `.tres`/`.animlib`**（VISION.md「解鎖 3D 所需」有完整步驟）：
重點是看 `rotation_3d`/`position_3d`/`scale_3d` 軌道（平坦 PackedFloat 格式，與 value 軌道 dict 不同）的真實寫法；最好 2 段以上共用骨骼、一段帶根骨骼位移、附 Godot 版本。
→ SLERP cross-fade 與 root motion 累加已備好，拿到格式就能套到 3D。

## 怎麼接上

1. **A（AnimationTree）**：開 Godot 用 `state_machine_sample.tres` 做一次真機載入＋回存驗證（見上）。
   通過就把合成範本換成真機版；不過工具邏輯不受影響，可以直接拿 `anim_tree.py` 來用。
2. **B（3D 軌道）**：仍等你匯出含 `Skeleton3D` 的 `.tres`（兩者獨立、不互擋）。
3. **測試**：尚未寫工具鏈自動化測試（這輪 /loop 下一步要做）；目前各功能皆以 fixture 副本手動實測過。

## 文檔

- 端到端教學：`analysis/godot/tutorial/anim_agent_workflow.md`（讀→標→調→事件→IK→烘→組→驗，指令皆實測）。
- 狀態機格式 reference：`analysis/godot/details/animation_node_state_machine_tres_format.md`。

## 本次 session 的進度（main 分支）

承前（目錄重整 / set-key 向量化 / Phase 2 / Phase 3①③ / 兩份待提供清單）後，本 session：
- **Phase 3 ② 自行逆向格式解鎖**：`anim_tree.py`（9 指令：summary[--lib]/add-state/rm-state/add-transition/rm-transition/set-blend/derive/bake-combo/scaffold-scene）+ 合成 `state_machine_sample.tres` + `combo.tres` + `fighter_tree.tscn` + `details/` 格式 reference。
- **Phase 2 補洞**：`anim_compose fix-seam`（非全程軌道頭/尾補靜止 key，rest 值由呼叫者給）。
- **文檔**：端到端教學 `tutorial/anim_agent_workflow.md`。
- **自動化測試（2026-06-02）**：`tests/` 目錄，6 個測試模組，102 test cases 全綠（unittest discover）。
  覆蓋：inspector（parse/summary/tracks/set-key/scale-time/offset/scale-value）、metadata（init/tag/compat）、compose（concat/blend/root-motion/check-seams/fix-seam）、events（list/add/rm/scaffold）、pose（IK 數學 + cmd_aim）、tree（load/dump/add-rm-state/transition/derive）。

## 接續點

- A. Phase 3 ② 真機驗證：開 Godot 載入 `examples/fighter_tree.tscn` → 確認狀態圖 + 播放 + `git diff`。
- B. 3D 動畫軌道：等含 Skeleton3D 的 `.tres` 匯出。
