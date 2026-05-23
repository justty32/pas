# 2D 角色系統：Skeleton2D 紙娃娃 + 骨骼動畫

## 目標

在 2D 策略遊戲中，用 **單一骨架 + 可換裝 Sprite2D 疊層** 構成角色，達成：

- 一套骨骼動畫（idle / walk / attack）驅動所有裝備外觀，換裝不需重做動畫。
- 換裝 = 替換對應槽位 Sprite2D 的 `texture`，由骨骼自動帶動位移與旋轉。
- 同一張「基底形狀」貼圖，透過材質疊加 shader 呈現鐵 / 鋼 / 紫晶等變體（對接 [[godot_material]]）。
- 動畫資產由 anim_agent 工具鏈（`anim_inspector.py` / `anim_compose.py` / `anim_tree.py`）以自然語言離線編輯，工具產出的 `.tres` / `.tscn` 可直接掛進本系統。

概念來源：`others/godot/godot_character/CONCEPT.md`。

---

## 原始碼位置

引擎類別 API 以 `projects/godot-cpp/gdextension/extension_api.json`（Godot Engine v4.6.stable.official）為準；GDExtension C++ 標頭路徑為生成式，編譯後位於 `projects/godot-cpp/include/godot_cpp/classes/<class>.hpp`（本倉庫尚未生成，類別/方法名以 JSON 為準）。

- 概念來源：`others/godot/godot_character/CONCEPT.md`
- 材質複用 shader：`others/godot/godot_material/CONCEPT.md`（[[godot_material]]）
- 染色 shader 範例：`analysis/godot/tutorial/gdextension_2d_dyeing_system.md`
- 動畫工具鏈：`others/godot/godot_anim_agent/progress.md`、`analysis/godot/tutorial/anim_agent_workflow.md`
- 引擎核心類別（皆來自 extension_api.json）：
  - `Skeleton2D`（inherits `Node2D`）：`get_bone_count()` / `get_bone(int) -> Bone2D` / `get_skeleton() -> RID` / `set_modification_stack(SkeletonModificationStack2D)` / `set_bone_local_pose_override(int, Transform2D, float, bool)`
  - `Bone2D`（inherits `Node2D`）：`set_rest(Transform2D)` / `apply_rest()` / `get_index_in_skeleton() -> int` / `set_length(float)` / `set_bone_angle(float)`
  - `Sprite2D`（inherits `Node2D`）：`set_texture(Texture2D)` / `set_offset(Vector2)` / `set_centered(bool)` / `set_region_enabled(bool)`
  - `CanvasItem`（Sprite2D 祖先）：`set_z_index(int)` / `set_z_as_relative(bool)` / `set_self_modulate(Color)` / `set_material(Material)`
  - IK：`SkeletonModificationStack2D`（inherits `Resource`）、`SkeletonModification2DTwoBoneIK` / `SkeletonModification2DFABRIK` / `SkeletonModification2DCCDIK`

---

## 核心設計

```
CharacterRoot (Node2D)              ← 角色腳本 character_2d.gd 掛此
├── AnimationPlayer                 ← 載入 anim_agent 產出的 fighter.tres
├── AnimationTree                   ← tree_root = AnimationNodeStateMachine（combo.tres）
└── Skeleton2D                      ← 骨架根
    └── Bone2D [Hip]
        ├── Bone2D [Torso]
        │   ├── Sprite2D [torso_base]        z_index 0   ← 軀幹基底（裸體層）
        │   ├── Sprite2D [armor_chest]       z_index 10  ← 裝備槽：胸甲（texture=null 即未裝備）
        │   ├── Sprite2D [armor_chest_detail]z_index 11  ← 材質/紋章疊加層
        │   ├── Bone2D [UpperArm_R]
        │   │   └── Bone2D [ForeArm_R]
        │   │       └── Bone2D [Hand_R]
        │   │           ├── Sprite2D [hand_base]    z_index 5
        │   │           └── Sprite2D [weapon_main]  z_index 30 ← 主手武器槽
        │   └── Bone2D [UpperArm_L] ...
        ├── Bone2D [Thigh_R] → Bone2D [Shin_R] → Sprite2D [leg_armor_R]
        └── Bone2D [Thigh_L] ...
```

設計三原則：

