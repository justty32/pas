# 教學：如何添加 3D 物件與特效 (VFX)

本教學將引導您如何在 COGITO 中添加新的 3D 物件，並根據其用途設定為擺設、可互動或具備物理特性的物件，最後說明如何整合視覺特效。

## 前置知識
- 已閱讀 [Level 3A: 互動物件系統](../architecture/level3_interactive_objects.md)。
- 已閱讀 [Level 4A: CogitoProperties 物質反應系統](../architecture/level4_properties_system.md)。
- 具備 Godot 4 的 3D 基礎（MeshInstance3D, CollisionShape3D）。

---

## 1. 添加擺設物件 (Static Decoration)

最簡單的靜態物件，玩家無法與其互動，也不會移動。

### 實作步驟
1. 建立一個 `StaticBody3D` 作為根節點。
2. 添加 `MeshInstance3D` 並賦予模型。
3. 添加 `CollisionShape3D` 並設定碰撞範圍。
4. **關鍵設定：Physics Layer**
   - 將物件設定在 **Layer 1 (Environment)**。這確保玩家能站在上面，且不會被當作互動物件偵測。

---

## 2. 添加可互動物件 (Interactable Object)

讓物件能被玩家「看見」並觸發行為（如：發出聲音、改變外觀）。

### 實作步驟
1. 建立一個 `StaticBody3D`（如果是固定的）或 `RigidBody3D`（如果可以推動）。
2. 添加 `MeshInstance3D` 與 `CollisionShape3D`。
3. **關鍵設定：Physics Layer**
   - 將物件設定在 **Layer 2 (Interactables)**。這能讓玩家的 `PlayerInteractionComponent` 掃描到它。
4. **添加組件**：
   - 添加一個 `BasicInteraction` 節點作為子節點。
   - 在 Inspector 中設定 `Interaction Text`（如："觀察"）。
   - 在 `BasicInteraction` 的訊號中，連結 `was_interacted_with` 到您的邏輯。

---

## 3. 添加物理物件 (Physics Object)

具備重力、可以被推動、撞擊時會發出聲音。

### 實作步驟
1. 建立一個 `RigidBody3D`。
2. 設定 `Mass`（重量）與 `Friction`（摩擦力）。
3. **添加 ImpactSounds 組件**：
   - 為了讓物體撞擊地面有聲音，添加 `addons/cogito/Components/ImpactSounds.tscn` 作為子節點。
   - 在 `Impact Sounds` 欄位中放入一個 `AudioStreamRandomizer`。
4. **添加 CogitoProperties (可選)**：
   - 若希望物件能被點燃或導電，添加 `CogitoProperties` 組件。
   - 設定 `Elemental Properties`（如：FLAMMABLE）。

---

## 4. 添加特效 (VFX)

COGITO 的特效通常透過預製件 (PackedScene) 的方式動態生成。

### 種類一：物質反應特效
在 `CogitoProperties` 組件中，您可以設定不同狀態觸發的特效：
- `spawn_on_ignite`: 當物件著火時。
- `spawn_on_wet`: 當物件變濕時。
- `spawn_on_electrified`: 當物件通電時。
- **實作方式**：將您的特效場景（例如一個包含 `GPUParticles3D` 的 `.tscn`）拖入上述欄位即可。

### 種類二：撞擊與死亡特效
- **子彈/投射物**：`CogitoProjectile` 具有 `spawn_on_death` 欄位，可用於生成彈孔、火花或爆炸特效。
- **自訂生成**：若要在特定時刻手動生成特效，請參考 `explosion.gd`：
  ```gdscript
  var vfx = my_vfx_scene.instantiate()
  get_parent().add_child(vfx)
  vfx.global_position = target_position
  ```

---

## 驗證方式

### 物件驗證
1. 將物件放入場景中。
2. 運行遊戲，嘗試看向物件。如果準心有變化或出現提示文字，代表互動層級設定正確。
3. 嘗試推擠物理物件，檢查其移動與撞擊音效是否正常。

### 特效驗證
1. 如果設定了著火特效，使用火源（如火把組件）觸碰該物件。
2. 觀察特效是否在 `reaction_threshold_time` 後正確生成在物件位置。
3. 檢查 `spawned_effects` 陣列，確保特效在結束後有被正確釋放（避免記憶體洩漏）。
