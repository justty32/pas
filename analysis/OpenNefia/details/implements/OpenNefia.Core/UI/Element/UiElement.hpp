#pragma once

#include "BaseDrawable.hpp"
#include "IUiElement.hpp"
#include "../../Locale/ILocalizable.hpp"
#include "../IUiInput.hpp"
#include <vector>
#include <memory>

namespace OpenNefia::Core::UI::Layer { class UiLayer; }

namespace OpenNefia::Core::UI::Element {

using namespace OpenNefia::Core::Locale;

class UiElement : public BaseDrawable, public virtual IUiElement, public virtual ILocalizable, public virtual IUiInput {
public:
    float MinWidth = 0.0f;
    float MinHeight = 0.0f;
    float PreferredWidth = NAN;
    float PreferredHeight = NAN;
    
    UiElement* Parent = nullptr;
    std::vector<std::unique_ptr<UiElement>> Children;
    OpenNefia::Core::UI::Layer::UiLayer* Root = nullptr;

    UiElement();
    virtual ~UiElement() = default;

    float GetUIScale() const override;

    Vector2 GetPreferredSize() const override { return {PreferredWidth, PreferredHeight}; }
    void SetPreferredSize(Vector2 size) override { PreferredWidth = size.X; PreferredHeight = size.Y; }
    
    void GetPreferredSize(Vector2& size) const override;
    void SetPreferredSize() override;

    void Localize(const LocaleKey& key) override;
    std::vector<UiKeyHint> MakeKeyHints() override { return {}; }

    void Update(float dt) override {}
    void Draw() override {}

    void AddChild(std::unique_ptr<UiElement> child);
};

} // namespace OpenNefia::Core::UI::Element
