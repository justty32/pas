# godot_character_3d — 進度保存

> 最後更新：2026-05-28。從 `CONCEPT.md` 落地的視覺層雛形。

## 一句話：這是什麼

3D 角色**視覺層**：紙娃娃換裝 + 動畫切換 + 整合 facade。
對接 `godot_character_controller`（行為層），訂閱 `state_changed` 切動畫。

## 真相校準

**mapcore_godot demo 沒有角色相關資產**——這是 13 個 CONCEPT 中第一個完全從零的，
沒有 demo 端可校準。也沒辦法現場建 .glb 或測 Blender 工作流。

故本檔聚焦三件「**有 .glb 後立刻能用**」的 GDScript 元件：
1. **PaperDoll3D**：吃 slot_specs（裝備槽到骨骼的映射），動態建 BoneAttachment3D + MeshInstance3D
2. **CharacterAnimator**：接 controller 的 state_changed signal → AnimationTree/Player 切狀態
3. **Character3D**：facade 把 controller + paper doll + animator 串起來

**未做**（需要美術或更多工程量）：
- .glb 範例資產（要 Blender 建模）
- 純 GDScript 程序生成的人形骨骼 + mesh（落地 CONCEPT「完全程序生成」待決事項，
  Skeleton3D bone matrix 設定容易出錯，留待真有需求時做）
- IK（腳踩地面、手持物件對準）

## 檔案清單

```
godot_character_3d/
├── CONCEPT.md
├── gd/
│   ├── paper_doll_3d.gd       # PaperDoll3D：BoneAttachment3D + MeshInstance3D 動態建立
│   ├── character_animator.gd  # CharacterAnimator：state signal → AnimationTree/Player
│   └── character_3d.gd        # Character3D：整合 facade
└── progress.md
```

## 整體狀態

| 區塊 | 內容 | 狀態 |
|------|------|------|
| PaperDoll3D 動態 slot | slot_specs Dictionary 自動展開、equip/unequip API、get_all_meshes 給 outline 用 | ✅ 完成 |
| CharacterAnimator 雙路線 | AnimationTree（StateMachinePlayback.travel）+ AnimationPlayer（play with crossfade）| ✅ 完成 |
| Character3D facade | 自動找子節點型別、forward controller/paper doll signal、get_outline_targets | ✅ 完成 |
| 視覺層 .glb 資產 | Blender 建好的低多邊形人形 + 動畫 | ❌ 未做（美術側） |
| 純 GDScript 程序人形 | Skeleton3D + 程序 mesh + 程序動畫 | ❌ 未做（留待辦） |
| IK | SkeletonModifier3D | ❌ 未做 |
| 真機驗證 | Godot 4 + 真實 .glb 跑完整流程 | ⏸ **待真機驗證** |

## 設計重點

### 1. PaperDoll3D 用 slot_specs Dictionary 解耦骨骼命名
不同 .glb 來源骨骼命名不一定一樣（`Hand_R` / `hand.R` / `WeaponBone`...）。
slot_specs 讓使用者在 inspector 餵入「裝備槽名 → 骨骼名 + 偏移」對應表：

```gdscript
paper_doll.slot_specs = {
    "weapon_main": {"bone": "Hand_R", "offset": Vector3(0, 0.05, 0)},
    "helmet": {"bone": "Head"},
}
```

`_ready()` 找到 Skeleton3D 後依此自動建立 BoneAttachment3D + MeshInstance3D 子節點。
事後 `equip("weapon_main", sword_mesh)` 一行就換裝。

### 2. CharacterAnimator 雙路線
策略遊戲常見兩種接法：
- **AnimationTree + StateMachine**（CONCEPT 推薦，可做轉場混合）→ 呼叫 playback.travel()
- **純 AnimationPlayer**（簡單情境，沒 blend tree）→ 呼叫 play() 含 crossfade

`bind()` 走第一條，`bind_player()` 走第二條。內部都用相同的 `UnitState.anim_state()` 映射。

### 3. Character3D facade 用 has_signal 檢查解耦 controller 類型
不寫死「controller 必須是 UnitController3D」。任何 Node 只要有 `state_changed` signal
與 `state: int` property 都能接。未來做 `godot_character_platformer/` 時可換 controller。

