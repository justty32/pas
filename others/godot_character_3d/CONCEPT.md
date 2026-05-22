# 3D 角色系統：骨骼動畫 + 紙娃娃

## 對應 2D 版本

2D 版本（`../godot_character/`）使用 Skeleton2D + Bone2D + Sprite2D 疊層。
3D 版本使用 Skeleton3D + BoneAttachment3D + MeshInstance3D，概念相同，但工具鏈更成熟。

---

## 資產管線

```
Blender（建模 + 骨骼綁定 + 動畫）
    ↓ 匯出 .glb（含 mesh + skeleton + animations）
Godot 導入
    ↓
CharacterRoot (Node3D)
├── AnimationPlayer
├── AnimationTree
└── [Skeleton3D + MeshInstance3D]  ← 從 .glb 展開
```

Low poly 角色的 Blender 工作量遠小於寫實風格：
- 軀幹、四肢用基本幾何體（cylinder, cube）稍加調整即可
- 不需要高精度拓撲，幾百個 poly 就夠
- UV unwrap 也相對簡單

---

## 骨骼動畫（Godot 3D）

Skeleton3D 骨骼樹結構與 2D 版本概念一致，只是多了 Z 軸：

```
Skeleton3D
└── Hip
    ├── Spine
    │   ├── Chest
    │   │   ├── UpperArm_L
    │   │   │   └── ForeArm_L
    │   │   │       └── Hand_L
    │   │   └── UpperArm_R ...
    │   └── Head
    ├── Thigh_L
    │   └── Shin_L
    │       └── Foot_L
    └── Thigh_R ...
```

AnimationPlayer 在 3D 中的 track 類型：
- `NodePath:position` — 位置（Vector3）
- `NodePath:rotation` — 旋轉（Quaternion，用 `rotation_edit_mode = QUATERNION`）
- `NodePath:scale` — 縮放（Vector3）

Root motion：Hip 骨骼的位移可作為角色移動的驅動來源（AnimationTree 的 `root_motion_track` 設定）。

---

## 紙娃娃系統（Paper Doll 3D）

### 核心概念

每個裝備槽是一個 **BoneAttachment3D + MeshInstance3D**，掛在對應骨骼下。
換裝 = 替換 `MeshInstance3D.mesh`，骨骼動畫自動帶動。

### 節點結構

```
Skeleton3D
├── [角色基底 mesh 內建於 skeleton]
├── BoneAttachment3D  [bone_name = "Hand_R"]   ← 武器掛點
│   └── MeshInstance3D  [weapon_slot]
├── BoneAttachment3D  [bone_name = "Head"]
│   └── MeshInstance3D  [helmet_slot]
├── BoneAttachment3D  [bone_name = "Chest"]
│   └── MeshInstance3D  [armor_chest_slot]
└── BoneAttachment3D  [bone_name = "Thigh_L"]
    └── MeshInstance3D  [armor_leg_slot]
```

### 換裝 API（GDScript）

```gdscript
func equip_weapon(mesh: Mesh) -> void:
    weapon_slot.mesh = mesh

func equip_armor(slot: MeshInstance3D, mesh: Mesh, mat: Material) -> void:
    slot.mesh = mesh
    slot.material_override = mat  # 覆蓋材質（稀有度色調等）

func unequip(slot: MeshInstance3D) -> void:
    slot.mesh = null
```

---

## 與材質系統的整合

3D 換裝比 2D 更直觀——直接用 `material_override` 或設定 `surface_material_override`：

```gdscript
# 同一把劍的 mesh，套用不同材質 → 鐵劍 / 鋼劍 / 紫晶劍
func set_weapon_quality(quality: int) -> void:
    weapon_slot.material_override = WEAPON_MATERIALS[quality]
```

材質細節見 `../godot_material_3d/`。

---

## 程序生成角色部件（Low Poly）

不想手工建模時，可以用 GDExtension 程序生成各部件的 low poly mesh（見 `../godot_procgen_mesh/`）：

| 部件 | 程序生成方式 |
|-----|------------|
| 軀幹 | 拉伸的橢球 + noise 擾動 |
| 四肢 | Cylinder + 隨機粗細分布 |
| 頭部 | 球體 + 頂點擾動 |
| 武器 | 程序幾何（劍 = 扁平六面體、錘 = 圓柱 + 球） |

骨骼仍由 Blender 製作（或用固定骨骼模板），程序生成的是**表面 mesh**，不是骨骼本身。

---

## 2D vs 3D 角色系統比較

| 面向 | 2D | 3D |
|-----|----|----|
| 工具鏈 | 自建 Sprite2D 疊層 | Blender + GLTF，成熟 |
| 換裝 | 替換 Sprite2D.texture | 替換 MeshInstance3D.mesh |
| 動畫 | AnimationPlayer on bone rotation (2D) | 同，但加 3D transform |
| 材質變體 | 需自訂 shader overlay | StandardMaterial3D 直接設定 |
| 程序生成 | 像素操作 | 多邊形操作 |
| 美術難度 | 像素畫（可程序） | Low poly 建模（可程序） |

---

## 待決定

- [ ] 角色基底：Blender 手工 low poly vs 完全程序生成 mesh
- [ ] 是否需要 IK（腳踩地面、手持物件）→ Godot 有 SkeletonModifier3D / FABRIKInverseKinematics
- [ ] 多角色同屏效能：MultiMesh + GPU instancing（裝備完全相同的士兵）
- [ ] 面部表情：Shape Key（Blend Shape）or 獨立 mesh 替換

---

*記錄時間：2026-05-22*
*狀態：概念階段，對應 2D 版本 `../godot_character/`*
