#pragma once

#include "IDrawable.hpp"

namespace OpenNefia::Core::UI::Element {

class BaseDrawable : public virtual IDrawable {
public:
    Vector2 Size;
    Vector2 Position;

    Vector2 GetSize() const override { return Size; }
    Vector2 GetPosition() const override { return Position; }
    virtual float GetUIScale() const override { return 1.0f; }

    void SetSize(float width, float height) override {
        Size = {width, height};
    }

    void SetPosition(float x, float y) override {
        Position = {x, y};
    }

    bool ContainsPoint(Vector2 point) const override {
        return UIBox2::FromDimensions(Position, Size).Contains(point);
    }

    virtual void Update(float dt) override = 0;
    virtual void Draw() override = 0;
};

} // namespace OpenNefia::Core::UI::Element
