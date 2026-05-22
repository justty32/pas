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
| Phase 3 ② | AnimationTree / 狀態機 | ⏸ **阻塞：等使用者範本** |
| 3D 動畫軌道 | rotation_3d/position_3d/scale_3d | ⏸ **阻塞：等使用者匯出** |

## 現有工具（都在本目錄，實測於 `examples/fighter.tres`）

- **`anim_inspector.py`** — 單一動畫讀/改：`summary` / `tracks` / `set-key`（float 與 Vector2/3/4/Quaternion）/ `scale-time` / `offset` / `scale-value`
- **`anim_metadata.py`** — 動畫旁置 metadata：`init` / `show` / `set-tag` / `rm-tag` / `compat`
- **`anim_compose.py`** — 多段組合：`concat`（`--blend` cross-fade，純量/向量線性、Quaternion SLERP；`--root-motion` 位移累加）/ `check-seams`（速度突變/瞬跳診斷）
- **`anim_events.py`** — method 軌道（動畫事件）：`list` / `add`（既有插入或新建軌道）/ `rm` / `scaffold`（產 `.gd` handler 樣板）
- **`anim_pose.py`** — 2-bone IK：`aim`（骨長/基準朝向當參數收，解上臂/前臂 rotation 寫回，FK 反算誤差 0）

## 範例素材（`examples/`）

- `fighter.tres` — 2D 格鬥角色，4 段動畫：`idle` / `guard` / `step_in`（前踏 24px）/ `punch`（含 method 軌道 spawn_hit_spark）
- `fighter.anim.meta.json` — 四段的 tags 與 compatible_after
- `fighter_events.gd` — scaffold 示範產物

## ⏸ 兩個阻塞點（回來時要做的事）

### A. Phase 3 ② AnimationTree（這次卡在這）
**需要你先給一份最小狀態機範本**（VISION.md「解鎖 AnimationTree」有完整步驟）：
1. Godot 加 `AnimationTree` 節點，`Tree Root` = 新 `AnimationNodeStateMachine`，Anim Player 指到含 fighter.tres 者。
2. 放 2 狀態（idle、punch）+ 1~2 轉場。
3. **把一條轉場設定調離預設**（Xfade Time=0.2 / 換 Switch Mode / 填 Advance Condition）。
4. Inspector 對 StateMachine 右鍵 → Save As → `examples/state_machine_sample.tres`（含 `.tscn` 更好）。
5. 告訴我 **Godot 4.x 次版本**。

→ 拿到後我寫 `anim_tree.py`（解析/生成狀態機：`add-state`/`add-transition`/`set-blend`），
讓**烘焙連招當狀態、metadata 的 compatible 關係自動推導成轉場**。

### B. 3D 動畫軌道支援
**需要你給一份含 `Skeleton3D` 動畫的 `.tres`/`.animlib`**（VISION.md「解鎖 3D 所需」有完整步驟）：
重點是看 `rotation_3d`/`position_3d`/`scale_3d` 軌道（平坦 PackedFloat 格式，與 value 軌道 dict 不同）的真實寫法；最好 2 段以上共用骨骼、一段帶根骨骼位移、附 Godot 版本。
→ SLERP cross-fade 與 root motion 累加已備好，拿到格式就能套到 3D。

## 怎麼接上

回來把 **A 的 `state_machine_sample.tres`** 丟進 `examples/` 或貼給我，我就開始寫 `anim_tree.py`。
（B 的 3D 檔有空再說，兩者獨立、不互相擋。）

## 本次 session 的 commit（main 分支）

目錄重整 → set-key 向量化 → Phase 2（設計/concat/cross-fade/root-motion/check-seams/SLERP）
→ Phase 3 ①事件 / ③IK → 兩份「待提供」清單。最後一筆：`4d7079e`（AnimationTree 範本清單）。
