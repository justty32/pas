# 04 - 渲染與使用者介面 (Graphics & UI)

我們將原本基於 Love2D 的渲染系統改為 raylib。

## 4.1 raylib 渲染後端 (Graphics)

對應 `OpenNefia.Core.Graphics`。

- **初始化**: 呼叫 `InitWindow` 與 `InitAudioDevice`。
- **紋理管理 (AssetManager)**: 使用 `LoadTexture` 並將結果快取在 `AssetManager` 中。
- **渲染指令**: 
    - 封裝為 `Graphics` 類別 API。
    - 支援 `DrawTextureRec`, `DrawTextEx` 等。

## 4.2 磁磚渲染器 (MapRenderer)

對應 `OpenNefia.Core.Rendering.MapRenderer`。

OpenNefia 使用分層渲染 (TileLayers)：
- **TileLayer**: 底層地面磁磚。
- **EntityLayer**: 實體（角色、物品）。
- **FovLayer**: 視野與陰影。

**C++ 實作建議：**
- 使用 `RenderTexture` (raylib) 緩存靜態地圖層，減少每幀的繪製次數。
- 在 `EntityLayer` 中根據 `DrawDepth` 對實體進行排序。

## 4.3 UI 系統 (UserInterface)

對應 `OpenNefia.Core.UserInterface` 與 `OpenNefia.Core.UI`。

OpenNefia 的 UI 是基於層 (Layer) 的堆疊系統：
- **UIManager**: 管理 `LayerStack`。
- **UiLayer**: 基礎類別，包含 `Update`, `Draw` 與輸入處理。

```cpp
// src/core/ui/UiLayer.hpp
class UiLayer {
public:
    virtual void OnOpen() {}
    virtual void OnClose() {}
    virtual void Update(float dt) {}
    virtual void Draw() {}
    virtual void OnKey(int key, bool pressed) {}
};
```

## 4.4 輸入管理 (InputManager)

對應 `OpenNefia.Core.Input`。

- **Action Bindings**: 將實體按鍵 (如 `KEY_W`) 映射為動作 (如 `ActionMoveUp`)。
- **Contexts**: 在不同 UI 模式下切換按鍵上下文。

## 4.5 字型管理 (FontManager)

對應 `OpenNefia.Core.Rendering.FontManager`。

- 使用 raylib 的 `LoadFontEx` 載入字體。
- 支援中、日、英文字符集 (Glyphs)。
- 封裝 `UiText` 組件，處理自動斷行與顏色標籤。
