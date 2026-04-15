#pragma once

#include <memory>
#include <vector>
#include "Layer/IUiLayer.hpp"
#include "../Timing/FrameEventArgs.hpp"

namespace OpenNefia::Core::UserInterface {

using namespace OpenNefia::Core::UI::Layer;
using namespace OpenNefia::Core::UI::Element;

class IUserInterfaceManager {
public:
    virtual ~IUserInterfaceManager() = default;

    virtual UiElement* GetKeyboardFocused() const = 0;
    virtual UiElement* GetControlFocused() const = 0;
    virtual void SetControlFocused(UiElement* value) = 0;

    virtual const std::vector<UiLayer*>& GetActiveLayers() const = 0;
    virtual UiLayer* GetCurrentLayer() const = 0;

    virtual void GrabKeyboardFocus(UiElement* control) = 0;
    virtual void ReleaseKeyboardFocus(UiElement* control) = 0;

    virtual void DrawLayers() = 0;
    virtual bool IsQuerying(UiLayer* layer) const = 0;
    virtual void PopLayer(UiLayer* layer) = 0;
    virtual void PushLayer(UiLayer* layer) = 0;
    virtual void UpdateLayers(const FrameEventArgs& frame) = 0;
    virtual bool IsInActiveLayerList(UiLayer* layer) const = 0;
};

} // namespace OpenNefia::Core::UserInterface
