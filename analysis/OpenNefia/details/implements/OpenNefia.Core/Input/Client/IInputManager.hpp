#pragma once

#include <string>
#include <functional>
#include <vector>
#include "../BoundKeyFunction.hpp"
#include "../BoundKeyEventArgs.hpp"
#include "../../UI/Element/IUiElement.hpp"

namespace OpenNefia::Core::Input {

using namespace OpenNefia::Core::UI::Element;

class IInputManager {
public:
    virtual ~IInputManager() = default;

    virtual void Initialize() = 0;
    virtual void Shutdown() = 0;

    virtual ScreenCoordinates GetMouseScreenPosition() const = 0;

    // Events
    std::function<bool(const BoundKeyEventArgs&)> UIKeyBindStateChanged;

    virtual std::string GetKeyFunctionButtonString(const BoundKeyFunction& function) = 0;
    
    virtual void HaltInput() = 0;
    
    // Viewport events (from IInputManager.cs)
    virtual void ViewportKeyEvent(IUiElement* viewport, const BoundKeyEventArgs& args) = 0;
};

} // namespace OpenNefia::Core::Input