### 4. get_outline_targets() 給 selection_highlight 用
策略遊戲選中角色要套描邊，但角色由 controller + paper doll 多 mesh 組成。
本檔提供 `get_outline_targets() -> Array[MeshInstance3D]`，呼叫端：

```gdscript
for mesh in character.get_outline_targets():
    SelectionHighlight.apply_3d(mesh, Color.YELLOW)
```

或直接用 `SelectionHighlight.apply_3d_recursive(character)`，效果一樣。

## 預期場景結構（要對接 .glb 資產時）

```
Character3D (本 script)
├── UnitController3D                  ← @export controller
├── Visual (Node3D)
│   └── (從 .glb 匯入展開的子樹)
│       ├── Skeleton3D
│       │   └── [mesh + bones]
│       ├── AnimationPlayer
│       └── AnimationTree (選用)
└── PaperDoll3D                        ← @export paper_doll
    [_ready 自動找 Skeleton3D 並建 BoneAttachment3D 子節點]
```

實際在 Godot 編輯器：
1. Drag .glb 到場景 → 自動展開 Visual 子樹
2. 加 Character3D / UnitController3D / PaperDoll3D 三節點
3. 在 PaperDoll3D 的 inspector 填 slot_specs 對應你 .glb 的骨骼命名
4. F5 跑

## 用法範例

### 完整移動 + 動畫 + 換裝
```gdscript
# 假設已在編輯器擺好場景，character 是 Character3D 節點
character.teleport_to_cell(Vector2i(10, 10))
character.equip("weapon_main", sword_mesh, Material3D.tint(Palette3D.WEAPON["steel"]))
character.equip("helmet", helmet_mesh)

# 命令移動 → 動畫自動切到 walk → 抵達後自動切回 idle
var path := map_data.find_path(Vector2i(10, 10), Vector2i(20, 30))
character.move_along_path(path)
character.arrived.connect(func(_pos: Vector3) -> void:
    print("到了"))
```

### 與 selection_highlight 整合
```gdscript
SelectionHighlight.apply_3d_recursive(character, Color.YELLOW, 0.03,
    SelectionHighlight.Style3D.SCREEN_SPACE)
```

### 與 camera_rig 整合
```gdscript
character.controller.step_completed.connect(func(_cell, world_pos: Vector3) -> void:
    camera_rig.focus(world_pos))
```

## 待決事項（從 CONCEPT.md 帶過來）

- [ ] **角色基底**：Blender 手工 low poly vs 完全程序生成 mesh
      → 兩條都未做。第一條等美術，第二條留 progress.md 待辦。
- [ ] **IK**：腳踩地面、手持物件對準 → 未做。Godot 4 有 `SkeletonModifier3D` /
      `LookAtModifier3D`，需要時補。
- [ ] **多角色 instancing 效能**：MultiMesh + GPU instancing 適用「裝備完全一樣的士兵」。
      策略遊戲一格一單位通常不會百個同款角色，本檔先不做。
- [ ] **面部表情**：Shape Key（Blend Shape）or 獨立 mesh 替換 → 未做。

## 與其他模組的串接

| 模組 | 互動 |
|------|------|
| `godot_character_controller` | controller 提供 `state_changed` signal，本檔訂閱切動畫 |
| `godot_material_3d` | 換裝時 `equip(slot, mesh, material)` 餵 Material3D.tint() 產的材質 |
| `godot_selection_highlight` | `apply_3d_recursive(character)` 或 `get_outline_targets()` 套描邊 |
| `godot_camera_rig` | `controller.step_completed` → `camera.focus(world_pos)` |
| `godot_anim_agent` | 編輯動畫資源（.tres / .gltf 內動畫）的工具鏈，與本檔互補 |

## 下一步（按需）

1. **真機驗證**：建一個低多邊形人形 .glb（Blender 或網路免費資產 mixamo），
   套上 PaperDoll3D + CharacterAnimator，跑完整 controller → animator → paper doll 流程。
2. **godot_character 2D 對應版**：與本檔對等的 2D 版（Skeleton2D + Bone2D + Sprite2D）。
3. **純 GDScript 程序人形**：給沒美術也想跑通的情境用。需要寫 Skeleton3D bone rest poses
   + cylinder/sphere mesh + 簡單 walk cycle 程序動畫。中等工程量。
