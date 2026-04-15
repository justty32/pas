#pragma once

#include "Vector2i.hpp"

namespace OpenNefia::Core::Maths {

struct UIBox2i {
    int Left;
    int Top;
    int Right;
    int Bottom;

    constexpr UIBox2i() : Left(0), Top(0), Right(0), Bottom(0) {}
    constexpr UIBox2i(int left, int top, int right, int bottom)
        : Left(left), Top(top), Right(right), Bottom(bottom) {}
    constexpr UIBox2i(Vector2i topLeft, Vector2i bottomRight)
        : Left(topLeft.X), Top(topLeft.Y), Right(bottomRight.X), Bottom(bottomRight.Y) {}

    static constexpr UIBox2i FromDimensions(Vector2i pos, Vector2i size) {
        return UIBox2i(pos.X, pos.Y, pos.X + size.X, pos.Y + size.Y);
    }

    int Width() const { return Right - Left; }
    int Height() const { return Bottom - Top; }
    Vector2i Size() const { return {Width(), Height()}; }
};

} // namespace OpenNefia::Core::Maths
