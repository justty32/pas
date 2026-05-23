# 3D 角色系統：Skeleton3D 紙娃娃 + glTF 骨骼動畫

## 目標

在 Low Poly 3D 策略遊戲中，用 **單一骨架 + BoneAttachment3D 掛載可換裝 MeshInstance3D** 構成角色，達成：

- 一套骨骼動畫（idle / walk / attack）驅動所有裝備外觀，換裝不需重做動畫。
- 換裝 = 替換對應槽位 `MeshInstance3D.mesh`，由骨骼自動帶動位移與旋轉。
- 材質變體（鐵 / 鋼 / 紫晶）直接靠 `material_override`，免自訂 shader（對接 [[gdextension_material_3d]] 的 MaterialLibrary）。
- 角色部件可由 GDExtension 程序生成 low poly mesh（對接 [[gdextension_procgen_mesh]]）。

與 2D 版 [[gdextension_character_2d]] 概念一致，差異在「工具鏈更成熟、材質天生支援、但動畫資產走 glTF 匯入而非 anim_agent」（見下方「與動畫整合」）。

概念來源：`others/godot/godot_character_3d/CONCEPT.md`。

---

## 原始碼位置

引擎類別 API 以 `projects/godot-cpp/gdextension/extension_api.json`（Godot Engine v4.6.stable.official）為準；GDExtension C++ 標頭為生成式，編譯後位於 `projects/godot-cpp/include/godot_cpp/classes/<class>.hpp`（本倉庫尚未生成，類別/方法名以 JSON 為準）。

- 概念來源：`others/godot/godot_character_3d/CONCEPT.md`
- 對應 2D 版：[[gdextension_character_2d]]（`analysis/godot/tutorial/gdextension_character_2d.md`）
- 材質系統：[[gdextension_material_3d]]（`analysis/godot/tutorial/gdextension_material_3d.md`）；既有 MaterialLibrary 實作 `others/gamecore/mapcore_godot/demo/scenes/material_library.gd`
- 程序生成部件：[[gdextension_procgen_mesh]]；C++ 實作 `others/gamecore/mapcore_godot/src/procgen_mesh_builder.cpp`（`generate_rock()` / `generate_tree_trunk()` / `generate_tree_foliage()`）
- MultiMesh 範例：`others/gamecore/mapcore_godot/demo/scenes/biome_scatter.gd`（3D `MultiMesh.set_instance_transform` GPU instancing）
- 引擎核心類別（皆來自 extension_api.json）：
  - `Skeleton3D`（inherits `Node3D`）：`get_bone_count()` / `find_bone(String) -> int` / `get_bone_global_pose(int) -> Transform3D` / `set_bone_pose_rotation(int, Quaternion)` / `reset_bone_poses()`
  - `BoneAttachment3D`（inherits `Node3D`）：`set_bone_name(String)` / `set_bone_idx(int)` / `set_use_external_skeleton(bool)` / `set_external_skeleton(NodePath)`
  - `MeshInstance3D`（inherits `GeometryInstance3D`）：`set_mesh(Mesh)` / `set_surface_override_material(int, Material)` / `get_surface_override_material_count()`；`GeometryInstance3D.set_material_override(Material)`
  - `AnimationTree` / `AnimationMixer`：`set_tree_root(AnimationRootNode)` / `set_active(bool)` / `set_callback_mode_process(int)` / `set_root_motion_track(NodePath)` / `get_root_motion_position() -> Vector3`
  - `StandardMaterial3D`（inherits `BaseMaterial3D`）：`set_albedo(Color)` / `set_texture(int, Texture2D)` / `set_emission(Color)`
  - `MultiMeshInstance3D` / `MultiMesh`：`set_instance_transform(int, Transform3D)` / `set_instance_count(int)` / `set_use_colors(bool)`
  - glTF 匯入：`GLTFDocument` / `GLTFState`（執行期載入 `.glb`）；編輯期由匯入器自動展開為含 `Skeleton3D` + `AnimationPlayer` 的繼承場景
  - IK（路線見「待決定」）：`SkeletonIK3D`（FABRIK，**已標記為舊路線**）、`SkeletonModifier3D`（4.3+ 新框架基底）、`LookAtModifier3D`（瞄準）

---

## 資產管線

