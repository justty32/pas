#include "RaylibGraphics.hpp"
#include <iostream>

namespace OpenNefia::Core::Graphics {

void RaylibGraphics::Initialize() {
    // These should ideally come from CVars resolved via IoC
    int width = 800;
    int height = 600;
    std::string title = "OpenNefia C++";

    ::InitWindow(width, height, title.c_str());
    ::SetTargetFPS(60);
}

void RaylibGraphics::Shutdown() {
    ::CloseWindow();
}

void RaylibGraphics::ShowSplashScreen() {
    // Placeholder
}

void RaylibGraphics::BeginDraw() {
    ::BeginDrawing();
    ::ClearBackground(BLACK);
}

void RaylibGraphics::EndDraw() {
    ::EndDrawing();
}

int RaylibGraphics::GetDisplayCount() {
    return ::GetMonitorCount();
}

std::string RaylibGraphics::GetDisplayName(int displayIndex) {
    return ::GetMonitorName(displayIndex);
}

void RaylibGraphics::SetWindowSettings(WindowMode mode, Vector2i size) {
    ::SetWindowSize(size.X, size.Y);
    if (mode == WindowMode::Fullscreen) {
        if (!::IsWindowFullscreen()) ::ToggleFullscreen();
    } else {
        if (::IsWindowFullscreen()) ::ToggleFullscreen();
    }
}

} // namespace OpenNefia::Core::Graphics
