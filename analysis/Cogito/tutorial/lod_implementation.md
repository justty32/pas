# 教學：如何實作 LOD（多層次細節）與可見性管理

在製作大型關卡時，LOD 是維持幀率的關鍵。Godot 4 提供三個層次的工具；本教學說明各層次的適用場景與具體設定。

## 前置知識
- 已閱讀 [Level 3B: NPC 狀態機行為](../architecture/level3_npc_states.md)。
- 瞭解 `VisibleOnScreenNotifier3D` 的基本概念。

---

## 一、自動網格 LOD（Automatic Mesh LOD）

Godot 4 匯入模型時預設自動生成多個精細度版本的網格。距離越遠，使用面數越少的版本。

### 確認匯入設定

1. 在 FileSystem 面板雙擊 `.glb` / `.gltf` 模型。
2. 選擇 **Meshes** 頁籤 → 確認 **Generate LODs** 已勾選。
3. 點擊 **Reimport**（若剛修改設定）。

這是**零程式碼**的最低成本最佳化——只要模型匯入正確，渲染器自動切換。

### 效能微調

```
Project Settings → Rendering → Mesh LOD → LOD Change Hysteresis
```

調小此值會更積極切換 LOD；調大則更保守（避免在邊界距離反覆閃爍）。

---

## 二、可見性範圍（Visibility Range，俗稱 HLOD）

自動 LOD 減少面數，但遠處物件仍然在計算 Draw Call。小物件（石頭、花草、雜物）超過一定距離應完全不渲染。

### 設定步驟

1. 選取場景中的 `MeshInstance3D`（如 `CogitoObject` 容器下的裝飾物件）。
2. Inspector → **Geometry → Visibility Range**：
   - `Begin`：物件開始淡入的最近距離（通常 0）。
   - `End`：物件完全消失的最遠距離（小物件：30~50m；大建築可設 300m）。
   - `Begin Margin` / `End Margin`：過渡區距離（設 3~5m）。Godot 在此使用 Dither 效果平滑淡出，避免物件突然閃現/消失。

### 物件分級建議

| 物件類型 | End 距離 |
|---|---|
| 草叢、小石頭 | 25m |
| 木桶、箱子等小道具 | 40m |
| NPC / 小型建築 | 80m |
| 大型建築 | 不設定（或 500m+）|

---

## 三、NPC 的 AI 與動畫 LOD（腳本控制）

NPC 遠離時不僅應停止渲染，還應停止 AI 計算（`_physics_process`）與骨架動畫（`AnimationTree`）。

### 方案 A：VisibleOnScreenEnabler3D（零程式碼）

在 NPC 根節點下加入 `VisibleOnScreenEnabler3D`：
1. 調整其 AABB 包覆整個 NPC。
2. Inspector 勾選：
   - `Enable Node → Physics Process`（隱藏時暫停 `_physics_process`）
   - `Enable Node → Process`（暫停 `_process`）
3. NPC 離開螢幕視錐後自動暫停，回到視錐後自動恢復。

**適用**：室內場景、關卡設計有明確遮擋的情況。

**限制**：玩家轉身背對 NPC 時 NPC 也被暫停——不適合需要持續模擬的開放世界 NPC。

### 方案 B：距離閾值腳本（開放世界推薦）

在 `cogito_npc.gd` 加入距離 LOD 管理：

```gdscript
# cogito_npc.gd 加入
@export var ai_disable_distance : float = 80.0   # 超過此距離停用完整 AI
@export var anim_disable_distance : float = 40.0  # 超過此距離停用動畫更新

var _player_ref : Node3D = null
var _current_lod : int = 0  # 0=完整, 1=無動畫, 2=無AI


func _ready():
    # ... 原有邏輯 ...
    _player_ref = get_tree().get_first_node_in_group("Player")


func _physics_process(delta: float) -> void:
    # 原有擊退邏輯保持不變
    if knockback_timer > 0:
        knockback_timer -= delta
        velocity = knockback_force
        knockback_force = lerp(knockback_force, Vector3.ZERO, delta * 5)
        move_and_slide()
        return

    # LOD 管理（每幀距離計算）
    _update_lod()

    if _current_lod >= 2:
        return  # 完全停用 AI

    if footsteps_enabled and _current_lod == 0:
        npc_footsteps(delta)


func _update_lod() -> void:
    if not _player_ref or not is_instance_valid(_player_ref):
        _player_ref = get_tree().get_first_node_in_group("Player")
        return

    var dist = global_position.distance_to(_player_ref.global_position)

    if dist > ai_disable_distance:
        if _current_lod != 2:
            _current_lod = 2
            set_physics_process(false)  # 停用 _physics_process
    elif dist > anim_disable_distance:
        if _current_lod != 1:
            _current_lod = 1
            set_physics_process(true)
            if animation_tree:
                animation_tree.active = false  # 停用骨架動畫
    else:
        if _current_lod != 0:
            _current_lod = 0
            if animation_tree:
                animation_tree.active = true
```

**注意**：`set_physics_process(false)` 在當前幀的 `_physics_process` 中呼叫會在**下一幀**生效。`_update_lod()` 放在 `_physics_process` 的最前面即可安全使用。

---

## 四、靜態物件批次渲染（MultiMeshInstance3D）

對於大量重複的靜態裝飾物件（樹木、草叢、石頭），用 `MultiMeshInstance3D` 比單獨放 `MeshInstance3D` 快數十倍：

```gdscript
# terrain_decorator.gd：程序化批次放置
extends Node3D

@export var mesh : Mesh
@export var count : int = 500
@export var spread : float = 50.0

func _ready() -> void:
    var mmi := MultiMeshInstance3D.new()
    var mmesh := MultiMesh.new()
    mmesh.mesh = mesh
    mmesh.transform_format = MultiMesh.TRANSFORM_3D
    mmesh.instance_count = count
    mmi.multimesh = mmesh
    add_child(mmi)

    for i in count:
        var t := Transform3D()
        t.origin = Vector3(
            randf_range(-spread, spread),
            0.0,
            randf_range(-spread, spread)
        )
        t = t.rotated(Vector3.UP, randf() * TAU)
        t = t.scaled(Vector3.ONE * randf_range(0.8, 1.2))
        mmesh.set_instance_transform(i, t)
```

`MultiMeshInstance3D` 同樣支援 **Visibility Range**，可配合遠距離剔除。

---

## 五、驗證清單

| 測試步驟 | 預期結果 |
|---|---|
| 遠離小道具 50m | 物件淡出消失（Visibility Range 生效）|
| 玩家轉身後面向 NPC 走近 | 80m 內 AI 恢復，40m 內動畫恢復 |
| 使用 Profiler → Rendering | 遠離後 DrawCalls 減少 |
| NPC LOD 設定後 | `animation_tree.active = false` 時 NPC 凍住不動 |
| 生成 500 棵樹（MultiMesh）| FPS 比放 500 個 MeshInstance3D 高出數倍 |