```
Blender（建模 + 骨骼綁定 + 動畫）
   └─ 匯出 .glb（含 mesh + skeleton + animations）
      └─ Godot 匯入器自動展開為繼承場景：
         CharacterRoot (Node3D)            ← 角色腳本 character_3d.gd 掛此（或繼承自匯入場景）
         ├── AnimationPlayer               ← .glb 內的動畫（idle / walk / attack）
         ├── AnimationTree                 ← tree_root = AnimationNodeStateMachine
         └── Skeleton3D                    ← .glb 骨架
             ├── MeshInstance3D [基底身體]  ← 隨 skeleton 蒙皮的角色本體
             ├── BoneAttachment3D [Hand_R] → MeshInstance3D [weapon_main]   ← 武器槽
             ├── BoneAttachment3D [Head]   → MeshInstance3D [helmet_slot]   ← 頭盔槽
             ├── BoneAttachment3D [Chest]  → MeshInstance3D [armor_chest]   ← 胸甲槽
             └── BoneAttachment3D [Thigh_L]→ MeshInstance3D [armor_leg_L]   ← 腿甲槽
```

Low poly 角色的 Blender 工作量遠小於寫實風格：軀幹四肢用基本幾何體稍加調整、幾百個 poly、UV unwrap 簡單即可。骨架本體（含蒙皮的基底 mesh）由 `.glb` 帶入；裝備槽則是**執行期掛在骨上的獨立 mesh**，不蒙皮，靠 `BoneAttachment3D` 跟隨骨骼剛體運動。

---

## 核心設計

設計三原則（與 2D 版同構，換成 3D 語彙）：

1. **一骨架多槽**：每個掛點是 `BoneAttachment3D`（綁定某根骨），其下掛一個 `MeshInstance3D` 當裝備槽。基底身體 mesh 蒙皮在 `Skeleton3D` 上隨骨變形；裝備 mesh 只跟隨掛點骨的全域 transform（剛體跟隨，不蒙皮）——這對劍、盾、頭盔這類硬物正合適。
2. **換裝只改 mesh**：換裝邏輯永遠不碰 transform，`BoneAttachment3D` 每幀自動把對應骨的 pose 抄到子節點。
3. **材質變體靠 override**：同一把劍 mesh，套不同 `material_override` 即鐵 / 鋼 / 紫晶——3D 材質是 Godot 原生設計，無需自訂 shader（這是相對 2D 的關鍵省力處）。

> `BoneAttachment3D` 需正確指定 `bone_name`（內部轉 `bone_idx`）。若掛點與被蒙皮的基底 mesh 不在同一 `Skeleton3D` 下，要開 `use_external_skeleton` 並設 `external_skeleton` 指向骨架。

---

## 實作細節

### 1. 裝備槽宣告與紙娃娃換裝

把每個 `BoneAttachment3D` 下的 `MeshInstance3D` 集中成槽位表。換裝只設 `mesh`；卸下設 `null`。

```gdscript
# character_3d.gd（節錄）— 槽位表 + 換裝 API
extends Node3D

@onready var slots := {
    "weapon_main": $Skeleton3D/Hand_R_Attach/weapon_main,
    "helmet":      $Skeleton3D/Head_Attach/helmet_slot,
    "armor_chest": $Skeleton3D/Chest_Attach/armor_chest,
    "armor_leg_L": $Skeleton3D/Thigh_L_Attach/armor_leg_L,
}

func equip(slot_name: String, mesh: Mesh) -> void:
    var mi: MeshInstance3D = slots.get(slot_name)
    if mi == null:
        push_warning("未知槽位：%s" % slot_name)
        return
    mi.mesh = mesh                         # MeshInstance3D.set_mesh

func unequip(slot_name: String) -> void:
    var mi: MeshInstance3D = slots.get(slot_name)
    if mi:
        mi.mesh = null                     # null = 該槽不繪製
```

`Skeleton3D` 播放揮砍動畫旋轉 `Hand_R` 骨時，掛在 `Hand_R_Attach` 下的 `weapon_main` 會被 `BoneAttachment3D` 每幀同步——這正是紙娃娃的核心：**動畫只認骨骼，不認裝備**，換任何武器都共用同一套動畫。

### 2. 材質變體（對接 [[gdextension_material_3d]]）

3D 換裝比 2D 直觀——直接用 `material_override`（覆蓋整個 mesh）或 `surface_override_material`（逐 surface，劍刃 / 劍柄分材質）：

```gdscript
# character_3d.gd（節錄）— 同一 mesh 套不同材質 → 鐵劍 / 鋼劍 / 紫晶劍
func set_weapon_quality(quality: int) -> void:
    var mi: MeshInstance3D = slots["weapon_main"]
    mi.material_override = MaterialLibrary.get_material(quality)   # 共用快取，見 material_library.gd

# 多 surface：劍刃用金屬、劍柄用皮革
func set_weapon_two_tone(blade_mat: Material, handle_mat: Material) -> void:
    var mi: MeshInstance3D = slots["weapon_main"]
    mi.set_surface_override_material(0, blade_mat)
    mi.set_surface_override_material(1, handle_mat)
```