1. **一骨架多槽**：每個身體部位的 `Bone2D` 下可掛多個 `Sprite2D`，分為「基底層」（裸體 / 永遠存在）與「裝備槽」（可換、可空）。
2. **換裝只改 texture**：裝備邏輯永遠不碰 transform，骨骼動畫自動帶動 Sprite2D 隨骨旋轉。
3. **疊層靠 z_index**：同一骨下的前後關係由 `CanvasItem.set_z_index()` 決定，與場景樹順序解耦，方便程式碼動態調整。

---

## 實作細節

### 1. 骨骼結構與 rest pose

`Bone2D` 不是普通 `Node2D`：它的 `rest` 透過 `set_rest(Transform2D)` 設定「靜止姿勢」，動畫軌道寫的是相對 rest 的偏移。手動建骨時務必呼叫 `apply_rest()` 讓當前 transform 落到 rest，否則動畫播放起點會錯位。`get_index_in_skeleton()` 回傳該骨在 `Skeleton2D` 內的索引，IK 與 pose override 都用這個索引定位。

```gdscript
# character_2d.gd（節錄）— 程式化建立或校正骨架
extends Node2D

@onready var skeleton: Skeleton2D = $Skeleton2D

func _ready() -> void:
    # 走訪所有 Bone2D，確保 rest 已套用（手工拼場景時的保險）
    _apply_rest_recursive(skeleton)

func _apply_rest_recursive(node: Node) -> void:
    for child in node.get_children():
        if child is Bone2D:
            child.apply_rest()      # 將當前 transform 設為 rest pose
        _apply_rest_recursive(child)
```

### 2. 裝備槽宣告與紙娃娃換裝

把每個槽位用 `@onready` 或一個 Dictionary 集中管理。換裝時只設 `texture`；卸下時設 `null`（`Sprite2D.set_texture(null)` 即不繪製）。

```gdscript
# character_2d.gd（節錄）— 槽位表 + 換裝 API
@onready var slots := {
    "torso":      $Skeleton2D/Hip/Torso/armor_chest,
    "torso_dtl":  $Skeleton2D/Hip/Torso/armor_chest_detail,
    "weapon_main":$Skeleton2D/Hip/Torso/UpperArm_R/ForeArm_R/Hand_R/weapon_main,
    "leg_R":      $Skeleton2D/Hip/Thigh_R/Shin_R/leg_armor_R,
}

func equip(slot_name: String, texture: Texture2D, z: int = -1) -> void:
    var sprite: Sprite2D = slots.get(slot_name)
    if sprite == null:
        push_warning("未知槽位：%s" % slot_name)
        return
    sprite.texture = texture
    if z >= 0:
        sprite.z_index = z          # CanvasItem.set_z_index：動態調整疊層

func unequip(slot_name: String) -> void:
    var sprite: Sprite2D = slots.get(slot_name)
    if sprite:
        sprite.texture = null       # null = 該槽不繪製
```

骨骼動畫旋轉 `Hand_R` 時，掛在其下的 `weapon_main` Sprite2D 會一起被帶動——這正是紙娃娃的核心：**動畫只認骨骼，不認裝備**，所以換任何武器都共用同一套揮砍動畫。

### 3. 材質疊加（基底形狀 + 材質層）— 對接 [[godot_material]]

裝備槽 Sprite2D 的 `texture` 只放「灰階基底形狀」，真正的鐵 / 鋼 / 紫晶外觀由 `ShaderMaterial` 的 uniform 決定。shader 用 `others/godot/godot_material/CONCEPT.md` 的 `sprite_material.gdshader`（multiply / additive / screen 三種 blend）。

```gdscript
# character_2d.gd（節錄）— 換裝同時套材質變體
const MAT_SHADER := preload("res://shaders/sprite_material.gdshader")

func equip_with_material(slot_name: String, base_tex: Texture2D,
                         material_tex: Texture2D, strength := 1.0) -> void:
    var sprite: Sprite2D = slots[slot_name]
    sprite.texture = base_tex                       # 形狀：灰階基底
    if sprite.material == null:
        var mat := ShaderMaterial.new()
        mat.shader = MAT_SHADER
        sprite.material = mat                        # CanvasItem.set_material
    sprite.material.set_shader_parameter("material_tex", material_tex)
    sprite.material.set_shader_parameter("material_strength", strength)
    sprite.material.set_shader_parameter("blend_mode", 0)  # 0 = Multiply 染色
```

稀有度色調可用 shader uniform，或更輕量地直接用 `CanvasItem.set_self_modulate(Color)`（不影響子節點，只染本 Sprite）：

```gdscript
sprite.self_modulate = Color(1.0, 0.84, 0.0)   # 傳奇金色快速 tint
```

