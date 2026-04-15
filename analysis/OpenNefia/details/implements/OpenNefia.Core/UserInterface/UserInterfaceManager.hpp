#pragma once

#include "IUserInterfaceManager.hpp"
#include <vector>
#include <memory>
#include <algorithm>

namespace OpenNefia::Core::UserInterface {

class UserInterfaceManager : public IUserInterfaceManager {
private:
    std::vector<UiLayer*> _layers;
    std::vector<UiLayer*> _layersByZOrder;
    UiElement* _keyboardFocused = nullptr;
    UiElement* _controlFocused = nullptr;
    UiElement* _currentlyHovered = nullptr;

public:
    UserInterfaceManager() = default;
    virtual ~UserInterfaceManager() = default;

    void Initialize();
    void Shutdown();

    UiElement* GetKeyboardFocused() const override { return _keyboardFocused; }
    UiElement* GetControlFocused() const override { return _controlFocused; }
    void SetControlFocused(UiElement* value) override { _controlFocused = value; }

    const std::vector<UiLayer*>& GetActiveLayers() const override { return _layers; }
    UiLayer* GetCurrentLayer() const override {
        return _layers.empty() ? nullptr : _layers.back();
    }

    void GrabKeyboardFocus(UiElement* control) override;
    void ReleaseKeyboardFocus(UiElement* control) override;
    void ReleaseKeyboardFocus();

    void DrawLayers() override;
    bool IsQuerying(UiLayer* layer) const override;
    void PopLayer(UiLayer* layer) override;
    void PushLayer(UiLayer* layer) override;
    void UpdateLayers(const FrameEventArgs& frame) override;
    bool IsInActiveLayerList(UiLayer* layer) const override;

    void ControlRemovedFromTree(UiElement* control);

private:
    void SortLayers();
    static void ResizeAndLayoutLayer(UiLayer* layer);
};

} // namespace OpenNefia::Core::UserInterface
