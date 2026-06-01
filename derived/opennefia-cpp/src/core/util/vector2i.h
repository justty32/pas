#pragma once

namespace opennefia {

struct Vector2i {
    int x{}, y{};

    Vector2i() = default;
    constexpr Vector2i(int x, int y) : x(x), y(y) {}

    constexpr Vector2i operator+(const Vector2i& o) const { return {x + o.x, y + o.y}; }
    constexpr Vector2i operator-(const Vector2i& o) const { return {x - o.x, y - o.y}; }
    constexpr Vector2i operator*(int s)             const { return {x * s, y * s}; }
    constexpr bool operator==(const Vector2i& o)    const { return x == o.x && y == o.y; }
    constexpr bool operator!=(const Vector2i& o)    const { return !(*this == o); }

    template<class Archive>
    void serialize(Archive& ar) { ar(x, y); }
};

} // namespace opennefia