材質快取沿用既有 `material_library.gd`（靜態工廠 + 快取，見 [[gdextension_material_3d]]）。稀有度色調用 `StandardMaterial3D.set_albedo()` tint 或 `set_emission()` 微光，與材質本體正交，組合不爆增。

### 3. 與動畫整合（glTF 匯入 → AnimationTree）

**重要差異（相對 2D）**：本系統的 3D 動畫資產走 **`.glb` 匯入**，由匯入器自動建 `AnimationPlayer` + `Skeleton3D`，再掛 `AnimationTree` 管狀態切換。anim_agent 工具鏈的 **3D 軌道（`rotation_3d` / `position_3d` / `scale_3d`）目前阻塞**（見 `others/godot/godot_anim_agent/progress.md` 的「⏸ B」：等使用者匯出含 `Skeleton3D` 的 `.tres` 以逆向平坦 `PackedFloat` 軌道格式）。因此**現階段 3D 角色動畫不經 anim_agent**，直接用 Blender / glTF 製作。

```gdscript
# character_3d.gd（節錄）— AnimationTree 狀態切換 + root motion
@onready var anim_tree: AnimationTree = $AnimationTree

func _ready() -> void:
    anim_tree.active = true                              # AnimationMixer.set_active
    anim_tree.set_root_motion_track("Skeleton3D:Hip")    # Hip 位移驅動角色移動

func attack() -> void:
    var sm = anim_tree.get("parameters/playback")        # AnimationNodeStateMachinePlayback
    sm.travel("attack")

func _physics_process(_d: float) -> void:
    # 把動畫的 root motion 套到角色實際位移
    var rm := anim_tree.get_root_motion_position()       # Vector3（本幀位移）
    global_translate(global_transform.basis * rm)
```

> 待 anim_agent 的 3D 軌道解鎖後（progress.md「⏸ B」一旦拿到格式），其 cross-fade SLERP 與 root-motion 累加已備好，即可把 2D 的離線連招烘焙流程套到 3D；在此之前，連招組合請在 Blender / Godot `AnimationTree` 內完成。

### 4. 程序生成角色部件（對接 [[gdextension_procgen_mesh]]）

不想手工建模時，用 GDExtension 程序生成 low poly 部件 mesh，骨架仍由 Blender（或固定模板）提供——**程序生成的是表面 mesh，不是骨骼**：

| 部件 | 程序生成方式 | 既有可借鑑實作 |
|-----|------------|--------------|
| 軀幹 | 拉伸橢球 + noise 擾動 | `procgen_mesh_builder.cpp::generate_rock()`（UV sphere + 位移）|
| 四肢 | Cylinder + 隨機粗細 | 同上的非均勻 XYZ 縮放 |
| 武器 | 程序幾何（劍＝扁平六面體、錘＝圓柱＋球）| `generate_tree_trunk()` 的稜柱思路 |

---

## GDScript 使用範例

```gdscript
# 遊戲層：生成一個全裝備騎士
func spawn_knight() -> Node3D:
    var knight := preload("res://characters/character_3d.tscn").instantiate() as Node3D
    add_child(knight)

    knight.equip("armor_chest", preload("res://art/armor/chest.mesh"))
    knight.equip("helmet",      preload("res://art/armor/helm.mesh"))
    knight.equip("weapon_main", preload("res://art/weapons/sword.mesh"))
    knight.set_weapon_quality(3)                    # 紫晶材質（MaterialLibrary 快取）

    knight.get_node("AnimationTree").active = true  # 進入 idle 狀態機
    return knight
```

---

## 場景設置（.tscn 結構示意）

> 多數情況直接以匯入的 `.glb` 繼承場景為基礎，再加裝備槽 `BoneAttachment3D`。

```
[gd_scene load_steps=3 format=3]

[ext_resource type="Script"     path="res://characters/character_3d.gd" id="1"]
[ext_resource type="PackedScene" path="res://art/knight_base.glb"        id="2"]  ; 含 Skeleton3D + AnimationPlayer

[node name="CharacterRoot" instance=ExtResource("2")]
script = ExtResource("1")

[node name="AnimationTree" type="AnimationTree" parent="."]
anim_player = NodePath("../AnimationPlayer")
active = true

; 裝備槽：掛在匯入骨架的對應骨上
[node name="Hand_R_Attach" type="BoneAttachment3D" parent="Skeleton3D"]
bone_name = "Hand_R"
[node name="weapon_main" type="MeshInstance3D" parent="Skeleton3D/Hand_R_Attach"]

[node name="Head_Attach" type="BoneAttachment3D" parent="Skeleton3D"]
bone_name = "Head"
[node name="helmet_slot" type="MeshInstance3D" parent="Skeleton3D/Head_Attach"]
```

---

## 2D vs 3D 角色系統對照