### 4. 與動畫整合（AnimationPlayer / AnimationTree）

動畫只對 `Bone2D` 的屬性製作 value track，**不碰任何 Sprite2D**：

- `NodePath:rotation` — 各骨旋轉（2D 用單一 float 弧度）。
- 進階：`Skeleton2D` 根骨 `position` 做 root motion 驅動角色位移。

`AnimationTree` 用 `set_tree_root(AnimationRootNode)` 掛 `AnimationNodeStateMachine` 管理 idle / walk / attack 的切換與 cross-fade。播放回呼模式由祖先類別 `AnimationMixer.set_callback_mode_process()` 控制（physics vs idle）。

```gdscript
# character_2d.gd（節錄）— 觸發攻擊狀態
@onready var anim_tree: AnimationTree = $AnimationTree

func _ready() -> void:
    anim_tree.active = true                          # AnimationMixer.set_active

func attack() -> void:
    var sm = anim_tree.get("parameters/playback")    # AnimationNodeStateMachinePlayback
    sm.travel("punch")                               # 走到 punch 狀態（含轉場 cross-fade）
```

### 5. IK（選用，腳踩地面 / 手持物件）

`Skeleton2D.set_modification_stack(SkeletonModificationStack2D)` 掛一條修改鏈，鏈內加 `SkeletonModification2DTwoBoneIK`（兩骨關節，最適合手臂 / 小腿）。Two-bone IK 用 `set_joint_one_bone2d_node()` / `set_joint_two_bone2d_node()` 指定上下骨，`set_target_node()` 指向目標 `Node2D`。

```gdscript
# character_2d.gd（節錄）— 程式化建立右腳的 Two-bone IK
func setup_foot_ik(thigh: Bone2D, shin: Bone2D, target_path: NodePath) -> void:
    var stack := SkeletonModificationStack2D.new()
    var ik := SkeletonModification2DTwoBoneIK.new()
    ik.set_target_node(target_path)
    ik.set_joint_one_bone2d_node(thigh.get_path())   # 大腿
    ik.set_joint_two_bone2d_node(shin.get_path())    # 小腿
    stack.add_modification(ik)
    skeleton.set_modification_stack(stack)
    # 注意：set_modification_stack 後引擎在 _process 自動 execute；
    # 若手動驅動可呼叫 skeleton.execute_modifications(delta, 0)
```

> 提醒：`SkeletonModification2D` 系列在 Godot 4.x 仍可用，但官方已標記為偏舊路線（2D IK 的後續演進不如 3D 的 `SkeletonModifier3D` 體系活躍）。腳踩地面 / 手持物件這類「少量、可預期」的需求，用 anim_agent 的 `anim_pose.py aim`（2-bone IK 離線烘進動畫，FK 反算誤差 0）通常比執行期 IK 更穩、更可控——見下方「與 anim_agent 銜接」。

---

## GDScript 使用範例

```gdscript
# 遊戲層：生成一個全裝備角色
func spawn_knight() -> Node2D:
    var knight := preload("res://characters/character_2d.tscn").instantiate() as Node2D
    add_child(knight)

    # 換上鋼製胸甲（基底形狀 + 鋼材質層）
    knight.equip_with_material(
        "torso",
        preload("res://art/armor/chest_base.png"),       # 灰階基底
        preload("res://art/materials/steel.png"),         # 鋼材質
        1.0
    )
    # 換上一把劍（共用劍型基底，套紫晶材質）
    knight.equip_with_material(
        "weapon_main",
        preload("res://art/weapons/sword_base.png"),
        preload("res://art/materials/amethyst.png"),
        1.0
    )
    # 傳奇品質：再疊一層金色 tint
    knight.slots["weapon_main"].self_modulate = Color(1.0, 0.84, 0.0)

    # 播放待機 → 工具鏈烘出的狀態機接管
    knight.get_node("AnimationTree").active = true
    return knight
```

---

## 場景設置（.tscn 結構示意）

> 本節僅為示意；實際請在 Godot 編輯器內建立，或由 anim_agent 的 `anim_tree.py scaffold-scene` 自動產骨架接線後再補裝備槽。

