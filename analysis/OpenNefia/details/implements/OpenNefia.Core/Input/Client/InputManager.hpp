#pragma once

#include "IInputManager.hpp"
#include <unordered_map>

namespace OpenNefia::Core::Input {

class InputManager : public IInputManager {
private:
    std::unordered_map<Keyboard::Key, std::vector<BoundKeyFunction>> _keyBindings;

public:
    InputManager() = default;
    virtual ~InputManager() = default;

    void Initialize() override;
    void Shutdown() override;

    ScreenCoordinates GetMouseScreenPosition() const override;

    std::string GetKeyFunctionButtonString(const BoundKeyFunction& function) override;
    
    void HaltInput() override;
    
    void ViewportKeyEvent(IUiElement* viewport, const BoundKeyEventArgs& args) override;

    // Implementation methods
    void KeyDown(Keyboard::Key key);
    void KeyUp(Keyboard::Key key);

private:
    bool TriggerKeyBind(const BoundKeyEventArgs& args);
};

} // namespace OpenNefia::Core::Input
