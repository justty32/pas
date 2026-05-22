# 角色系統：紙娃娃 + 骨骼動畫

## 概述

Godot 原生已完整支援這兩個系統，實作難度不高。此文件記錄設計意圖與整合要點。

---

## 骨骼動畫系統（Skeleton2D + Bone2D）

### 節點結構

```
CharacterRoot (Node2D)
└── Skeleton2D
    ├── Bone2D [Hip]
    │   ├── Bone2D [Torso]
    │   │   ├── Bone2D [UpperArm_L]
    │   │   │   └── Bone2D [ForeArm_L]
    │   │   │       └── Bone2D [Hand_L]
    │   │   └── Bone2D [UpperArm_R] ...
    │   ├── Bone2D [Thigh_L]
    │   │   └── Bone2D [Shin_L] ...
    │   └── Bone2D [Thigh_R] ...
```

### 動畫方式

- **AnimationPlayer**：綁定在 CharacterRoot，對各 Bone2D.rotation 製作 value track
- **AnimationTree + StateMachine**：管理 idle / walk / attack 狀態切換與 blend
- 進階：root motion（Skeleton2D 根骨骼位移）驅動角色移動

---

## 紙娃娃系統（Paper Doll）

### 核心概念

每個裝備槽是一個 **Sprite2D，掛在對應的 Bone2D 下**。
換裝 = 替換 Sprite2D 的 `texture` 屬性，骨骼動畫自動帶動。

### 節點結構（接上方骨骼）

```
Bone2D [Torso]
├── Sprite2D [torso_base]          ← 軀幹基底
├── Sprite2D [armor_chest]         ← 裝備槽：胸甲（null = 無裝備）
└── Sprite2D [armor_chest_detail]  ← 裝備材質疊加層（見 material system）

Bone2D [Hand_R]
└── Sprite2D [weapon_main]         ← 裝備槽：主手武器
```

### 繪製順序

- Sprite2D 的 `z_index` 或節點順序決定前後層
- 軀幹基底 < 護甲底層 < 護甲細節層 < 武器

### 換裝 API（GDScript）

```gdscript
func equip_weapon(slot: Sprite2D, texture: Texture2D) -> void:
    slot.texture = texture

func equip_armor(slot: Sprite2D, base_tex: Texture2D, material_tex: Texture2D) -> void:
    slot.texture = base_tex
    slot.material.set_shader_parameter("material_tex", material_tex)
```

---

## 與材質系統的整合

裝備槽的 Sprite2D 使用**材質複用 shader**（見 `../godot_material/CONCEPT.md`）：
- `texture`：形狀/基底（換裝時替換）
- shader uniform `material_tex`：材質疊加層（決定品質/稀有度外觀）

這讓同一把「劍型 texture」可以用不同材質 shader 呈現鐵、鋼、紫晶等變體。

---

## 待決定

- [ ] 是否需要 IK（腳踩地面、手持物件）→ Godot 有 SkeletonModificationStack2D
- [ ] 影子/輪廓效果是單獨 Sprite 還是 shader
- [ ] 多角色同屏時的 draw call 優化（考慮 MultiMesh 或 bake）

---

*記錄時間：2026-05-22*
