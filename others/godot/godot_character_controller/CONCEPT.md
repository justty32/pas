# 角色 Controller（行為層）

## 定位

`godot_character` / `godot_character_3d` 是**視覺層**（紙娃娃 + 骨骼動畫）。
本目錄是**行為層**：吃命令、沿路徑走、發動畫狀態 signal 給視覺層 hook。

兩者組合 = 完整可用的角色。

## 範圍邊界

本目錄做的：
- **策略單位 controller**：接 `move_along_path(path)` 命令，沿格走、抵達 signal、可中斷
- **動畫狀態 signal**：`state_changed(prev, next)`，狀態定義為 enum（IDLE / MOVING / ATTACKING / DEAD …）
- **2D + 3D 平行雙版**：Node2D / CharacterBody3D 各一支
- **不耦合 mapcore**：路徑由外部給（用 mapcore find_path 或別的尋路器都行）

本目錄**不做**的：
- 動作遊戲 platformer 跳躍 / gravity / dash —— 那是另一個 controller 類型（CharacterBody3D 走跳）。
  若未來需要，新建 `godot_character_platformer/`。
- 攻擊 / 戰鬥邏輯 —— 那是遊戲規則層。
- AI 決策 —— 在 controller 之上的層級。

## 為什麼從策略單位 controller 起手

1. **pas 主線是策略遊戲**（civ-like），單位 controller 是最直接的需求。
2. **mapcore_godot demo 已驗證**過「逐格走」（成本感知 find_path → `_process` 每 0.12s 推一步），
   本檔抽出可拆出版。
3. **與既有模組串接**：
   - `mapcore_godot` 提供路徑（`find_path` 回傳 `Array[Vector2i]`）
   - `godot_camera_rig` 提供 `focus(unit.position)` 跟著走
   - `godot_selection_highlight` 在 selected 狀態變化時套描邊
   - `godot_character` / `_3d`（未做）會訂閱 `state_changed` 切動畫

## 狀態 enum

```gdscript
enum State { IDLE, MOVING, ATTACKING, HURT, DEAD }
```

策略遊戲一個 turn 中通常只走 IDLE / MOVING / DEAD 三狀態；ATTACKING / HURT 留給戰鬥動畫。
視覺層可以 `match state` 切換到對應的 AnimationTree state。

## 信號設計

```
state_changed(prev: State, next: State)   ## 給視覺層切動畫
arrived(at: Vector2i / Vector3)            ## 抵達目的地（path 走完）
step_completed(at: Vector2i / Vector3)     ## 走完一格（給 UI 更新 cost、檢查視野）
path_blocked()                             ## 卡住（前方格不可走，需重新尋路）
```

## 待決定

- [ ] 移動速度單位：每秒幾格 vs 每格幾秒？目前傾向後者（mapcore demo 用 `step_seconds`）。
- [ ] 中斷策略：途中收到新 path 是「立刻切」還是「走完當前格再切」？傾向後者，避免格中央卡住。
- [ ] 平滑插值 vs 瞬移：3D 走一格 0.12s 線性插值看起來比較對；2D 同理。
- [ ] 路徑視覺化（剩餘步數線條）是 controller 內建還是另一個系統？傾向**另一個系統**——
      controller 只暴露 `get_remaining_path()` 讓 UI 層自繪。

---

*記錄時間：2026-05-28*
*狀態：CONCEPT + 2D/3D 基礎實作完成；視覺層銜接待 godot_character* 啟動時對齊*
