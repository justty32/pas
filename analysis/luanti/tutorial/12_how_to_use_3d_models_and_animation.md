# 開發教學 12：如何使用 3D 模型與骨架動畫

## 目標
本教學將引導你實作一個 3D 動畫角色（如「魔法守衛」），包含：
1. 載入 3D 模型與材質。
2. 控制預錄的動畫序列。
3. 使用 Lua 手動操作骨架關節。

## 1. 前置知識
- 了解如何在 Blender 中匯出 `.b3d` 或 `.gltf` 檔案。
- 了解模型中的關節 (Joints/Bones) 命名。

## 2. 原始碼導航 (核心參考)
- **C++ 骨架處理**：`src/client/content_cao.cpp` (行號 712, `setOnAnimateCallback`)。
- **API 定義**：`doc/lua_api.md` (搜尋 `set_animation`, `set_bone_override`)。

## 3. 實作步驟

### A. 檔案準備
將以下檔案放入 `mods/magic_stuff/models/` 與 `textures/`：
- `guard.b3d` (包含名為 "idle" 與 "walk" 的動畫)
- `guard_texture.png`

### B. 註冊 3D 實體
在 `mods/magic_stuff/init.lua` 中加入：
```lua
core.register_entity("magic_stuff:guard", {
    initial_properties = {
        visual = "mesh",
        mesh = "guard.b3d",
        textures = {"guard_texture.png"},
        visual_size = {x=1, y=1, z=1},
        physical = true,
    },

    on_activate = function(self)
        -- 1. 播放預錄動畫：從第 1 幀到第 40 幀，速度 30 FPS，循環播放
        self.object:set_animation({x=1, y=40}, 30, 0, true)
    end,

    on_step = function(self, dtime)
        -- 2. 動態操作骨架：讓頭部 ("Head" 骨骼) 隨機旋轉
        local time = core.get_gametime()
        local yaw = math.sin(time) * 30 -- 產生 -30 到 30 度的旋轉
        
        self.object:set_bone_override("Head", {
            rotation = {x=0, y=yaw, z=0}
        })
    end,
})
```

## 4. 驗證方式
1. 使用指令 `/spawnentity magic_stuff:guard`。
2. **觀察基礎動畫**：確認角色是否正在執行循環的 Idle 動態。
3. **觀察骨架覆寫**：確認角色的頭部是否在左右緩慢擺動，且與基礎動畫獨立運作。
4. **檢查 UV 材質**：確認貼圖是否正確對應到模型表面。

## 5. 常見問題 (Blender 匯出建議)
- **座標軸**：匯出時請確保 Z 軸向上 (Z-Up)，否則角色會躺在地上。
- **骨骼權重**：確保每個頂點至少被一個骨骼影響，否則該部分在遊戲中會呈現靜止狀態。
