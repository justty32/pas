#pragma once

#include <cmath>

namespace OpenNefia::Core::Maths {

struct Vector2i {
    int X;
    int Y;

    constexpr Vector2i() : X(0), Y(0) {}
    constexpr Vector2i(int x, int y) : X(x), Y(y) {}

    static constexpr Vector2i Zero() { return {0, 0}; }
    static constexpr Vector2i One() { return {1, 1}; }

    bool operator==(const Vector2i& other) const {
        return X == other.X && Y == other.Y;
    }

    bool operator!=(const Vector2i& other) const {
        return !(*this == other);
    }

    Vector2i operator+(const Vector2i& other) const {
        return {X + other.X, Y + other.Y};
    }

    Vector2i operator-(const Vector2i& other) const {
        return {X - other.X, Y - other.Y};
    }

    Vector2i operator*(int scalar) const {
        return {X * scalar, Y * scalar};
    }

    Vector2i operator/(int scalar) const {
        return {X / scalar, Y / scalar};
    }
};

} // namespace OpenNefia::Core::Maths
