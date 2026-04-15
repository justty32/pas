# Level 11: 3D 模型與骨架動畫系統深度分析

## 1. 支援格式與載入機制
Luanti 透過渲染引擎 (Irrlicht MT) 支援多種模型格式：
- **.obj**：靜態模型，無動畫。最簡單且相容性最高。
- **.b3d (Blitz3D)**：Luanti 最常用的動畫格式，支援完整的骨架動畫。
- **.gltf / .glb**：現代標準格式，支援物理材質與複雜骨架。
- **載入入口**：`Client::getMesh` (`src/client/client.cpp`, 行號 2048)。

## 2. 實體與模型的綁定 (GenericCAO)
當一個 Lua 實體被建立且其 `visual = "mesh"` 時：
1. **實例化**：引擎呼叫 `addAnimatedMeshSceneNode` 建立 3D 物件。
2. **法線修正**：若模型法線不正確，引擎會自動呼叫 `recalculateNormals` (行號 692)。
3. **材質套用**：
    - Lua 中的 `textures = {"tex1.png", "tex2.png"}` 會按順序分配給模型的 Material ID 0, 1, 2...。
    - UV 映射完全遵循 3D 建模軟體（如 Blender）中的定義。

## 3. 骨架控制機制 (Bone Overrides)
這是 Luanti 實作動態 AI 視覺效果的核心：
- **運作原理**：`GenericCAO` 在每幀動畫更新後，會檢查 Lua 是否設定了 `set_bone_override`。
- **C++ 實作**：在 `src/client/content_cao.cpp` (行號 712) 的回呼函數中：
    - 透過關節名稱（如 "Head"）取得 `IBoneSceneNode`。
    - 強制套用自定義的旋轉與位移。
- **應用場景**：NPC 轉頭看玩家、手持武器的動態位置調整。

## 4. 效能優化：Hardware Skinning
- 引擎會透過 `mesh->needsHwSkinning()` 判斷是否將骨骼計算交給 GPU Shader 處理。
- 這能大幅減少具有大量動畫實體時的 CPU 壓力。
