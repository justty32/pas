#include "UserInterfaceManager.hpp"
#include "../Graphics/IGraphics.hpp"
#include "../IoC/IoCManager.hpp"
#include <stdexcept>

namespace OpenNefia::Core::UserInterface {

using namespace OpenNefia::Core::IoC;
using namespace OpenNefia::Core::Graphics;

void UserInterfaceManager::Initialize() {
    // In C#, this binds events from IInputManager and IGraphics.
    // In C++, we might do similar or handle it in GameController.
}

void UserInterfaceManager::Shutdown() {
    while (!_layers.empty()) {
        PopLayer(_layers.back());
    }
}

void UserInterfaceManager::GrabKeyboardFocus(UiElement* control) {
    if (control == nullptr) throw std::invalid_argument("control");
    // Simplified logic
    if (_keyboardFocused == control) return;
    ReleaseKeyboardFocus();
    _keyboardFocused = control;
    // control->KeyboardFocusEntered(); // Call when ported
}

void UserInterfaceManager::ReleaseKeyboardFocus() {
    if (_keyboardFocused) {
        // _keyboardFocused->KeyboardFocusExited(); // Call when ported
        _keyboardFocused = nullptr;
    }
}

void UserInterfaceManager::ReleaseKeyboardFocus(UiElement* ifControl) {
    if (ifControl == _keyboardFocused) {
        ReleaseKeyboardFocus();
    }
}

void UserInterfaceManager::UpdateLayers(const FrameEventArgs& frame) {
    for (auto layer : _layers) {
        layer->Update(frame.Elapsed);
    }
}

void UserInterfaceManager::DrawLayers() {
    for (auto layer : _layersByZOrder) {
        layer->Draw();
    }
}

void UserInterfaceManager::PushLayer(UiLayer* layer) {
    auto& graphics = IoCManager::Resolve<IGraphics>();
    // layer->LayerUIScale = graphics.GetWindowScale();
    ResizeAndLayoutLayer(layer);
    _layers.push_back(layer);
    SortLayers();

    // layer->GrabFocus();
}

void UserInterfaceManager::PopLayer(UiLayer* layer) {
    auto it = std::find(_layers.begin(), _layers.end(), layer);
    if (it != _layers.end()) {
        _layers.erase(it);
        SortLayers();
    }
}

bool UserInterfaceManager::IsQuerying(UiLayer* layer) const {
    return !_layers.empty() && GetCurrentLayer() == layer;
}

bool UserInterfaceManager::IsInActiveLayerList(UiLayer* layer) const {
    return std::find(_layers.begin(), _layers.end(), layer) != _layers.end();
}

void UserInterfaceManager::ControlRemovedFromTree(UiElement* control) {
    ReleaseKeyboardFocus(control);
    if (control == _currentlyHovered) _currentlyHovered = nullptr;
    if (control == _controlFocused) _controlFocused = nullptr;
}

void UserInterfaceManager::SortLayers() {
    _layersByZOrder = _layers;
    std::sort(_layersByZOrder.begin(), _layersByZOrder.end(), [](UiLayer* a, UiLayer* b) {
        return a->GetZOrder() < b->GetZOrder();
    });
}

void UserInterfaceManager::ResizeAndLayoutLayer(UiLayer* layer) {
    UIBox2 bounds;
    layer->GetPreferredBounds(bounds);
    layer->SetSize(bounds.Width(), bounds.Height());
    layer->SetPosition(bounds.Left, bounds.Top);
}

} // namespace OpenNefia::Core::UserInterface
