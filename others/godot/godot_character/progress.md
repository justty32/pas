# godot_character — 進度保存

> 最後更新：2026-05-28。從 `CONCEPT.md` 落地的 2D 視覺層雛形。

## 一句話：這是什麼

2D 角色視覺層：紙娃娃換裝 + AnimationTree 切換 + facade。
對應 `godot_character_3d`，介面對等；同樣銜接 `godot_character_controller`（行為層）。

## 真相校準

mapcore_godot 端**沒有**任何 2D 角色（Skeleton2D / Bone2D / 紙娃娃）相關實作。
這跟 `godot_character_3d` 一樣是完全從零。

主線已轉 3D（`godot_lowpoly` 2026-05-22 決策），這份的優先級偏低，但保留以維持 2D/3D 對偶。

## 檔案清單

```
godot_character/
├── CONCEPT.md
├── gd/
│   ├── paper_doll_2d.gd     # PaperDoll2D：Sprite2D 動態掛 Bone2D 下
│   └── character_2d.gd      # Character2D facade
└── progress.md
```

註：`character_animator.gd`（CharacterAnimator）**跨 2D/3D 通用**，已在 `godot_character_3d/gd/` 落地，
本檔直接引用，不重複實作。Godot 4 的 AnimationTree 同樣支援 2D root，
唯一差別只是 root node 型別（Node2D vs Node3D）。

## 整體狀態

| 區塊 | 內容 | 狀態 |
|------|------|------|
| PaperDoll2D 動態 slot | slot_specs Dictionary（bone_path + z_index + offset），自動找 Bone2D 建 Sprite2D | ✅ 完成 |
| equip_with_material 整合 SpriteMaterial | 自動套 `godot_material/SpriteMaterial.apply()` | ✅ 完成 |
| Character2D facade | forward signal、自動找子節點、get_outline_targets | ✅ 完成 |
| AnimationTree 銜接 | 用 godot_character_3d 的 CharacterAnimator | ✅ 完成（複用） |
| Skeleton2D 素材 | 美術側產出（手繪 + Bone2D 綁定） | ❌ 未做 |
| 純 GDScript 程序 2D 骨架 | 與 character_3d 程序人形對齊待辦 | ❌ 未做 |
| 真機驗證 | Godot 4 + 真實 Skeleton2D 素材跑流程 | ⏸ **待真機驗證** |

## 設計重點

### 1. PaperDoll2D 用 bone_path 而非 bone_name
2D Skeleton 沒有 `find_bone()`，bone 只是 Bone2D 子節點。所以 slot_specs 要給的是
**節點路徑**（相對於 skeleton 的父節點），例如：
```
"Skeleton2D/Hip/Torso/UpperArm_R/ForeArm_R/Hand_R"
```
然後 PaperDoll2D 在該節點下 add_child 一個 Sprite2D。骨骼動畫自動帶動 sprite。

### 2. z_index 解決 2D 沒有深度的問題
3D 自帶深度測試，2D 要靠 `z_index` 排前後。slot_specs 要明確指定每個槽的 z_index：
- 軀幹基底 z=0
- 護甲底層 z=2
- 護甲細節層 z=3
- 武器 z=5
建議在 slot_specs 統一管理而不是各 sprite 自己設。

### 3. equip_with_material 自動串 SpriteMaterial
CONCEPT 明確點到「裝備槽 Sprite2D 用材質複用 shader」。本檔 `equip_with_material()`
自動套 `godot_material/SpriteMaterial.apply()`，少打一條繩。

### 4. CharacterAnimator 是跨 2D/3D 元件
Godot 4 的 AnimationTree 設計上是 root node 中立的（內部用 NodePath 操作，
不關心 root 是 Node2D 還是 Node3D）。`bind(tree, controller)` 對兩者一視同仁。
本檔不重複 animator，直接 `var _animator: CharacterAnimator = ...`。

## 用法範例

```gdscript
# 場景結構在編輯器已擺好（Skeleton2D + AnimationPlayer + UnitController2D + PaperDoll2D）

# slot_specs 在 inspector 填，或程式碼設：
paper_doll.slot_specs = {
    "weapon_main": {"bone_path": "Skeleton2D/Hip/Torso/UpperArm_R/ForeArm_R/Hand_R", "z_index": 5},
    "helmet": {"bone_path": "Skeleton2D/Hip/Torso/Head", "z_index": 4},
    "armor_chest": {"bone_path": "Skeleton2D/Hip/Torso", "z_index": 2},
}

# 移動 + 換裝
character.teleport_to_cell(Vector2i(5, 5))
character.equip("weapon_main", sword_texture)
character.equip_with_material("armor_chest", chest_base_tex, gold_material_tex,
        1.0, SpriteMaterial.BlendMode.MULTIPLY)

# 路徑命令
var path := [Vector2i(5, 5), Vector2i(6, 5), Vector2i(7, 5)]
character.move_along_path(path)
character.arrived.connect(func(_pos: Vector2) -> void: print("到了"))
```

## 待決事項（從 CONCEPT.md 帶過來）

- [ ] **IK**：腳踩地面、手持物件對準 → 未做。Godot 4 用 `SkeletonModificationStack2D`。
- [ ] **影子/輪廓效果**：用 `godot_selection_highlight/` 的 2D outline shader 即可。
- [ ] **多角色同屏 draw call**：策略遊戲一格一單位通常不會百個，先不做。

## 與其他模組的串接

| 模組 | 互動 |
|------|------|
| `godot_character_controller.UnitController2D` | 行為層，提供 state signal |
| `godot_character_3d.CharacterAnimator` | 跨 2D/3D 通用，本檔直接引用 |
| `godot_material.SpriteMaterial` | equip_with_material 自動串接 |
| `godot_selection_highlight` | `apply_2d` 套描邊；本檔 `get_outline_targets` 給陣列 |
| `godot_camera_rig.CameraRig2D` | controller.step_completed → camera.focus |

## 下一步（按需）

1. **真機驗證**：需要一份 2D 骨骼角色素材（手繪 + Bone2D 綁定）。
2. **godot_procgen_art** 落地後，可程序生成軀幹/四肢圖像，再用 PaperDoll2D 組裝（CONCEPT Level 3）。
