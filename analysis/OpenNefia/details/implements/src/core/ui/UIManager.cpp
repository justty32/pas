#include <core/ui/UIManager.hpp>

namespace opennefia {
namespace core {

void UIManager::Shutdown() {
    while (!_layers.empty()) {
        PopLayer();
    }
}

void UIManager::PushLayer(std::unique_ptr<UiLayer> layer) {
    layer->OnOpen();
    _layers.push_back(std::move(layer));
}

void UIManager::PopLayer() {
    if (!_layers.empty()) {
        _layers.back()->OnClose();
        _layers.pop_back();
    }
}

void UIManager::Update(float dt) {
    if (_layers.empty()) return;

    // 只有最上層的 Layer 接收更新
    _layers.back()->Update(dt);
}

void UIManager::Draw() {
    if (_layers.empty()) return;

    // 找出最上層的不透明層
    size_t firstToDraw = 0;
    for (int i = (int)_layers.size() - 1; i >= 0; --i) {
        if (_layers[i]->IsOpaque()) {
            firstToDraw = i;
            break;
        }
    }

    // 從該層開始依序繪製到最頂層
    for (size_t i = firstToDraw; i < _layers.size(); ++i) {
        _layers[i]->Draw();
    }
}

} // namespace core
} // namespace opennefia
