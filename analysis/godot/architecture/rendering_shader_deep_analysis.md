# Godot Shader 系統深度架構分析 - Level 3 & 5

Godot 的著色器系統旨在提供高效的跨平台渲染能力，同時保持開發者的易用性。

## 1. 核心組成與資料流
著色器在 Godot 中被視為資源 (`Shader`)，而具體的參數配置則儲存在材質 (`Material`) 中。

### 1.1 RenderingServer 的角色
- **資源標記**：所有的著色器與材質在底層都由 `RID` 標記。
- **狀態同步**：當您在 C++ 中呼叫 `mat->set_shader_parameter()` 時，該請求會被排入 `RenderingServer` 的指令隊列中，並在下一個渲染影格同步到 GPU。
- **後端適配**：`RenderingServer` 會根據當前啟動的渲染器（如 Forward+, Mobile, Compatibility）將 Godot Shading Language (相似於 GLSL) 編譯為對應的 SPIR-V 或 MSL 代碼。

## 2. 材質類型與階層
- **`CanvasItemMaterial`**：用於 2D 渲染，支援混合模式 (Blend Mode) 與光照模式。
- **`ShaderMaterial`**：最靈活的材質，允許載入自定義的 `.gdshader` 檔案。
- **`StandardMaterial3D`**：高階封裝的 PBR 材質，內部會自動生成複雜的著色器代碼。

## 3. 互動式著色器 (Interactive Shaders)
Godot 實現互動特效的核心模式是 **「屬性驅動」**：
1. **定義 Uniform**：在 Shader 中定義 `uniform float hover_intensity;`。
2. **事件監聽**：節點監聽系統通知（如滑鼠事件、血量變化）。
3. **動態更新**：透過 `set_shader_parameter()` 實時修改 Uniform。

## 4. 效能考量
- **Shader 變體 (Variants)**：頻繁切換 Shader 可能導致渲染狀態切換 (State Switch) 的開銷。
- **Uniform 批次更新**：對於大量物件共享的參數，應使用全域著色器參數 (`RenderingServer::global_shader_parameter_set`)。

---
*檔案參考：`servers/rendering/rendering_server.h`, `scene/resources/shader.h`, `scene/main/canvas_item.cpp`*