| 面向 | 2D（[[gdextension_character_2d]]）| 3D（本文）|
|-----|----|----|
| 槽位載體 | `Bone2D` 下多層 `Sprite2D` + z_index | `BoneAttachment3D` + `MeshInstance3D` |
| 換裝 | 替換 `Sprite2D.texture` | 替換 `MeshInstance3D.mesh` |
| 材質變體 | **需自訂 canvas_item shader**（[[gdextension_material_2d]]）| `material_override`，**原生** |
| 動畫資產 | anim_agent 工具鏈（2D 全綠）| **glTF 匯入**（anim_agent 3D 軌道阻塞中）|
| 程序生成 | 逐像素 `Image`（[[gdextension_procgen_art]]）| 逐頂點 `ArrayMesh`（[[gdextension_procgen_mesh]]）|
| 高低差 / 燈光 | 偽 2.5D，需手繪 | 幾何 + 燈光天生（見 [[2d_vs_lowpoly_tradeoff]]）|

---

## 效能 / 已知限制

- **同款士兵大量同屏**：完全相同裝備的單位用 `MultiMeshInstance3D` + `MultiMesh`（`biome_scatter.gd` 有現成 `set_instance_transform` GPU instancing 模式），但 **MultiMesh 不支援逐實例骨骼動畫**，僅適合靜止 / 共用單姿勢的遠景兵團。
- **BoneAttachment3D 成本**：每個掛點每幀抄一次骨 pose；數十槽 × 數百單位時，遠景單位應降為「不換裝的合併 mesh」LOD。
- **動畫路線現況**：3D 連招組合暫時無法用 anim_agent 離線烘焙（3D 軌道阻塞），需在 Blender / `AnimationTree` 內完成；2D 版則可全程用工具鏈。
- **蒙皮 vs 剛體掛載**：硬物（劍、盾、頭盔）用 `BoneAttachment3D` 剛體跟隨即可；需要隨身體變形的軟質裝備（披風、長袍）需另行蒙皮到同一 `Skeleton3D`，成本較高。

---

## 待決定

逐項回應 `others/godot/godot_character_3d/CONCEPT.md` 的待決定清單：

- **角色基底：Blender 手工 low poly vs 完全程序生成 mesh？**
  - **建議：基底身體以 Blender 模板（含骨架與蒙皮）為主，部件可程序生成。** 理由：蒙皮權重（skin weights）程序生成困難且易出錯，手工模板一次做好可重用；而劍、盾、岩石飾物這類**剛體部件**用 [[gdextension_procgen_mesh]] 程序生成最划算（無需蒙皮，掛 `BoneAttachment3D` 即可）。先程序生成部件解鎖「無限變體」，基底身體留給模板。

- **是否需要 IK（腳踩地面 / 手持物件）？**
  - **建議：預設離線 / glTF 內製作姿勢，執行期 IK 限縮到必要場景。** 理由：Godot 4.6 的 3D IK 處於 API 轉換期——`SkeletonIK3D`（FABRIK）已標記為舊路線，新框架 `SkeletonModifier3D`（4.3+）尚需自寫 2-bone 修改器或用 `LookAtModifier3D` 做瞄準。策略遊戲鏡頭較遠、地面多為格子平面，腳踩地面視覺收益有限。「斜坡踩地 / 滑鼠跟隨瞄準」才掛 `LookAtModifier3D` 或自訂 `SkeletonModifier3D`；其餘用動畫資產內既有姿勢。

- **多角色同屏效能：MultiMesh + GPU instancing？**
  - **建議：分 LOD——近景完整骨架角色、遠景 `MultiMeshInstance3D` 合併 mesh（共用單姿勢）。** 理由：MultiMesh 無逐實例骨骼動畫，只能播共用姿勢，適合遠景兵團（沿用 `biome_scatter.gd` 模式）。主要 / 近景單位仍用完整 `Skeleton3D` + 換裝槽。切換門檻按螢幕佔比（與 [[gdextension_camera_rig]] 的 `get_zoom_normalized()` 聯動）。

- **面部表情：Shape Key（Blend Shape）vs 獨立 mesh 替換？**
  - **建議：Low Poly 風格用「獨立 mesh / 貼圖替換」即可，暫不上 Blend Shape。** 理由：icon 級 low poly 臉部細節低，表情用「換一張臉貼圖或換一個嘴部 mesh」成本最低、效果足；Blend Shape 需 Blender 製作多組形狀且增加蒙皮成本，留待確有近景特寫需求再導入。

---

*記錄時間：2026-05-23*
*狀態：概念補完為實作教學；API 對齊 Godot v4.6.stable（extension_api.json）；對應 2D 版 [[gdextension_character_2d]]。注意：3D 動畫軌道於 anim_agent 仍阻塞，本系統動畫走 glTF 匯入*
