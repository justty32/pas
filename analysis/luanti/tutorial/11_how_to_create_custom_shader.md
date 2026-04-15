# 開發教學 11：如何實作自定義 Shader 特效

## 目標
本教學將引導你修改 Luanti 的節點著色器 (Nodes Shader)，實作一個全域方塊的「魔力脈動」效果（方塊顏色會隨時間週期性變換）。

## 1. 前置知識
- 基礎 GLSL 語法（了解 `varying`, `uniform`, `gl_FragColor`）。
- 了解 Luanti 的 Shader 文件結構。

## 2. 原始碼導航 (核心參考)
- **節點著色器原始碼**：`client/shaders/nodes_shader/opengl_fragment.glsl` (片段著色器)。
- **C++ 常量傳遞**：`src/client/shader.cpp` (搜尋 `mTime`)。

## 3. 實作步驟

### A. 備份與定位
在修改前，請確保備份 `client/shaders/nodes_shader/`。我們將修改 `opengl_fragment.glsl`。

### B. 修改片段著色器
開啟 `client/shaders/nodes_shader/opengl_fragment.glsl`，找到處理最終顏色的位置（通常在 `main()` 函數末尾）：

```glsl
// 在文件頂部確認 uniform mTime 是否存在，若無則加入：
uniform float mTime;

void main() {
    // ... 原有的光照與貼圖採樣邏輯 ...
    vec4 color = texture2D(baseTexture, uv);
    
    // --- 實作魔力脈動邏輯 ---
    // 使用正弦波根據時間產生 0.8 到 1.2 之間的係數
    float pulse = 1.0 + sin(mTime * 2.0) * 0.2;
    
    // 讓方塊的藍色與綠色通道隨脈動增強
    color.rgb *= vec3(1.0, pulse, pulse);
    
    // 應用原有的光照等級
    gl_FragColor = vec4(color.rgb * lightColor, color.a);
}
```

### C. 啟用自定義 Shader 路徑
為了不破壞原始安裝目錄，建議在 `minetest.conf` 中設定：
```ini
enable_shaders = true
shader_path = [你的自定義 Shader 目錄路徑]
```

## 4. 驗證方式
1. **重啟遊戲**：Shader 修改後必須重啟客戶端才會重新編譯。
2. **進入世界**：
    - 觀察普通方塊（如石頭、泥土）。
    - 確認它們是否呈現緩慢的青藍色脈動發光。
3. **檢查錯誤**：
    - 若畫面全黑或出現異常，請查看控制台輸出。GLSL 編譯錯誤會詳細列出出錯的行號。

## 5. 進階：僅針對特定 Mod 方塊
若只想讓 `magic_stuff:glowing_stone` 脈動，你需要：
1. 在 `opengl_vertex.glsl` 中利用 `vColor` 或額外的 `varying` 傳遞方塊類型標記。
2. 或是在 Lua 中為該方塊設定特殊的 `drawtype` 並在 Shader 中針對該類型的渲染標籤進行判定。
