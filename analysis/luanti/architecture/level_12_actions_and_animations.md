# Level 12: 動作觸發與動畫同步機制深度分析

## 1. 動作與動畫的分類
Luanti 將視覺動態分為三大類：
- **模型動畫 (Skeletal Animation)**：儲存在 `.b3d` 或 `.gltf` 檔案中的預錄動作。
- **手持動作 (Wield Actions)**：玩家在第一人稱視角下的手臂揮動、防禦動作。
- **代碼驅動動作 (Procedural Actions)**：透過 C++ 或 Lua 即時計算骨架座標產生的動態（如轉頭看向玩家）。

## 2. 第一人稱：WieldMeshSceneNode
**原始碼位置**：`src/client/wieldmesh.cpp`
- **職責**：專門處理玩家螢幕右下角手持的模型（手臂 + 工具）。
- **揮動邏輯**：當玩家執行 `Left Click` 時，`Camera` 會啟動一個揮動計時器。`WieldMeshSceneNode` 根據此計時器計算正弦或餘弦偏移，讓手臂產生「向下砍」的視覺效果。這完全是在客戶端端計算的，以確保操作即時感。

## 3. 第三人稱與實體動畫同步 (Server-Client Sync)
- **流程**：
    1. **Lua 請求**：Mod 呼叫 `object:set_animation({x=1, y=20}, 30, 0)`。
    2. **狀態標記**：伺服器端的 `PlayerSAO` 或 `LuaEntitySAO` 更新內部的 `m_animation_range` 等變數。
    3. **封包廣播**：在下一個伺服器步進中，發送 `TOCLIENT_ANIMATION` (Opcode 0x42) 給附近的所有客戶端。
    4. **客戶端執行**：客戶端的 `GenericCAO` 接收封包，並呼叫 Irrlicht 的 `setFrameLoop` 使模型開始播放動畫。

## 4. 動作回呼鏈 (Action Callback Chain)
動作的邏輯處理遵循以下順序：
1. **輸入捕捉**：`src/client/game.cpp` 捕捉滑鼠事件。
2. **網路發送**：發送 `TOSERVER_INTERACT`。
3. **伺服器判定**：`Server::handleCommand_Interact` 驗證行為合法性。
4. **Lua 執行**：觸發 `on_use`, `on_punch` 等回呼。
5. **視覺反饋**：Lua 回呼內可能再次呼叫 `set_animation` 或 `add_particlespawner` 完成視覺閉環。
    - *注意*：為了平滑度，部分視覺效果（如採礦粒子）也會在客戶端先行「預測」產生。
 Riverside, 
