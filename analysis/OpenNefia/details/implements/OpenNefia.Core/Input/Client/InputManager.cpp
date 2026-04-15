#include "InputManager.hpp"
#include "../../IoC/IoCManager.hpp"
#include "../../Graphics/IGraphics.hpp"
#include <raylib.h>

namespace OpenNefia::Core::Input {

using namespace OpenNefia::Core::IoC;
using namespace OpenNefia::Core::Graphics;

void InputManager::Initialize() {
    // Porting key names and binding logic...
}

void InputManager::Shutdown() {
}

ScreenCoordinates InputManager::GetMouseScreenPosition() const {
    auto pos = ::GetMousePosition();
    return ScreenCoordinates(pos.x, pos.y);
}

std::string InputManager::GetKeyFunctionButtonString(const BoundKeyFunction& function) {
    return "???";
}

void InputManager::HaltInput() {
    // Reset key states
}

void InputManager::ViewportKeyEvent(IUiElement* viewport, const BoundKeyEventArgs& args) {
    // Handle viewport-specific input
}

void InputManager::KeyDown(Keyboard::Key key) {
    auto it = _keyBindings.find(key);
    if (it != _keyBindings.end()) {
        for (const auto& func : it->second) {
            BoundKeyEventArgs args(func, BoundKeyState::Down, GetMouseScreenPosition(), true);
            TriggerKeyBind(args);
        }
    }
}

void InputManager::KeyUp(Keyboard::Key key) {
    auto it = _keyBindings.find(key);
    if (it != _keyBindings.end()) {
        for (const auto& func : it->second) {
            BoundKeyEventArgs args(func, BoundKeyState::Up, GetMouseScreenPosition(), true);
            TriggerKeyBind(args);
        }
    }
}

bool InputManager::TriggerKeyBind(const BoundKeyEventArgs& args) {
    if (UIKeyBindStateChanged) {
        return UIKeyBindStateChanged(args);
    }
    return false;
}

} // namespace OpenNefia::Core::Input
