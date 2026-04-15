#pragma once

#include "IDrawable.hpp"

namespace OpenNefia::Core::UI::Element {

class IUiElement : public virtual IDrawable {
public:
    virtual ~IUiElement() = default;

    virtual Vector2 GetPreferredSize() const = 0;
    virtual void SetPreferredSize(Vector2 size) = 0;

    virtual void GetPreferredSize(Vector2& size) const = 0;
    virtual void SetPreferredSize() = 0;
};

} // namespace OpenNefia::Core::UI::Element
