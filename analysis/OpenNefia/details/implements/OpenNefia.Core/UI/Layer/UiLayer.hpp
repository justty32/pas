#pragma once

#include "../Element/UiElement.hpp"
#include "IUiLayer.hpp"

namespace OpenNefia::Core::UI::Layer {

class UiLayer : public OpenNefia::Core::UI::Element::UiElement, public virtual IUiLayer {
public:
    float LayerUIScale = 1.0f;
    int ZOrder = 0;

    UiLayer();
    virtual ~UiLayer() = default;

    float GetUIScale() const override { return LayerUIScale; }
    int GetZOrder() const override { return ZOrder; }
    void SetZOrder(int value) override { ZOrder = value; }

    void GetPreferredBounds(UIBox2& bounds) override;
    void GetPreferredPosition(Vector2& pos) override;
    void SetPreferredPosition() override;

    bool IsInActiveLayerList() const override;
    bool IsQuerying() const override;

    void OnQuery() override {}
    void OnQueryFinish() override {}

    void Localize() override;
    void Localize(const LocaleKey& key) override { OpenNefia::Core::UI::Element::UiElement::Localize(key); }
};

} // namespace OpenNefia::Core::UI::Layer