```
[gd_scene load_steps=4 format=3]

[ext_resource type="Script"    path="res://characters/character_2d.gd" id="1"]
[ext_resource type="Animation" path="res://anim/fighter.tres"          id="2"]  ; anim_agent 產
[ext_resource type="Resource"  path="res://anim/combo.tres"            id="3"]  ; AnimationNodeStateMachine

[node name="CharacterRoot" type="Node2D"]
script = ExtResource("1")

[node name="AnimationPlayer" type="AnimationPlayer" parent="."]
; libraries 指向 fighter.tres 內的動畫

[node name="AnimationTree" type="AnimationTree" parent="."]
tree_root = ExtResource("3")
anim_player = NodePath("../AnimationPlayer")
active = true

[node name="Skeleton2D" type="Skeleton2D" parent="."]

[node name="Hip"   type="Bone2D" parent="Skeleton2D"]
[node name="Torso" type="Bone2D" parent="Skeleton2D/Hip"]

[node name="torso_base"   type="Sprite2D" parent="Skeleton2D/Hip/Torso"]
z_index = 0
[node name="armor_chest"  type="Sprite2D" parent="Skeleton2D/Hip/Torso"]
z_index = 10
[node name="armor_chest_detail" type="Sprite2D" parent="Skeleton2D/Hip/Torso"]
z_index = 11

; ... 手臂鏈與武器槽 ...
[node name="UpperArm_R" type="Bone2D" parent="Skeleton2D/Hip/Torso"]
[node name="ForeArm_R"  type="Bone2D" parent="Skeleton2D/Hip/Torso/UpperArm_R"]
[node name="Hand_R"     type="Bone2D" parent="Skeleton2D/Hip/Torso/UpperArm_R/ForeArm_R"]
[node name="weapon_main" type="Sprite2D" parent="Skeleton2D/Hip/Torso/UpperArm_R/ForeArm_R/Hand_R"]
z_index = 30
```

---

## 換裝 / 材質與 [[godot_material]] 系統的關係

| 元素 | 由誰決定 | 對應 [[godot_material]] 概念 |
|------|---------|------------------------------|
| 裝備「是什麼」（劍 / 斧 / 胸甲） | `Sprite2D.texture` = 灰階基底形狀 | Base Texture（形狀 + UV） |
| 裝備「是什麼材質」（鐵 / 鋼 / 紫晶） | shader uniform `material_tex` | Material Layer |
| 磨損 / 紋章 / 微光 | 獨立的 `*_detail` Sprite2D 或 shader detail | Detail Layer |
| 稀有度色調 | `self_modulate` 或 shader `rarity_tint` | 待決定項（見 [[godot_material]] 待決定） |

關鍵收益：**N 種武器形狀 × M 種材質 = N×M 種外觀，但貼圖只需 N+M 張**。一把「劍型基底」配上鐵 / 鋼 / 紫晶三種材質貼圖，就是三把劍，動畫完全共用。多區域材質（劍刃 + 劍柄分別上色）用 [[godot_material]] 進階版的 `region_mask_tex`（R/G channel 分區）。

---

## 與 anim_agent 動畫工具鏈的銜接

`others/godot/godot_anim_agent/`（進度見其 `progress.md`）的工具鏈專為 2D / value 軌道設計，本系統正是它的下游消費者：

1. **動畫資產來源**：`examples/fighter.tres` 即 2D 格鬥角色四段動畫（idle / guard / step_in / punch），軌道路徑形如 `Skeleton2D/Hip/...:rotation`。本系統的 `Bone2D` 命名應與這些軌道路徑一致，動畫才綁得上。
2. **離線編輯**：用 `anim_inspector.py set-key / scale-time / offset` 微調單段；用 `anim_compose.py concat --blend` 把 step_in + punch 串成「衝刺攻擊」連招（cross-fade 線性插值 + root-motion 位移累加）。
3. **狀態機**：`anim_tree.py derive` 依 metadata 的 `compatible_after` 自動推導轉場，烘出 `combo.tres`（`AnimationNodeStateMachine`），直接當本場景 `AnimationTree.tree_root`。
4. **場景骨架**：`anim_tree.py scaffold-scene` 會「依 library 軌道路徑自動建 Node2D + 小 Polygon2D 骨架 + 接好 AnimationPlayer/AnimationTree」（見 progress.md），產出 `fighter_tree.tscn`。**本系統的做法是：拿這個骨架，把自動產的 Polygon2D 佔位換成真正的 Bone2D + 裝備槽 Sprite2D 疊層**，骨名對齊即可無痛接上。
5. **手持 / 踩地姿勢**：`anim_pose.py aim`（2-bone IK，解上臂 / 前臂 rotation 寫回，FK 反算誤差 0）可離線把「手對準握把」的姿勢烘進關鍵影格，省去執行期 IK 的不確定性。
6. **打擊事件**：`anim_events.py add` 在 punch 動畫加 method 軌道（如 `spawn_hit_spark`），由本角色腳本實作對應方法即可——刀光特效與換裝外觀解耦。

