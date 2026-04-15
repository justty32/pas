#pragma once

#include <vector>
#include <string>
#include <functional>
#include <optional>
#include "../Maths/Vector2.hpp"
#include "../Maths/Vector2i.hpp"
#include "WindowMode.hpp"

namespace OpenNefia::Core::Graphics {

using namespace OpenNefia::Core::Maths;

struct FullscreenMode {
    int Width;
    int Height;

    constexpr FullscreenMode(int w, int h) : Width(w), Height(h) {}
    
    operator Vector2i() const { return {Width, Height}; }
};

// Event arguments (simplified placeholders)
struct WindowResizedEventArgs { Vector2i NewSize; };
struct QuitEventArgs {};

class IGraphics {
public:
    virtual ~IGraphics() = default;

    virtual float GetWindowScale() const = 0;
    virtual Vector2 GetWindowSize() const = 0;
    virtual Vector2i GetWindowPixelSize() const = 0;

    // Events (using std::function for simplicity in this port)
    std::function<void(const WindowResizedEventArgs&)> OnWindowResized;
    std::function<bool(const QuitEventArgs&)> OnQuit;
    // ... other events can be added similarly

    virtual void Initialize() = 0;
    virtual void Shutdown() = 0;
    virtual void ShowSplashScreen() = 0;

    virtual void BeginDraw() = 0;
    virtual void EndDraw() = 0;

    virtual int GetDisplayCount() = 0;
    virtual std::string GetDisplayName(int displayIndex) = 0;
    
    // Window settings (placeholders for now)
    virtual void SetWindowSettings(WindowMode mode, Vector2i size) = 0;
};

} // namespace OpenNefia::Core::Graphics
