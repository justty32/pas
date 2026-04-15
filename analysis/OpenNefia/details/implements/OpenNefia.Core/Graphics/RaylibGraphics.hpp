#pragma once

#include "IGraphics.hpp"
#include <raylib.h>

namespace OpenNefia::Core::Graphics {

class RaylibGraphics : public IGraphics {
private:
    float _windowScale = 1.0f;

public:
    RaylibGraphics() = default;
    virtual ~RaylibGraphics() = default;

    float GetWindowScale() const override { return _windowScale; }
    Vector2 GetWindowSize() const override { 
        return { (float)GetScreenWidth() / _windowScale, (float)GetScreenHeight() / _windowScale };
    }
    Vector2i GetWindowPixelSize() const override {
        return { GetScreenWidth(), GetScreenHeight() };
    }

    void Initialize() override;
    void Shutdown() override;
    void ShowSplashScreen() override;

    void BeginDraw() override;
    void EndDraw() override;

    int GetDisplayCount() override;
    std::string GetDisplayName(int displayIndex) override;
    
    void SetWindowSettings(WindowMode mode, Vector2i size) override;
};

} // namespace OpenNefia::Core::Graphics
