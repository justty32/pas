#pragma once

#include <cmath>
#include "Vector2i.hpp"

namespace OpenNefia::Core::Maths {

struct Vector2 {
    float X;
    float Y;

    constexpr Vector2() : X(0.0f), Y(0.0f) {}
    constexpr Vector2(float x, float y) : X(x), Y(y) {}
    Vector2(const Vector2i& other) : X((float)other.X), Y((float)other.Y) {}

    static constexpr Vector2 Zero() { return {0.0f, 0.0f}; }
    static constexpr Vector2 One() { return {1.0f, 1.0f}; }

    bool operator==(const Vector2& other) const {
        return X == other.X && Y == other.Y;
    }

    bool operator!=(const Vector2& other) const {
        return !(*this == other);
    }

    Vector2 operator+(const Vector2& other) const {
        return {X + other.X, Y + other.Y};
    }

    Vector2 operator-(const Vector2& other) const {
        return {X - other.X, Y - other.Y};
    }

    Vector2 operator*(float scalar) const {
        return {X * scalar, Y * scalar};
    }

    Vector2 operator/(float scalar) const {
        return {X / scalar, Y / scalar};
    }

    float Length() const {
        return std::sqrt(X * X + Y * Y);
    }
};

} // namespace OpenNefia::Core::Maths