> 注意：anim_agent 的 3D 軌道（`rotation_3d` 等）目前阻塞（progress.md「⏸ B」），但 **2D 軌道全綠**，本系統可直接使用其所有現成工具與範例。

---

## 效能 / 已知限制

- **draw call**：每個 Sprite2D 疊層是一個 draw call。單一角色約 8～15 槽尚可；數十名同款士兵同屏時，建議：
  - 完全相同的單位用 `MultiMeshInstance2D` + `MultiMesh`（`mapcore_godot/demo/scenes/biome_scatter.gd:73` 有 3D `MultiMesh.set_instance_transform` 的實作可借鑑，2D 對應 `MultiMeshInstance2D`），但 MultiMesh 不支援逐實例骨骼動畫，僅適合「靜止 / 共用單一姿勢」的遠景兵團。
  - 或把換裝後的角色 `bake` 成單張貼圖（用 `SubViewport` 截圖），遠景 LOD 用 bake 圖、近景才用完整骨架。
- **z_index 排序成本**：大量 Sprite2D 動態改 `z_index` 會觸發 CanvasItem 重排；穩定的疊層順序盡量在場景固定，只有「武器繪於身前 / 身後」這種少數情況才執行期切換。
- **IK 路線風險**：`SkeletonModification2D` 系列為偏舊 API，重度 IK 需求建議改走離線烘焙（`anim_pose.py`）而非執行期鏈。
- **材質實例化**：每個 Sprite2D 各自 `ShaderMaterial` 會增加 uniform 上傳；同材質的多個槽可共用一個 `ShaderMaterial` 實例（參考 [[godot_material_3d]] 中 MaterialLibrary 的快取思路，`analysis/godot/tutorial/gdextension_material_3d.md`）。

---

## 待決定

逐項回應 `others/godot/godot_character/CONCEPT.md` 的待決定清單：

- **是否需要 IK（腳踩地面 / 手持物件）？**
  - **建議：預設「離線烘焙」優先，執行期 IK 限縮到必要場景。** 理由：CONCEPT 提到 `SkeletonModificationStack2D` 可行，但該系列為偏舊 API；策略遊戲視角通常較遠、地面多為平面格子，腳踩地面的視覺收益有限。手持物件可用 `anim_pose.py aim`（誤差 0）離線解，比執行期更可控。僅在「斜坡踩地 / 滑鼠跟隨瞄準」這類即時需求才掛 `SkeletonModification2DTwoBoneIK`。

- **影子 / 輪廓效果是單獨 Sprite 還是 shader？**
  - **建議：輪廓用 shader（角色 Sprite 共用一個描邊 ShaderMaterial），影子用單獨 Sprite2D（橢圓貼圖掛 Hip 下）。** 理由：輪廓（選取高亮 / 受擊閃白）需要逐裝備槽生效且隨動畫變形，shader 可一鍵套用全身且零額外節點；參考 [[godot_material]] 的疊加思路與選取高亮 `analysis/godot/tutorial/gdextension_selection_highlight_2d.md`。影子若用 shader 需投影計算成本高，2D 策略遊戲一張固定橢圓貼圖（隨角色 XY 移動、不隨骨骼變形）視覺已足夠且近乎零成本。

- **多角色同屏時的 draw call 優化（MultiMesh 或 bake）？**
  - **建議：分 LOD 兩段——近景完整骨架、遠景 bake 貼圖；超大規模同款兵團才上 MultiMeshInstance2D。** 理由：MultiMesh 無法逐實例骨骼動畫，只能播共用姿勢，不適合需要獨立動畫的主要單位；但對「站樁 / 行軍中姿勢一致」的遠景兵團極省 draw call（見 biome_scatter.gd 的 GPU instancing 模式）。最務實的是用 `SubViewport` 把換裝完成的角色 bake 成精靈表，遠景單位改播 bake 動畫，近景才實時骨架——這同時解決 draw call 與骨骼計算兩個瓶頸。

---

*記錄時間：2026-05-23*
*狀態：概念補完為實作教學；API 對齊 Godot v4.6.stable（extension_api.json）；對應 3D 版 `gdextension_character_3d.md`*
