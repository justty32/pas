#pragma once

#include "../../Maths/Vector2.hpp"
#include "../../Maths/Vector2i.hpp"
#include "../../Maths/UIBox2.hpp"
#include "../../Maths/UIBox2i.hpp"

namespace OpenNefia::Core::UI::Element {

using namespace OpenNefia::Core::Maths;

class IDrawable {
public:
    virtual ~IDrawable() = default;

    virtual Vector2 GetSize() const = 0;
    virtual Vector2 GetPosition() const = 0;
    virtual float GetUIScale() const = 0;

    virtual void SetSize(float width, float height) = 0;
    virtual void SetPosition(float x, float y) = 0;

    virtual void Update(float dt) = 0;
    virtual void Draw() = 0;

    virtual bool ContainsPoint(Vector2 point) const = 0;
};

} // namespace OpenNefia::Core::UI::Element
