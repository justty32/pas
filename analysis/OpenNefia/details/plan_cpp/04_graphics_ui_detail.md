# 04 - 渲染與 UI 實作細節 (Graphics & UI Detail)

## 4.1 raylib 渲染層 (Graphics)

封裝 raylib 的常用繪製方法。

```cpp
// src/core/graphics/Graphics.hpp
#include <raylib.h>

class Graphics {
public:
    void Initialize(int width, int height, const std::string& title);
    void Shutdown();

    void BeginDraw();
    void EndDraw();

    void DrawTexture(const Texture2D& tex, float x, float y, Color tint = WHITE);
    void DrawRectangle(float x, float y, float w, float h, Color color);
    
    // 文字渲染
    void DrawText(const Font& font, const std::string& text, Vector2 pos, float fontSize, Color tint = BLACK);
};
```

## 4.2 資源管理 (AssetManager)

對應 `OpenNefia.Core.ResourceManagement` 與 `AssetManager`。

```cpp
// src/core/resources/AssetManager.hpp
class AssetManager {
public:
    // 快取紋理、字體與音效
    Texture2D& GetTexture(const std::string& logicalPath);
    Font& GetFont(const std::string& logicalPath);
    Sound& GetSound(const std::string& logicalPath);

    // 釋放所有快取
    void Clear();

private:
    std::unordered_map<std::string, Texture2D> _textures;
    std::unordered_map<std::string, Font> _fonts;
    std::unordered_map<std::string, Sound> _sounds;
};
```

## 4.3 UI 層堆疊 (UIManager)

這是 UI 系統的核心。對應 `OpenNefia.Core.UserInterface.UserInterfaceManager`。

```cpp
// src/core/ui/UiLayer.hpp
class UiLayer {
public:
    virtual ~UiLayer() = default;
    virtual void OnOpen() {}
    virtual void OnClose() {}
    virtual void Update(float dt) = 0;
    virtual void Draw() = 0;
    
    // 事件處理
    virtual bool OnEvent(const SDL_Event& event) { return false; } // raylib 可以直接用 GetKeyPressed()
};

// src/core/ui/UIManager.hpp
class UIManager {
public:
    void PushLayer(std::unique_ptr<UiLayer> layer) {
        layer->OnOpen();
        _layers.push_back(std::move(layer));
    }

    void PopLayer() {
        if (!_layers.empty()) {
            _layers.back()->OnClose();
            _layers.pop_back();
        }
    }

    void Update(float dt) {
        if (_layers.empty()) return;
        _layers.back()->Update(dt); // 只有頂層 Layer 接收 Update
    }

    void Draw() {
        for (auto& layer : _layers) {
            layer->Draw(); // 所有 Layer 依序繪製 (底層到頂層)
        }
    }

private:
    std::vector<std::unique_ptr<UiLayer>> _layers;
};
```

## 4.4 輸入綁定 (InputManager)

對應 `OpenNefia.Core.Input.InputManager`。

```cpp
// src/core/input/InputManager.hpp
enum class Action {
    MoveUp, MoveDown, MoveLeft, MoveRight,
    Confirm, Cancel, OpenInventory
};

class InputManager {
public:
    // 將 raylib 的 KEY 映射至邏輯 Action
    void BindKey(int raylibKey, Action action);
    
    // 檢查本幀 Action 是否觸發
    bool IsActionTriggered(Action action);

private:
    std::unordered_map<int, Action> _keyBinds;
};
```

## 4.5 遊戲控制器 (GameController) 主循環整合

```cpp
// src/core/GameController.cpp
void GameController::Run() {
    auto& ui = ServiceLocator::Resolve<IUIManager>();
    auto& graphics = ServiceLocator::Resolve<IGraphics>();

    while (!WindowShouldClose()) {
        float dt = GetFrameTime();

        // 1. 更新 UI (邏輯)
        ui.Update(dt);

        // 2. 繪製
        graphics.BeginDraw();
        ui.Draw();
        graphics.EndDraw();
    }
}
```
