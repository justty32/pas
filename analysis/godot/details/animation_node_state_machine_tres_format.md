# AnimationNodeStateMachine `.tres` 序列化格式（逆向確認）

> 用途：`others/godot/godot_anim_agent/anim_tree.py`（Phase 3 ②）解析/生成狀態機的依據。
> 來源：Godot 引擎原始碼 + 官方文件，**非**從真實 Godot 編輯器匯出。詳見文末「可信度」。
> 對應範本：`others/godot/godot_anim_agent/examples/state_machine_sample.tres`。

## 1. 整體骨架

狀態機是一個 `AnimationNodeStateMachine` 資源，掛在 `AnimationTree` 節點的 `tree_root`。
單獨存檔時的 `.tres`：

```
[gd_resource type="AnimationNodeStateMachine" load_steps=N format=3 uid="uid://..."]

[sub_resource type="..." id="..."]   # 每個狀態的節點、每條轉場各一個 sub_resource
...

[resource]
states/<名>/node = SubResource("...")
states/<名>/position = Vector2(x, y)
transitions = ["from", "to", SubResource("..."), ...]
graph_offset = Vector2(x, y)
```

`load_steps` = sub_resource 數 + 1。`anim_tree.py` 重生成時自動重算。

## 2. 序列化鍵（取自引擎 `scene/animation/animation_node_state_machine.cpp`）

`_get_property_list` / `_set` / `_get` 揭露的持久化鍵：

| 鍵 | 型別 | 說明 |
|----|------|------|
| `states/<名>/node` | Object(AnimationNode) | 該狀態的內容節點，存為 `SubResource(...)` |
| `states/<名>/position` | Vector2 | 編輯器圖上座標（純視覺，不影響邏輯） |
| `transitions` | Array | **三元組扁平陣列**：`[from, to, transition, from, to, transition, ...]`，每組 = 來源名(String)、目標名(String)、轉場物件(SubResource) |
| `graph_offset` | Vector2 | 編輯器視窗平移（純視覺） |
| `state_machine_type` | enum | 0=Root / 1=Nested / 2=Grouped；經 `_set`/`_get` 處理，預設 Root 通常不寫出 |

## 3. 特殊節點：Start / End

「Start」「End」不是抽象概念，而是**真實的內部節點類別**
（PR godotengine/godot#102433 證實它們以 internal 形式存在）：

- `AnimationNodeStartState` — 入口，存為 `states/Start/node`
- `AnimationNodeEndState` — 出口（巢狀狀態機才實際有用），`states/End/node`

兩者皆無屬性，sub_resource 區塊是空的。轉場用名字 `"Start"` / `"End"` 引用它們。

## 4. 狀態內容節點：`AnimationNodeAnimation`

最常見的葉狀態，播一段 AnimationPlayer 裏的動畫：

```
[sub_resource type="AnimationNodeAnimation" id="..."]
animation = &"idle"
```

`animation` 是 **StringName**（寫作 `&"名"`）。其餘屬性與預設：
`play_mode`=0(forward)、`advance_on_start`=false、`use_custom_timeline`=false、
`loop_mode` / `start_offset` / `timeline_length` / `stretch_time_scale`。

> ⚠ 動畫名取決於 AnimationPlayer 怎麼掛 AnimationLibrary：
> 掛成**不具名（預設）library** → 直接 `&"idle"`；
> 掛成**具名 library**（如 "fighter"）→ 需 `&"fighter/idle"`。
> `anim_tree.py derive --libname fighter` 可自動加前綴。

## 5. 轉場：`AnimationNodeStateMachineTransition`

每條轉場一個 sub_resource。屬性與預設值（取自官方類別文件）：

| 屬性 | 型別 | 預設 | 友善名（anim_tree.py） |
|------|------|------|------|
| `xfade_time` | float | `0.0` | `--xfade` |
| `xfade_curve` | Curve | （無） | — |
| `switch_mode` | enum | `0` | `--switch immediate(0)/sync(1)/at_end(2)` |
| `advance_mode` | enum | `1` | `--advance disabled(0)/enabled(1)/auto(2)` |
| `advance_condition` | StringName | `&""` | `--cond` |
| `advance_expression` | String | `""` | — |
| `break_loop_at_end` | bool | `false` | — |
| `reset` | bool | `true` | — |
| `priority` | int | `1` | — |

`anim_tree.py` 重生成時**只寫出非預設屬性**，與 Godot 編輯器存檔行為一致（減少 diff 噪音）。

## 6. 完整最小範本

見 `examples/state_machine_sample.tres`：2 個動畫狀態（idle/punch）+ Start/End，
3 條轉場，其中 `idle→punch` 與 `punch→idle` 刻意調離預設（xfade/switch_mode/advance_mode/condition），
用來驗證 `anim_tree.py` 能正確讀出非預設值。

## 7. 可信度與待驗證

此格式由**引擎原始碼（鍵名）+ 官方文件（屬性/預設）+ 已知內部類別**三方交叉確認，
逐項有據；`anim_tree.py` 的 load→dump→load round-trip 自洽。

但範本是**合成的，未經真實 Godot 編輯器匯出/載入**。建議使用者下次開 Godot 時：
1. 把 `state_machine_sample.tres` 指給某個 `AnimationTree.tree_root` 看能否載入；
2. 在編輯器再存一次，`git diff` 比對是否有格式差異（如 uid、屬性排序、額外鍵）。
若有差異回報，據此微調 `anim_tree.py` 的生成器即可。
