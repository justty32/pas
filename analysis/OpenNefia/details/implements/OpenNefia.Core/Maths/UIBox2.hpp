#pragma once

#include "Vector2.hpp"

namespace OpenNefia::Core::Maths {

struct UIBox2 {
    float Left;
    float Top;
    float Right;
    float Bottom;

    constexpr UIBox2() : Left(0), Top(0), Right(0), Bottom(0) {}
    constexpr UIBox2(float left, float top, float right, float bottom)
        : Left(left), Top(top), Right(right), Bottom(bottom) {}
    constexpr UIBox2(Vector2 topLeft, Vector2 bottomRight)
        : Left(topLeft.X), Top(topLeft.Y), Right(bottomRight.X), Bottom(bottomRight.Y) {}

    static constexpr UIBox2 FromDimensions(Vector2 pos, Vector2 size) {
        return UIBox2(pos.X, pos.Y, pos.X + size.X, pos.Y + size.Y);
    }

    float Width() const { return Right - Left; }
    float Height() const { return Bottom - Top; }
    Vector2 Size() const { return {Width(), Height()}; }
    Vector2 TopLeft() const { return {Left, Top}; }

    bool Contains(Vector2 point) const {
        return point.X >= Left && point.X < Right && point.Y >= Top && point.Y < Bottom;
    }
};

} // namespace OpenNefia::Core::Maths
