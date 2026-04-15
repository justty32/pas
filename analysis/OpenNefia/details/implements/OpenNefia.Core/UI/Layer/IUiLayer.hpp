#pragma once

#include "../Element/IUiElement.hpp"
#include "../../Locale/ILocalizable.hpp"
#include "../../Maths/UIBox2.hpp"

namespace OpenNefia::Core::UI::Layer {

using namespace OpenNefia::Core::UI::Element;
using namespace OpenNefia::Core::Locale;
using namespace OpenNefia::Core::Maths;

class IUiLayer : public virtual IUiElement, public virtual ILocalizable {
public:
    virtual ~IUiLayer() = default;

    virtual int GetZOrder() const = 0;
    virtual void SetZOrder(int value) = 0;

    virtual void GetPreferredBounds(UIBox2& bounds) = 0;
    virtual void GetPreferredPosition(Vector2& pos) = 0;
    virtual void SetPreferredPosition() = 0;

    virtual void OnQuery() = 0;
    virtual void OnQueryFinish() = 0;
    virtual bool IsQuerying() const = 0;
    virtual bool IsInActiveLayerList() const = 0;
    virtual void Localize() = 0;
};

} // namespace OpenNefia::Core::UI::Layer
